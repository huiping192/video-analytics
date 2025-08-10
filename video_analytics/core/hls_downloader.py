"""
HLS Downloader - High-performance downloader for large HLS streams.
Supports concurrent downloads, progress tracking, and automatic merging.
"""

import os
import tempfile
import shutil
import hashlib
import threading
import subprocess
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

import requests
import m3u8
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, DownloadColumn, SpinnerColumn, TransferSpeedColumn
from rich.console import Console

from ..utils.logger import get_logger

logger = get_logger(__name__)
console = Console()


@dataclass
class SegmentInfo:
    """HLS segment information"""
    index: int
    url: str
    duration: float
    size_bytes: Optional[int] = None


@dataclass 
class DownloadResult:
    """Download operation result"""
    success: bool
    local_file_path: Optional[str] = None
    total_size: int = 0
    duration: float = 0.0
    segments_count: int = 0
    error_message: Optional[str] = None


class HLSDownloader:
    """High-performance HLS stream downloader"""
    
    def __init__(self, max_workers: int = 10, timeout: int = 30):
        """
        Initialize HLS downloader
        
        Args:
            max_workers: Maximum concurrent download threads
            timeout: Request timeout in seconds
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site'
        })
    
    def is_hls_url(self, url: str) -> bool:
        """Check if URL is HLS stream"""
        if not url or not isinstance(url, str):
            return False
            
        url_lower = url.lower()
        return (url_lower.endswith('.m3u8') or 
                url_lower.endswith('.m3u') or
                'm3u8' in url_lower)
    
    def download_hls_stream(self, hls_url: str, output_path: Optional[str] = None) -> DownloadResult:
        """
        Download complete HLS stream as single video file
        
        Args:
            hls_url: HLS playlist URL (.m3u8)
            output_path: Optional output file path (if None, creates temporary file)
            
        Returns:
            DownloadResult with local file path and metadata
        """
        logger.info(f"Starting HLS download: {hls_url}")
        
        if output_path is None:
            output_path = self._generate_output_path(hls_url)
        
        # Try FFmpeg native download first (most reliable for complex streams)
        logger.info("Trying FFmpeg native download first...")
        result = self._download_with_ffmpeg(hls_url, output_path)
        
        if result.success:
            return result
        
        # Fallback to manual segment download
        logger.info("FFmpeg download failed, trying high-performance manual download...")
        return self._download_segments_manually(hls_url, output_path)
    
    def _download_with_ffmpeg(self, hls_url: str, output_path: str) -> DownloadResult:
        """Download HLS stream using FFmpeg native support with user confirmation"""
        try:
            # First estimate file size for user confirmation
            estimated_size_mb, estimated_duration = self.estimate_download_time(hls_url)
            
            # Show user confirmation for large files (>1GB)
            if estimated_size_mb > 1000:
                from rich.console import Console
                from rich.prompt import Confirm
                
                console = Console()
                console.print(f"\n[yellow]检测到大文件下载：[/yellow]")
                console.print(f"  预估大小: [bold]{estimated_size_mb:.1f} MB[/bold]")
                console.print(f"  预估时长: [bold]{estimated_duration/60:.1f} 分钟[/bold]")
                console.print(f"  下载地址: {hls_url[:80]}...")
                
                if not Confirm.ask("\n是否继续下载？", default=False):
                    return DownloadResult(
                        success=False,
                        error_message="用户取消下载"
                    )
                
                console.print("\n[green]开始下载...[/green]")
            elif estimated_size_mb > 500:  # Show info for medium files
                from rich.console import Console
                console = Console()
                console.print(f"[blue]下载信息：[/blue] 预估大小 {estimated_size_mb:.1f} MB，时长 {estimated_duration/60:.1f} 分钟")
            
            import ffmpeg
            
            logger.info(f"Using FFmpeg native HLS download for {estimated_size_mb:.1f}MB file...")
            
            # Get optimized parameters based on file size
            input_args = self._get_optimized_input_args(estimated_size_mb)
            output_args = self._get_optimized_output_args(estimated_size_mb)
            
            # Use FFmpeg to download with progress monitoring
            process = (
                ffmpeg
                .input(hls_url, **input_args)
                .output(output_path, **output_args)
                .overwrite_output()
                .run_async(pipe_stderr=True, pipe_stdout=True)
            )
            
            # Monitor FFmpeg progress
            self._monitor_ffmpeg_progress(process, output_path, estimated_duration)
            
            # Check process exit code
            if process.returncode != 0:
                # FFmpeg failed - collect error output
                stderr_output = process.stderr.read().decode('utf-8', errors='ignore') if process.stderr else ''
                logger.error(f"FFmpeg HLS download failed with code {process.returncode}: {stderr_output[:200]}...")
                return DownloadResult(
                    success=False,
                    error_message=f"FFmpeg download failed (exit code {process.returncode})"
                )
            
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                
                # Try to get duration from the downloaded file
                try:
                    probe = ffmpeg.probe(output_path)
                    duration = float(probe['format']['duration'])
                except:
                    duration = estimated_duration
                
                logger.info(f"FFmpeg HLS download complete: {output_path} ({file_size/1024/1024:.1f} MB)")
                
                return DownloadResult(
                    success=True,
                    local_file_path=output_path,
                    total_size=file_size,
                    duration=duration,
                    segments_count=0  # Unknown for FFmpeg download
                )
            else:
                return DownloadResult(
                    success=False,
                    error_message="FFmpeg download completed but output file not found"
                )
                
        except ffmpeg.Error as e:
            stderr = e.stderr.decode('utf-8') if e.stderr else 'No stderr available'
            logger.error(f"FFmpeg HLS download failed: {stderr}")
            return DownloadResult(
                success=False,
                error_message=f"FFmpeg download failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"FFmpeg HLS download failed: {e}")
            return DownloadResult(
                success=False,
                error_message=f"FFmpeg download error: {str(e)}"
            )
    
    def _get_optimized_input_args(self, estimated_size_mb: float) -> dict:
        """Get optimized FFmpeg input arguments based on file size"""
        input_args = {
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'headers': 'Accept: */*\r\nConnection: keep-alive\r\n'
        }
        
        # Large file optimizations (>500MB)
        if estimated_size_mb > 500:
            input_args.update({
                'http_persistent': '1',      # Keep HTTP connections alive
                'multiple_requests': '1',     # Allow multiple concurrent requests
                'max_reload': '10',          # Increase retry attempts
                'reconnect': '1',            # Enable automatic reconnection
                'reconnect_streamed': '1',   # Enable streaming reconnection
                'reconnect_delay_max': '5'   # Maximum reconnection delay (seconds)
            })
        
        # Super large file optimizations (>2GB)
        if estimated_size_mb > 2000:
            input_args.update({
                'max_reload': '20',          # Even more retries for huge files
                'reconnect_delay_max': '10', # Longer delay for stability
                'timeout': '30'              # Extended timeout
            })
        
        return input_args
    
    def _get_optimized_output_args(self, estimated_size_mb: float) -> dict:
        """Get optimized FFmpeg output arguments based on file size"""
        output_args = {
            'c': 'copy',     # Stream copy (no re-encoding)
            'f': 'mp4',      # MP4 container format
            'movflags': 'faststart'  # Optimize for web playback
        }
        
        # Large file optimizations
        if estimated_size_mb > 2000:
            # For very large files, use fragmented MP4 for better streaming
            output_args['movflags'] = 'empty_moov+default_base_moof'
        
        return output_args
    
    def _monitor_ffmpeg_progress(self, process, output_path: str, estimated_duration: float):
        """Monitor FFmpeg progress and display real-time updates"""
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            TransferSpeedColumn(),
            console=console
        ) as progress:
            
            download_task = progress.add_task("FFmpeg下载", total=100)
            
            while process.poll() is None:
                line = process.stderr.readline()
                if line:
                    line = line.decode('utf-8', errors='ignore').strip()
                    
                    # Parse FFmpeg progress from stderr
                    time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
                    if time_match:
                        hours, minutes, seconds = time_match.groups()
                        current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                        
                        if estimated_duration > 0:
                            progress_percent = min((current_time / estimated_duration) * 100, 100)
                            progress.update(download_task, completed=progress_percent)
                    
                    # Parse file size for transfer speed calculation
                    size_match = re.search(r'size=\s*(\d+)kB', line)
                    if size_match and os.path.exists(output_path):
                        try:
                            current_size = os.path.getsize(output_path)
                            elapsed_time = time.time() - start_time
                            if elapsed_time > 0:
                                speed = current_size / elapsed_time
                                progress.update(download_task, 
                                              description=f"FFmpeg下载 ({current_size/1024/1024:.1f}MB)")
                        except:
                            pass
                
                time.sleep(0.1)  # Small delay to avoid excessive CPU usage
            
            # Wait for process to complete
            process.wait()
            progress.update(download_task, completed=100)
    
    def _download_segments_manually(self, hls_url: str, output_path: str) -> DownloadResult:
        """Fallback: Download HLS segments manually and merge"""
        try:
            # Parse HLS playlist
            segments, init_segment_url = self._parse_hls_playlist(hls_url)
            if not segments:
                return DownloadResult(
                    success=False, 
                    error_message="Failed to parse HLS playlist or no segments found"
                )
            
            logger.info(f"Found {len(segments)} segments, estimated duration: {sum(s.duration for s in segments):.1f}s")
            
            # Create temporary directory for segments
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download init segment first if exists
                init_segment_file = None
                if init_segment_url:
                    init_segment_file = self._download_init_segment(init_segment_url, temp_dir)
                    if not init_segment_file:
                        logger.warning("Failed to download init segment, trying without it")
                
                # Download all segments concurrently
                segment_files = self._download_segments(segments, temp_dir)
                
                if not segment_files:
                    return DownloadResult(
                        success=False,
                        error_message="Failed to download any segments"
                    )
                
                # Merge segments into single file (with init segment if available)
                success = self._merge_segments_with_init(segment_files, output_path, init_segment_file)
                
                if success:
                    file_size = os.path.getsize(output_path)
                    total_duration = sum(s.duration for s in segments)
                    
                    logger.info(f"Manual HLS download complete: {output_path} ({file_size/1024/1024:.1f} MB)")
                    
                    return DownloadResult(
                        success=True,
                        local_file_path=output_path,
                        total_size=file_size,
                        duration=total_duration,
                        segments_count=len(segments)
                    )
                else:
                    return DownloadResult(
                        success=False,
                        error_message="Failed to merge segments"
                    )
                    
        except Exception as e:
            logger.error(f"Manual HLS download failed: {e}")
            return DownloadResult(
                success=False,
                error_message=f"Manual download error: {str(e)}"
            )
    
    def _parse_hls_playlist(self, hls_url: str) -> Tuple[List[SegmentInfo], Optional[str]]:
        """Parse HLS playlist and extract segment information with init segment"""
        try:
            # Load playlist
            playlist = m3u8.load(hls_url, timeout=self.timeout)
            
            # Track the actual playlist URL for base URL calculation
            actual_playlist_url = hls_url
            
            # Handle master playlist (multivariant) - select highest quality stream
            if playlist.is_variant and playlist.playlists:
                logger.info("Detected multivariant playlist, selecting highest quality stream")
                
                # Sort by bandwidth (descending) to get highest quality
                best_variant = max(playlist.playlists, key=lambda p: p.stream_info.bandwidth if p.stream_info else 0)
                
                # Get the URL of the best quality stream
                variant_url = best_variant.uri
                if not variant_url.startswith(('http://', 'https://')):
                    variant_url = urljoin(self._get_base_url(hls_url), variant_url)
                
                logger.info(f"Selected stream: {best_variant.stream_info.bandwidth}bps, {best_variant.stream_info.resolution}")
                
                # Load the actual playlist with segments
                playlist = m3u8.load(variant_url, timeout=self.timeout)
                actual_playlist_url = variant_url
            
            if not playlist.segments:
                logger.error("No segments found in HLS playlist")
                return [], None
            
            # Check for init segment (required for fMP4)
            init_segment_url = None
            if playlist.segments and hasattr(playlist.segments[0], 'init_section') and playlist.segments[0].init_section:
                init_uri = playlist.segments[0].init_section.uri
                base_url = self._get_base_url(actual_playlist_url)
                if not init_uri.startswith(('http://', 'https://')):
                    init_segment_url = urljoin(base_url, init_uri)
                else:
                    init_segment_url = init_uri
                logger.info(f"Found init segment: {init_segment_url}")
            
            # Parse regular segments
            segments = []
            base_url = self._get_base_url(actual_playlist_url)
            
            for i, segment in enumerate(playlist.segments):
                # Handle relative URLs
                segment_url = segment.uri
                if not segment_url.startswith(('http://', 'https://')):
                    segment_url = urljoin(base_url, segment_url)
                
                segments.append(SegmentInfo(
                    index=i,
                    url=segment_url,
                    duration=segment.duration
                ))
            
            logger.info(f"Parsed {len(segments)} segments from HLS playlist")
            return segments, init_segment_url
            
        except Exception as e:
            logger.error(f"Failed to parse HLS playlist: {e}")
            return [], None
    
    def _get_base_url(self, hls_url: str) -> str:
        """Extract base URL for resolving relative segment URLs"""
        parsed = urlparse(hls_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        if parsed.path:
            base_url += "/".join(parsed.path.split("/")[:-1]) + "/"
        return base_url
    
    def _download_segments(self, segments: List[SegmentInfo], temp_dir: str) -> List[str]:
        """Download all segments concurrently with progress tracking"""
        segment_files = [None] * len(segments)  # Maintain order
        failed_downloads = []
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            DownloadColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            download_task = progress.add_task("Downloading segments", total=len(segments))
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all download tasks
                future_to_segment = {
                    executor.submit(self._download_single_segment, segment, temp_dir): segment 
                    for segment in segments
                }
                
                # Process completed downloads
                for future in as_completed(future_to_segment):
                    segment = future_to_segment[future]
                    
                    try:
                        result = future.result()
                        if result:
                            segment_files[segment.index] = result
                        else:
                            failed_downloads.append(segment.index)
                            
                    except Exception as e:
                        logger.error(f"Segment {segment.index} download failed: {e}")
                        failed_downloads.append(segment.index)
                    
                    progress.update(download_task, advance=1)
        
        # Filter out failed downloads
        successful_files = [f for f in segment_files if f is not None]
        
        if failed_downloads:
            logger.warning(f"{len(failed_downloads)} segments failed to download")
        
        logger.info(f"Successfully downloaded {len(successful_files)}/{len(segments)} segments")
        return successful_files
    
    def _download_init_segment(self, init_url: str, temp_dir: str) -> Optional[str]:
        """Download init segment for fMP4 streams"""
        try:
            response = self.session.get(init_url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Create output file
            init_path = os.path.join(temp_dir, 'init_segment.mp4')
            
            with open(init_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Downloaded init segment: {init_path}")
            return init_path
            
        except Exception as e:
            logger.error(f"Failed to download init segment: {e}")
            return None
    
    def _merge_segments_with_init(self, segment_files: List[str], output_path: str, init_segment_file: Optional[str] = None) -> bool:
        """Merge segments with optional init segment"""
        if init_segment_file:
            logger.info(f"Merging {len(segment_files)} segments with init segment")
            # Prepend init segment to the list
            all_files = [init_segment_file] + segment_files
            return self._merge_segments(all_files, output_path)
        else:
            logger.info(f"Merging {len(segment_files)} segments without init segment")
            return self._merge_segments(segment_files, output_path)
    
    def _download_single_segment(self, segment: SegmentInfo, temp_dir: str) -> Optional[str]:
        """Download a single HLS segment"""
        try:
            response = self.session.get(segment.url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Create output file
            segment_filename = f"segment_{segment.index:06d}.ts"
            segment_path = os.path.join(temp_dir, segment_filename)
            
            with open(segment_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return segment_path
            
        except Exception as e:
            logger.error(f"Failed to download segment {segment.index}: {e}")
            return None
    
    def _merge_segments(self, segment_files: List[str], output_path: str) -> bool:
        """Merge downloaded segments into single video file using FFmpeg"""
        try:
            import ffmpeg
            
            # Sort segment files to ensure correct order
            segment_files.sort()
            
            if not segment_files:
                logger.error("No segment files to merge")
                return False
            
            # Detect actual segment format by examining file headers
            segment_format = self._detect_segment_format(segment_files[0])
            logger.info(f"Detected segment format: {segment_format}")
            
            if segment_format == 'fmp4':
                # For fMP4 segments, use specialized handling
                logger.info(f"Using specialized fMP4 merge for {len(segment_files)} segments")
                return self._merge_fmp4_segments(segment_files, output_path)
            elif segment_format == 'ts':
                # Use FFmpeg concat for TS segments
                logger.info(f"Using TS merge for {len(segment_files)} segments") 
                return self._merge_ts_segments(segment_files, output_path)
            else:
                # For unknown format, try to detect based on content and use appropriate method
                logger.info(f"Using default merge approach for {len(segment_files)} segments (format: {segment_format})")
                return self._merge_with_ffmpeg_default(segment_files, output_path)
            
        except Exception as e:
            logger.error(f"Failed to merge segments: {e}")
            return False
    
    def _detect_segment_format(self, segment_file: str) -> str:
        """Detect segment format by examining file header"""
        try:
            with open(segment_file, 'rb') as f:
                header = f.read(32)  # Read more bytes for better detection
                
            # Check for fMP4 signature (ftyp box)
            if header[4:8] == b'ftyp':
                return 'fmp4'
            # Check for MPEG-4 container anywhere in header
            elif b'ftyp' in header:
                return 'fmp4'
            # Check for MP4 box signatures
            elif header[4:8] in [b'moof', b'moov', b'styp', b'sidx']:
                return 'fmp4'
            # Check for TS sync byte at start
            elif header[0:1] == b'\x47':
                return 'ts'
            # Check for TS sync bytes at other positions (188-byte packets)
            elif header[188:189] == b'\x47' or header[376:377] == b'\x47':
                return 'ts'
            # Check if file extension suggests format
            elif segment_file.endswith('.mp4') or segment_file.endswith('.m4s'):
                return 'fmp4'
            elif segment_file.endswith('.ts'):
                # Check if it's actually fMP4 with .ts extension (common in modern HLS)
                if len(header) >= 8 and (b'ftyp' in header or header[4:8] in [b'moof', b'moov']):
                    return 'fmp4'
                else:
                    return 'ts'
            else:
                logger.warning(f"Could not detect format for segment: {segment_file}, header: {header[:8]}")
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Format detection failed: {e}")
            return 'unknown'
    
    def _merge_fmp4_segments(self, segment_files: List[str], output_path: str) -> bool:
        """Merge fMP4 segments using optimal FFmpeg strategy"""
        try:
            import ffmpeg
            
            # Strategy 1: Try FFmpeg with explicit fMP4 handling
            logger.info(f"Attempting FFmpeg fMP4 merge for {len(segment_files)} segments...")
            
            try:
                # Create input list for FFmpeg
                list_file_path = output_path + '.list'
                
                with open(list_file_path, 'w') as f:
                    for segment_file in segment_files:
                        f.write(f"file '{segment_file}'\n")
                
                # Use FFmpeg with fMP4-optimized settings
                (
                    ffmpeg
                    .input(list_file_path, format='concat', safe=0, fflags='+genpts')
                    .output(output_path, 
                           c='copy', 
                           f='mp4', 
                           movflags='faststart+frag_keyframe',
                           avoid_negative_ts='make_zero')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
                
                # Clean up list file
                if os.path.exists(list_file_path):
                    os.remove(list_file_path)
                
                # Verify the output file is readable
                try:
                    ffmpeg.probe(output_path)
                    logger.info(f"Successfully merged {len(segment_files)} fMP4 segments with FFmpeg")
                    return True
                except ffmpeg.Error:
                    logger.warning("FFmpeg merge produced unreadable file, trying alternative...")
                    
            except ffmpeg.Error as e:
                # Clean up list file on error
                if os.path.exists(list_file_path):
                    os.remove(list_file_path)
                
                stderr = e.stderr.decode('utf-8') if e.stderr else 'No stderr available'
                logger.warning(f"Standard FFmpeg merge failed: {stderr[:200]}...")
            
            # Strategy 2: Force re-encode first few segments to create proper header
            logger.info("Trying header reconstruction approach...")
            return self._merge_fmp4_with_header_fix(segment_files, output_path)
                
        except Exception as e:
            logger.error(f"fMP4 merge failed: {e}")
            return False
    
    def _merge_fmp4_with_header_fix(self, segment_files: List[str], output_path: str) -> bool:
        """Advanced fMP4 merge with header reconstruction"""
        try:
            import ffmpeg
            temp_dir = os.path.dirname(output_path)
            
            # Re-encode first segment to create proper MP4 header
            header_segment = os.path.join(temp_dir, 'header_segment.mp4')
            list_file_path = output_path + '.headerfix.list'
            
            try:
                # Re-encode first segment with proper MP4 structure
                (
                    ffmpeg
                    .input(segment_files[0])
                    .output(header_segment, vcodec='copy', acodec='copy', f='mp4', 
                           movflags='faststart+frag_keyframe')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
                
                # Create list with header segment + remaining segments
                
                with open(list_file_path, 'w') as f:
                    f.write(f"file '{header_segment}'\n")
                    for segment_file in segment_files[1:]:
                        f.write(f"file '{segment_file}'\n")
                
                # Merge with the fixed header
                (
                    ffmpeg
                    .input(list_file_path, format='concat', safe=0)
                    .output(output_path, c='copy', f='mp4', movflags='faststart')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
                
                # Clean up
                for cleanup_file in [header_segment, list_file_path]:
                    if os.path.exists(cleanup_file):
                        os.remove(cleanup_file)
                
                logger.info(f"Successfully merged {len(segment_files)} fMP4 segments with header fix")
                return True
                
            except ffmpeg.Error as e:
                # Clean up on error
                for cleanup_file in [header_segment, list_file_path]:
                    if os.path.exists(cleanup_file):
                        try:
                            os.remove(cleanup_file)
                        except:
                            pass
                
                stderr = e.stderr.decode('utf-8') if e.stderr else 'No stderr available'
                logger.warning(f"Header fix merge failed: {stderr[:200]}...")
                
                # Final fallback: binary concatenation
                logger.info("Trying binary concatenation as final fallback...")
                return self._merge_with_binary_concat(segment_files, output_path)
                
        except Exception as e:
            logger.error(f"Header fix merge failed: {e}")
            return self._merge_with_binary_concat(segment_files, output_path)
    
    def _merge_fmp4_alternative(self, segment_files: List[str], output_path: str) -> bool:
        """Alternative fMP4 merge using binary concatenation or batch concat"""
        try:
            import ffmpeg
            
            # For large number of segments, use binary concatenation (most efficient for fMP4)
            if len(segment_files) > 100:
                logger.info(f"Using binary concatenation for {len(segment_files)} fMP4 segments")
                return self._merge_with_binary_concat(segment_files, output_path)
            else:
                # For smaller numbers, try ffmpeg concat filter
                try:
                    inputs = [ffmpeg.input(f) for f in segment_files]
                    
                    # Use concat filter for fMP4
                    (
                        ffmpeg
                        .concat(*inputs, v=1, a=1)
                        .output(output_path, f='mp4', movflags='faststart')
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True, quiet=True)
                    )
                    
                    logger.info(f"Successfully merged {len(segment_files)} fMP4 segments using concat filter")
                    return True
                    
                except Exception as e:
                    logger.error(f"Concat filter failed: {e}")
                    # Fallback to binary concatenation
                    return self._merge_with_binary_concat(segment_files, output_path)
            
        except Exception as e:
            logger.error(f"Alternative fMP4 merge failed: {e}")
            return False
    
    def _merge_ts_segments(self, segment_files: List[str], output_path: str) -> bool:
        """Merge TS segments using FFmpeg"""
        try:
            import ffmpeg
            
            if len(segment_files) == 1:
                # Single segment, just copy
                (
                    ffmpeg
                    .input(segment_files[0])
                    .output(output_path, c='copy')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
            else:
                # Use concat demuxer for TS files
                list_file_path = output_path + '.list'
                
                with open(list_file_path, 'w') as f:
                    for segment_file in segment_files:
                        f.write(f"file '{segment_file}'\n")
                
                try:
                    (
                        ffmpeg
                        .input(list_file_path, format='concat', safe=0)
                        .output(output_path, c='copy')
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True, quiet=True)
                    )
                    
                    # Clean up list file
                    if os.path.exists(list_file_path):
                        os.remove(list_file_path)
                        
                except ffmpeg.Error as e:
                    # Clean up list file on error
                    if os.path.exists(list_file_path):
                        os.remove(list_file_path)
                    raise e
            
            logger.info(f"Successfully merged {len(segment_files)} TS segments")
            return True
            
        except ffmpeg.Error as e:
            stderr = e.stderr.decode('utf-8') if e.stderr else 'No stderr available'
            logger.error(f"TS merge failed: {stderr}")
            return False
        except Exception as e:
            logger.error(f"TS merge failed: {e}")
            return False
    
    def _merge_with_ffmpeg_default(self, segment_files: List[str], output_path: str) -> bool:
        """Default FFmpeg merge approach with fallbacks"""
        try:
            import ffmpeg
            
            # Try concat demuxer first
            list_file_path = output_path + '.list'
            
            with open(list_file_path, 'w') as f:
                for segment_file in segment_files:
                    f.write(f"file '{segment_file}'\n")
            
            try:
                (
                    ffmpeg
                    .input(list_file_path, format='concat', safe=0)
                    .output(output_path, c='copy')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
                
                # Clean up list file
                if os.path.exists(list_file_path):
                    os.remove(list_file_path)
                
                logger.info(f"Successfully merged {len(segment_files)} segments using default approach")
                return True
                
            except ffmpeg.Error as e:
                # Clean up list file on error
                if os.path.exists(list_file_path):
                    os.remove(list_file_path)
                
                stderr = e.stderr.decode('utf-8') if e.stderr else 'No stderr available'
                logger.error(f"Default merge failed: {stderr}")
                
                # Fallback to binary concatenation for small numbers
                if len(segment_files) <= 100:
                    return self._merge_with_binary_concat(segment_files, output_path)
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Default merge failed: {e}")
            return False
    
    def _merge_with_remux_fallback(self, segment_files: List[str], output_path: str) -> bool:
        """Final fallback: remux each segment and then concat"""
        try:
            import ffmpeg
            temp_dir = os.path.dirname(output_path)
            remuxed_files = []
            
            # Remux each segment to ensure compatibility
            for i, segment_file in enumerate(segment_files[:10]):  # Limit to first 10 for safety
                remuxed_path = os.path.join(temp_dir, f"remuxed_{i:06d}.mp4")
                
                try:
                    (
                        ffmpeg
                        .input(segment_file)
                        .output(remuxed_path, c='copy', f='mp4')
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True, quiet=True)
                    )
                    remuxed_files.append(remuxed_path)
                except:
                    # Skip problematic segments
                    continue
            
            if remuxed_files:
                # Concat remuxed files
                result = self._merge_with_ffmpeg_default(remuxed_files, output_path)
                
                # Clean up remuxed files
                for f in remuxed_files:
                    try:
                        os.remove(f)
                    except:
                        pass
                        
                return result
            else:
                return False
                
        except Exception as e:
            logger.error(f"Remux fallback failed: {e}")
            return False
    
    def _merge_with_binary_concat(self, segment_files: List[str], output_path: str) -> bool:
        """Binary concatenation fallback"""
        try:
            logger.info("Trying binary concatenation as fallback...")
            with open(output_path, 'wb') as outfile:
                for segment_file in segment_files:
                    with open(segment_file, 'rb') as infile:
                        outfile.write(infile.read())
            
            logger.info(f"Successfully merged {len(segment_files)} segments using binary concat")
            return True
            
        except Exception as e:
            logger.error(f"Binary concatenation failed: {e}")
            return False
    
    def _generate_output_path(self, hls_url: str) -> str:
        """Generate output file path based on HLS URL"""
        # Create hash of URL for unique filename
        url_hash = hashlib.md5(hls_url.encode()).hexdigest()[:8]
        
        # Use temporary directory
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"hls_download_{url_hash}.mp4")
        
        return output_path
    
    def estimate_download_time(self, hls_url: str) -> Tuple[int, float]:
        """
        Improved estimation with better sampling precision
        
        Returns:
            (estimated_size_mb, estimated_duration_seconds)
        """
        try:
            playlist = m3u8.load(hls_url, timeout=self.timeout)
            
            # Handle master playlist - select highest quality stream for estimation
            if playlist.is_variant and playlist.playlists:
                best_variant = max(playlist.playlists, 
                                 key=lambda p: p.stream_info.bandwidth if p.stream_info else 0)
                variant_url = urljoin(self._get_base_url(hls_url), best_variant.uri)
                playlist = m3u8.load(variant_url, timeout=self.timeout)
            
            if not playlist.segments:
                return 0, 0.0
            
            segments = playlist.segments
            total_duration = sum(segment.duration for segment in segments)
            
            # Improved sampling: sample 10 segments for better precision
            sample_size = 0
            sample_duration = 0.0
            samples_to_check = min(10, len(segments))
            
            # Sample from beginning, middle, and end for better accuracy
            sample_indices = []
            if len(segments) >= 10:
                # Sample evenly distributed segments
                step = len(segments) // 10
                sample_indices = [i * step for i in range(10)]
            else:
                # Sample all available segments
                sample_indices = list(range(len(segments)))
            
            successful_samples = 0
            for i in sample_indices:
                try:
                    segment_url = segments[i].uri
                    if not segment_url.startswith(('http://', 'https://')):
                        base_url = self._get_base_url(hls_url if not playlist.is_variant 
                                                    else variant_url)
                        segment_url = urljoin(base_url, segment_url)
                    
                    response = self.session.head(segment_url, timeout=5)
                    if 'content-length' in response.headers:
                        sample_size += int(response.headers['content-length'])
                        sample_duration += segments[i].duration
                        successful_samples += 1
                except:
                    continue
            
            if sample_duration > 0 and successful_samples >= 3:
                # Estimate total size based on improved sampling
                estimated_size_bytes = (sample_size / sample_duration) * total_duration
                estimated_size_mb = estimated_size_bytes / (1024 * 1024)
            else:
                # Enhanced fallback with bandwidth hint from playlist
                fallback_bitrate = 3.0  # Default 3 Mbps
                
                # Try to get bitrate from stream info if available
                if hasattr(playlist, 'playlists') and playlist.playlists:
                    try:
                        fallback_bitrate = playlist.playlists[0].stream_info.bandwidth / 1_000_000
                    except:
                        pass
                elif hasattr(playlist, 'stream_info') and playlist.stream_info:
                    try:
                        fallback_bitrate = playlist.stream_info.bandwidth / 1_000_000
                    except:
                        pass
                
                estimated_size_mb = total_duration * fallback_bitrate / 8.0
            
            return int(estimated_size_mb), total_duration
            
        except Exception as e:
            logger.error(f"Failed to estimate download: {e}")
            return 0, 0.0


# Utility functions
def is_hls_url(url: str) -> bool:
    """Quick check if URL appears to be HLS"""
    downloader = HLSDownloader()
    return downloader.is_hls_url(url)


def download_hls_stream(hls_url: str, output_path: Optional[str] = None, 
                       max_workers: int = 10) -> DownloadResult:
    """
    Convenience function for downloading HLS streams
    
    Args:
        hls_url: HLS playlist URL
        output_path: Optional output file path
        max_workers: Maximum concurrent download threads
        
    Returns:
        DownloadResult with local file path and metadata
    """
    downloader = HLSDownloader(max_workers=max_workers)
    return downloader.download_hls_stream(hls_url, output_path)