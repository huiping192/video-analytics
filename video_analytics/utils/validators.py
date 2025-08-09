import os
import subprocess
from typing import Sequence, Optional


class ValidationError(Exception):
    """Raised when validation of inputs or environment fails."""
    pass


def validate_file_path(file_path: str) -> None:
    """Validate basic file properties and readability."""
    if not file_path or not isinstance(file_path, str):
        raise ValidationError("Invalid file path")
    if not os.path.exists(file_path):
        raise ValidationError(f"File not found: {file_path}")
    if not os.path.isfile(file_path):
        raise ValidationError(f"Not a file: {file_path}")
    if not os.access(file_path, os.R_OK):
        raise ValidationError(f"File not readable: {file_path}")
    if os.path.getsize(file_path) < 1024:
        raise ValidationError("File too small; may not be a valid video")


def validate_ffmpeg_available(timeout_sec: int = 10) -> None:
    """Ensure ffmpeg CLI is available and responsive."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=timeout_sec, check=True)
    except Exception as e:
        raise ValidationError(f"FFmpeg not available: {e}")


def validate_python_deps() -> None:
    """Validate critical Python dependencies are importable."""
    try:
        import ffmpeg  # noqa: F401
    except Exception as e:
        raise ValidationError(f"ffmpeg-python not installed: {e}")
    try:
        import matplotlib  # noqa: F401
    except Exception as e:
        raise ValidationError(f"matplotlib not installed: {e}")


def validate_metadata(metadata) -> None:
    """Validate minimal metadata for video analysis."""
    duration = getattr(metadata, "duration", 0)
    width = getattr(metadata, "width", 0)
    height = getattr(metadata, "height", 0)
    video_codec = getattr(metadata, "video_codec", "")

    if duration is None or duration <= 0:
        raise ValidationError("Unable to get video duration")
    if width is None or height is None or width <= 0 or height <= 0:
        raise ValidationError("Unable to get video resolution")
    if not video_codec:
        raise ValidationError("No video stream found")


def ensure_non_empty_sequence(name: str, seq: Sequence) -> None:
    if not seq:
        raise ValidationError(f"Empty sequence: {name}")


def normalize_interval(interval: float, duration: float) -> float:
    """Optionally tune sampling interval for large files; return adjusted value."""
    if duration > 7200 and interval < 30.0:  # >2h
        return 30.0
    if duration > 3600 and interval < 20.0:  # >1h
        return 20.0
    return interval
