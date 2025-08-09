"""
HLS Downloader - High-performance downloader for large HLS streams.
Supports concurrent downloads, progress tracking, and automatic merging.
"""

import os
import tempfile
import shutil
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

import requests
import m3u8
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, DownloadColumn
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
        
        try:
            # Parse HLS playlist
            segments = self._parse_hls_playlist(hls_url)
            if not segments:
                return DownloadResult(
                    success=False, 
                    error_message="Failed to parse HLS playlist or no segments found"
                )
            
            logger.info(f"Found {len(segments)} segments, estimated duration: {sum(s.duration for s in segments):.1f}s")
            
            # Create temporary directory for segments
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download all segments concurrently
                segment_files = self._download_segments(segments, temp_dir)
                
                if not segment_files:
                    return DownloadResult(
                        success=False,
                        error_message="Failed to download any segments"
                    )
                
                # Merge segments into single file
                if output_path is None:
                    output_path = self._generate_output_path(hls_url)
                
                success = self._merge_segments(segment_files, output_path)
                
                if success:
                    file_size = os.path.getsize(output_path)
                    total_duration = sum(s.duration for s in segments)
                    
                    logger.info(f"HLS download complete: {output_path} ({file_size/1024/1024:.1f} MB)")
                    
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
            logger.error(f"HLS download failed: {e}")
            return DownloadResult(
                success=False,
                error_message=f"Download error: {str(e)}"
            )
    
    def _parse_hls_playlist(self, hls_url: str) -> List[SegmentInfo]:
        """Parse HLS playlist and extract segment information"""
        try:
            # Load playlist
            playlist = m3u8.load(hls_url, timeout=self.timeout)
            
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
            
            if not playlist.segments:
                logger.error("No segments found in HLS playlist")
                return []
            
            segments = []
            base_url = self._get_base_url(hls_url)
            
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
            return segments
            
        except Exception as e:
            logger.error(f"Failed to parse HLS playlist: {e}")
            return []
    
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
            
            # Create input list file for FFmpeg
            list_file_path = output_path + '.list'
            
            with open(list_file_path, 'w') as f:
                for segment_file in segment_files:
                    f.write(f"file '{segment_file}'\n")
            
            try:
                # Use FFmpeg concat demuxer for efficient merging
                (
                    ffmpeg
                    .input(list_file_path, format='concat', safe=0)
                    .output(output_path, c='copy')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                logger.info(f"Successfully merged {len(segment_files)} segments")
                return True
                
            finally:
                # Clean up list file
                if os.path.exists(list_file_path):
                    os.remove(list_file_path)
            
        except Exception as e:
            logger.error(f"Failed to merge segments: {e}")
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
        Estimate download time and file size for HLS stream
        
        Returns:
            (estimated_size_mb, estimated_duration_seconds)
        """
        try:
            segments = self._parse_hls_playlist(hls_url)
            if not segments:
                return 0, 0.0
            
            total_duration = sum(s.duration for s in segments)
            
            # Sample first few segments to estimate bitrate
            sample_size = 0
            sample_duration = 0.0
            samples_to_check = min(3, len(segments))
            
            for i in range(samples_to_check):
                try:
                    response = self.session.head(segments[i].url, timeout=5)
                    if 'content-length' in response.headers:
                        sample_size += int(response.headers['content-length'])
                        sample_duration += segments[i].duration
                except:
                    continue
            
            if sample_duration > 0:
                # Estimate total size based on sample
                estimated_size_bytes = (sample_size / sample_duration) * total_duration
                estimated_size_mb = estimated_size_bytes / (1024 * 1024)
            else:
                # Fallback estimation (assume 2-5 Mbps for typical video)
                estimated_size_mb = total_duration * 3.0 / 8.0  # 3 Mbps average
            
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