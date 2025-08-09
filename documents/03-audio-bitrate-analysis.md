# 音频码率分析模块 - 技术文档

## 模块概述

音频码率分析模块负责分析音频流的码率变化情况，通过基于ffprobe的音频包分析提供准确的码率数据和全面的质量评估。支持CBR/VBR检测和质量问题诊断。

## 核心功能

- 基于ffprobe音频包的真实码率分析
- 时间窗口音频码率计算（默认15秒间隔）
- 完整的音频信息提取（编码器、声道、采样率）
- CBR/VBR自动检测
- 全面的音频质量评估和问题诊断
- 质量改进建议生成
- 数据导出（JSON/CSV格式）

## 技术实现

### 核心类设计

```python
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import subprocess
from datetime import datetime
from video_analytics.core.file_processor import ProcessedFile
from video_analytics.utils.logger import get_logger

@dataclass
class AudioBitrateDataPoint:
    """音频码率数据点"""
    timestamp: float       # 时间戳(秒)
    bitrate: float        # 音频码率(bps)

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
        """音质等级评估（英文标签）"""
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
    """音频码率分析器"""
    
    def __init__(self, sample_interval: float = 15.0):
        self.sample_interval = sample_interval  # 音频采样间隔
        self._bitrate_cache = {}  # 码率缓存
        self._logger = get_logger(__name__)
    
    def analyze(self, processed_file: ProcessedFile) -> AudioBitrateAnalysis:
        """分析音频码率"""
        metadata = processed_file.load_metadata()
        
        if not metadata.audio_codec:
            raise ValueError("文件不包含音频流")
        
        self._logger.info(f"开始分析音频码率 (采样间隔: {self.sample_interval}秒)")
        
        # 生成采样时间点
        duration = metadata.duration
        sample_times = np.arange(0, duration, self.sample_interval)
        
        self._logger.debug(f"共需分析 {len(sample_times)} 个采样点...")
        
        # 采样分析
        data_points = []
        for i, timestamp in enumerate(sample_times):
            try:
                bitrate = self._get_audio_bitrate_at_time(processed_file.file_path, timestamp)
                data_points.append(AudioBitrateDataPoint(timestamp, bitrate))
                
                # 进度显示
                if (i + 1) % 5 == 0 or i == len(sample_times) - 1:
                    progress = (i + 1) / len(sample_times) * 100
                    self._logger.debug(f"音频分析进度: {progress:.1f}%")
                    
            except Exception as e:
                self._logger.warning(f"音频采样失败于 {timestamp:.1f}s: {e}")
                # 使用元数据码率作为备选值
                fallback_bitrate = metadata.audio_bitrate or (metadata.bit_rate * 0.1) if metadata.bit_rate else 128000
                data_points.append(AudioBitrateDataPoint(timestamp, fallback_bitrate))
        
        from ..utils.validators import ensure_non_empty_sequence
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
                    print(f"音频分析进度: {progress:.1f}%")
                    
            except Exception as e:
                print(f"警告: 时间点 {timestamp:.1f}s 音频采样失败: {e}")
                # 使用元数据中的码率作为备选值
                fallback_bitrate = metadata.audio_bitrate or (metadata.bit_rate * 0.1)
                data_points.append(AudioBitrateDataPoint(timestamp, fallback_bitrate))
        
        if not data_points:
            raise ValueError("无法获取有效的音频码率数据")
        
        # 计算统计信息
        bitrates = [dp.bitrate for dp in data_points]
        
        return AudioBitrateAnalysis(
            file_path=processed_file.file_path,
            duration=duration,
            codec=metadata.audio_codec,
            channels=metadata.channels,
            sample_rate=metadata.sample_rate,
            average_bitrate=np.mean(bitrates),
            max_bitrate=np.max(bitrates),
            min_bitrate=np.min(bitrates),
            bitrate_variance=np.var(bitrates),
            data_points=data_points,
            sample_interval=self.sample_interval
        )
    
    def _get_audio_bitrate_at_time(self, file_path: str, timestamp: float, window_size: float = 10.0) -> float:
        """获取指定时间点的音频码率"""
        start_time = max(0, timestamp - window_size/2)
        
        try:
            # 使用ffprobe分析指定时间段的音频包数据
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'packet=size',
                '-select_streams', 'a:0',  # 只选择第一个音频流
                '-ss', str(start_time),
                '-t', str(window_size),
                '-of', 'csv=p=0',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            
            # 计算总字节数
            total_bytes = 0
            packet_count = 0
            
            for line in lines:
                if line.strip():
                    try:
                        packet_size = int(line.strip())
                        total_bytes += packet_size
                        packet_count += 1
                    except ValueError:
                        continue
            
            if packet_count > 0:
                # 计算码率 (字节转换为比特，除以时间窗口)
                bitrate = (total_bytes * 8) / window_size
                return bitrate
            else:
                return 0.0
                
        except subprocess.CalledProcessError as e:
            raise ValueError(f"FFprobe执行失败: {e}")
```

## 音频特性分析

### 声道配置检测

```python
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
```

### 音频质量评估

```python
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
```

## 数据导出

### JSON导出

```python
import json
from datetime import datetime

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
```

## 错误处理

### 音频特有错误处理

```python
def _handle_audio_errors(self, error: Exception, file_path: str) -> AudioBitrateAnalysis:
    """处理音频分析错误"""
    error_str = str(error)
    
    if "No audio stream found" in error_str:
        raise ValueError("文件不包含音频流")
    
    elif "Unsupported codec" in error_str:
        print("检测到不常见的音频编码，使用通用分析方法...")
        return self._fallback_audio_analysis(file_path)
    
    elif "Corrupted audio data" in error_str:
        print("音频数据部分损坏，将跳过损坏部分...")
        return self._analyze_with_error_tolerance(file_path)
    
    else:
        raise ValueError(f"音频分析失败: {error}")

def _fallback_audio_analysis(self, file_path: str) -> AudioBitrateAnalysis:
    """备选音频分析方法（基于文件信息估算）"""
    try:
        processor = FileProcessor()
        processed_file = processor.process_input(file_path)
        metadata = processed_file.load_metadata()
        
        # 使用元数据估算
        estimated_bitrate = metadata.audio_bitrate or (metadata.bit_rate * 0.1)
        
        # 创建单个数据点
        data_point = AudioBitrateDataPoint(
            timestamp=metadata.duration / 2,
            bitrate=estimated_bitrate
        )
        
        return AudioBitrateAnalysis(
            file_path=file_path,
            duration=metadata.duration,
            codec=metadata.audio_codec or "unknown",
            channels=metadata.channels or 2,
            sample_rate=metadata.sample_rate or 44100,
            average_bitrate=estimated_bitrate,
            max_bitrate=estimated_bitrate,
            min_bitrate=estimated_bitrate,
            bitrate_variance=0.0,
            data_points=[data_point],
            sample_interval=0
        )
        
    except Exception as e:
        raise ValueError(f"备选分析也失败: {e}")
```

## 使用示例

### 基本音频分析

```python
from core.audio_analyzer import AudioBitrateAnalyzer
from core.file_processor import FileProcessor

# 处理文件
processor = FileProcessor()
processed_file = processor.process_input("video.mp4")

# 创建分析器
analyzer = AudioBitrateAnalyzer(sample_interval=15.0)

try:
    result = analyzer.analyze(processed_file)
    
    print(f"音频编码: {result.codec}")
    print(f"声道配置: {result.channels}ch ({analyzer.get_channel_layout(result.channels)})")
    print(f"采样率: {result.sample_rate}Hz")
    print(f"平均码率: {result.average_bitrate/1000:.1f} kbps")
    print(f"码率稳定性: {result.bitrate_stability:.1%}")
    print(f"音质等级: {result.quality_level}")
    
    # 质量评估
    quality = analyzer.assess_audio_quality(result)
    print(f"\n质量评估:")
    print(f"编码格式: {quality['codec_rating']}")
    print(f"采样率: {quality['sample_rate_rating']}")
    
    if quality['recommendations']:
        print(f"\n改进建议:")
        for rec in quality['recommendations']:
            print(f"- {rec}")
    
    # 导出数据
    analyzer.export_analysis_data(result, "audio_analysis.json")
    
except Exception as e:
    print(f"音频分析失败: {e}")
```

### 音频格式对比分析

```python
def compare_audio_formats(file_paths: List[str]):
    """对比多个文件的音频格式"""
    analyzer = AudioBitrateAnalyzer()
    processor = FileProcessor()
    
    results = []
    for file_path in file_paths:
        try:
            processed_file = processor.process_input(file_path)
            result = analyzer.analyze(processed_file)
            results.append(result)
        except Exception as e:
            print(f"分析失败 {file_path}: {e}")
    
    # 打印对比结果
    print("\n音频格式对比:")
    print("-" * 80)
    print(f"{'文件名':<20} {'编码':<8} {'码率':<10} {'声道':<6} {'采样率':<8} {'质量':<8}")
    print("-" * 80)
    
    for result in results:
        filename = result.file_path.split('/')[-1][:18]
        print(f"{filename:<20} {result.codec:<8} {result.average_bitrate/1000:>6.1f}k "
              f"{result.channels:<6} {result.sample_rate:<8} {result.quality_level:<8}")

# 使用示例
video_files = ["video1.mp4", "video2.mp4", "video3.mp4"]
compare_audio_formats(video_files)
```

这个模块提供了简洁实用的音频码率分析功能，专注于核心的音频质量评估需求。