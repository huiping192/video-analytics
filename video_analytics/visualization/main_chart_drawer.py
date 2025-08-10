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
        
        # Styling
        ax.set_ylabel('Video Bitrate (Mbps)', fontsize=self.font_size)
        ax.set_title('Video Bitrate Changes', fontsize=self.font_size, fontweight='bold')
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
        
        # Styling
        ax.set_ylabel('Audio Bitrate (kbps)', fontsize=self.font_size)
        ax.set_title('Audio Bitrate Changes', fontsize=self.font_size, fontweight='bold')
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
        
        # Styling
        ax.set_ylabel('FPS', fontsize=self.font_size)
        ax.set_xlabel('Time (minutes)', fontsize=self.font_size)
        ax.set_title('FPS Changes', fontsize=self.font_size, fontweight='bold')
        ax.grid(True, alpha=self.grid_alpha)
        ax.legend(loc='upper right')