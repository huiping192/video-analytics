# 视频码率分析模块 - 技术文档

## 模块概述

视频码率分析模块负责分析视频流的码率变化情况，通过基于ffprobe的真实数据采样生成准确的码率时间序列数据，支持大型视频文件的高效分析。

## 核心功能

- 基于ffprobe的真实码率数据采样
- 时间窗口码率计算（默认10秒间隔）
- 完整的统计信息计算（平均值、方差、最值）
- CBR/VBR类型自动检测
- 质量评估和建议生成
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
class VideoBitrateDataPoint:
    """视频码率数据点"""
    timestamp: float    # 时间戳(秒)
    bitrate: float     # 码率(bps)

@dataclass
class VideoBitrateAnalysis:
    """视频码率分析结果"""
    file_path: str
    duration: float
    
    # 基础信息
    codec: str              # 视频编码器
    width: int              # 视频宽度
    height: int             # 视频高度
    fps: float              # 帧率
    
    # 统计信息
    average_bitrate: float    # 平均码率(bps)
    max_bitrate: float       # 最大码率(bps)
    min_bitrate: float       # 最小码率(bps)
    bitrate_variance: float  # 码率方差
    
    # 时间序列数据
    data_points: List[VideoBitrateDataPoint]
    
    # 采样信息
    sample_interval: float   # 采样间隔(秒)
    
    @property
    def bitrate_stability(self) -> float:
        """码率稳定性 (0-1, 数值越高表示越稳定)"""
        if self.average_bitrate == 0:
            return 0.0
        cv = np.sqrt(self.bitrate_variance) / self.average_bitrate
        return max(0, 1 - cv)
    
    @property
    def is_cbr(self) -> bool:
        """判断是否为恒定码率(CBR)"""
        # 变异系数小于10%认为是CBR
        return self.bitrate_stability > 0.9
    
    @property
    def quality_grade(self) -> str:
        """质量等级评估"""
        avg_mbps = self.average_bitrate / 1000000
        resolution = self.width * self.height
        
        # 基于分辨率和码率的质量评估
        if resolution >= 3840 * 2160:  # 4K
            if avg_mbps >= 25:
                return "Excellent"
            elif avg_mbps >= 15:
                return "Good"
            else:
                return "Poor"
        elif resolution >= 1920 * 1080:  # 1080p
            if avg_mbps >= 8:
                return "Excellent"
            elif avg_mbps >= 5:
                return "Good"
            else:
                return "Fair"
        else:  # 720p and below
            if avg_mbps >= 3:
                return "Good"
            elif avg_mbps >= 1.5:
                return "Fair"
            else:
                return "Poor"

class VideoBitrateAnalyzer:
    """视频码率分析器"""
    
    def __init__(self, sample_interval: float = 10.0):
        self.sample_interval = sample_interval
        self._logger = get_logger(__name__)
    
    def analyze(self, processed_file: ProcessedFile) -> VideoBitrateAnalysis:
        """分析视频码率"""
        metadata = processed_file.load_metadata()
        
        if not metadata.video_codec:
            raise ValueError("文件不包含视频流")
        
        self._logger.info(f"开始分析视频码率 (采样间隔: {self.sample_interval}秒)")
        
        # 生成采样时间点
        duration = metadata.duration
        sample_times = np.arange(0, duration, self.sample_interval)
        
        self._logger.debug(f"共需分析 {len(sample_times)} 个采样点...")
        
        # 采样分析
        data_points = []
        for i, timestamp in enumerate(sample_times):
            try:
                bitrate = self._get_video_bitrate_at_time(processed_file.file_path, timestamp)
                data_points.append(VideoBitrateDataPoint(timestamp, bitrate))
                
                # 进度显示
                if (i + 1) % 10 == 0 or i == len(sample_times) - 1:
                    progress = (i + 1) / len(sample_times) * 100
                    self._logger.debug(f"视频码率分析进度: {progress:.1f}%")
                    
            except Exception as e:
                self._logger.warning(f"时间点 {timestamp:.1f}s 采样失败: {e}")
                # 使用元数据码率作为备选值
                fallback_bitrate = metadata.video_bitrate or (metadata.bit_rate * 0.8) if metadata.bit_rate else 2000000
                data_points.append(VideoBitrateDataPoint(timestamp, fallback_bitrate))
        
        from ..utils.validators import ensure_non_empty_sequence
        ensure_non_empty_sequence("video bitrate data points", data_points)
        
        # 计算统计信息
        bitrates = [dp.bitrate for dp in data_points]
        
        return VideoBitrateAnalysis(
            file_path=processed_file.file_path,
            duration=duration,
            codec=metadata.video_codec,
            width=metadata.width,
            height=metadata.height,
            fps=metadata.fps,
            average_bitrate=float(np.mean(bitrates)),
            max_bitrate=float(np.max(bitrates)),
            min_bitrate=float(np.min(bitrates)),
            bitrate_variance=float(np.var(bitrates)),
            data_points=data_points,
            sample_interval=self.sample_interval
        )
    
    def _get_video_bitrate_at_time(self, file_path: str, timestamp: float, window_size: float = 5.0) -> float:
        """获取指定时间点的视频码率"""
        try:
            # 使用ffprobe分析指定时间段的视频包数据
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-select_streams', 'v:0',
                '-show_entries', 'packet=size,pts_time',
                '-of', 'csv=nk=1',
                '-ss', str(timestamp),
                '-t', str(window_size),
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0 or not result.stdout.strip():
                return self._get_fallback_video_bitrate(file_path)
            
            # 解析包数据
            total_bytes = 0
            packet_count = 0
            valid_timestamps = []
            
            for line in result.stdout.strip().split('\n'):
                if line and ',' in line:
                    try:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            size_str, pts_time_str = parts[0], parts[1]
                            
                            if size_str and pts_time_str:
                                packet_size = int(size_str)
                                pts_time = float(pts_time_str)
                                
                                # 确保在时间窗口内
                                if timestamp <= pts_time <= timestamp + window_size:
                                    total_bytes += packet_size
                                    packet_count += 1
                                    valid_timestamps.append(pts_time)
                    except (ValueError, IndexError):
                        continue
            
            if packet_count == 0 or not valid_timestamps:
                return self._get_fallback_video_bitrate(file_path)
            
            # 计算实际持续时间
            if len(valid_timestamps) > 1:
                actual_duration = max(valid_timestamps) - min(valid_timestamps)
                if actual_duration > 0:
                    bitrate = (total_bytes * 8) / actual_duration
                    return bitrate
            
            # 使用窗口时间如果时间戳无效
            return (total_bytes * 8) / window_size
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            self._logger.warning(f"视频码率分析失败于 {timestamp:.1f}s: {e}")
            return self._get_fallback_video_bitrate(file_path)
    
    def _get_fallback_video_bitrate(self, file_path: str) -> float:
        """获取备用视频码率"""
        try:
            # 尝试获取声明的视频流码率
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'stream=bit_rate',
                '-select_streams', 'v:0',
                '-of', 'csv=p=0',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            bitrate_str = result.stdout.strip()
            
            if bitrate_str and bitrate_str != 'N/A':
                return float(bitrate_str)
            else:
                # 如果不可用，从文件估算
                return self._estimate_video_bitrate_from_file(file_path)
                
        except Exception:
            return self._estimate_video_bitrate_from_file(file_path)
    
    def _estimate_video_bitrate_from_file(self, file_path: str) -> float:
        """从文件信息估算视频码率"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(file_path)
            
            format_info = probe.get('format', {})
            total_bitrate = format_info.get('bit_rate')
            
            if total_bitrate:
                # 视频通常占总码率的85-95%
                return float(total_bitrate) * 0.9
                
        except Exception:
            pass
        
        # 默认码率 (2 Mbps)
        return 2000000.0
    
    def export_analysis_data(self, analysis: VideoBitrateAnalysis, output_path: str):
        """导出分析数据为JSON"""
        quality_assessment = self.assess_video_quality(analysis)
        
        data = {
            "metadata": {
                "file_path": analysis.file_path,
                "analysis_time": datetime.now().isoformat(),
                "sample_interval": analysis.sample_interval,
                "duration": analysis.duration
            },
            "video_info": {
                "codec": analysis.codec,
                "resolution": f"{analysis.width}x{analysis.height}",
                "fps": analysis.fps
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
                    "bitrate": dp.bitrate,
                    "bitrate_mbps": dp.bitrate / 1000000
                }
                for dp in analysis.data_points
            ]
        }
        
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self._logger.info(f"视频码率分析导出至: {output_path}")
```

## 采样策略

### 标准模式采样
- **采样间隔**: 10秒
- **窗口大小**: 5秒 (每个采样点分析前后2.5秒的数据)
- **处理方式**: 计算时间窗口内的平均码率

### 大文件优化
```python
def _optimize_for_large_files(self, duration: float) -> float:
    """根据视频长度调整采样间隔"""
    if duration > 7200:  # 超过2小时
        return 30.0  # 30秒间隔
    elif duration > 3600:  # 1-2小时
        return 20.0  # 20秒间隔
    else:
        return self.sample_interval  # 默认10秒间隔
```

## 统计分析

### 基础统计信息
- **平均码率**: 所有采样点的平均值
- **最大码率**: 采样点中的最大值
- **最小码率**: 采样点中的最小值
- **码率方差**: 衡量码率变化程度

### CBR/VBR检测
```python
def analyze_encoding_type(self, analysis: VideoBitrateAnalysis) -> str:
    """分析编码类型"""
    if analysis.is_cbr:
        return f"CBR (恒定码率) - 变化幅度小于10%"
    else:
        cv = np.sqrt(analysis.bitrate_variance) / analysis.average_bitrate
        return f"VBR (可变码率) - 变异系数: {cv:.1%}"
```

## 错误处理

### 常见错误处理

```python
def _handle_analysis_errors(self, error: Exception, timestamp: float) -> float:
    """处理分析过程中的错误"""
    error_msg = str(error)
    
    if "Invalid data found" in error_msg:
        print(f"时间点 {timestamp:.1f}s: 检测到损坏数据，跳过")
        return 0.0
    
    elif "No such file" in error_msg:
        raise FileNotFoundError("视频文件不存在")
    
    else:
        print(f"时间点 {timestamp:.1f}s: 未知错误 - {error}")
        return 0.0
```

## 数据导出

### JSON导出

```python
import json
from datetime import datetime

def export_analysis_data(self, analysis: VideoBitrateAnalysis, output_path: str):
    """导出分析结果为JSON"""
    data = {
        "metadata": {
            "file_path": analysis.file_path,
            "analysis_time": datetime.now().isoformat(),
            "sample_interval": analysis.sample_interval,
            "duration": analysis.duration
        },
        "statistics": {
            "average_bitrate": analysis.average_bitrate,
            "max_bitrate": analysis.max_bitrate,
            "min_bitrate": analysis.min_bitrate,
            "bitrate_variance": analysis.bitrate_variance,
            "encoding_type": "CBR" if analysis.is_cbr else "VBR"
        },
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
    
    print(f"分析结果已导出到: {output_path}")
```

### CSV导出

```python
import pandas as pd

def export_to_csv(self, analysis: VideoBitrateAnalysis, output_path: str):
    """导出为CSV格式"""
    df = pd.DataFrame([
        {
            "timestamp": dp.timestamp,
            "bitrate_mbps": dp.bitrate / 1000000  # 转换为Mbps
        }
        for dp in analysis.data_points
    ])
    
    df.to_csv(output_path, index=False)
    print(f"数据已导出到: {output_path}")
```

## 使用示例

### 基本分析

```python
from core.video_analyzer import VideoBitrateAnalyzer
from core.file_processor import FileProcessor

# 处理文件
processor = FileProcessor()
processed_file = processor.process_input("video.mp4")

# 创建分析器
analyzer = VideoBitrateAnalyzer(sample_interval=10.0)

# 执行分析
try:
    result = analyzer.analyze(processed_file)
    
    print(f"视频文件: {result.file_path}")
    print(f"视频时长: {result.duration:.1f}秒")
    print(f"平均码率: {result.average_bitrate/1000000:.2f} Mbps")
    print(f"码率范围: {result.min_bitrate/1000000:.2f} - {result.max_bitrate/1000000:.2f} Mbps")
    print(f"编码类型: {'CBR' if result.is_cbr else 'VBR'}")
    print(f"采样点数: {len(result.data_points)}")
    
    # 导出数据
    analyzer.export_analysis_data(result, "bitrate_analysis.json")
    analyzer.export_to_csv(result, "bitrate_data.csv")
    
except Exception as e:
    print(f"分析失败: {e}")
```

### 批量分析

```python
def analyze_multiple_videos(video_files: List[str]) -> List[VideoBitrateAnalysis]:
    """批量分析多个视频"""
    processor = FileProcessor()
    analyzer = VideoBitrateAnalyzer()
    
    results = []
    for video_file in video_files:
        try:
            processed_file = processor.process_input(video_file)
            result = analyzer.analyze(processed_file)
            results.append(result)
            print(f"✓ 完成分析: {video_file}")
            
        except Exception as e:
            print(f"✗ 分析失败 {video_file}: {e}")
    
    return results

# 批量处理
video_files = ["video1.mp4", "video2.mp4", "video3.mp4"]
results = analyze_multiple_videos(video_files)
```

这个模块提供了简单有效的视频码率分析功能，专注于核心需求，避免了过度复杂的设计。