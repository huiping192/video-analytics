# FPS分析模块 - 技术文档

## 模块概述

FPS(Frames Per Second)分析模块负责分析视频的帧率变化和掉帧情况，通过标准模式采样检测视频播放质量问题。

## 核心功能

- 视频FPS时间序列分析
- 标准模式采样（10秒间隔）
- 基础掉帧检测
- 帧率稳定性评估

## 技术实现

### 核心类设计

```python
from dataclasses import dataclass
from typing import List
import numpy as np
import subprocess
from core.file_processor import ProcessedFile

@dataclass
class FPSDataPoint:
    """FPS数据点"""
    timestamp: float      # 时间戳(秒)
    fps: float           # 瞬时帧率
    frame_count: int     # 该时间窗口内的帧数
    dropped_frames: int  # 检测到的掉帧数

@dataclass
class FPSAnalysis:
    """FPS分析结果"""
    file_path: str
    duration: float
    
    # 帧率信息
    declared_fps: float      # 元数据中的声明帧率
    actual_average_fps: float # 实际平均帧率
    max_fps: float          # 最大瞬时帧率
    min_fps: float          # 最小瞬时帧率
    fps_variance: float     # 帧率方差
    
    # 帧数统计
    total_frames: int       # 总帧数
    total_dropped_frames: int # 总掉帧数
    
    # 时间序列数据
    data_points: List[FPSDataPoint]
    
    # 采样信息
    sample_interval: float   # 采样间隔(秒)
    
    @property
    def fps_stability(self) -> float:
        """帧率稳定性(0-1, 越接近1越稳定)"""
        if self.actual_average_fps == 0:
            return 0.0
        cv = np.sqrt(self.fps_variance) / self.actual_average_fps
        return max(0, 1 - cv)
    
    @property
    def drop_rate(self) -> float:
        """掉帧率"""
        if self.total_frames == 0:
            return 0.0
        return self.total_dropped_frames / self.total_frames
    
    @property
    def performance_grade(self) -> str:
        """性能等级评估"""
        if self.drop_rate < 0.01 and self.fps_stability > 0.95:
            return "优秀"
        elif self.drop_rate < 0.05 and self.fps_stability > 0.9:
            return "良好"
        elif self.drop_rate < 0.1 and self.fps_stability > 0.8:
            return "一般"
        else:
            return "较差"

class FPSAnalyzer:
    """FPS分析器"""
    
    def __init__(self, sample_interval: float = 10.0):
        self.sample_interval = sample_interval
        self.drop_threshold = 0.8  # 低于80%的期望帧率认为有掉帧
    
    def analyze(self, processed_file: ProcessedFile) -> FPSAnalysis:
        """分析视频FPS"""
        metadata = processed_file.load_metadata()
        
        if not metadata.video_codec:
            raise ValueError("文件不包含视频流")
        
        declared_fps = metadata.fps
        if declared_fps <= 0:
            raise ValueError("无法获取视频帧率信息")
        
        print(f"开始分析FPS (声明帧率: {declared_fps:.2f}fps, 采样间隔: {self.sample_interval}秒)")
        
        # 生成采样时间点
        duration = metadata.duration
        sample_times = np.arange(0, duration, self.sample_interval)
        
        print(f"共需分析 {len(sample_times)} 个采样点...")
        
        # 采样分析
        data_points = []
        total_frames = 0
        total_dropped = 0
        
        for i, timestamp in enumerate(sample_times):
            try:
                fps_data = self._analyze_fps_window(
                    processed_file.file_path, 
                    timestamp, 
                    declared_fps
                )
                data_points.append(fps_data)
                total_frames += fps_data.frame_count
                total_dropped += fps_data.dropped_frames
                
                # 进度显示
                if (i + 1) % 5 == 0 or i == len(sample_times) - 1:
                    progress = (i + 1) / len(sample_times) * 100
                    print(f"FPS分析进度: {progress:.1f}%")
                    
            except Exception as e:
                print(f"警告: 时间点 {timestamp:.1f}s FPS采样失败: {e}")
                # 使用声明帧率作为备选值
                fallback_fps_data = FPSDataPoint(
                    timestamp=timestamp,
                    fps=declared_fps,
                    frame_count=int(declared_fps * self.sample_interval),
                    dropped_frames=0
                )
                data_points.append(fallback_fps_data)
                total_frames += fallback_fps_data.frame_count
        
        if not data_points:
            raise ValueError("无法获取有效的FPS数据")
        
        # 计算统计信息
        fps_values = [dp.fps for dp in data_points]
        actual_avg_fps = total_frames / duration if duration > 0 else 0
        
        return FPSAnalysis(
            file_path=processed_file.file_path,
            duration=duration,
            declared_fps=declared_fps,
            actual_average_fps=actual_avg_fps,
            max_fps=np.max(fps_values),
            min_fps=np.min(fps_values),
            fps_variance=np.var(fps_values),
            total_frames=total_frames,
            total_dropped_frames=total_dropped,
            data_points=data_points,
            sample_interval=self.sample_interval
        )
    
    def _analyze_fps_window(self, file_path: str, timestamp: float, expected_fps: float, 
                           window_size: float = 5.0) -> FPSDataPoint:
        """分析指定时间窗口的FPS"""
        start_time = max(0, timestamp - window_size/2)
        
        try:
            # 使用ffprobe获取帧信息
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'frame=pkt_pts_time',
                '-select_streams', 'v:0',
                '-ss', str(start_time),
                '-t', str(window_size),
                '-of', 'csv=p=0',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            
            # 解析帧时间戳
            frame_times = []
            for line in lines:
                if line.strip():
                    try:
                        frame_time = float(line.strip())
                        frame_times.append(frame_time)
                    except ValueError:
                        continue
            
            frame_count = len(frame_times)
            
            if frame_count < 2:
                return FPSDataPoint(
                    timestamp=timestamp,
                    fps=0.0,
                    frame_count=frame_count,
                    dropped_frames=0
                )
            
            # 计算实际FPS
            time_span = max(frame_times) - min(frame_times)
            if time_span > 0:
                actual_fps = (frame_count - 1) / time_span
            else:
                actual_fps = 0.0
            
            # 检测掉帧
            dropped_frames = self._detect_dropped_frames(frame_times, expected_fps)
            
            return FPSDataPoint(
                timestamp=timestamp,
                fps=actual_fps,
                frame_count=frame_count,
                dropped_frames=dropped_frames
            )
            
        except subprocess.CalledProcessError as e:
            raise ValueError(f"FFprobe执行失败: {e}")
    
    def _detect_dropped_frames(self, frame_times: List[float], expected_fps: float) -> int:
        """简单的掉帧检测"""
        if len(frame_times) < 2 or expected_fps <= 0:
            return 0
        
        expected_interval = 1.0 / expected_fps
        tolerance = expected_interval * 0.5  # 50%容差
        
        dropped_count = 0
        for i in range(1, len(frame_times)):
            actual_interval = frame_times[i] - frame_times[i-1]
            
            # 如果间隔明显大于期望间隔，估算掉帧数
            if actual_interval > expected_interval + tolerance:
                estimated_drops = int(actual_interval / expected_interval) - 1
                dropped_count += max(0, estimated_drops)
        
        return dropped_count
```

## 性能评估

### FPS质量分析

```python
def analyze_fps_quality(self, analysis: FPSAnalysis) -> dict:
    """分析FPS质量"""
    quality_report = {
        "performance_grade": analysis.performance_grade,
        "fps_consistency": f"{analysis.fps_stability:.1%}",
        "drop_rate": f"{analysis.drop_rate:.2%}",
        "fps_accuracy": self._calculate_fps_accuracy(analysis),
        "issues": [],
        "recommendations": []
    }
    
    # 检测问题
    if analysis.drop_rate > 0.05:  # 超过5%掉帧率
        quality_report["issues"].append(f"掉帧率较高: {analysis.drop_rate:.1%}")
        quality_report["recommendations"].append("检查视频编码设置或源文件质量")
    
    if analysis.fps_stability < 0.9:  # 稳定性低于90%
        quality_report["issues"].append("帧率不够稳定")
        quality_report["recommendations"].append("可能存在VFR编码或性能问题")
    
    fps_diff = abs(analysis.declared_fps - analysis.actual_average_fps)
    if fps_diff > 1.0:  # 声明帧率与实际帧率差异大于1fps
        quality_report["issues"].append(f"实际帧率与声明帧率差异较大: {fps_diff:.1f}fps")
    
    if not quality_report["issues"]:
        quality_report["recommendations"].append("FPS表现良好，无需改进")
    
    return quality_report

def _calculate_fps_accuracy(self, analysis: FPSAnalysis) -> str:
    """计算FPS准确性"""
    if analysis.declared_fps == 0:
        return "无法计算"
    
    accuracy = 1 - abs(analysis.declared_fps - analysis.actual_average_fps) / analysis.declared_fps
    accuracy = max(0, accuracy)  # 确保不为负数
    
    return f"{accuracy:.1%}"
```

### 掉帧严重程度分析

```python
def analyze_drop_severity(self, analysis: FPSAnalysis) -> dict:
    """分析掉帧严重程度"""
    drop_analysis = {
        "total_drops": analysis.total_dropped_frames,
        "drop_rate": analysis.drop_rate,
        "severity": "正常",
        "affected_time": 0.0,
        "worst_segments": []
    }
    
    # 找出掉帧最严重的时间段
    serious_drops = []
    affected_time = 0.0
    
    for dp in analysis.data_points:
        if dp.dropped_frames > 0:
            affected_time += analysis.sample_interval
            if dp.dropped_frames > 2:  # 单个窗口掉帧超过2帧
                serious_drops.append((dp.timestamp, dp.dropped_frames))
    
    drop_analysis["affected_time"] = affected_time
    drop_analysis["worst_segments"] = sorted(serious_drops, key=lambda x: x[1], reverse=True)[:5]
    
    # 判断严重程度
    if analysis.drop_rate > 0.1:
        drop_analysis["severity"] = "严重"
    elif analysis.drop_rate > 0.05:
        drop_analysis["severity"] = "中等"
    elif analysis.drop_rate > 0.01:
        drop_analysis["severity"] = "轻微"
    
    return drop_analysis
```

## 数据导出

### JSON导出

```python
import json
from datetime import datetime

def export_analysis_data(self, analysis: FPSAnalysis, output_path: str):
    """导出FPS分析结果为JSON"""
    quality_report = self.analyze_fps_quality(analysis)
    drop_analysis = self.analyze_drop_severity(analysis)
    
    data = {
        "metadata": {
            "file_path": analysis.file_path,
            "analysis_time": datetime.now().isoformat(),
            "sample_interval": analysis.sample_interval,
            "duration": analysis.duration
        },
        "fps_info": {
            "declared_fps": analysis.declared_fps,
            "actual_average_fps": analysis.actual_average_fps,
            "fps_range": {
                "min": analysis.min_fps,
                "max": analysis.max_fps
            },
            "fps_variance": analysis.fps_variance,
            "fps_stability": analysis.fps_stability
        },
        "frame_statistics": {
            "total_frames": analysis.total_frames,
            "total_dropped_frames": analysis.total_dropped_frames,
            "drop_rate": analysis.drop_rate
        },
        "quality_assessment": quality_report,
        "drop_analysis": drop_analysis,
        "data_points": [
            {
                "timestamp": dp.timestamp,
                "fps": dp.fps,
                "frame_count": dp.frame_count,
                "dropped_frames": dp.dropped_frames
            }
            for dp in analysis.data_points
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"FPS分析结果已导出到: {output_path}")
```

## 错误处理

### FPS分析错误处理

```python
def _handle_fps_errors(self, error: Exception, file_path: str) -> FPSAnalysis:
    """处理FPS分析错误"""
    error_str = str(error)
    
    if "No video frames found" in error_str:
        raise ValueError("文件不包含视频帧")
    
    elif "Invalid frame timestamps" in error_str:
        print("帧时间戳异常，使用备选分析方法...")
        return self._fallback_fps_analysis(file_path)
    
    else:
        raise ValueError(f"FPS分析失败: {error}")

def _fallback_fps_analysis(self, file_path: str) -> FPSAnalysis:
    """备选FPS分析方法（基于元数据估算）"""
    try:
        processor = FileProcessor()
        processed_file = processor.process_input(file_path)
        metadata = processed_file.load_metadata()
        
        declared_fps = metadata.fps
        duration = metadata.duration
        
        # 使用声明帧率创建简单的分析结果
        estimated_frames = int(declared_fps * duration)
        
        # 创建单个数据点
        data_point = FPSDataPoint(
            timestamp=duration / 2,
            fps=declared_fps,
            frame_count=estimated_frames,
            dropped_frames=0
        )
        
        return FPSAnalysis(
            file_path=file_path,
            duration=duration,
            declared_fps=declared_fps,
            actual_average_fps=declared_fps,  # 假设相等
            max_fps=declared_fps,
            min_fps=declared_fps,
            fps_variance=0.0,  # 假设稳定
            total_frames=estimated_frames,
            total_dropped_frames=0,
            data_points=[data_point],
            sample_interval=0
        )
        
    except Exception as e:
        raise ValueError(f"备选分析也失败: {e}")
```

## 使用示例

### 基本FPS分析

```python
from core.fps_analyzer import FPSAnalyzer
from core.file_processor import FileProcessor

# 处理文件
processor = FileProcessor()
processed_file = processor.process_input("video.mp4")

# 创建分析器
analyzer = FPSAnalyzer(sample_interval=10.0)

try:
    result = analyzer.analyze(processed_file)
    
    print(f"视频文件: {result.file_path}")
    print(f"声明帧率: {result.declared_fps:.2f}fps")
    print(f"实际平均帧率: {result.actual_average_fps:.2f}fps")
    print(f"帧率稳定性: {result.fps_stability:.1%}")
    print(f"总帧数: {result.total_frames}")
    print(f"掉帧数: {result.total_dropped_frames}")
    print(f"掉帧率: {result.drop_rate:.2%}")
    print(f"性能等级: {result.performance_grade}")
    
    # 质量分析
    quality = analyzer.analyze_fps_quality(result)
    print(f"\n质量评估:")
    print(f"性能等级: {quality['performance_grade']}")
    print(f"FPS一致性: {quality['fps_consistency']}")
    print(f"FPS准确性: {quality['fps_accuracy']}")
    
    if quality['issues']:
        print(f"\n发现的问题:")
        for issue in quality['issues']:
            print(f"- {issue}")
    
    if quality['recommendations']:
        print(f"\n建议:")
        for rec in quality['recommendations']:
            print(f"- {rec}")
    
    # 掉帧分析
    drop_info = analyzer.analyze_drop_severity(result)
    if drop_info['worst_segments']:
        print(f"\n最严重掉帧时间段:")
        for timestamp, drops in drop_info['worst_segments'][:3]:
            print(f"- {timestamp:.1f}s: {drops}帧")
    
    # 导出数据
    analyzer.export_analysis_data(result, "fps_analysis.json")
    
except Exception as e:
    print(f"FPS分析失败: {e}")
```

### FPS对比分析

```python
def compare_fps_performance(file_paths: List[str]):
    """对比多个视频的FPS性能"""
    analyzer = FPSAnalyzer()
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
    print("\nFPS性能对比:")
    print("-" * 90)
    print(f"{'文件名':<20} {'声明FPS':<10} {'实际FPS':<10} {'掉帧率':<8} {'稳定性':<8} {'等级':<8}")
    print("-" * 90)
    
    for result in results:
        filename = result.file_path.split('/')[-1][:18]
        print(f"{filename:<20} {result.declared_fps:>6.1f}fps {result.actual_average_fps:>6.1f}fps "
              f"{result.drop_rate:>6.1%} {result.fps_stability:>6.1%} {result.performance_grade:<8}")

# 使用示例
video_files = ["video1.mp4", "video2.mp4", "video3.mp4"]
compare_fps_performance(video_files)
```

这个模块提供了简单有效的FPS分析功能，专注于实用的帧率监测和掉帧检测需求。