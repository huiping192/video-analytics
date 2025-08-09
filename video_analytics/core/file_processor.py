from dataclasses import dataclass
from typing import List, Optional
import os
import ffmpeg
from ..utils.logger import get_logger
from ..utils.validators import (
    validate_file_path,
    validate_metadata,
    ValidationError,
)


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


class ProcessedFile:
    """Processed video file object"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
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
            )
            
        except ffmpeg.Error as e:
            raise ValueError(f"FFmpeg probe failed: {e}")
    
    def _parse_fps(self, video_stream: dict) -> float:
        """Parse FPS value"""
        fps_str = video_stream.get('r_frame_rate', '0/1')
        try:
            num, den = fps_str.split('/')
            return float(num) / float(den) if float(den) != 0 else 0.0
        except:
            return 0.0


class FileProcessor:
    """File processor"""
    
    def process_input(self, file_path: str) -> ProcessedFile:
        """Process input file"""
        # Validate file via shared validators
        validate_file_path(file_path)
        
        # Create processed file
        processed_file = ProcessedFile(file_path)
        
        # Load metadata to validate
        metadata = processed_file.load_metadata()
        
        # Validate video content
        validate_metadata(metadata)
        
        return processed_file


class FileProcessingError(Exception):
    """Base file processing error"""
    pass


class InvalidFormatError(FileProcessingError):
    """Unsupported file format"""
    pass


class CorruptedFileError(FileProcessingError):
    """Corrupted file"""
    pass


def safe_process_file(file_path: str) -> Optional[ProcessedFile]:
    """Safely process a file"""
    try:
        processor = FileProcessor()
        return processor.process_input(file_path)
        
    except FileNotFoundError:
        from ..utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"File not found - {file_path}")
        return None
        
    except PermissionError:
        from ..utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"No permission to read file - {file_path}")
        return None
        
    except ValidationError as e:
        from ..utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Validation error - {e}")
        return None

    except ValueError as e:
        from ..utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"File format issue - {e}")
        return None
        
    except Exception as e:
        from ..utils.logger import get_logger
        logger = get_logger(__name__)
        logger.exception(f"Unknown error while processing file: {e}")
        return None