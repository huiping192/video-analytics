"""
Video bitrate analysis module
Analyzes video bitrate over time to generate a bitrate time series.
"""

import json
import subprocess
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import numpy as np

from .file_processor import ProcessedFile
from ..utils.logger import get_logger
from ..utils.validators import ensure_non_empty_sequence, normalize_interval


@dataclass
class BitrateDataPoint:
    """Bitrate data point"""
    timestamp: float    # seconds
    bitrate: float     # bitrate (bps)


@dataclass
class VideoBitrateAnalysis:
    """Video bitrate analysis result"""
    file_path: str
    duration: float
    
    # Statistics
    average_bitrate: float    # average bitrate (bps)
    max_bitrate: float       # max bitrate (bps)
    min_bitrate: float       # min bitrate (bps)
    bitrate_variance: float  # variance
    
    # Time series
    data_points: List[BitrateDataPoint]
    
    # Sampling
    sample_interval: float   # interval (seconds)
    
    @property
    def is_cbr(self) -> bool:
        """Whether bitrate is constant (CBR)"""
        if self.average_bitrate == 0:
            return False
        # CV < 10% considered CBR
        cv = np.sqrt(self.bitrate_variance) / self.average_bitrate
        return cv < 0.1
    
    @property
    def encoding_type(self) -> str:
        """Get encoding type description"""
        if self.is_cbr:
            return "CBR (Constant Bitrate)"
        else:
            cv = np.sqrt(self.bitrate_variance) / self.average_bitrate
            return f"VBR (Variable Bitrate) - CV: {cv:.1%}"


class VideoBitrateAnalyzer:
    """Video bitrate analyzer"""
    
    def __init__(self, sample_interval: float = 10.0):
        self.sample_interval = sample_interval
        self._logger = get_logger(__name__)
    
    def analyze(self, processed_file: ProcessedFile) -> VideoBitrateAnalysis:
        """Analyze video bitrate"""
        metadata = processed_file.load_metadata()
        
        if not metadata.video_codec:
            raise ValueError("No video stream found")
        
        self._logger.info(f"Analyzing video bitrate (interval: {self.sample_interval}s)")
        
        # Optimize interval for long videos
        optimized_interval = normalize_interval(self.sample_interval, metadata.duration)
        if optimized_interval != self.sample_interval:
            self._logger.debug(f"Long video detected, adjusting interval to: {optimized_interval}s")
        interval = optimized_interval
        
        # Generate sample timestamps
        duration = metadata.duration
        sample_times = np.arange(0, duration, interval)
        
        self._logger.debug(f"Video duration: {duration:.1f}s")
        self._logger.debug(f"Total sample points: {len(sample_times)} ...")
        
        # Sampling analysis
        data_points = []
        for i, timestamp in enumerate(sample_times):
            try:
                bitrate = self._get_bitrate_at_time(processed_file.file_path, timestamp)
                data_points.append(BitrateDataPoint(timestamp, bitrate))
                
                # Progress
                if (i + 1) % 10 == 0 or i == len(sample_times) - 1:
                    progress = (i + 1) / len(sample_times) * 100
                    self._logger.debug(f"Progress: {progress:.1f}%")
                    
            except Exception as e:
                self._logger.warning(f"Sampling failed at {timestamp:.1f}s: {e}")
                # Fallback to overall average bitrate ratio
                fallback_bitrate = metadata.video_bitrate or (metadata.bit_rate * 0.8)
                data_points.append(BitrateDataPoint(timestamp, fallback_bitrate))
        
        ensure_non_empty_sequence("bitrate data points", data_points)
        
        # Compute statistics
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
        """Adjust sampling interval based on duration"""
        if duration > 7200:  # > 2 hours
            return 30.0
        elif duration > 3600:  # 1-2 hours
            return 20.0
        else:
            return self.sample_interval  # default 10s
    
    def _get_bitrate_at_time(self, file_path: str, timestamp: float, window_size: float = 5.0) -> float:
        """Get bitrate at a timestamp within a window"""
        start_time = max(0, timestamp - window_size/2)
        end_time = start_time + window_size
        
        try:
            # Use ffprobe to get packet data in window
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_packets',
                '-select_streams', 'v:0',
                '-show_entries', 'packet=size,pts_time',
                '-of', 'csv=p=0',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            
            if not result.stdout.strip():
                # Fallback to average bitrate
                return self._get_fallback_bitrate(file_path)
            
            lines = result.stdout.strip().split('\n')
            
            # Sum bytes in time window
            total_bytes = 0
            packet_count = 0
            valid_timestamps = []
            
            for line in lines:
                if line.strip() and ',' in line:
                    try:
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            pts_time_str, size_str = parts[0], parts[1]
                            
                            if pts_time_str and size_str:
                                pts_time = float(pts_time_str)
                                packet_size = int(size_str)
                                
                                # Filter packets in time window
                                if start_time <= pts_time <= end_time:
                                    total_bytes += packet_size
                                    packet_count += 1
                                    valid_timestamps.append(pts_time)
                    except (ValueError, IndexError):
                        continue
            
            if packet_count > 0 and len(valid_timestamps) > 1:
                # Calculate actual duration from timestamps
                actual_duration = max(valid_timestamps) - min(valid_timestamps)
                if actual_duration > 0:
                    # bitrate = (total_bytes * 8) / actual_duration
                    bitrate = (total_bytes * 8) / actual_duration
                    return bitrate
                else:
                    # Single packet or same timestamp, use window size
                    return (total_bytes * 8) / window_size
            else:
                return self._get_fallback_bitrate(file_path)
                
        except subprocess.CalledProcessError as e:
            self._logger.warning(f"FFprobe command failed: {e}, using fallback")
            return self._get_fallback_bitrate(file_path)
        except subprocess.TimeoutExpired:
            self._logger.warning("FFprobe timed out, using fallback")
            return self._get_fallback_bitrate(file_path)
    
    def _get_fallback_bitrate(self, file_path: str) -> float:
        """Get fallback bitrate (based on file-level info)"""
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
                # Estimate from file-level bitrate
                return self._estimate_bitrate_from_file(file_path)
                
        except Exception:
            return self._estimate_bitrate_from_file(file_path)
    
    def _estimate_bitrate_from_file(self, file_path: str) -> float:
        """Estimate bitrate from file info"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(file_path)
            
            # Get overall bitrate
            format_info = probe.get('format', {})
            total_bitrate = format_info.get('bit_rate')
            
            if total_bitrate:
                # Assume ~80% of total bitrate is video
                return float(total_bitrate) * 0.8
            else:
                # Estimate from file size and duration
                duration = float(format_info.get('duration', 1))
                file_size = int(format_info.get('size', 0))
                if duration > 0 and file_size > 0:
                    total_bitrate = (file_size * 8) / duration
                    return total_bitrate * 0.8  # estimate video portion
                
        except Exception:
            pass
        
        # Default
        return 2000000.0  # 2 Mbps
    
    def export_analysis_data(self, analysis: VideoBitrateAnalysis, output_path: str):
        """Export analysis result as JSON"""
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
        
        self._logger.info(f"Analysis exported to: {output_path}")
    
    def export_to_csv(self, analysis: VideoBitrateAnalysis, output_path: str):
        """Export to CSV"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'bitrate_mbps'])
            
            for dp in analysis.data_points:
                writer.writerow([dp.timestamp, dp.bitrate / 1000000])  # Mbps
        
        self._logger.info(f"Data exported to: {output_path}")


def analyze_multiple_videos(video_files: List[str], sample_interval: float = 10.0) -> List[VideoBitrateAnalysis]:
    """Analyze multiple videos"""
    from .file_processor import FileProcessor
    
    processor = FileProcessor()
    analyzer = VideoBitrateAnalyzer(sample_interval)
    _logger = get_logger(__name__)
    
    results = []
    for video_file in video_files:
        try:
            processed_file = processor.process_input(video_file)
            result = analyzer.analyze(processed_file)
            results.append(result)
            _logger.info(f"Completed analysis: {video_file}")
            
        except Exception as e:
            _logger.error(f"Analysis failed {video_file}: {e}")
    
    return results