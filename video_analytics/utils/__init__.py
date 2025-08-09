"""
Utils module

Provides common utilities and helper functions.
"""

from .logger import setup_logging, get_logger
from .validators import (
    validate_file_path,
    validate_metadata,
    validate_ffmpeg_available,
    validate_python_deps,
    ensure_non_empty_sequence,
    normalize_interval
)
from .config import ConfigManager, AnalysisConfig, get_merged_config