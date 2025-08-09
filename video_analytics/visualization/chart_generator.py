"""
图表可视化模块
负责将视频分析结果转换为直观的PNG图表
"""

import json
import os
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from ..core.video_bitrate_analyzer import VideoBitrateAnalysis
from ..core.audio_bitrate_analyzer import AudioBitrateAnalysis
from ..core.fps_analyzer import FPSAnalysis


@dataclass
class ChartConfig:
    """图表配置"""
    width: int = 12          # 图表宽度(英寸)
    height: int = 8          # 图表高度(英寸)
    dpi: int = 150          # 图片分辨率
    title: str = ""         # 图表标题
    output_dir: str = "output"  # 输出目录
    
    # 样式配置
    line_width: float = 2.0
    grid_alpha: float = 0.3
    font_size: int = 11


class ChartGenerator:
    """图表生成器"""
    
    def __init__(self):
        # 设置默认样式
        plt.style.use('default')
        
        # 默认颜色
        self.colors = {
            'video': '#1f77b4',    # 蓝色
            'audio': '#ff7f0e',    # 橙色  
            'fps': '#2ca02c',      # 绿色
            'dropped': '#d62728',  # 红色
            'average': '#ff0000'   # 红色虚线
        }
    
    def generate_video_bitrate_chart(self, analysis: VideoBitrateAnalysis, 
                                   config: ChartConfig) -> str:
        """生成视频码率图表"""
        fig, ax = plt.subplots(figsize=(config.width, config.height))
        
        # 准备数据
        timestamps = [dp.timestamp / 60 for dp in analysis.data_points]  # 转换为分钟
        bitrates = [dp.bitrate / 1000000 for dp in analysis.data_points]  # 转换为Mbps
        
        # 绘制主线
        ax.plot(timestamps, bitrates, 
               color=self.colors['video'],
               linewidth=config.line_width,
               label='Video Bitrate',
               alpha=0.8)
        
        # 添加平均线
        avg_bitrate = analysis.average_bitrate / 1000000
        ax.axhline(y=avg_bitrate, 
                  color=self.colors['average'], 
                  linestyle='--', 
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'Average ({avg_bitrate:.1f} Mbps)')
        
        # 设置样式
        ax.set_title(config.title or f"Video Bitrate Analysis - {os.path.basename(analysis.file_path)}", 
                    fontsize=config.font_size + 2, fontweight='bold', pad=20)
        ax.set_xlabel("Time (minutes)", fontsize=config.font_size)
        ax.set_ylabel("Bitrate (Mbps)", fontsize=config.font_size)
        ax.grid(True, alpha=config.grid_alpha)
        ax.legend(loc='upper right')
        
        # 保存图表
        output_path = self._generate_filename("video_bitrate", config)
        plt.tight_layout()
        plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_audio_bitrate_chart(self, analysis: AudioBitrateAnalysis,
                                   config: ChartConfig) -> str:
        """生成音频码率图表"""
        fig, ax = plt.subplots(figsize=(config.width, config.height))
        
        # 准备数据
        timestamps = [dp.timestamp / 60 for dp in analysis.data_points]
        bitrates = [dp.bitrate / 1000 for dp in analysis.data_points]  # 转换为kbps
        
        # 绘制主线
        ax.plot(timestamps, bitrates,
               color=self.colors['audio'],
               linewidth=config.line_width,
               label='Audio Bitrate',
               alpha=0.8)
        
        # 添加平均线
        avg_bitrate = analysis.average_bitrate / 1000
        ax.axhline(y=avg_bitrate,
                  color=self.colors['average'],
                  linestyle='--',
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'Average ({avg_bitrate:.0f} kbps)')
        
        # 设置样式
        ax.set_title(config.title or f"Audio Bitrate Analysis - {os.path.basename(analysis.file_path)}",
                    fontsize=config.font_size + 2, fontweight='bold', pad=20)
        ax.set_xlabel("Time (minutes)", fontsize=config.font_size)
        ax.set_ylabel("Bitrate (kbps)", fontsize=config.font_size)
        ax.grid(True, alpha=config.grid_alpha)
        ax.legend(loc='upper right')
        
        # 保存图表
        output_path = self._generate_filename("audio_bitrate", config)
        plt.tight_layout()
        plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_fps_chart(self, analysis: FPSAnalysis, config: ChartConfig) -> str:
        """生成FPS图表"""
        fig, ax = plt.subplots(figsize=(config.width, config.height))
        
        # 准备数据
        timestamps = [dp.timestamp / 60 for dp in analysis.data_points]
        fps_values = [dp.fps for dp in analysis.data_points]
        
        # 绘制主线
        ax.plot(timestamps, fps_values,
               color=self.colors['fps'],
               linewidth=config.line_width,
               label='FPS',
               alpha=0.8)
        
        # 添加掉帧标记
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
        
        # 添加声明帧率线
        ax.axhline(y=analysis.declared_fps,
                  color=self.colors['average'],
                  linestyle='--',
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'Declared FPS ({analysis.declared_fps:.1f} fps)')
        
        # 设置样式
        ax.set_title(config.title or f"FPS Analysis - {os.path.basename(analysis.file_path)}",
                    fontsize=config.font_size + 2, fontweight='bold', pad=20)
        ax.set_xlabel("Time (minutes)", fontsize=config.font_size)
        ax.set_ylabel("FPS", fontsize=config.font_size)
        ax.grid(True, alpha=config.grid_alpha)
        ax.legend(loc='upper right')
        
        # 保存图表
        output_path = self._generate_filename("fps_analysis", config)
        plt.tight_layout()
        plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_combined_chart(self, video_analysis: VideoBitrateAnalysis,
                              audio_analysis: AudioBitrateAnalysis,
                              fps_analysis: FPSAnalysis,
                              config: ChartConfig) -> str:
        """生成综合分析图表（三合一）"""
        
        # 创建子图
        fig, axes = plt.subplots(3, 1, figsize=(config.width, config.height),
                               sharex=True)
        
        # 1. 视频码率子图
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
        
        # 2. 音频码率子图
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
        
        # 3. FPS子图
        ax3 = axes[2]
        fps_times = [dp.timestamp / 60 for dp in fps_analysis.data_points]
        fps_values = [dp.fps for dp in fps_analysis.data_points]
        
        ax3.plot(fps_times, fps_values,
                color=self.colors['fps'],
                linewidth=config.line_width,
                label='FPS')
        
        # 添加掉帧标记
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
        
        # 整体标题
        fig.suptitle(config.title or "Video Analysis Report",
                    fontsize=config.font_size + 4,
                    fontweight='bold', y=0.98)
        
        # 调整布局
        plt.tight_layout()
        plt.subplots_adjust(top=0.93)
        
        # 保存
        output_path = self._generate_filename("combined_analysis", config)
        plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_summary_chart(self, video_analysis: VideoBitrateAnalysis,
                              audio_analysis: AudioBitrateAnalysis,
                              fps_analysis: FPSAnalysis,
                              config: ChartConfig) -> str:
        """生成统计信息汇总图表"""
        
        fig, axes = plt.subplots(2, 2, figsize=(config.width, config.height))
        
        # 1. 码率对比柱状图
        ax1 = axes[0, 0]
        categories = ['Video Avg\nBitrate (Mbps)', 'Audio Avg\nBitrate (kbps)']
        values = [video_analysis.average_bitrate / 1000000, audio_analysis.average_bitrate / 1000]
        colors = [self.colors['video'], self.colors['audio']]
        
        bars = ax1.bar(categories, values, color=colors, alpha=0.7)
        ax1.set_title('Average Bitrate Comparison', fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 在柱状图上添加数值标签
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.1f}', ha='center', va='bottom')
        
        # 2. 质量等级饼图
        ax2 = axes[0, 1]
        
        # 转换中文质量等级为英文
        audio_quality_map = {'高品质': 'High', '中等': 'Medium', '低品质': 'Low', '标准': 'Standard'}
        fps_grade_map = {'优秀': 'Excellent', '良好': 'Good', '一般': 'Fair', '较差': 'Poor'}
        
        audio_quality_en = audio_quality_map.get(audio_analysis.quality_level, audio_analysis.quality_level)
        fps_grade_en = fps_grade_map.get(fps_analysis.performance_grade, fps_analysis.performance_grade)
        
        quality_labels = ['Video CBR' if video_analysis.is_cbr else 'Video VBR',
                         f'Audio {audio_quality_en}',
                         f'FPS {fps_grade_en}']
        quality_values = [1, 1, 1]  # 等权重
        colors = [self.colors['video'], self.colors['audio'], self.colors['fps']]
        
        ax2.pie(quality_values, labels=quality_labels, colors=colors, autopct='')
        ax2.set_title('Quality Assessment', fontweight='bold')
        
        # 3. FPS稳定性和掉帧率
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
        
        # 4. 文件基本信息文本
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
        
        # 整体设置
        fig.suptitle(config.title or "Video Analysis Summary",
                    fontsize=config.font_size + 2, fontweight='bold')
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.93)
        
        # 保存
        output_path = self._generate_filename("summary", config)
        plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_full_report(self, video_analysis: VideoBitrateAnalysis,
                            audio_analysis: AudioBitrateAnalysis,
                            fps_analysis: FPSAnalysis,
                            output_dir: str = "output") -> dict:
        """生成完整的分析报告（所有图表）"""
        
        results = {}
        config = ChartConfig(output_dir=output_dir)
        
        print("Generating charts...")
        
        try:
            # 1. 综合分析图
            config.title = "Video Analysis Report"
            results['combined'] = self.generate_combined_chart(
                video_analysis, audio_analysis, fps_analysis, config
            )
            print("✓ Combined analysis chart generated")
            
            # 2. 视频码率图
            config.title = "Video Bitrate Detailed Analysis"
            results['video_bitrate'] = self.generate_video_bitrate_chart(
                video_analysis, config
            )
            print("✓ Video bitrate chart generated")
            
            # 3. 音频码率图
            config.title = "Audio Bitrate Detailed Analysis"
            results['audio_bitrate'] = self.generate_audio_bitrate_chart(
                audio_analysis, config
            )
            print("✓ Audio bitrate chart generated")
            
            # 4. FPS分析图
            config.title = "FPS Detailed Analysis"
            results['fps'] = self.generate_fps_chart(fps_analysis, config)
            print("✓ FPS analysis chart generated")
            
            # 5. 统计汇总图
            config.title = "Video Analysis Summary"
            results['summary'] = self.generate_summary_chart(
                video_analysis, audio_analysis, fps_analysis, config
            )
            print("✓ Summary chart generated")
            
            print(f"\nAll charts saved to: {output_dir}")
            
        except Exception as e:
            print(f"Error generating charts: {e}")
            raise
        
        return results
    
    def _generate_filename(self, chart_type: str, config: ChartConfig) -> str:
        """生成输出文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{chart_type}_{timestamp}.png"
        
        # 确保输出目录存在
        os.makedirs(config.output_dir, exist_ok=True)
        
        return os.path.join(config.output_dir, filename)


class ChartStyles:
    """图表样式预设"""
    
    @staticmethod
    def get_default_config() -> ChartConfig:
        """默认样式配置"""
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
        """高分辨率配置"""
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
        """紧凑样式配置"""
        return ChartConfig(
            width=10,
            height=6,
            dpi=150,
            line_width=1.5,
            grid_alpha=0.3,
            font_size=10
        )