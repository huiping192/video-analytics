"""
FPS分析模块
负责分析视频流的帧率变化情况，提供掉帧检测和性能评估
"""

import json
import subprocess
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import numpy as np

from .file_processor import ProcessedFile


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
        self.vfr_threshold = 0.1   # FPS变异系数超过10%认为是VFR视频
    
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
        # 修正实际平均帧率计算 - 基于采样点的FPS值
        actual_avg_fps = np.mean(fps_values) if fps_values else 0
        
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
        """分析指定时间窗口的真实FPS"""
        try:
            # 检查这个时间点是否超出文件时长
            metadata = self._get_file_metadata(file_path)
            duration = metadata['duration']
            
            if timestamp > duration:
                # 超出文件时长，返回空数据点
                return FPSDataPoint(
                    timestamp=timestamp,
                    fps=0.0,
                    frame_count=0,
                    dropped_frames=0
                )
            
            # 获取真实帧时间戳
            frame_times = self._get_frame_timestamps(file_path, timestamp, window_size)
            
            if not frame_times:
                # 无法获取帧时间戳，使用fallback
                return self._fallback_fps_data_point(timestamp, expected_fps, window_size)
            
            # 计算实际帧数
            actual_frame_count = len(frame_times)
            
            # 计算实际FPS
            if len(frame_times) > 1:
                # 基于实际时间跨度计算FPS
                time_span = frame_times[-1] - frame_times[0]
                if time_span > 0:
                    actual_fps = (actual_frame_count - 1) / time_span
                else:
                    actual_fps = expected_fps
            else:
                actual_fps = expected_fps
            
            # 检测掉帧
            dropped_frames = self._detect_dropped_frames_in_window(
                frame_times, expected_fps, window_size
            )
            
            return FPSDataPoint(
                timestamp=timestamp,
                fps=actual_fps,
                frame_count=actual_frame_count,
                dropped_frames=dropped_frames
            )
            
        except Exception as e:
            print(f"警告: 时间点 {timestamp:.1f}s 真实FPS分析失败: {e}")
            # 异常情况下使用备选方法
            return self._fallback_fps_data_point(timestamp, expected_fps, window_size)
    
    def _fallback_fps_data_point(self, timestamp: float, expected_fps: float, window_size: float) -> FPSDataPoint:
        """创建备选的FPS数据点"""
        window_expected_frames = int(expected_fps * window_size)
        return FPSDataPoint(
            timestamp=timestamp,
            fps=expected_fps,
            frame_count=window_expected_frames,
            dropped_frames=0
        )
    
    def _get_file_metadata(self, file_path: str) -> dict:
        """获取文件元数据"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(file_path)
            format_info = probe.get('format', {})
            return {
                'duration': float(format_info.get('duration', 0))
            }
        except Exception:
            return {'duration': 0}
    
    def _get_frame_timestamps(self, file_path: str, start_time: float, window_size: float) -> List[float]:
        """获取指定时间窗口内的真实帧时间戳"""
        end_time = start_time + window_size
        
        try:
            # 使用ffprobe获取帧时间戳
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-select_streams', 'v:0',
                '-show_entries', 'packet=pts_time',
                '-of', 'csv=nk=1:nokey=1',
                '-read_intervals', f'{start_time}%+#{int(window_size * 30)}',  # 估算最多30fps
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # 尝试备选命令格式
                cmd_backup = [
                    'ffprobe',
                    '-v', 'quiet',
                    '-select_streams', 'v:0',
                    '-show_frames',
                    '-show_entries', 'frame=pkt_pts_time',
                    '-of', 'csv=nk=1',
                    '-ss', str(start_time),
                    '-t', str(window_size),
                    file_path
                ]
                
                result_backup = subprocess.run(cmd_backup, capture_output=True, text=True, timeout=30)
                if result_backup.returncode != 0:
                    return []
                
                # 解析frame格式输出
                frame_times = []
                for line in result_backup.stdout.strip().split('\n'):
                    if line and ',' in line:
                        try:
                            # 提取pkt_pts_time字段
                            parts = line.split(',')
                            if len(parts) >= 2:
                                pts_time = float(parts[1]) if parts[1] else 0
                                if start_time <= pts_time <= end_time:
                                    frame_times.append(pts_time)
                        except (ValueError, IndexError):
                            continue
                return sorted(frame_times)
            
            # 解析时间戳
            frame_times = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        # 处理 "packet,time_value" 格式
                        if ',' in line:
                            pts_time = float(line.split(',')[1].strip())
                        else:
                            pts_time = float(line.strip())
                        
                        # 只保留窗口内的时间戳
                        if start_time <= pts_time <= end_time:
                            frame_times.append(pts_time)
                    except (ValueError, IndexError):
                        continue
            
            return sorted(frame_times)
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            # 如果ffprobe失败，返回空列表
            print(f"帧时间戳获取失败: {e}")
            return []
    
    def _detect_dropped_frames_in_window(self, frame_times: List[float], expected_fps: float, 
                                        window_size: float) -> int:
        """检测时间窗口内的掉帧数"""
        if len(frame_times) < 2 or expected_fps <= 0:
            return 0
        
        expected_interval = 1.0 / expected_fps
        tolerance = expected_interval * 0.3  # 30%容差，更精确
        
        dropped_count = 0
        for i in range(1, len(frame_times)):
            actual_interval = frame_times[i] - frame_times[i-1]
            
            # 如果间隔明显大于期望间隔，估算掉帧数
            if actual_interval > expected_interval + tolerance:
                estimated_drops = round(actual_interval / expected_interval) - 1
                dropped_count += max(0, estimated_drops)
        
        return dropped_count
    
    def _detect_dropped_frames(self, frame_times: List[float], expected_fps: float) -> int:
        """传统的掉帧检测方法（保持向后兼容）"""
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
    
    def _detect_vfr(self, analysis: FPSAnalysis) -> bool:
        """检测是否为可变帧率（VFR）视频"""
        if not analysis.data_points or analysis.actual_average_fps == 0:
            return False
        
        fps_values = [dp.fps for dp in analysis.data_points if dp.fps > 0]
        if len(fps_values) < 2:
            return False
        
        # 计算变异系数（CV = 标准差/均值）
        fps_std = np.std(fps_values)
        fps_mean = np.mean(fps_values)
        
        if fps_mean > 0:
            cv = fps_std / fps_mean
            return cv > self.vfr_threshold
        
        return False
    
    def analyze_fps_quality(self, analysis: FPSAnalysis) -> dict:
        """分析FPS质量"""
        is_vfr = self._detect_vfr(analysis)
        
        quality_report = {
            "performance_grade": analysis.performance_grade,
            "fps_consistency": f"{analysis.fps_stability:.1%}",
            "drop_rate": f"{analysis.drop_rate:.2%}",
            "fps_accuracy": self._calculate_fps_accuracy(analysis),
            "is_vfr": is_vfr,
            "issues": [],
            "recommendations": []
        }
        
        # 检测问题
        if analysis.drop_rate > 0.05:  # 超过5%掉帧率
            quality_report["issues"].append(f"掉帧率较高: {analysis.drop_rate:.1%}")
            quality_report["recommendations"].append("检查视频编码设置或源文件质量")
        
        if analysis.fps_stability < 0.9:  # 稳定性低于90%
            if is_vfr:
                quality_report["issues"].append("检测到可变帧率(VFR)编码")
                quality_report["recommendations"].append("VFR视频正常，但可能影响播放兼容性")
            else:
                quality_report["issues"].append("帧率不够稳定")
                quality_report["recommendations"].append("可能存在编码问题或播放性能问题")
        
        fps_diff = abs(analysis.declared_fps - analysis.actual_average_fps)
        if fps_diff > 1.0:  # 声明帧率与实际帧率差异大于1fps
            quality_report["issues"].append(f"实际帧率与声明帧率差异较大: {fps_diff:.1f}fps")
            if is_vfr:
                quality_report["recommendations"].append("VFR视频的帧率差异属于正常现象")
            else:
                quality_report["recommendations"].append("检查视频编码参数设置")
        
        if is_vfr:
            quality_report["recommendations"].append("VFR视频建议转换为CFR格式以提高兼容性")
        
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
    
    def export_to_csv(self, analysis: FPSAnalysis, output_path: str):
        """导出为CSV格式"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'fps', 'frame_count', 'dropped_frames'])
            
            for dp in analysis.data_points:
                writer.writerow([dp.timestamp, dp.fps, dp.frame_count, dp.dropped_frames])
        
        print(f"数据已导出到: {output_path}")


def analyze_multiple_fps(video_files: List[str], sample_interval: float = 10.0) -> List[FPSAnalysis]:
    """批量分析多个视频的FPS"""
    from .file_processor import FileProcessor
    
    processor = FileProcessor()
    analyzer = FPSAnalyzer(sample_interval)
    
    results = []
    for video_file in video_files:
        try:
            processed_file = processor.process_input(video_file)
            result = analyzer.analyze(processed_file)
            results.append(result)
            print(f"✓ 完成FPS分析: {video_file}")
            
        except Exception as e:
            print(f"✗ FPS分析失败 {video_file}: {e}")
    
    return results