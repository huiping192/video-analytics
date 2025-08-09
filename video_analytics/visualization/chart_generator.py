"""
Chart visualization module
Converts analysis results into clear PNG charts.
"""

import json
import os
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from ..core.video_analyzer import VideoBitrateAnalysis
from ..core.audio_analyzer import AudioBitrateAnalysis
from ..core.fps_analyzer import FPSAnalysis
from ..utils.logger import get_logger


@dataclass
class ChartConfig:
    """Chart configuration"""
    width: int = 12          # figure width (inches)
    height: int = 8          # figure height (inches)
    dpi: int = 150           # image dpi
    title: str = ""          # figure title
    output_dir: str = "output"  # output directory
    
    # Style
    line_width: float = 2.0
    grid_alpha: float = 0.3
    font_size: int = 11


class ChartGenerator:
    """Chart generator"""
    
    def __init__(self):
        # Default style
        plt.style.use('default')
        self._logger = get_logger(__name__)
        
        # Default colors
        self.colors = {
            'video': '#1f77b4',
            'audio': '#ff7f0e',  
            'fps': '#2ca02c',
            'dropped': '#d62728',
            'average': '#ff0000'
        }
    
    def generate_video_bitrate_chart(self, analysis: VideoBitrateAnalysis, 
                                   config: ChartConfig) -> str:
        """Generate video bitrate chart"""
        fig, ax = plt.subplots(figsize=(config.width, config.height))
        
        # Prepare data
        timestamps = [dp.timestamp / 60 for dp in analysis.data_points]  # minutes
        bitrates = [dp.bitrate / 1000000 for dp in analysis.data_points]  # Mbps
        
        # Main line
        ax.plot(timestamps, bitrates, 
               color=self.colors['video'],
               linewidth=config.line_width,
               label='Video Bitrate',
               alpha=0.8)
        
        # Average line
        avg_bitrate = analysis.average_bitrate / 1000000
        ax.axhline(y=avg_bitrate, 
                  color=self.colors['average'], 
                  linestyle='--', 
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'Average ({avg_bitrate:.1f} Mbps)')
        
        # Style
        ax.set_title(config.title or f"Video Bitrate Analysis - {os.path.basename(analysis.file_path)}", 
                    fontsize=config.font_size + 2, fontweight='bold', pad=20)
        ax.set_xlabel("Time (minutes)", fontsize=config.font_size)
        ax.set_ylabel("Bitrate (Mbps)", fontsize=config.font_size)
        ax.grid(True, alpha=config.grid_alpha)
        ax.legend(loc='upper right')
        
        # Save chart
        output_path = self._generate_filename("video_bitrate", config)
        plt.tight_layout()
        plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_audio_bitrate_chart(self, analysis: AudioBitrateAnalysis,
                                   config: ChartConfig) -> str:
        """Generate audio bitrate chart"""
        fig, ax = plt.subplots(figsize=(config.width, config.height))
        
        # Prepare data
        timestamps = [dp.timestamp / 60 for dp in analysis.data_points]
        bitrates = [dp.bitrate / 1000 for dp in analysis.data_points]  # kbps
        
        # Main line
        ax.plot(timestamps, bitrates,
               color=self.colors['audio'],
               linewidth=config.line_width,
               label='Audio Bitrate',
               alpha=0.8)
        
        # Average line
        avg_bitrate = analysis.average_bitrate / 1000
        ax.axhline(y=avg_bitrate,
                  color=self.colors['average'],
                  linestyle='--',
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'Average ({avg_bitrate:.0f} kbps)')
        
        # Style
        ax.set_title(config.title or f"Audio Bitrate Analysis - {os.path.basename(analysis.file_path)}",
                    fontsize=config.font_size + 2, fontweight='bold', pad=20)
        ax.set_xlabel("Time (minutes)", fontsize=config.font_size)
        ax.set_ylabel("Bitrate (kbps)", fontsize=config.font_size)
        ax.grid(True, alpha=config.grid_alpha)
        ax.legend(loc='upper right')
        
        # Save chart
        output_path = self._generate_filename("audio_bitrate", config)
        plt.tight_layout()
        plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_fps_chart(self, analysis: FPSAnalysis, config: ChartConfig) -> str:
        """Generate FPS chart"""
        fig, ax = plt.subplots(figsize=(config.width, config.height))
        
        # Prepare data
        timestamps = [dp.timestamp / 60 for dp in analysis.data_points]
        fps_values = [dp.fps for dp in analysis.data_points]
        
        # Main line
        ax.plot(timestamps, fps_values,
               color=self.colors['fps'],
               linewidth=config.line_width,
               label='FPS',
               alpha=0.8)
        
        # Dropped-frame markers
        dropped_times = []
        dropped_fps = []
        for dp in analysis.data_points:
            if dp.dropped_frames > 0:
                dropped_times.append(dp.timestamp / 60)
                dropped_fps.append(dp.fps)
        
        if dropped_times:
            ax.scatter(dropped_times, dropped_fps,
                      color=self.colors['dropped'],
                      s=30, alpha=0.7,
                      label='Dropped Frames', zorder=5)
        
        # Declared FPS line
        ax.axhline(y=analysis.declared_fps,
                  color=self.colors['average'],
                  linestyle='--',
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'Declared FPS ({analysis.declared_fps:.1f} fps)')
        
        # Style
        ax.set_title(config.title or f"FPS Analysis - {os.path.basename(analysis.file_path)}",
                    fontsize=config.font_size + 2, fontweight='bold', pad=20)
        ax.set_xlabel("Time (minutes)", fontsize=config.font_size)
        ax.set_ylabel("FPS", fontsize=config.font_size)
        ax.grid(True, alpha=config.grid_alpha)
        ax.legend(loc='upper right')
        
        # Save chart
        output_path = self._generate_filename("fps_analysis", config)
        plt.tight_layout()
        plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_combined_chart(self, video_analysis: VideoBitrateAnalysis,
                              audio_analysis: AudioBitrateAnalysis,
                              fps_analysis: FPSAnalysis,
                              config: ChartConfig) -> str:
        """Generate combined analysis chart (3 subplots)"""
        
        # Subplots
        fig, axes = plt.subplots(3, 1, figsize=(config.width, config.height),
                               sharex=True)
        
        # 1) Video bitrate subplot
        ax1 = axes[0]
        video_times = [dp.timestamp / 60 for dp in video_analysis.data_points]
        video_rates = [dp.bitrate / 1000000 for dp in video_analysis.data_points]
        
        ax1.plot(video_times, video_rates,
                color=self.colors['video'],
                linewidth=config.line_width,
                label='Video Bitrate')
        
        ax1.set_ylabel('Video Bitrate (Mbps)', fontsize=config.font_size)
        ax1.set_title('Video Bitrate Changes', fontsize=config.font_size, fontweight='bold')
        ax1.grid(True, alpha=config.grid_alpha)
        ax1.legend(loc='upper right')
        
        # 2) Audio bitrate subplot
        ax2 = axes[1]
        audio_times = [dp.timestamp / 60 for dp in audio_analysis.data_points]
        audio_rates = [dp.bitrate / 1000 for dp in audio_analysis.data_points]
        
        ax2.plot(audio_times, audio_rates,
                color=self.colors['audio'],
                linewidth=config.line_width,
                label='Audio Bitrate')
        
        ax2.set_ylabel('Audio Bitrate (kbps)', fontsize=config.font_size)
        ax2.set_title('Audio Bitrate Changes', fontsize=config.font_size, fontweight='bold')
        ax2.grid(True, alpha=config.grid_alpha)
        ax2.legend(loc='upper right')
        
        # 3) FPS subplot
        ax3 = axes[2]
        fps_times = [dp.timestamp / 60 for dp in fps_analysis.data_points]
        fps_values = [dp.fps for dp in fps_analysis.data_points]
        
        ax3.plot(fps_times, fps_values,
                color=self.colors['fps'],
                linewidth=config.line_width,
                label='FPS')
        
        # Dropped-frame markers
        dropped_times = [dp.timestamp / 60 for dp in fps_analysis.data_points if dp.dropped_frames > 0]
        dropped_fps = [dp.fps for dp in fps_analysis.data_points if dp.dropped_frames > 0]
        
        if dropped_times:
            ax3.scatter(dropped_times, dropped_fps,
                       color=self.colors['dropped'], s=20, alpha=0.7,
                       label='Dropped Frames', zorder=5)
        
        ax3.set_ylabel('FPS', fontsize=config.font_size)
        ax3.set_xlabel('Time (minutes)', fontsize=config.font_size)
        ax3.set_title('FPS Changes', fontsize=config.font_size, fontweight='bold')
        ax3.grid(True, alpha=config.grid_alpha)
        ax3.legend(loc='upper right')
        
        # Overall title
        fig.suptitle(config.title or "Video Analysis Report",
                    fontsize=config.font_size + 4,
                    fontweight='bold', y=0.98)
        
        # Layout
        plt.tight_layout()
        plt.subplots_adjust(top=0.93)
        
        # Save
        output_path = self._generate_filename("combined_analysis", config)
        plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_summary_chart(self, video_analysis: VideoBitrateAnalysis,
                              audio_analysis: AudioBitrateAnalysis,
                              fps_analysis: FPSAnalysis,
                              config: ChartConfig) -> str:
        """Generate summary statistics chart"""
        
        fig, axes = plt.subplots(2, 2, figsize=(config.width, config.height))
        
        # 1) Average bitrate comparison (bar)
        ax1 = axes[0, 0]
        categories = ['Video Avg\nBitrate (Mbps)', 'Audio Avg\nBitrate (kbps)']
        values = [video_analysis.average_bitrate / 1000000, audio_analysis.average_bitrate / 1000]
        colors = [self.colors['video'], self.colors['audio']]
        
        bars = ax1.bar(categories, values, color=colors, alpha=0.7)
        ax1.set_title('Average Bitrate Comparison', fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Value labels
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.1f}', ha='center', va='bottom')
        
        # 2) Quality level pie
        ax2 = axes[0, 1]
        
        # Map Chinese quality levels to English (for compatibility)
        audio_quality_map = {'高品质': 'High', '中等': 'Medium', '低品质': 'Low', '标准': 'Standard'}
        fps_grade_map = {'优秀': 'Excellent', '良好': 'Good', '一般': 'Fair', '较差': 'Poor'}
        
        audio_quality_en = audio_quality_map.get(audio_analysis.quality_level, audio_analysis.quality_level)
        fps_grade_en = fps_grade_map.get(fps_analysis.performance_grade, fps_analysis.performance_grade)
        # If already English, pass through
        
        quality_labels = ['Video CBR' if video_analysis.is_cbr else 'Video VBR',
                         f'Audio {audio_quality_en}',
                         f'FPS {fps_grade_en}']
        quality_values = [1, 1, 1]  
        colors = [self.colors['video'], self.colors['audio'], self.colors['fps']]
        
        ax2.pie(quality_values, labels=quality_labels, colors=colors, autopct='')
        ax2.set_title('Quality Assessment', fontweight='bold')
        
        # 3) FPS stability and drop rate
        ax3 = axes[1, 0]
        metrics = ['FPS Stability', 'Drop Rate']
        values = [fps_analysis.fps_stability * 100, fps_analysis.drop_rate * 100]
        colors = [self.colors['fps'], self.colors['dropped']]
        
        bars = ax3.bar(metrics, values, color=colors, alpha=0.7)
        ax3.set_title('FPS Performance Metrics', fontweight='bold')
        ax3.set_ylabel('Percentage (%)')
        ax3.grid(True, alpha=0.3, axis='y')
        
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.1f}%', ha='center', va='bottom')
        
        # 4) File information text
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        info_text = f"""File Information:
Duration: {video_analysis.duration/60:.1f} minutes

Video Information:
Average Bitrate: {video_analysis.average_bitrate/1000000:.2f} Mbps
Encoding Type: {'CBR' if video_analysis.is_cbr else 'VBR'}

Audio Information:
Average Bitrate: {audio_analysis.average_bitrate/1000:.0f} kbps
Codec: {audio_analysis.codec}
Channels: {audio_analysis.channels}

FPS Information:
Declared FPS: {fps_analysis.declared_fps:.1f} fps
Actual FPS: {fps_analysis.actual_average_fps:.1f} fps
Dropped Frames: {fps_analysis.total_dropped_frames}
"""
        
        ax4.text(0.1, 0.9, info_text, transform=ax4.transAxes,
                fontsize=config.font_size - 1, verticalalignment='top',
                fontfamily='monospace')
        
        # Title
        fig.suptitle(config.title or "Video Analysis Summary",
                    fontsize=config.font_size + 2, fontweight='bold')
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.93)
        
        # Save
        output_path = self._generate_filename("summary", config)
        plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_full_report(self, video_analysis: VideoBitrateAnalysis,
                            audio_analysis: AudioBitrateAnalysis,
                            fps_analysis: FPSAnalysis,
                            output_dir: str = "output") -> dict:
        """Generate a full set of analysis charts"""
        
        results = {}
        config = ChartConfig(output_dir=output_dir)
        
        self._logger.info("Generating charts...")
        
        try:
            # 1) Combined analysis chart
            config.title = "Video Analysis Report"
            results['combined'] = self.generate_combined_chart(
                video_analysis, audio_analysis, fps_analysis, config
            )
            self._logger.info("Combined analysis chart generated")
            
            # 2) Video bitrate chart
            config.title = "Video Bitrate Detailed Analysis"
            results['video_bitrate'] = self.generate_video_bitrate_chart(
                video_analysis, config
            )
            self._logger.info("Video bitrate chart generated")
            
            # 3) Audio bitrate chart
            config.title = "Audio Bitrate Detailed Analysis"
            results['audio_bitrate'] = self.generate_audio_bitrate_chart(
                audio_analysis, config
            )
            self._logger.info("Audio bitrate chart generated")
            
            # 4) FPS analysis chart
            config.title = "FPS Detailed Analysis"
            results['fps'] = self.generate_fps_chart(fps_analysis, config)
            self._logger.info("FPS analysis chart generated")
            
            # 5) Summary chart
            config.title = "Video Analysis Summary"
            results['summary'] = self.generate_summary_chart(
                video_analysis, audio_analysis, fps_analysis, config
            )
            self._logger.info("Summary chart generated")
            
            self._logger.info(f"All charts saved to: {output_dir}")
            
        except Exception as e:
            self._logger.exception(f"Error generating charts: {e}")
            raise
        
        return results
    
    def _generate_filename(self, chart_type: str, config: ChartConfig) -> str:
        """Generate output filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{chart_type}_{timestamp}.png"
        
        # Ensure output directory exists
        os.makedirs(config.output_dir, exist_ok=True)
        
        return os.path.join(config.output_dir, filename)


class ChartStyles:
    """Chart style presets"""
    
    @staticmethod
    def get_default_config() -> ChartConfig:
        """Default style config"""
        return ChartConfig(
            width=12,
            height=8,
            dpi=150,
            line_width=2.0,
            grid_alpha=0.3,
            font_size=11
        )
    
    @staticmethod
    def get_high_res_config() -> ChartConfig:
        """High-resolution config"""
        return ChartConfig(
            width=16,
            height=10,
            dpi=300,
            line_width=2.5,
            grid_alpha=0.2,
            font_size=12
        )
    
    @staticmethod
    def get_compact_config() -> ChartConfig:
        """Compact style config"""
        return ChartConfig(
            width=10,
            height=6,
            dpi=150,
            line_width=1.5,
            grid_alpha=0.3,
            font_size=10
        )