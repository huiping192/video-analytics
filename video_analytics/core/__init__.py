"""
Core module - 核心功能模块

包含视频分析的核心功能：
- 文件处理
- 视频分析
- 音频分析
- FPS分析
"""

from .file_processor import FileProcessor, ProcessedFile, VideoMetadata, safe_process_file
from .video_analyzer import VideoBitrateAnalyzer, VideoBitrateAnalysis, BitrateDataPoint, analyze_multiple_videos
from .audio_analyzer import AudioBitrateAnalyzer, AudioBitrateAnalysis, AudioBitrateDataPoint, analyze_multiple_audio
from .fps_analyzer import FPSAnalyzer, FPSAnalysis, FPSDataPoint, analyze_multiple_fps

__all__ = [
    'FileProcessor', 'ProcessedFile', 'VideoMetadata', 'safe_process_file',
    'VideoBitrateAnalyzer', 'VideoBitrateAnalysis', 'BitrateDataPoint', 'analyze_multiple_videos',
    'AudioBitrateAnalyzer', 'AudioBitrateAnalysis', 'AudioBitrateDataPoint', 'analyze_multiple_audio',
    'FPSAnalyzer', 'FPSAnalysis', 'FPSDataPoint', 'analyze_multiple_fps'
]