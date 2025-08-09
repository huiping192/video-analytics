"""
视频码率分析模块
负责分析视频流的码率变化情况，通过定时采样生成码率时间序列数据
"""

import json
import subprocess
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import numpy as np

from .file_processor import ProcessedFile


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
    
    @property
    def encoding_type(self) -> str:
        """获取编码类型描述"""
        if self.is_cbr:
            return "CBR (恒定码率)"
        else:
            cv = np.sqrt(self.bitrate_variance) / self.average_bitrate
            return f"VBR (可变码率) - 变异系数: {cv:.1%}"


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
        
        # 根据视频长度优化采样间隔
        optimized_interval = self._optimize_for_large_files(metadata.duration)
        if optimized_interval != self.sample_interval:
            print(f"检测到长视频，调整采样间隔为: {optimized_interval}秒")
            interval = optimized_interval
        else:
            interval = self.sample_interval
        
        # 生成采样时间点
        duration = metadata.duration
        sample_times = np.arange(0, duration, interval)
        
        print(f"视频时长: {duration:.1f}秒")
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
            average_bitrate=float(np.mean(bitrates)),
            max_bitrate=float(np.max(bitrates)),
            min_bitrate=float(np.min(bitrates)),
            bitrate_variance=float(np.var(bitrates)),
            data_points=data_points,
            sample_interval=interval
        )
    
    def _optimize_for_large_files(self, duration: float) -> float:
        """根据视频长度调整采样间隔"""
        if duration > 7200:  # 超过2小时
            return 30.0  # 30秒间隔
        elif duration > 3600:  # 1-2小时
            return 20.0  # 20秒间隔
        else:
            return self.sample_interval  # 默认10秒间隔
    
    def _get_bitrate_at_time(self, file_path: str, timestamp: float, window_size: float = 5.0) -> float:
        """获取指定时间点的码率"""
        start_time = max(0, timestamp - window_size/2)
        end_time = start_time + window_size
        
        try:
            # 使用ffprobe获取指定时间段的帧数据
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-ss', str(start_time),
                '-t', str(window_size),
                '-i', file_path,
                '-select_streams', 'v:0',
                '-show_entries', 'frame=pkt_size',
                '-of', 'csv=p=0'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            
            if not result.stdout.strip():
                # 如果没有获取到数据，回退到使用平均码率
                return self._get_fallback_bitrate(file_path)
            
            lines = result.stdout.strip().split('\n')
            
            # 计算总字节数
            total_bytes = 0
            frame_count = 0
            
            for line in lines:
                if line.strip():
                    try:
                        frame_size = int(line.strip())
                        total_bytes += frame_size
                        frame_count += 1
                    except ValueError:
                        continue
            
            if frame_count > 0:
                # 计算码率 (字节转换为比特，除以时间窗口)
                bitrate = (total_bytes * 8) / window_size
                return bitrate
            else:
                return self._get_fallback_bitrate(file_path)
                
        except subprocess.CalledProcessError as e:
            print(f"FFprobe命令失败: {e}, 使用备选方法")
            return self._get_fallback_bitrate(file_path)
        except subprocess.TimeoutExpired:
            print("FFprobe执行超时，使用备选方法")
            return self._get_fallback_bitrate(file_path)
    
    def _get_fallback_bitrate(self, file_path: str) -> float:
        """获取备选码率（基于文件级别的码率信息）"""
        try:
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
                # 如果无法获取流码率，使用文件整体码率估算
                return self._estimate_bitrate_from_file(file_path)
                
        except Exception:
            return self._estimate_bitrate_from_file(file_path)
    
    def _estimate_bitrate_from_file(self, file_path: str) -> float:
        """从文件信息估算码率"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(file_path)
            
            # 获取总码率
            format_info = probe.get('format', {})
            total_bitrate = format_info.get('bit_rate')
            
            if total_bitrate:
                # 估算视频码率约占总码率的80%
                return float(total_bitrate) * 0.8
            else:
                # 基于文件大小和时长估算
                duration = float(format_info.get('duration', 1))
                file_size = int(format_info.get('size', 0))
                if duration > 0 and file_size > 0:
                    total_bitrate = (file_size * 8) / duration
                    return total_bitrate * 0.8  # 估算视频部分
                
        except Exception:
            pass
        
        # 最后的默认值
        return 2000000.0  # 2 Mbps 默认值
    
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
    
    def export_to_csv(self, analysis: VideoBitrateAnalysis, output_path: str):
        """导出为CSV格式"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'bitrate_mbps'])
            
            for dp in analysis.data_points:
                writer.writerow([dp.timestamp, dp.bitrate / 1000000])  # 转换为Mbps
        
        print(f"数据已导出到: {output_path}")


def analyze_multiple_videos(video_files: List[str], sample_interval: float = 10.0) -> List[VideoBitrateAnalysis]:
    """批量分析多个视频"""
    from .file_processor import FileProcessor
    
    processor = FileProcessor()
    analyzer = VideoBitrateAnalyzer(sample_interval)
    
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