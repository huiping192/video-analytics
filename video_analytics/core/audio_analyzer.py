"""
Audio bitrate analysis module
Analyzes audio bitrate over time and provides quality assessment and statistics.
"""

import json
import subprocess
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import numpy as np

from .file_processor import ProcessedFile
from ..utils.logger import get_logger
from ..utils.validators import ensure_non_empty_sequence


@dataclass
class AudioBitrateDataPoint:
    """Audio bitrate data point"""
    timestamp: float    # seconds
    bitrate: float     # bitrate (bps)


@dataclass
class AudioBitrateAnalysis:
    """Audio bitrate analysis result"""
    file_path: str
    duration: float
    
    # Basic info
    codec: str            # codec
    channels: int         # channels
    sample_rate: int      # sample rate
    
    # Statistics
    average_bitrate: float    # average bitrate (bps)
    max_bitrate: float       # max bitrate (bps)
    min_bitrate: float       # min bitrate (bps)
    bitrate_variance: float  # variance
    
    # Time series
    data_points: List[AudioBitrateDataPoint]
    
    # Sampling
    sample_interval: float   # interval (seconds)
    
    @property
    def bitrate_stability(self) -> float:
        """Compute bitrate stability (0-1, higher means more stable)"""
        if self.average_bitrate == 0:
            return 1.0
        cv = np.sqrt(self.bitrate_variance) / self.average_bitrate
        return max(0, 1 - cv)
    
    @property
    def quality_level(self) -> str:
        """Simple quality level evaluation (English labels)"""
        avg_kbps = self.average_bitrate / 1000
        
        if self.codec.lower() == 'aac':
            if avg_kbps >= 256:
                return "Excellent"
            elif avg_kbps >= 128:
                return "Good"
            elif avg_kbps >= 96:
                return "Fair"
            else:
                return "Poor"
        
        elif self.codec.lower() == 'mp3':
            if avg_kbps >= 320:
                return "Excellent"
            elif avg_kbps >= 192:
                return "Good"
            elif avg_kbps >= 128:
                return "Fair"
            else:
                return "Poor"
        
        else:
            return "Unknown"


class AudioBitrateAnalyzer:
    """Audio bitrate analyzer"""
    
    def __init__(self, sample_interval: float = 15.0):
        self.sample_interval = sample_interval  # audio sampling interval
        self._bitrate_cache = {}  # cache
        self._logger = get_logger(__name__)
    
    def analyze(self, processed_file: ProcessedFile) -> AudioBitrateAnalysis:
        """Analyze audio bitrate"""
        metadata = processed_file.load_metadata()
        
        if not metadata.audio_codec:
            raise ValueError("No audio stream found")
        
        self._logger.info(f"Analyzing audio bitrate (interval: {self.sample_interval}s)")
        
        # 生成采样时间点
        duration = metadata.duration
        sample_times = np.arange(0, duration, self.sample_interval)
        
        self._logger.debug(f"Total sample points: {len(sample_times)} ...")
        
        # 采样分析
        data_points = []
        for i, timestamp in enumerate(sample_times):
            try:
                bitrate = self._get_audio_bitrate_at_time(processed_file.file_path, timestamp)
                data_points.append(AudioBitrateDataPoint(timestamp, bitrate))
                
                # progress
                if (i + 1) % 5 == 0 or i == len(sample_times) - 1:
                    progress = (i + 1) / len(sample_times) * 100
                    self._logger.debug(f"Audio analysis progress: {progress:.1f}%")
                    
            except Exception as e:
                self._logger.warning(f"Audio sampling failed at {timestamp:.1f}s: {e}")
                # fallback to metadata bitrate
                fallback_bitrate = metadata.audio_bitrate or (metadata.bit_rate * 0.1) if metadata.bit_rate else 128000
                data_points.append(AudioBitrateDataPoint(timestamp, fallback_bitrate))
        
        ensure_non_empty_sequence("audio bitrate data points", data_points)
        
        # 计算统计信息
        bitrates = [dp.bitrate for dp in data_points]
        
        return AudioBitrateAnalysis(
            file_path=processed_file.file_path,
            duration=duration,
            codec=metadata.audio_codec,
            channels=metadata.channels or 2,
            sample_rate=int(metadata.sample_rate) if metadata.sample_rate else 44100,
            average_bitrate=float(np.mean(bitrates)),
            max_bitrate=float(np.max(bitrates)),
            min_bitrate=float(np.min(bitrates)),
            bitrate_variance=float(np.var(bitrates)),
            data_points=data_points,
            sample_interval=self.sample_interval
        )
    
    def _get_audio_bitrate_at_time(self, file_path: str, timestamp: float, window_size: float = 10.0) -> float:
        """Get audio bitrate at a timestamp using a real time window"""
        try:
            # Use ffprobe to analyze audio packets within the time window
            end_time = timestamp + window_size
            
            # 获取音频包信息
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_packets',
                '-select_streams', 'a:0',
                '-show_entries', 'packet=size,pts_time',
                '-of', 'csv=p=0',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0 or not result.stdout.strip():
                # Fallback if no packet info
                return self._get_fallback_audio_bitrate(file_path)
            
            # Parse packet data
            total_bytes = 0
            packet_count = 0
            valid_timestamps = []
            
            for line in result.stdout.strip().split('\n'):
                if line and ',' in line:
                    try:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            pts_time_str, size_str = parts[0], parts[1]
                            
                            if size_str and pts_time_str:
                                pts_time = float(pts_time_str)
                                packet_size = int(size_str)
                                
                                # ensure inside window
                                if timestamp <= pts_time <= end_time:
                                    total_bytes += packet_size
                                    packet_count += 1
                                    valid_timestamps.append(pts_time)
                    except (ValueError, IndexError):
                        continue
            
            if packet_count == 0 or not valid_timestamps:
                return self._get_fallback_audio_bitrate(file_path)
            
            # compute actual duration
            if len(valid_timestamps) > 1:
                actual_duration = max(valid_timestamps) - min(valid_timestamps)
                if actual_duration > 0:
                    # bitrate = (total_bytes * 8) / duration
                    bitrate = (total_bytes * 8) / actual_duration
                    return bitrate
            
            # use window size if duration invalid
            if window_size > 0:
                return (total_bytes * 8) / window_size
            
            return self._get_fallback_audio_bitrate(file_path)
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            self._logger.warning(f"Audio bitrate analysis failed at {timestamp:.1f}s: {e}")
            return self._get_fallback_audio_bitrate(file_path)
    
    def _get_fallback_audio_bitrate(self, file_path: str) -> float:
        """Get fallback audio bitrate (based on file-level info)"""
        # 添加缓存以避免重复计算同一文件的备选码率
        if not hasattr(self, '_bitrate_cache'):
            self._bitrate_cache = {}
        
        if file_path in self._bitrate_cache:
            return self._bitrate_cache[file_path]
        
        try:
            # Try to get declared audio stream bitrate
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'stream=bit_rate',
                '-select_streams', 'a:0',
                '-of', 'csv=p=0',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            bitrate_str = result.stdout.strip()
            
            if bitrate_str and bitrate_str != 'N/A':
                bitrate = float(bitrate_str)
                self._bitrate_cache[file_path] = bitrate
                return bitrate
            else:
                # If not available, estimate from file
                estimated_bitrate = self._estimate_audio_bitrate_from_file(file_path)
                self._bitrate_cache[file_path] = estimated_bitrate
                return estimated_bitrate
                
        except Exception:
            estimated_bitrate = self._estimate_audio_bitrate_from_file(file_path)
            self._bitrate_cache[file_path] = estimated_bitrate
            return estimated_bitrate
    
    def _estimate_audio_bitrate_from_file(self, file_path: str) -> float:
        """Estimate audio bitrate from file info"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(file_path)
            
            # First try audio stream info
            audio_streams = [s for s in probe.get('streams', []) if s.get('codec_type') == 'audio']
            if audio_streams:
                audio_stream = audio_streams[0]  # 使用第一个音频流
                
                # Try stream bitrate
                stream_bitrate = audio_stream.get('bit_rate')
                if stream_bitrate:
                    return float(stream_bitrate)
            
            # Otherwise, estimate from total bitrate
            format_info = probe.get('format', {})
            total_bitrate = format_info.get('bit_rate')
            
            if total_bitrate:
                # Adjust ratio based on presence of video stream
                video_streams = [s for s in probe.get('streams', []) if s.get('codec_type') == 'video']
                
                if video_streams:
                    # With video, audio is typically 5-15%
                    video_bitrate = video_streams[0].get('bit_rate')
                    if video_bitrate:
                        estimated_audio_ratio = min(0.15, 200000 / float(video_bitrate))
                    else:
                        estimated_audio_ratio = 0.1  # 默认10%
                    return float(total_bitrate) * estimated_audio_ratio
                else:
                    # Audio-only case
                    return float(total_bitrate)
            else:
                # Estimate from file size and duration
                duration = float(format_info.get('duration', 1))
                file_size = int(format_info.get('size', 0))
                if duration > 0 and file_size > 0:
                    total_bitrate = (file_size * 8) / duration
                    # Assume audio-only or audio-dominant
                    return total_bitrate * 0.8
                
        except Exception:
            pass
        
        # Default
        return 128000.0  # 128 kbps
    
    def get_channel_layout(self, channels: int) -> str:
        """Infer channel layout from channel count"""
        layouts = {
            1: "Mono",
            2: "Stereo",
            3: "2.1 Surround",
            4: "4.0 Surround",
            5: "4.1 Surround",
            6: "5.1 Surround",
            7: "6.1 Surround",
            8: "7.1 Surround"
        }
        return layouts.get(channels, f"{channels}ch")
    
    def assess_audio_quality(self, analysis: AudioBitrateAnalysis) -> dict:
        """Assess audio quality"""
        # Detect bitrate changes
        bitrate_changes = self._detect_bitrate_changes(analysis)
        is_vbr = self._detect_vbr(analysis)
        
        assessment = {
            "quality_level": analysis.quality_level,
            "stability": f"{analysis.bitrate_stability:.1%}",
            "codec_rating": self._rate_codec(analysis.codec),
            "sample_rate_rating": self._rate_sample_rate(analysis.sample_rate),
            "is_vbr": is_vbr,
            "bitrate_changes": bitrate_changes,
            "issues": [],
            "recommendations": []
        }
        
        # Detect issues and generate recommendations
        if analysis.average_bitrate < 128000:  # 小于128kbps
            assessment["issues"].append("Low audio bitrate")
            assessment["recommendations"].append("Increase audio bitrate for better quality")
        
        if analysis.sample_rate < 44100:
            assessment["issues"].append("Sample rate below 44.1kHz")
            assessment["recommendations"].append("Use 44.1kHz or higher sample rate")
        
        if analysis.channels == 1:
            assessment["issues"].append("Mono audio")
            assessment["recommendations"].append("Consider stereo for a better experience")
        
        if analysis.bitrate_stability < 0.8:
            if is_vbr:
                assessment["issues"].append("Detected VBR (variable bitrate) audio")
                assessment["recommendations"].append("VBR can provide better quality-to-bitrate efficiency")
            else:
                assessment["issues"].append("Unstable audio bitrate")
                assessment["recommendations"].append("Check encoding settings or source quality")
        
        # Bitrate change analysis
        if bitrate_changes["significant_changes"] > 0:
            assessment["issues"].append(f"Detected {bitrate_changes['significant_changes']} significant bitrate change points")
            if is_vbr:
                assessment["recommendations"].append("Bitrate variation is normal for VBR audio")
            else:
                assessment["recommendations"].append("Check the audio source and encoding settings")
        
        if not assessment["issues"]:
            assessment["recommendations"].append("No obvious audio quality issues")
        
        return assessment
    
    def _rate_codec(self, codec: str) -> str:
        """Rate codec"""
        codec_ratings = {
            'aac': 'Excellent - modern efficient codec',
            'mp3': 'Good - widely compatible',
            'ac3': 'Fair - good multichannel support',
            'opus': 'Excellent - very efficient',
            'flac': 'Perfect - lossless',
            'pcm': 'Perfect - uncompressed'
        }
        return codec_ratings.get(codec.lower(), 'Unknown codec')
    
    def _detect_vbr(self, analysis: AudioBitrateAnalysis) -> bool:
        """Detect whether the audio is VBR"""
        if not analysis.data_points or len(analysis.data_points) < 3:
            return False
        
        bitrates = [dp.bitrate for dp in analysis.data_points]
        
        # Coefficient of variation (std/mean)
        bitrate_std = np.std(bitrates)
        bitrate_mean = np.mean(bitrates)
        
        if bitrate_mean > 0:
            cv = bitrate_std / bitrate_mean
            # 音频的VBR阈值相对低一些，5%变异系数以上认为VBR
            return cv > 0.05
        
        return False
    
    def _detect_bitrate_changes(self, analysis: AudioBitrateAnalysis) -> dict:
        """Detect bitrate changes"""
        if len(analysis.data_points) < 2:
            return {
                "total_changes": 0,
                "significant_changes": 0,
                "max_change": 0,
                "change_points": []
            }
        
        changes = []
        significant_changes = 0
        change_points = []
        
        # Change between consecutive samples
        for i in range(1, len(analysis.data_points)):
            prev_bitrate = analysis.data_points[i-1].bitrate
            curr_bitrate = analysis.data_points[i].bitrate
            
            if prev_bitrate > 0:  # 避免除以零
                change_ratio = abs(curr_bitrate - prev_bitrate) / prev_bitrate
                changes.append(change_ratio)
                
                # >10% change considered significant
                if change_ratio > 0.1:
                    significant_changes += 1
                    change_points.append({
                        "timestamp": analysis.data_points[i].timestamp,
                        "from_bitrate": prev_bitrate,
                        "to_bitrate": curr_bitrate,
                        "change_ratio": change_ratio
                    })
        
        return {
            "total_changes": len(changes),
            "significant_changes": significant_changes,
            "max_change": max(changes) if changes else 0,
            "change_points": sorted(change_points, key=lambda x: x["change_ratio"], reverse=True)[:5]
        }
    
    def _rate_sample_rate(self, sample_rate: int) -> str:
        """Rate sample rate"""
        if sample_rate >= 96000:
            return "Excellent - audiophile"
        elif sample_rate >= 48000:
            return "Good - professional quality"
        elif sample_rate >= 44100:
            return "Standard - CD quality"
        else:
            return "Low - consider increasing"
    
    def export_analysis_data(self, analysis: AudioBitrateAnalysis, output_path: str):
        """Export analysis data to JSON"""
        quality_assessment = self.assess_audio_quality(analysis)
        
        data = {
            "metadata": {
                "file_path": analysis.file_path,
                "analysis_time": datetime.now().isoformat(),
                "sample_interval": analysis.sample_interval,
                "duration": analysis.duration
            },
            "audio_info": {
                "codec": analysis.codec,
                "channels": analysis.channels,
                "sample_rate": analysis.sample_rate,
                "channel_layout": self.get_channel_layout(analysis.channels)
            },
            "statistics": {
                "average_bitrate": analysis.average_bitrate,
                "max_bitrate": analysis.max_bitrate,
                "min_bitrate": analysis.min_bitrate,
                "bitrate_variance": analysis.bitrate_variance,
                "stability": analysis.bitrate_stability,
                "bitrate_range_kbps": {
                    "min": analysis.min_bitrate / 1000,
                    "max": analysis.max_bitrate / 1000,
                    "avg": analysis.average_bitrate / 1000
                }
            },
            "quality_assessment": quality_assessment,
            "data_points": [
                {
                    "timestamp": dp.timestamp,
                    "bitrate": dp.bitrate,
                    "bitrate_kbps": dp.bitrate / 1000
                }
                for dp in analysis.data_points
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self._logger.info(f"Audio analysis exported to: {output_path}")
        
        # Print key info
        self._logger.info("Audio quality assessment:")
        self._logger.info(f"- Quality level: {quality_assessment['quality_level']}")
        self._logger.info(f"- Stability: {quality_assessment['stability']}")
        vbr_status = "Yes" if quality_assessment['is_vbr'] else "No"
        self._logger.info(f"- VBR: {vbr_status}")
        if quality_assessment['bitrate_changes']['significant_changes'] > 0:
            self._logger.info(f"- Significant bitrate changes: {quality_assessment['bitrate_changes']['significant_changes']}")
    
    def export_to_csv(self, analysis: AudioBitrateAnalysis, output_path: str):
        """Export to CSV format"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'bitrate_bps', 'bitrate_kbps'])
            
            for dp in analysis.data_points:
                writer.writerow([dp.timestamp, dp.bitrate, dp.bitrate / 1000])  # 保留原始值和kbps
        
        self._logger.info(f"Data exported to: {output_path}")


def analyze_multiple_audio(video_files: List[str], sample_interval: float = 15.0) -> List[AudioBitrateAnalysis]:
    """Analyze audio bitrate for multiple videos"""
    from .file_processor import FileProcessor
    
    processor = FileProcessor()
    analyzer = AudioBitrateAnalyzer(sample_interval)
    _logger = get_logger(__name__)
    
    results = []
    for video_file in video_files:
        try:
            processed_file = processor.process_input(video_file)
            result = analyzer.analyze(processed_file)
            results.append(result)
            _logger.info(f"Completed audio analysis: {video_file}")
            
        except Exception as e:
            _logger.error(f"Audio analysis failed {video_file}: {e}")
    
    return results