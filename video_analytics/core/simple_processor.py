"""
Simple file processor - for basic testing without FFmpeg.
Validates overall code structure and provides mock metadata.
"""

import os
from .file_processor import VideoMetadata, ProcessedFile


class SimpleProcessedFile(ProcessedFile):
    """Simplified processed file object - for testing"""
    
    def _extract_metadata(self) -> VideoMetadata:
        """Mock extraction of video metadata"""
        file_size = os.path.getsize(self.file_path)
        
        # Return mock metadata
        return VideoMetadata(
            file_path=self.file_path,
            duration=120.0,  # mock 2 minutes
            file_size=file_size,
            format_name="mp4",
            bit_rate=2000000,  # 2Mbps
            
            # Video stream info
            video_codec="h264",
            width=1920,
            height=1080,
            fps=30.0,
            video_bitrate=1800000,
            
            # Audio stream info
            audio_codec="aac",
            channels=2,
            sample_rate=48000,
            audio_bitrate=200000,
        )