# 视频码率分析模块 - 技术文档

## 模块概述

视频码率分析模块负责分析视频流的码率变化情况，通过定时采样生成码率时间序列数据，用于后续的可视化分析。

## 核心功能

- 视频码率时间序列分析
- 标准模式采样（10秒间隔）
- 码率统计信息计算
- CBR/VBR类型检测

## 技术实现

### 核心类设计

```python
from dataclasses import dataclass
from typing import List
import numpy as np
import subprocess
from core.file_processor import ProcessedFile

@dataclass
class BitrateDataPoint:
    """码率数据点"""
    timestamp: float    # 时间戳(秒)
    bitrate: float     # 码率(bps)

@dataclass
class VideoBitrateAnalysis:
    """视频码率分析结果"""
    file_path: str
    duration: float
    
    # 统计信息
    average_bitrate: float    # 平均码率(bps)
    max_bitrate: float       # 最大码率(bps)
    min_bitrate: float       # 最小码率(bps)
    bitrate_variance: float  # 码率方差
    
    # 时间序列数据
    data_points: List[BitrateDataPoint]
    
    # 采样信息
    sample_interval: float   # 采样间隔(秒)
    
    @property
    def is_cbr(self) -> bool:
        """判断是否为恒定码率(CBR)"""
        if self.average_bitrate == 0:
            return False
        # 变异系数小于10%认为是CBR
        cv = np.sqrt(self.bitrate_variance) / self.average_bitrate
        return cv < 0.1

class VideoBitrateAnalyzer:
    """视频码率分析器"""
    
    def __init__(self, sample_interval: float = 10.0):
        self.sample_interval = sample_interval
    
    def analyze(self, processed_file: ProcessedFile) -> VideoBitrateAnalysis:
        """分析视频码率"""
        metadata = processed_file.load_metadata()
        
        if not metadata.video_codec:
            raise ValueError("文件不包含视频流")
        
        print(f"开始分析视频码率 (采样间隔: {self.sample_interval}秒)")
        
        # 生成采样时间点
        duration = metadata.duration
        sample_times = np.arange(0, duration, self.sample_interval)
        
        print(f"共需分析 {len(sample_times)} 个采样点...")
        
        # 采样分析
        data_points = []
        for i, timestamp in enumerate(sample_times):
            try:
                bitrate = self._get_bitrate_at_time(processed_file.file_path, timestamp)
                data_points.append(BitrateDataPoint(timestamp, bitrate))
                
                # 进度显示
                if (i + 1) % 10 == 0 or i == len(sample_times) - 1:
                    progress = (i + 1) / len(sample_times) * 100
                    print(f"进度: {progress:.1f}%")
                    
            except Exception as e:
                print(f"警告: 时间点 {timestamp:.1f}s 采样失败: {e}")
                # 使用平均码率作为备选值
                fallback_bitrate = metadata.video_bitrate or (metadata.bit_rate * 0.8)
                data_points.append(BitrateDataPoint(timestamp, fallback_bitrate))
        
        if not data_points:
            raise ValueError("无法获取有效的码率数据")
        
        # 计算统计信息
        bitrates = [dp.bitrate for dp in data_points]
        
        return VideoBitrateAnalysis(
            file_path=processed_file.file_path,
            duration=duration,
            average_bitrate=np.mean(bitrates),
            max_bitrate=np.max(bitrates),
            min_bitrate=np.min(bitrates),
            bitrate_variance=np.var(bitrates),
            data_points=data_points,
            sample_interval=self.sample_interval
        )
    
    def _get_bitrate_at_time(self, file_path: str, timestamp: float, window_size: float = 5.0) -> float:
        """获取指定时间点的码率"""
        start_time = max(0, timestamp - window_size/2)
        
        try:
            # 使用ffprobe分析指定时间段的包数据
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'packet=size',
                '-select_streams', 'v:0',  # 只选择第一个视频流
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