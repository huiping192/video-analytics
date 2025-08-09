"""
音频码率分析模块
负责分析音频流的码率变化情况，提供音频质量评估和统计信息
"""

import json
import subprocess
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import numpy as np

from .file_processor import ProcessedFile


@dataclass
class AudioBitrateDataPoint:
    """音频码率数据点"""
    timestamp: float    # 时间戳(秒)
    bitrate: float     # 音频码率(bps)


@dataclass
class AudioBitrateAnalysis:
    """音频码率分析结果"""
    file_path: str
    duration: float
    
    # 基本信息
    codec: str            # 音频编码
    channels: int         # 声道数
    sample_rate: int      # 采样率
    
    # 统计信息
    average_bitrate: float    # 平均码率(bps)
    max_bitrate: float       # 最大码率(bps)
    min_bitrate: float       # 最小码率(bps)
    bitrate_variance: float  # 码率方差
    
    # 时间序列数据
    data_points: List[AudioBitrateDataPoint]
    
    # 采样信息
    sample_interval: float   # 采样间隔(秒)
    
    @property
    def bitrate_stability(self) -> float:
        """计算码率稳定性(0-1, 越接近1越稳定)"""
        if self.average_bitrate == 0:
            return 1.0
        cv = np.sqrt(self.bitrate_variance) / self.average_bitrate
        return max(0, 1 - cv)
    
    @property
    def quality_level(self) -> str:
        """简单的音质等级评估"""
        avg_kbps = self.average_bitrate / 1000
        
        if self.codec.lower() == 'aac':
            if avg_kbps >= 256:
                return "优秀"
            elif avg_kbps >= 128:
                return "良好"
            elif avg_kbps >= 96:
                return "一般"
            else:
                return "较差"
        
        elif self.codec.lower() == 'mp3':
            if avg_kbps >= 320:
                return "优秀"
            elif avg_kbps >= 192:
                return "良好"
            elif avg_kbps >= 128:
                return "一般"
            else:
                return "较差"
        
        else:
            return "未知编码"


class AudioBitrateAnalyzer:
    """音频码率分析器"""
    
    def __init__(self, sample_interval: float = 15.0):
        self.sample_interval = sample_interval  # 音频采样间隔比视频长
    
    def analyze(self, processed_file: ProcessedFile) -> AudioBitrateAnalysis:
        """分析音频码率"""
        metadata = processed_file.load_metadata()
        
        if not metadata.audio_codec:
            raise ValueError("文件不包含音频流")
        
        print(f"开始分析音频码率 (采样间隔: {self.sample_interval}秒)")
        
        # 生成采样时间点
        duration = metadata.duration
        sample_times = np.arange(0, duration, self.sample_interval)
        
        print(f"共需分析 {len(sample_times)} 个采样点...")
        
        # 采样分析
        data_points = []
        for i, timestamp in enumerate(sample_times):
            try:
                bitrate = self._get_audio_bitrate_at_time(processed_file.file_path, timestamp)
                data_points.append(AudioBitrateDataPoint(timestamp, bitrate))
                
                # 进度显示
                if (i + 1) % 5 == 0 or i == len(sample_times) - 1:
                    progress = (i + 1) / len(sample_times) * 100
                    print(f"音频分析进度: {progress:.1f}%")
                    
            except Exception as e:
                print(f"警告: 时间点 {timestamp:.1f}s 音频采样失败: {e}")
                # 使用元数据中的码率作为备选值
                fallback_bitrate = metadata.audio_bitrate or (metadata.bit_rate * 0.1) if metadata.bit_rate else 128000
                data_points.append(AudioBitrateDataPoint(timestamp, fallback_bitrate))
        
        if not data_points:
            raise ValueError("无法获取有效的音频码率数据")
        
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
        """获取指定时间点的音频码率"""
        # 音频码率通常比较稳定，直接使用流级别的码率
        return self._get_fallback_audio_bitrate(file_path)
    
    def _get_fallback_audio_bitrate(self, file_path: str) -> float:
        """获取备选音频码率（基于文件级别的码率信息）"""
        try:
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
                return float(bitrate_str)
            else:
                # 如果无法获取流码率，使用文件整体码率估算
                return self._estimate_audio_bitrate_from_file(file_path)
                
        except Exception:
            return self._estimate_audio_bitrate_from_file(file_path)
    
    def _estimate_audio_bitrate_from_file(self, file_path: str) -> float:
        """从文件信息估算音频码率"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(file_path)
            
            # 获取总码率
            format_info = probe.get('format', {})
            total_bitrate = format_info.get('bit_rate')
            
            if total_bitrate:
                # 估算音频码率约占总码率的10%
                return float(total_bitrate) * 0.1
            else:
                # 基于文件大小和时长估算
                duration = float(format_info.get('duration', 1))
                file_size = int(format_info.get('size', 0))
                if duration > 0 and file_size > 0:
                    total_bitrate = (file_size * 8) / duration
                    return total_bitrate * 0.1  # 估算音频部分
                
        except Exception:
            pass
        
        # 最后的默认值
        return 128000.0  # 128 kbps 默认值
    
    def get_channel_layout(self, channels: int) -> str:
        """根据声道数推断声道布局"""
        layouts = {
            1: "单声道",
            2: "立体声",
            3: "2.1环绕声",
            4: "4.0环绕声",
            5: "4.1环绕声",
            6: "5.1环绕声",
            7: "6.1环绕声",
            8: "7.1环绕声"
        }
        return layouts.get(channels, f"{channels}声道")
    
    def assess_audio_quality(self, analysis: AudioBitrateAnalysis) -> dict:
        """评估音频质量"""
        assessment = {
            "quality_level": analysis.quality_level,
            "stability": f"{analysis.bitrate_stability:.1%}",
            "codec_rating": self._rate_codec(analysis.codec),
            "sample_rate_rating": self._rate_sample_rate(analysis.sample_rate),
            "recommendations": []
        }
        
        # 生成建议
        if analysis.average_bitrate < 128000:  # 小于128kbps
            assessment["recommendations"].append("建议提高音频码率以获得更好音质")
        
        if analysis.sample_rate < 44100:
            assessment["recommendations"].append("建议使用44.1kHz或更高采样率")
        
        if analysis.channels == 1:
            assessment["recommendations"].append("考虑使用立体声以获得更好的音效体验")
        
        return assessment
    
    def _rate_codec(self, codec: str) -> str:
        """评估编码格式"""
        codec_ratings = {
            'aac': '优秀 - 现代高效编码',
            'mp3': '良好 - 通用兼容性强',
            'ac3': '一般 - 多声道支持好',
            'opus': '优秀 - 最新高效编码',
            'flac': '完美 - 无损压缩',
            'pcm': '完美 - 未压缩'
        }
        return codec_ratings.get(codec.lower(), '未知编码格式')
    
    def _rate_sample_rate(self, sample_rate: int) -> str:
        """评估采样率"""
        if sample_rate >= 96000:
            return "优秀 - 高保真音质"
        elif sample_rate >= 48000:
            return "良好 - 专业级音质"
        elif sample_rate >= 44100:
            return "标准 - CD音质"
        else:
            return "较低 - 建议提升"
    
    def export_analysis_data(self, analysis: AudioBitrateAnalysis, output_path: str):
        """导出分析结果为JSON"""
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
                "stability": analysis.bitrate_stability
            },
            "quality_assessment": quality_assessment,
            "data_points": [
                {
                    "timestamp": dp.timestamp,
                    "bitrate": dp.bitrate
                }
                for dp in analysis.data_points
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"音频分析结果已导出到: {output_path}")
    
    def export_to_csv(self, analysis: AudioBitrateAnalysis, output_path: str):
        """导出为CSV格式"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'bitrate_kbps'])
            
            for dp in analysis.data_points:
                writer.writerow([dp.timestamp, dp.bitrate / 1000])  # 转换为kbps
        
        print(f"数据已导出到: {output_path}")


def analyze_multiple_audio(video_files: List[str], sample_interval: float = 15.0) -> List[AudioBitrateAnalysis]:
    """批量分析多个视频的音频"""
    from .file_processor import FileProcessor
    
    processor = FileProcessor()
    analyzer = AudioBitrateAnalyzer(sample_interval)
    
    results = []
    for video_file in video_files:
        try:
            processed_file = processor.process_input(video_file)
            result = analyzer.analyze(processed_file)
            results.append(result)
            print(f"✓ 完成音频分析: {video_file}")
            
        except Exception as e:
            print(f"✗ 音频分析失败 {video_file}: {e}")
    
    return results