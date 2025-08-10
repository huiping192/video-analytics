"""
Main chart drawer module
Draws the main analysis charts (video, audio, fps) in combined_analysis style.
"""

import matplotlib.pyplot as plt
from typing import Dict, Any
from ..core.video_analyzer import VideoBitrateAnalysis
from ..core.audio_analyzer import AudioBitrateAnalysis
from ..core.fps_analyzer import FPSAnalysis


class MainChartDrawer:
    """Main chart drawer for enhanced layouts"""
    
    def __init__(self):
        # Chart colors (same as original ChartGenerator)
        self.colors = {
            'video': '#1f77b4',
            'audio': '#ff7f0e',  
            'fps': '#2ca02c',
            'dropped': '#d62728',
            'average': '#ff0000'
        }
        
        # Chart styling
        self.line_width = 2.0
        self.grid_alpha = 0.3
        self.font_size = 11
    
    def draw_combined_charts(self, main_charts: Dict[str, Any], 
                            video_analysis: VideoBitrateAnalysis,
                            audio_analysis: AudioBitrateAnalysis,
                            fps_analysis: FPSAnalysis):
        """
        Draw combined analysis charts (3 subplots style)
        
        Args:
            main_charts: Dictionary of main chart axes
            video_analysis: Video bitrate analysis results
            audio_analysis: Audio bitrate analysis results  
            fps_analysis: FPS analysis results
        """
        
        # 1) Video bitrate subplot
        self._draw_video_bitrate_chart(
            main_charts['video_bitrate'], 
            video_analysis
        )
        
        # 2) Audio bitrate subplot
        self._draw_audio_bitrate_chart(
            main_charts['audio_bitrate'], 
            audio_analysis
        )
        
        # 3) FPS subplot
        self._draw_fps_chart(
            main_charts['fps'], 
            fps_analysis
        )
    
    def _draw_video_bitrate_chart(self, ax, video_analysis: VideoBitrateAnalysis):
        """Draw video bitrate chart"""
        # Prepare data
        video_times = [dp.timestamp / 60 for dp in video_analysis.data_points]  # minutes
        video_rates = [dp.bitrate / 1000000 for dp in video_analysis.data_points]  # Mbps
        
        # Main line
        ax.plot(video_times, video_rates,
                color=self.colors['video'],
                linewidth=self.line_width,
                label='Video Bitrate',
                alpha=0.8)
        
        # Average line
        avg_bitrate = video_analysis.average_bitrate / 1000000
        ax.axhline(y=avg_bitrate,
                  color=self.colors['average'],
                  linestyle='--',
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'Average ({avg_bitrate:.1f} Mbps)')

        # Threshold lines (±30% from average)
        upper_threshold = avg_bitrate * 1.3
        lower_threshold = max(0, avg_bitrate * 0.7)
        ax.axhline(y=upper_threshold, color='#888888', linestyle=':', linewidth=1.0, alpha=0.9, label='Upper threshold')
        ax.axhline(y=lower_threshold, color='#888888', linestyle=':', linewidth=1.0, alpha=0.9, label='Lower threshold')

        # Highlight anomaly regions where bitrate beyond thresholds
        labeled_anomaly = False
        half_window = max(0.25, (video_analysis.sample_interval / 60) / 2)
        for i, rate in enumerate(video_rates):
            if rate > upper_threshold or rate < lower_threshold:
                center = video_times[i]
                start_x = max(0, center - half_window)
                end_x = center + half_window
                ax.axvspan(
                    start_x, end_x,
                    color='#fde725', alpha=0.18,
                    label='Bitrate anomaly' if not labeled_anomaly else None
                )
                labeled_anomaly = True

        # Annotate top peak points (up to 3)
        try:
            import numpy as np
            if len(video_rates) >= 3:
                # Simple local maxima detection
                local_max_indices = [
                    i for i in range(1, len(video_rates) - 1)
                    if video_rates[i] > video_rates[i - 1] and video_rates[i] > video_rates[i + 1]
                ]
                # Fallback: include global max if no local peaks
                if not local_max_indices:
                    local_max_indices = [int(np.argmax(video_rates))]
                # Pick top 3 peaks by value
                top_indices = sorted(local_max_indices, key=lambda idx: video_rates[idx], reverse=True)[:3]
                for idx in top_indices:
                    x = video_times[idx]
                    y = video_rates[idx]
                    ax.scatter([x], [y], color='#8e44ad', s=30, zorder=6, label=None)
                    ax.annotate(
                        f"Peak {y:.1f} Mbps",
                        xy=(x, y), xytext=(5, 8), textcoords='offset points',
                        fontsize=self.font_size - 1, color='#4a235a',
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='#4a235a', lw=0.6)
                    )
        except Exception:
            # Safe ignore annotation errors
            pass
        
        # Adjust y-limits to add headroom to avoid title/annotations overlap
        try:
            y_candidates = video_rates + [avg_bitrate, upper_threshold]
            if y_candidates:
                ymax = max(y_candidates)
                ymin = min(video_rates) if video_rates else 0
                ax.set_ylim(bottom=max(0, ymin * 0.95), top=ymax * 1.15)
        except Exception:
            pass

        # Styling
        ax.set_ylabel('Video Bitrate (Mbps)', fontsize=self.font_size)
        ax.set_title('Video Bitrate Changes', fontsize=self.font_size + 1, fontweight='bold', pad=16)
        ax.grid(True, alpha=self.grid_alpha)
        ax.legend(loc='upper right')
    
    def _draw_audio_bitrate_chart(self, ax, audio_analysis: AudioBitrateAnalysis):
        """Draw audio bitrate chart"""
        # Prepare data
        audio_times = [dp.timestamp / 60 for dp in audio_analysis.data_points]  # minutes
        audio_rates = [dp.bitrate / 1000 for dp in audio_analysis.data_points]  # kbps
        
        # Main line
        ax.plot(audio_times, audio_rates,
                color=self.colors['audio'],
                linewidth=self.line_width,
                label='Audio Bitrate',
                alpha=0.8)
        
        # Average line
        avg_bitrate = audio_analysis.average_bitrate / 1000
        ax.axhline(y=avg_bitrate,
                  color=self.colors['average'],
                  linestyle='--',
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'Average ({avg_bitrate:.0f} kbps)')

        # Annotate up to 2 peak points for audio
        try:
            if len(audio_rates) >= 3:
                peak_indices = [
                    i for i in range(1, len(audio_rates) - 1)
                    if audio_rates[i] > audio_rates[i - 1] and audio_rates[i] > audio_rates[i + 1]
                ]
                if not peak_indices:
                    import numpy as np
                    peak_indices = [int(np.argmax(audio_rates))]
                for idx in sorted(peak_indices, key=lambda i: audio_rates[i], reverse=True)[:2]:
                    x = audio_times[idx]
                    y = audio_rates[idx]
                    ax.scatter([x], [y], color='#8e44ad', s=25, zorder=6, label=None)
                    ax.annotate(
                        f"Peak {y:.0f} kbps",
                        xy=(x, y), xytext=(5, 6), textcoords='offset points',
                        fontsize=self.font_size - 2, color='#4a235a',
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.7)
                    )
        except Exception:
            pass
        
        # Adjust y-limits to add headroom
        try:
            y_candidates = audio_rates + [avg_bitrate]
            if y_candidates:
                ymax = max(y_candidates)
                ymin = min(audio_rates) if audio_rates else 0
                ax.set_ylim(bottom=max(0, ymin * 0.95), top=ymax * 1.15)
        except Exception:
            pass

        # Styling
        ax.set_ylabel('Audio Bitrate (kbps)', fontsize=self.font_size)
        ax.set_title('Audio Bitrate Changes', fontsize=self.font_size + 1, fontweight='bold', pad=16)
        ax.grid(True, alpha=self.grid_alpha)
        ax.legend(loc='upper right')
    
    def _draw_fps_chart(self, ax, fps_analysis: FPSAnalysis):
        """Draw FPS chart"""
        # Prepare data
        fps_times = [dp.timestamp / 60 for dp in fps_analysis.data_points]  # minutes
        fps_values = [dp.fps for dp in fps_analysis.data_points]
        
        # Main line
        ax.plot(fps_times, fps_values,
                color=self.colors['fps'],
                linewidth=self.line_width,
                label='FPS',
                alpha=0.8)
        
        # Dropped-frame markers
        dropped_times = [dp.timestamp / 60 for dp in fps_analysis.data_points if dp.dropped_frames > 0]
        dropped_fps = [dp.fps for dp in fps_analysis.data_points if dp.dropped_frames > 0]
        
        if dropped_times:
            ax.scatter(dropped_times, dropped_fps,
                       color=self.colors['dropped'], s=20, alpha=0.7,
                       label='Dropped Frames', zorder=5)
        
        # Declared FPS line
        ax.axhline(y=fps_analysis.declared_fps,
                  color=self.colors['average'],
                  linestyle='--',
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'Declared FPS ({fps_analysis.declared_fps:.1f} fps)')

        # Actual average FPS line
        if fps_values:
            actual_avg = sum(fps_values) / len(fps_values)
            ax.axhline(y=actual_avg, color='#888888', linestyle=':', linewidth=1.0, alpha=0.9, label=f'Actual Avg ({actual_avg:.1f} fps)')

        # Highlight severe drop regions and annotate worst drop
        labeled_region = False
        worst_drop_idx = None
        worst_drop_count = -1
        half_window = max(0.25, (fps_analysis.sample_interval / 60) / 2)
        expected_frames_per_window = max(1.0, fps_analysis.declared_fps * fps_analysis.sample_interval)
        for i, dp in enumerate(fps_analysis.data_points):
            if dp.dropped_frames > 0:
                drop_ratio = dp.dropped_frames / expected_frames_per_window
                if drop_ratio >= 0.05:  # >=5% considered severe region
                    center = fps_times[i]
                    ax.axvspan(
                        max(0, center - half_window), center + half_window,
                        color='#ff4d4f', alpha=0.12,
                        label='Severe drop region' if not labeled_region else None
                    )
                    labeled_region = True
                if dp.dropped_frames > worst_drop_count:
                    worst_drop_count = dp.dropped_frames
                    worst_drop_idx = i

        if worst_drop_idx is not None and worst_drop_count > 0:
            x = fps_times[worst_drop_idx]
            y = fps_values[worst_drop_idx]
            ax.annotate(
                f"Severe drop: {worst_drop_count} frames",
                xy=(x, y), xytext=(6, -12), textcoords='offset points',
                fontsize=self.font_size - 1, color=self.colors['dropped'],
                bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.7),
                arrowprops=dict(arrowstyle='->', color=self.colors['dropped'], lw=0.6)
            )
        
        # Adjust y-limits to add headroom
        try:
            y_candidates = fps_values + [fps_analysis.declared_fps]
            try:
                y_candidates.append(actual_avg)
            except Exception:
                pass
            if y_candidates:
                ymax = max(y_candidates)
                ymin = min(fps_values) if fps_values else 0
                ax.set_ylim(bottom=max(0, ymin * 0.95), top=ymax * 1.15)
        except Exception:
            pass

        # Styling
        ax.set_ylabel('FPS', fontsize=self.font_size)
        ax.set_xlabel('Time (minutes)', fontsize=self.font_size)
        ax.set_title('FPS Changes', fontsize=self.font_size + 1, fontweight='bold', pad=16)
        ax.grid(True, alpha=self.grid_alpha)
        ax.legend(loc='upper right')