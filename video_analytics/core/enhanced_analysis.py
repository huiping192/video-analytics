"""
Enhanced analysis information module
Provides comprehensive video analysis information for rich chart display.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import os
import math

from .file_processor import VideoMetadata
from .video_analyzer import VideoBitrateAnalysis
from .audio_analyzer import AudioBitrateAnalysis
from .fps_analyzer import FPSAnalysis


class VideoQuality(Enum):
    """Video quality levels"""
    EXCELLENT = "Excellent"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"


class BitrateType(Enum):
    """Bitrate encoding type"""
    CBR = "CBR (Constant Bitrate)"
    VBR = "VBR (Variable Bitrate)"
    UNKNOWN = "Unknown"


@dataclass
class FileBasicInfo:
    """文件基础信息"""
    filename: str
    file_size: int          # bytes
    file_size_mb: float     # MB for display
    resolution: str         # e.g., "1920x1080"
    duration: float         # seconds
    duration_str: str       # human readable, e.g., "1h 23m 45s"
    overall_bitrate: int    # bps
    overall_bitrate_mbps: float  # Mbps for display


@dataclass
class CodecTechInfo:
    """编码技术信息"""
    video_codec: str        # e.g., "h264", "hevc"
    video_codec_full: str   # Full name, e.g., "H.264/AVC"
    audio_codec: str        # e.g., "aac", "mp3"
    audio_codec_full: str   # Full name, e.g., "AAC"
    container_format: str   # e.g., "mp4", "mkv"
    audio_channels: int     # number of channels
    audio_channels_str: str # e.g., "立体声 (2声道)"
    sample_rate: int        # Hz
    sample_rate_str: str    # e.g., "48 kHz"


@dataclass
class QualityAssessment:
    """质量评估指标"""
    overall_quality: VideoQuality
    bitrate_stability: float        # 0-1, higher is more stable
    fps_stability: float           # 0-1, higher is more stable
    bitrate_type: BitrateType      # CBR/VBR
    quality_score: int             # 0-100 overall score
    
    # Detailed metrics
    video_bitrate_cv: float        # Coefficient of variation for video bitrate
    audio_bitrate_cv: float        # Coefficient of variation for audio bitrate
    fps_consistency: float         # FPS consistency score


@dataclass
class IssueDetection:
    """问题检测结果"""
    has_dropped_frames: bool
    severe_dropped_frames: bool     # > 5% frames dropped
    has_bitrate_spikes: bool       # Abnormal bitrate variations
    has_audio_issues: bool         # Audio quality issues
    
    # Issue counts
    dropped_frame_count: int
    dropped_frame_percentage: float
    bitrate_spike_count: int       # Number of significant spikes
    
    # Recommendations
    recommendations: List[str]     # User-friendly improvement suggestions
    warnings: List[str]           # Important warnings


@dataclass
class AnalysisMetrics:
    """分析统计指标"""
    # Video metrics
    video_avg_bitrate: float      # bps
    video_max_bitrate: float      # bps
    video_min_bitrate: float      # bps
    
    # Audio metrics  
    audio_avg_bitrate: float      # bps
    audio_max_bitrate: float      # bps
    audio_min_bitrate: float      # bps
    
    # FPS metrics
    declared_fps: float
    actual_avg_fps: float
    fps_variance: float
    
    # Time series lengths
    video_data_points: int
    audio_data_points: int
    fps_data_points: int


@dataclass
class EnhancedAnalysisInfo:
    """增强分析信息 - 包含图表显示需要的所有信息"""
    
    # Core info
    file_basic_info: FileBasicInfo
    codec_tech_info: CodecTechInfo
    quality_assessment: QualityAssessment
    issue_detection: IssueDetection
    analysis_metrics: AnalysisMetrics
    
    # Source analysis results (for chart generation)
    video_analysis: Optional[VideoBitrateAnalysis] = None
    audio_analysis: Optional[AudioBitrateAnalysis] = None
    fps_analysis: Optional[FPSAnalysis] = None
    
    # Metadata
    generated_at: str = ""
    analysis_version: str = "1.0"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


def get_codec_full_name(codec: str) -> str:
    """Get full codec name"""
    codec_map = {
        'h264': 'H.264/AVC',
        'hevc': 'H.265/HEVC', 
        'h265': 'H.265/HEVC',
        'vp9': 'VP9',
        'vp8': 'VP8',
        'av1': 'AV1',
        'aac': 'AAC (Advanced Audio Coding)',
        'mp3': 'MP3',
        'ac3': 'AC-3 (Dolby Digital)',
        'eac3': 'E-AC-3 (Dolby Digital Plus)',
        'opus': 'Opus',
        'vorbis': 'Vorbis',
        'flac': 'FLAC (Lossless)',
    }
    return codec_map.get(codec.lower(), codec.upper())


def get_audio_channels_description(channels: int) -> str:
    """Get audio channels description"""
    channel_map = {
        1: "Mono",
        2: "Stereo",
        5: "5.0 Surround", 
        6: "5.1 Surround",
        7: "6.1 Surround",
        8: "7.1 Surround",
    }
    base_desc = channel_map.get(channels, f"{channels} Channel")
    return f"{base_desc} ({channels}ch)"


def assess_overall_quality(bitrate_stability: float, fps_stability: float, 
                          has_issues: bool) -> tuple[VideoQuality, int]:
    """Assess overall video quality"""
    # Base score calculation
    stability_score = (bitrate_stability + fps_stability) / 2 * 100
    
    # Apply penalties for issues
    if has_issues:
        stability_score *= 0.8
    
    # Determine quality level
    if stability_score >= 90:
        quality = VideoQuality.EXCELLENT
    elif stability_score >= 75:
        quality = VideoQuality.GOOD
    elif stability_score >= 60:
        quality = VideoQuality.FAIR
    else:
        quality = VideoQuality.POOR
    
    return quality, int(stability_score)


def detect_bitrate_type(video_analysis: VideoBitrateAnalysis, 
                       audio_analysis: AudioBitrateAnalysis) -> BitrateType:
    """Detect bitrate encoding type (CBR/VBR)"""
    if video_analysis and hasattr(video_analysis, 'is_cbr'):
        if video_analysis.is_cbr:
            return BitrateType.CBR
        else:
            return BitrateType.VBR
    return BitrateType.UNKNOWN


def generate_recommendations(issue_detection: IssueDetection, 
                           quality_assessment: QualityAssessment) -> List[str]:
    """Generate improvement recommendations"""
    recommendations = []
    
    if issue_detection.severe_dropped_frames:
        recommendations.append("Severe frame drops detected. Consider lowering encoding settings or upgrading hardware.")
    
    if issue_detection.has_bitrate_spikes:
        recommendations.append("High bitrate variation detected. Consider using smoother encoding settings.")
    
    if quality_assessment.bitrate_stability < 0.7:
        recommendations.append("Video bitrate is unstable. Consider using CBR encoding or optimizing parameters.")
    
    if quality_assessment.fps_stability < 0.8:
        recommendations.append("Frame rate is inconsistent. Check video source or encoding settings.")
    
    if quality_assessment.overall_quality == VideoQuality.POOR:
        recommendations.append("Overall quality is poor. Consider re-encoding or checking source file.")
    
    if not recommendations:
        recommendations.append("Video quality is good. No specific optimization needed.")
    
    return recommendations


def create_enhanced_analysis_info(
    metadata: VideoMetadata,
    video_analysis: Optional[VideoBitrateAnalysis] = None,
    audio_analysis: Optional[AudioBitrateAnalysis] = None, 
    fps_analysis: Optional[FPSAnalysis] = None
) -> EnhancedAnalysisInfo:
    """从分析结果创建增强分析信息"""
    
    from datetime import datetime
    
    # File basic info
    file_basic_info = FileBasicInfo(
        filename=os.path.basename(metadata.file_path),
        file_size=metadata.file_size,
        file_size_mb=round(metadata.file_size / (1024 * 1024), 2),
        resolution=f"{metadata.width}x{metadata.height}",
        duration=metadata.duration,
        duration_str=format_duration(metadata.duration),
        overall_bitrate=metadata.bit_rate,
        overall_bitrate_mbps=round(metadata.bit_rate / 1_000_000, 2)
    )
    
    # Codec tech info
    codec_tech_info = CodecTechInfo(
        video_codec=metadata.video_codec,
        video_codec_full=get_codec_full_name(metadata.video_codec),
        audio_codec=metadata.audio_codec,
        audio_codec_full=get_codec_full_name(metadata.audio_codec),
        container_format=metadata.format_name,
        audio_channels=metadata.channels,
        audio_channels_str=get_audio_channels_description(metadata.channels),
        sample_rate=int(metadata.sample_rate) if metadata.sample_rate else 0,
        sample_rate_str=f"{int(metadata.sample_rate) // 1000} kHz" if metadata.sample_rate and int(metadata.sample_rate) > 0 else "Unknown"
    )
    
    # Calculate stability metrics
    bitrate_stability = 1.0  # Default high stability
    fps_stability = 1.0      # Default high stability
    video_bitrate_cv = 0.0
    audio_bitrate_cv = 0.0
    
    if video_analysis:
        if video_analysis.average_bitrate > 0:
            video_bitrate_cv = (video_analysis.bitrate_variance ** 0.5) / video_analysis.average_bitrate
            bitrate_stability = max(0.0, 1.0 - video_bitrate_cv)
    
    if fps_analysis:
        if fps_analysis.actual_average_fps > 0:
            fps_cv = (fps_analysis.fps_variance ** 0.5) / fps_analysis.actual_average_fps
            fps_stability = max(0.0, 1.0 - fps_cv)
    
    if audio_analysis:
        if audio_analysis.average_bitrate > 0:
            audio_bitrate_cv = (audio_analysis.bitrate_variance ** 0.5) / audio_analysis.average_bitrate
    
    # Issue detection
    has_dropped_frames = fps_analysis.total_dropped_frames > 0 if fps_analysis else False
    dropped_frame_percentage = (fps_analysis.total_dropped_frames / fps_analysis.total_frames * 100) if fps_analysis and fps_analysis.total_frames > 0 else 0.0
    severe_dropped_frames = dropped_frame_percentage > 5.0
    
    has_bitrate_spikes = video_bitrate_cv > 0.5 if video_analysis else False
    has_audio_issues = audio_bitrate_cv > 0.3 if audio_analysis else False
    
    issue_detection = IssueDetection(
        has_dropped_frames=has_dropped_frames,
        severe_dropped_frames=severe_dropped_frames,
        has_bitrate_spikes=has_bitrate_spikes,
        has_audio_issues=has_audio_issues,
        dropped_frame_count=fps_analysis.total_dropped_frames if fps_analysis else 0,
        dropped_frame_percentage=dropped_frame_percentage,
        bitrate_spike_count=0,  # TODO: Implement spike detection
        recommendations=[],
        warnings=[]
    )
    
    # Quality assessment
    overall_quality, quality_score = assess_overall_quality(
        bitrate_stability, fps_stability, 
        has_dropped_frames or has_bitrate_spikes or has_audio_issues
    )
    
    bitrate_type = detect_bitrate_type(video_analysis, audio_analysis)
    
    quality_assessment = QualityAssessment(
        overall_quality=overall_quality,
        bitrate_stability=bitrate_stability,
        fps_stability=fps_stability,
        bitrate_type=bitrate_type,
        quality_score=quality_score,
        video_bitrate_cv=video_bitrate_cv,
        audio_bitrate_cv=audio_bitrate_cv,
        fps_consistency=fps_stability
    )
    
    # Generate recommendations
    issue_detection.recommendations = generate_recommendations(issue_detection, quality_assessment)
    
    # Analysis metrics
    analysis_metrics = AnalysisMetrics(
        video_avg_bitrate=video_analysis.average_bitrate if video_analysis else 0,
        video_max_bitrate=video_analysis.max_bitrate if video_analysis else 0,
        video_min_bitrate=video_analysis.min_bitrate if video_analysis else 0,
        audio_avg_bitrate=audio_analysis.average_bitrate if audio_analysis else 0,
        audio_max_bitrate=audio_analysis.max_bitrate if audio_analysis else 0,
        audio_min_bitrate=audio_analysis.min_bitrate if audio_analysis else 0,
        declared_fps=fps_analysis.declared_fps if fps_analysis else 0,
        actual_avg_fps=fps_analysis.actual_average_fps if fps_analysis else 0,
        fps_variance=fps_analysis.fps_variance if fps_analysis else 0,
        video_data_points=len(video_analysis.data_points) if video_analysis else 0,
        audio_data_points=len(audio_analysis.data_points) if audio_analysis else 0,
        fps_data_points=len(fps_analysis.data_points) if fps_analysis else 0,
    )
    
    return EnhancedAnalysisInfo(
        file_basic_info=file_basic_info,
        codec_tech_info=codec_tech_info,
        quality_assessment=quality_assessment,
        issue_detection=issue_detection,
        analysis_metrics=analysis_metrics,
        video_analysis=video_analysis,
        audio_analysis=audio_analysis,
        fps_analysis=fps_analysis,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        analysis_version="1.0"
    )