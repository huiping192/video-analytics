"""
FPS analysis module
Analyzes frame rate changes, detects dropped frames, and assesses performance.
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
class FPSDataPoint:
    """FPS data point"""
    timestamp: float      # seconds
    fps: float           # instantaneous fps
    frame_count: int     # frames in window
    dropped_frames: int  # estimated dropped frames


@dataclass
class FPSAnalysis:
    """FPS analysis result"""
    file_path: str
    duration: float
    
    # FPS info
    declared_fps: float      # declared fps
    actual_average_fps: float # actual avg fps
    max_fps: float          # max instantaneous fps
    min_fps: float          # min instantaneous fps
    fps_variance: float     # variance
    
    # Frame stats
    total_frames: int       # total frames
    total_dropped_frames: int # total dropped frames
    
    # Time series
    data_points: List[FPSDataPoint]
    
    # Sampling
    sample_interval: float   # interval (seconds)
    
    @property
    def fps_stability(self) -> float:
        """FPS stability (0-1, higher means more stable)"""
        if self.actual_average_fps == 0:
            return 0.0
        cv = np.sqrt(self.fps_variance) / self.actual_average_fps
        return max(0, 1 - cv)
    
    @property
    def drop_rate(self) -> float:
        """Drop rate"""
        if self.total_frames == 0:
            return 0.0
        return self.total_dropped_frames / self.total_frames
    
    @property
    def performance_grade(self) -> str:
        """Performance grade (English labels)"""
        if self.drop_rate < 0.01 and self.fps_stability > 0.95:
            return "Excellent"
        elif self.drop_rate < 0.05 and self.fps_stability > 0.9:
            return "Good"
        elif self.drop_rate < 0.1 and self.fps_stability > 0.8:
            return "Fair"
        else:
            return "Poor"


class FPSAnalyzer:
    """FPS analyzer"""
    
    def __init__(self, sample_interval: float = 10.0):
        self.sample_interval = sample_interval
        self.drop_threshold = 0.8  # < 80% of expected FPS considered drop
        self.vfr_threshold = 0.1   # CV > 10% considered VFR
        self._logger = get_logger(__name__)
    
    def analyze(self, processed_file: ProcessedFile) -> FPSAnalysis:
        """Analyze video FPS"""
        metadata = processed_file.load_metadata()
        
        if not metadata.video_codec:
            raise ValueError("No video stream found")
        
        declared_fps = metadata.fps
        if declared_fps <= 0:
            raise ValueError("Unable to get FPS metadata")
        
        self._logger.info(f"Analyzing FPS (declared: {declared_fps:.2f}fps, interval: {self.sample_interval}s)")
        
        # Generate sampling timestamps
        duration = metadata.duration
        sample_times = np.arange(0, duration, self.sample_interval)
        
        self._logger.debug(f"Total sample points: {len(sample_times)} ...")
        
        # Sampling analysis
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
                
                # progress
                if (i + 1) % 5 == 0 or i == len(sample_times) - 1:
                    progress = (i + 1) / len(sample_times) * 100
                    self._logger.debug(f"FPS analysis progress: {progress:.1f}%")
                    
            except Exception as e:
                self._logger.warning(f"FPS sampling failed at {timestamp:.1f}s: {e}")
                # fallback to declared fps
                fallback_fps_data = FPSDataPoint(
                    timestamp=timestamp,
                    fps=declared_fps,
                    frame_count=int(declared_fps * self.sample_interval),
                    dropped_frames=0
                )
                data_points.append(fallback_fps_data)
                total_frames += fallback_fps_data.frame_count
        
        ensure_non_empty_sequence("fps data points", data_points)
        
        # Stats
        fps_values = [dp.fps for dp in data_points]
        # Actual average FPS - based on per-sample values
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
        """Analyze real FPS within a given time window"""
        try:
            # Check bounds
            metadata = self._get_file_metadata(file_path)
            duration = metadata['duration']
            
            if timestamp > duration:
                # Out of bounds
                return FPSDataPoint(
                    timestamp=timestamp,
                    fps=0.0,
                    frame_count=0,
                    dropped_frames=0
                )
            
            # Get real frame timestamps
            frame_times = self._get_frame_timestamps(file_path, timestamp, window_size)
            
            if not frame_times:
                # Fallback if timestamps unavailable
                return self._fallback_fps_data_point(timestamp, expected_fps, window_size)
            
            # Frame count
            actual_frame_count = len(frame_times)
            
            # Actual FPS
            if len(frame_times) > 1:
                # Based on time span
                time_span = frame_times[-1] - frame_times[0]
                if time_span > 0:
                    actual_fps = (actual_frame_count - 1) / time_span
                else:
                    actual_fps = expected_fps
            else:
                actual_fps = expected_fps
            
            # Detect dropped frames
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
            self._logger.warning(f"Real FPS analysis failed at {timestamp:.1f}s: {e}")
            # Fallback in exception
            return self._fallback_fps_data_point(timestamp, expected_fps, window_size)
    
    def _fallback_fps_data_point(self, timestamp: float, expected_fps: float, window_size: float) -> FPSDataPoint:
        """Create fallback FPS data point"""
        window_expected_frames = int(expected_fps * window_size)
        return FPSDataPoint(
            timestamp=timestamp,
            fps=expected_fps,
            frame_count=window_expected_frames,
            dropped_frames=0
        )
    
    def _get_file_metadata(self, file_path: str) -> dict:
        """Get basic file metadata"""
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
        """Get real frame timestamps within the window"""
        end_time = start_time + window_size
        
        try:
            # Use ffprobe to get frame timestamps
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-select_streams', 'v:0',
                '-show_entries', 'packet=pts_time',
                '-of', 'csv=nk=1:nokey=1',
                '-read_intervals', f'{start_time}%+#{int(window_size * 30)}',  # up to ~30fps
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # Try fallback command format
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
                
                # Parse 'frame' format output
                frame_times = []
                for line in result_backup.stdout.strip().split('\n'):
                    if line and ',' in line:
                        try:
                            # Extract pkt_pts_time field
                            parts = line.split(',')
                            if len(parts) >= 2:
                                pts_time = float(parts[1]) if parts[1] else 0
                                if start_time <= pts_time <= end_time:
                                    frame_times.append(pts_time)
                        except (ValueError, IndexError):
                            continue
                return sorted(frame_times)
            
            # Parse timestamps
            frame_times = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        # Handle "packet,time_value" format
                        if ',' in line:
                            pts_time = float(line.split(',')[1].strip())
                        else:
                            pts_time = float(line.strip())
                        
                        # Keep timestamps within window
                        if start_time <= pts_time <= end_time:
                            frame_times.append(pts_time)
                    except (ValueError, IndexError):
                        continue
            
            return sorted(frame_times)
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            # If ffprobe fails, return empty list
            self._logger.warning(f"Failed to get frame timestamps: {e}")
            return []
    
    def _detect_dropped_frames_in_window(self, frame_times: List[float], expected_fps: float, 
                                        window_size: float) -> int:
        """Detect dropped frames in a window"""
        if len(frame_times) < 2 or expected_fps <= 0:
            return 0
        
        expected_interval = 1.0 / expected_fps
        tolerance = expected_interval * 0.3  # 30% tolerance
        
        dropped_count = 0
        for i in range(1, len(frame_times)):
            actual_interval = frame_times[i] - frame_times[i-1]
            
            # If interval > expected, estimate dropped frames
            if actual_interval > expected_interval + tolerance:
                estimated_drops = round(actual_interval / expected_interval) - 1
                dropped_count += max(0, estimated_drops)
        
        return dropped_count
    
    def _detect_dropped_frames(self, frame_times: List[float], expected_fps: float) -> int:
        """Legacy dropped-frame detection (backward compatibility)"""
        if len(frame_times) < 2 or expected_fps <= 0:
            return 0
        
        expected_interval = 1.0 / expected_fps
        tolerance = expected_interval * 0.5  # 50% tolerance
        
        dropped_count = 0
        for i in range(1, len(frame_times)):
            actual_interval = frame_times[i] - frame_times[i-1]
            
            # If interval > expected, estimate dropped frames
            if actual_interval > expected_interval + tolerance:
                estimated_drops = int(actual_interval / expected_interval) - 1
                dropped_count += max(0, estimated_drops)
        
        return dropped_count
    
    def _detect_vfr(self, analysis: FPSAnalysis) -> bool:
        """Detect variable frame rate (VFR)"""
        if not analysis.data_points or analysis.actual_average_fps == 0:
            return False
        
        fps_values = [dp.fps for dp in analysis.data_points if dp.fps > 0]
        if len(fps_values) < 2:
            return False
        
        # Coefficient of variation (std/mean)
        fps_std = np.std(fps_values)
        fps_mean = np.mean(fps_values)
        
        if fps_mean > 0:
            cv = fps_std / fps_mean
            return cv > self.vfr_threshold
        
        return False
    
    def analyze_fps_quality(self, analysis: FPSAnalysis) -> dict:
        """Analyze FPS quality"""
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
        
        # Issues
        if analysis.drop_rate > 0.05:  # >5% drop rate
            quality_report["issues"].append(f"High drop rate: {analysis.drop_rate:.1%}")
            quality_report["recommendations"].append("Check encoding settings or source quality")
        
        if analysis.fps_stability < 0.9:  # stability below 90%
            if is_vfr:
                quality_report["issues"].append("Detected VFR encoding")
                quality_report["recommendations"].append("VFR is normal but may affect playback compatibility")
            else:
                quality_report["issues"].append("FPS instability detected")
                quality_report["recommendations"].append("Possible encoding or playback performance issue")
        
        fps_diff = abs(analysis.declared_fps - analysis.actual_average_fps)
        if fps_diff > 1.0:  # declared vs actual difference > 1 fps
            quality_report["issues"].append(f"Large difference between declared and actual FPS: {fps_diff:.1f}fps")
            if is_vfr:
                quality_report["recommendations"].append("FPS differences are normal for VFR video")
            else:
                quality_report["recommendations"].append("Check video encoding parameters")
        
        if is_vfr:
            quality_report["recommendations"].append("Consider converting VFR to CFR for better compatibility")
        
        if not quality_report["issues"]:
            quality_report["recommendations"].append("FPS performance is good; no action needed")
        
        return quality_report
    
    def _calculate_fps_accuracy(self, analysis: FPSAnalysis) -> str:
        """Calculate FPS accuracy"""
        if analysis.declared_fps == 0:
            return "N/A"
        
        accuracy = 1 - abs(analysis.declared_fps - analysis.actual_average_fps) / analysis.declared_fps
        accuracy = max(0, accuracy)  # ensure non-negative
        
        return f"{accuracy:.1%}"
    
    def analyze_drop_severity(self, analysis: FPSAnalysis) -> dict:
        """Analyze dropped-frame severity"""
        drop_analysis = {
            "total_drops": analysis.total_dropped_frames,
            "drop_rate": analysis.drop_rate,
            "severity": "正常",
            "affected_time": 0.0,
            "worst_segments": []
        }
        
        # Find worst segments
        serious_drops = []
        affected_time = 0.0
        
        for dp in analysis.data_points:
            if dp.dropped_frames > 0:
                affected_time += analysis.sample_interval
                if dp.dropped_frames > 2:  # > 2 drops in window
                    serious_drops.append((dp.timestamp, dp.dropped_frames))
        
        drop_analysis["affected_time"] = affected_time
        drop_analysis["worst_segments"] = sorted(serious_drops, key=lambda x: x[1], reverse=True)[:5]
        
        # Determine severity
        if analysis.drop_rate > 0.1:
            drop_analysis["severity"] = "严重"
        elif analysis.drop_rate > 0.05:
            drop_analysis["severity"] = "中等"
        elif analysis.drop_rate > 0.01:
            drop_analysis["severity"] = "轻微"
        
        return drop_analysis
    
    def export_analysis_data(self, analysis: FPSAnalysis, output_path: str):
        """Export FPS analysis result as JSON"""
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
        
        self._logger.info(f"FPS analysis exported to: {output_path}")
    
    def export_to_csv(self, analysis: FPSAnalysis, output_path: str):
        """Export to CSV"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'fps', 'frame_count', 'dropped_frames'])
            
            for dp in analysis.data_points:
                writer.writerow([dp.timestamp, dp.fps, dp.frame_count, dp.dropped_frames])
        
        self._logger.info(f"Data exported to: {output_path}")


def analyze_multiple_fps(video_files: List[str], sample_interval: float = 10.0) -> List[FPSAnalysis]:
    """Analyze FPS for multiple videos"""
    from .file_processor import FileProcessor
    
    processor = FileProcessor()
    analyzer = FPSAnalyzer(sample_interval)
    _logger = get_logger(__name__)
    
    results = []
    for video_file in video_files:
        try:
            processed_file = processor.process_input(video_file)
            result = analyzer.analyze(processed_file)
            results.append(result)
            _logger.info(f"Completed FPS analysis: {video_file}")
            
        except Exception as e:
            _logger.error(f"FPS analysis failed {video_file}: {e}")
    
    return results