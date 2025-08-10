from dataclasses import dataclass
from typing import List, Optional
import os
import tempfile
import requests
import ffmpeg
from ..utils.logger import get_logger
from ..utils.validators import (
    validate_file_path,
    validate_metadata,
    validate_input,
    is_url,
    is_hls_url,
    ValidationError,
)
from ..utils.download_cache import get_download_cache
from .hls_downloader import HLSDownloader


@dataclass
class VideoMetadata:
    """Video metadata"""
    file_path: str
    duration: float          # duration (seconds)
    file_size: int          # file size (bytes)
    format_name: str        # container format
    bit_rate: int           # overall bitrate (bps)
    
    # Video stream info
    video_codec: str        # video codec
    width: int             # width
    height: int            # height
    fps: float             # frames per second
    video_bitrate: int     # video bitrate (bps)
    
    # Audio stream info
    audio_codec: str       # audio codec
    channels: int          # channels
    sample_rate: int       # sample rate
    audio_bitrate: int     # audio bitrate (bps)
    
    # Source info
    original_url: Optional[str] = None  # Original URL if downloaded
    is_cached: bool = False             # Whether file is from cache


class ProcessedFile:
    """Processed video file object"""
    
    def __init__(self, file_path: str, original_url: Optional[str] = None, is_cached: bool = False):
        self.file_path = file_path
        self.original_url = original_url
        self.is_cached = is_cached
        self.metadata = None
    
    def load_metadata(self) -> VideoMetadata:
        """Load video metadata"""
        if self.metadata is None:
            self.metadata = self._extract_metadata()
        return self.metadata
    
    def _extract_metadata(self) -> VideoMetadata:
        """Extract video metadata"""
        try:
            probe = ffmpeg.probe(self.file_path)
            format_info = probe['format']
            
            # Find video and audio streams
            video_stream = None
            audio_stream = None
            
            for stream in probe['streams']:
                if stream['codec_type'] == 'video' and video_stream is None:
                    video_stream = stream
                elif stream['codec_type'] == 'audio' and audio_stream is None:
                    audio_stream = stream
            
            return VideoMetadata(
                file_path=self.file_path,
                duration=float(format_info.get('duration', 0)),
                file_size=int(format_info.get('size', 0)),
                format_name=format_info.get('format_name', 'unknown'),
                bit_rate=int(format_info.get('bit_rate', 0)),
                
                # Video stream info
                video_codec=video_stream['codec_name'] if video_stream else '',
                width=video_stream.get('width', 0) if video_stream else 0,
                height=video_stream.get('height', 0) if video_stream else 0,
                fps=self._parse_fps(video_stream) if video_stream else 0.0,
                video_bitrate=int(video_stream.get('bit_rate', 0)) if video_stream else 0,
                
                # Audio stream info
                audio_codec=audio_stream['codec_name'] if audio_stream else '',
                channels=audio_stream.get('channels', 0) if audio_stream else 0,
                sample_rate=audio_stream.get('sample_rate', 0) if audio_stream else 0,
                audio_bitrate=int(audio_stream.get('bit_rate', 0)) if audio_stream else 0,
                
                # Source info
                original_url=self.original_url,
                is_cached=self.is_cached,
            )
            
        except ffmpeg.Error as e:
            # Try to fix common HLS/fMP4 issues before giving up
            stderr = e.stderr.decode('utf-8') if e.stderr else ''
            
            if 'could not find corresponding trex' in stderr or 'trun track id unknown' in stderr:
                # Try fixing fMP4 format issues
                if self._attempt_file_fix():
                    try:
                        # Retry probe after fixing
                        probe = ffmpeg.probe(self.file_path)
                        format_info = probe['format']
                        
                        # Find video and audio streams
                        video_stream = None
                        audio_stream = None
                        
                        for stream in probe['streams']:
                            if stream['codec_type'] == 'video' and video_stream is None:
                                video_stream = stream
                            elif stream['codec_type'] == 'audio' and audio_stream is None:
                                audio_stream = stream
                        
                        return VideoMetadata(
                            file_path=self.file_path,
                            duration=float(format_info['duration']),
                            file_size=int(format_info['size']),
                            format_name=format_info['format_name'],
                            bit_rate=int(format_info.get('bit_rate', 0)),
                            
                            # Video stream info
                            video_codec=video_stream['codec_name'] if video_stream else '',
                            width=video_stream.get('width', 0) if video_stream else 0,
                            height=video_stream.get('height', 0) if video_stream else 0,
                            fps=self._parse_fps(video_stream) if video_stream else 0.0,
                            video_bitrate=int(video_stream.get('bit_rate', 0)) if video_stream else 0,
                            
                            # Audio stream info
                            audio_codec=audio_stream['codec_name'] if audio_stream else '',
                            channels=audio_stream.get('channels', 0) if audio_stream else 0,
                            sample_rate=audio_stream.get('sample_rate', 0) if audio_stream else 0,
                            audio_bitrate=int(audio_stream.get('bit_rate', 0)) if audio_stream else 0,
                            
                            # Source info
                            original_url=self.original_url,
                            is_cached=self.is_cached,
                        )
                    except ffmpeg.Error:
                        pass
            
            raise ValueError(f"File format issue - FFmpeg probe failed: {e}")
    
    def _attempt_file_fix(self) -> bool:
        """Attempt to fix common HLS/fMP4 format issues"""
        try:
            import shutil
            from ..utils.logger import get_logger
            logger = get_logger(__name__)
            
            # Create a fixed version using FFmpeg
            fixed_path = self.file_path + '.fixed.mp4'
            
            # Try multiple fixing strategies
            strategies = [
                # Strategy 1: Simple remux with faststart
                lambda: (
                    ffmpeg
                    .input(self.file_path)
                    .output(fixed_path, c='copy', f='mp4', movflags='faststart')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                ),
                # Strategy 2: Force MP4 format with fragment fixing 
                lambda: (
                    ffmpeg
                    .input(self.file_path)
                    .output(fixed_path, c='copy', f='mp4', movflags='faststart+frag_keyframe', fflags='+genpts')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                ),
                # Strategy 3: Re-encode to fix corruption (slower but more reliable)
                lambda: (
                    ffmpeg
                    .input(self.file_path)
                    .output(fixed_path, vcodec='libx264', acodec='aac', crf=23, preset='medium', f='mp4', movflags='faststart')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
            ]
            
            for i, strategy in enumerate(strategies):
                try:
                    logger.info(f"Trying file fix strategy {i+1}/3...")
                    strategy()
                    
                    # Verify the fixed file is readable
                    try:
                        ffmpeg.probe(fixed_path)
                        # If probe succeeds, replace original
                        shutil.move(fixed_path, self.file_path)
                        logger.info(f"Successfully fixed file using strategy {i+1}")
                        return True
                    except ffmpeg.Error:
                        # Fixed file still has issues, try next strategy
                        if os.path.exists(fixed_path):
                            os.remove(fixed_path)
                        continue
                        
                except Exception as e:
                    logger.debug(f"Fix strategy {i+1} failed: {e}")
                    if os.path.exists(fixed_path):
                        try:
                            os.remove(fixed_path)
                        except:
                            pass
                    continue
            
            logger.warning("All file fix strategies failed")
            return False
            
        except Exception as e:
            # Clean up if fix failed
            fixed_path = self.file_path + '.fixed.mp4'
            if os.path.exists(fixed_path):
                try:
                    os.remove(fixed_path)
                except:
                    pass
            return False
    
    def _parse_fps(self, video_stream: dict) -> float:
        """Parse FPS value with fallback and validation"""
        # Try avg_frame_rate first (more accurate for VFR content)
        avg_fps_str = video_stream.get('avg_frame_rate', '')
        if avg_fps_str and avg_fps_str != '0/0':
            try:
                num, den = avg_fps_str.split('/')
                avg_fps = float(num) / float(den) if float(den) != 0 else 0.0
                # Validate reasonable range (0.1 to 240 fps)
                if 0.1 <= avg_fps <= 240:
                    return avg_fps
            except:
                pass
        
        # Fallback to r_frame_rate
        fps_str = video_stream.get('r_frame_rate', '0/1')
        try:
            num, den = fps_str.split('/')
            fps = float(num) / float(den) if float(den) != 0 else 0.0
            # Validate reasonable range (0.1 to 240 fps)
            if 0.1 <= fps <= 240:
                return fps
            else:
                return 0.0  # Invalid fps, return 0
        except:
            return 0.0


class FileProcessor:
    """File processor"""
    
    def __init__(self, use_cache: bool = True, max_workers: int = 10):
        """
        Initialize file processor
        
        Args:
            use_cache: Whether to use download cache
            max_workers: Maximum download threads for HLS
        """
        self.use_cache = use_cache
        self.max_workers = max_workers
        self.cache = get_download_cache() if use_cache else None
        self.hls_downloader = HLSDownloader(max_workers=max_workers)
        self.logger = get_logger(__name__)
    
    def process_input(self, input_path: str, force_download: bool = False) -> ProcessedFile:
        """
        Process input - can be local file, HTTP URL, or HLS stream
        
        Args:
            input_path: Local file path, HTTP URL, or HLS stream URL
            force_download: Force re-download even if cached
            
        Returns:
            ProcessedFile object
        """
        # Validate and determine input type
        input_type = validate_input(input_path)
        
        if input_type == 'file':
            # Local file - process directly
            processed_file = ProcessedFile(input_path)
        
        elif input_type == 'hls':
            # HLS stream - download first
            processed_file = self._process_hls_input(input_path, force_download)
        
        elif input_type == 'url':
            # HTTP URL - download first
            processed_file = self._process_url_input(input_path, force_download)
        
        else:
            raise ValidationError(f"Unsupported input type: {input_type}")
        
        # Load metadata to validate
        metadata = processed_file.load_metadata()
        
        # Validate video content
        validate_metadata(metadata)
        
        return processed_file
    
    def _process_hls_input(self, hls_url: str, force_download: bool = False) -> ProcessedFile:
        """Process HLS stream input"""
        self.logger.info(f"Processing HLS stream: {hls_url[:50]}...")
        
        # Check cache first (unless forced download)
        if self.use_cache and not force_download:
            cached_path = self.cache.get_cached_file(hls_url)
            if cached_path:
                self.logger.info("Using cached HLS file")
                return ProcessedFile(cached_path, original_url=hls_url, is_cached=True)
        
        # Download HLS stream
        self.logger.info("Downloading HLS stream...")
        download_result = self.hls_downloader.download_hls_stream(hls_url)
        
        if not download_result.success:
            raise ValidationError(f"HLS download failed: {download_result.error_message}")
        
        # Add to cache
        if self.use_cache and download_result.local_file_path:
            self.cache.add_to_cache(
                url=hls_url,
                file_path=download_result.local_file_path,
                duration=download_result.duration,
                format_name='mp4'
            )
        
        return ProcessedFile(
            download_result.local_file_path,
            original_url=hls_url,
            is_cached=False
        )
    
    def _process_url_input(self, url: str, force_download: bool = False) -> ProcessedFile:
        """Process HTTP URL input"""
        self.logger.info(f"Processing HTTP URL: {url[:50]}...")
        
        # Check cache first (unless forced download)
        if self.use_cache and not force_download:
            cached_path = self.cache.get_cached_file(url)
            if cached_path:
                self.logger.info("Using cached URL file")
                return ProcessedFile(cached_path, original_url=url, is_cached=True)
        
        # Download file
        local_path = self._download_http_file(url)
        
        # Add to cache
        if self.use_cache and local_path:
            self.cache.add_to_cache(url=url, file_path=local_path)
        
        return ProcessedFile(local_path, original_url=url, is_cached=False)
    
    def _download_http_file(self, url: str) -> str:
        """Download file from HTTP URL"""
        try:
            # Create temporary file
            import tempfile
            from urllib.parse import urlparse
            import os
            
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path) or 'video'
            if '.' not in filename:
                filename += '.mp4'  # Default extension
            
            temp_dir = tempfile.gettempdir()
            local_path = os.path.join(temp_dir, filename)
            
            # Download with progress
            from rich.progress import Progress, BarColumn, TextColumn, DownloadColumn
            from rich.console import Console
            
            console = Console()
            
            with requests.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    DownloadColumn(),
                    console=console
                ) as progress:
                    
                    download_task = progress.add_task("Downloading", total=total_size)
                    
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                progress.update(download_task, advance=len(chunk))
            
            self.logger.info(f"Downloaded to: {local_path}")
            return local_path
            
        except Exception as e:
            raise ValidationError(f"HTTP download failed: {e}")


class FileProcessingError(Exception):
    """Base file processing error"""
    pass


class InvalidFormatError(FileProcessingError):
    """Unsupported file format"""
    pass


class CorruptedFileError(FileProcessingError):
    """Corrupted file"""
    pass


def safe_process_file(input_path: str, force_download: bool = False, 
                      use_cache: bool = True, max_workers: int = 10) -> Optional[ProcessedFile]:
    """
    Safely process input - file, URL, or HLS stream
    
    Args:
        input_path: Local file path, HTTP URL, or HLS stream URL
        force_download: Force re-download even if cached
        use_cache: Whether to use download cache
        max_workers: Maximum download threads for HLS
        
    Returns:
        ProcessedFile if successful, None on error
    """
    try:
        processor = FileProcessor(use_cache=use_cache, max_workers=max_workers)
        return processor.process_input(input_path, force_download=force_download)
        
    except FileNotFoundError:
        logger = get_logger(__name__)
        logger.error(f"File not found - {input_path}")
        return None
        
    except PermissionError:
        logger = get_logger(__name__)
        logger.error(f"No permission to read file - {input_path}")
        return None
        
    except ValidationError as e:
        logger = get_logger(__name__)
        logger.error(f"Validation error - {e}")
        return None

    except ValueError as e:
        logger = get_logger(__name__)
        logger.error(f"File format issue - {e}")
        return None
        
    except Exception as e:
        logger = get_logger(__name__)
        logger.exception(f"Unknown error while processing input: {e}")
        return None