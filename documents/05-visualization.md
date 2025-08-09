# 图表可视化模块 - 技术文档

## 模块概述

图表可视化模块负责将视频分析结果转换为直观的PNG图表，支持多种图表类型和样式配置，提供专业级的数据可视化功能。

## 核心功能

- 视频码率线形图（带平均线和趋势分析）
- 音频码率线形图（带VBR检测）
- FPS分析图（带掉帧标记和声明FPS线）
- 综合分析图表（三子图组合）
- 摘要报告图表（关键指标总览）
- 多种输出格式（PNG/PDF）
- 可配置样式（默认/高分辨率/紧凑）

## 技术实现

### 核心类设计

```python
from dataclasses import dataclass
from typing import List, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
from datetime import datetime
from video_analytics.core.video_analyzer import VideoBitrateAnalysis
from video_analytics.core.audio_analyzer import AudioBitrateAnalysis
from video_analytics.core.fps_analyzer import FPSAnalysis
from video_analytics.utils.logger import get_logger

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
        self._logger = get_logger(__name__)
        
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
               label='视频码率',
               alpha=0.8)
        
        # 添加平均线
        avg_bitrate = analysis.average_bitrate / 1000000
        ax.axhline(y=avg_bitrate, 
                  color=self.colors['average'], 
                  linestyle='--', 
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'平均码率 ({avg_bitrate:.1f} Mbps)')
        
        # 设置样式
        ax.set_title(config.title or f"视频码率分析 - {os.path.basename(analysis.file_path)}", 
                    fontsize=config.font_size + 2, fontweight='bold', pad=20)
        ax.set_xlabel("时间 (分钟)", fontsize=config.font_size)
        ax.set_ylabel("码率 (Mbps)", fontsize=config.font_size)
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
               label='音频码率',
               alpha=0.8)
        
        # 添加平均线
        avg_bitrate = analysis.average_bitrate / 1000
        ax.axhline(y=avg_bitrate,
                  color=self.colors['average'],
                  linestyle='--',
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'平均码率 ({avg_bitrate:.0f} kbps)')
        
        # 设置样式
        ax.set_title(config.title or f"音频码率分析 - {os.path.basename(analysis.file_path)}",
                    fontsize=config.font_size + 2, fontweight='bold', pad=20)
        ax.set_xlabel("时间 (分钟)", fontsize=config.font_size)
        ax.set_ylabel("码率 (kbps)", fontsize=config.font_size)
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
                      label='掉帧点', zorder=5)
        
        # 添加声明帧率线
        ax.axhline(y=analysis.declared_fps,
                  color=self.colors['average'],
                  linestyle='--',
                  alpha=0.7,
                  linewidth=1.5,
                  label=f'声明帧率 ({analysis.declared_fps:.1f} fps)')
        
        # 设置样式
        ax.set_title(config.title or f"FPS分析 - {os.path.basename(analysis.file_path)}",
                    fontsize=config.font_size + 2, fontweight='bold', pad=20)
        ax.set_xlabel("时间 (分钟)", fontsize=config.font_size)
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
                label='视频码率')
        
        ax1.set_ylabel('视频码率 (Mbps)', fontsize=config.font_size)
        ax1.set_title('视频码率变化', fontsize=config.font_size, fontweight='bold')
        ax1.grid(True, alpha=config.grid_alpha)
        ax1.legend(loc='upper right')
        
        # 2. 音频码率子图
        ax2 = axes[1]
        audio_times = [dp.timestamp / 60 for dp in audio_analysis.data_points]
        audio_rates = [dp.bitrate / 1000 for dp in audio_analysis.data_points]
        
        ax2.plot(audio_times, audio_rates,
                color=self.colors['audio'],
                linewidth=config.line_width,
                label='音频码率')
        
        ax2.set_ylabel('音频码率 (kbps)', fontsize=config.font_size)
        ax2.set_title('音频码率变化', fontsize=config.font_size, fontweight='bold')
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
                       label='掉帧', zorder=5)
        
        ax3.set_ylabel('FPS', fontsize=config.font_size)
        ax3.set_xlabel('时间 (分钟)', fontsize=config.font_size)
        ax3.set_title('帧率变化', fontsize=config.font_size, fontweight='bold')
        ax3.grid(True, alpha=config.grid_alpha)
        ax3.legend(loc='upper right')
        
        # 整体标题
        fig.suptitle(config.title or "视频综合分析报告",
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
    
    def _generate_filename(self, chart_type: str, config: ChartConfig) -> str:
        """生成输出文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{chart_type}_{timestamp}.png"
        
        # 确保输出目录存在
        os.makedirs(config.output_dir, exist_ok=True)
        
        return os.path.join(config.output_dir, filename)
```

## 图表样式配置

### 样式预设

```python
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
```

## 批量图表生成

### 完整报告生成

```python
def generate_full_report(self, video_analysis: VideoBitrateAnalysis,
                        audio_analysis: AudioBitrateAnalysis,
                        fps_analysis: FPSAnalysis,
                        output_dir: str = "output") -> dict:
    """生成完整的分析报告（所有图表）"""
    
    results = {}
    config = ChartConfig(output_dir=output_dir)
    
    print("正在生成图表...")
    
    try:
        # 1. 综合分析图
        config.title = "视频综合分析报告"
        results['combined'] = self.generate_combined_chart(
            video_analysis, audio_analysis, fps_analysis, config
        )
        print("✓ 综合分析图表已生成")
        
        # 2. 视频码率图
        config.title = "视频码率详细分析"
        results['video_bitrate'] = self.generate_video_bitrate_chart(
            video_analysis, config
        )
        print("✓ 视频码率图表已生成")
        
        # 3. 音频码率图
        config.title = "音频码率详细分析"
        results['audio_bitrate'] = self.generate_audio_bitrate_chart(
            audio_analysis, config
        )
        print("✓ 音频码率图表已生成")
        
        # 4. FPS分析图
        config.title = "FPS详细分析"
        results['fps'] = self.generate_fps_chart(fps_analysis, config)
        print("✓ FPS分析图表已生成")
        
        print(f"\n所有图表已保存到: {output_dir}")
        
    except Exception as e:
        print(f"生成图表时出错: {e}")
        raise
    
    return results
```

### 统计信息图表

```python
def generate_summary_chart(self, video_analysis: VideoBitrateAnalysis,
                          audio_analysis: AudioBitrateAnalysis,
                          fps_analysis: FPSAnalysis,
                          config: ChartConfig) -> str:
    """生成统计信息汇总图表"""
    
    fig, axes = plt.subplots(2, 2, figsize=(config.width, config.height))
    
    # 1. 码率对比柱状图
    ax1 = axes[0, 0]
    categories = ['视频平均码率\n(Mbps)', '音频平均码率\n(kbps)']
    values = [video_analysis.average_bitrate / 1000000, audio_analysis.average_bitrate / 1000]
    colors = [self.colors['video'], self.colors['audio']]
    
    bars = ax1.bar(categories, values, color=colors, alpha=0.7)
    ax1.set_title('平均码率对比', fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 在柱状图上添加数值标签
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.1f}', ha='center', va='bottom')
    
    # 2. 质量等级饼图
    ax2 = axes[0, 1]
    quality_labels = ['视频CBR' if video_analysis.is_cbr else '视频VBR',
                     f'音频{audio_analysis.quality_level}',
                     f'FPS{fps_analysis.performance_grade}']
    quality_values = [1, 1, 1]  # 等权重
    colors = [self.colors['video'], self.colors['audio'], self.colors['fps']]
    
    ax2.pie(quality_values, labels=quality_labels, colors=colors, alpha=0.7, autopct='')
    ax2.set_title('质量评级', fontweight='bold')
    
    # 3. FPS稳定性和掉帧率
    ax3 = axes[1, 0]
    metrics = ['FPS稳定性', '掉帧率']
    values = [fps_analysis.fps_stability * 100, fps_analysis.drop_rate * 100]
    colors = [self.colors['fps'], self.colors['dropped']]
    
    bars = ax3.bar(metrics, values, color=colors, alpha=0.7)
    ax3.set_title('FPS性能指标', fontweight='bold')
    ax3.set_ylabel('百分比 (%)')
    ax3.grid(True, alpha=0.3, axis='y')
    
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.1f}%', ha='center', va='bottom')
    
    # 4. 文件基本信息文本
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    info_text = f"""文件信息：
    时长: {video_analysis.duration/60:.1f} 分钟
    
    视频信息：
    平均码率: {video_analysis.average_bitrate/1000000:.2f} Mbps
    编码类型: {'CBR' if video_analysis.is_cbr else 'VBR'}
    
    音频信息：
    平均码率: {audio_analysis.average_bitrate/1000:.0f} kbps
    编码格式: {audio_analysis.codec}
    声道数: {audio_analysis.channels}
    
    FPS信息：
    声明帧率: {fps_analysis.declared_fps:.1f} fps
    实际帧率: {fps_analysis.actual_average_fps:.1f} fps
    掉帧数: {fps_analysis.total_dropped_frames}
    """
    
    ax4.text(0.1, 0.9, info_text, transform=ax4.transAxes,
            fontsize=config.font_size - 1, verticalalignment='top',
            fontfamily='monospace')
    
    # 整体设置
    fig.suptitle(config.title or "视频分析统计汇总",
                fontsize=config.font_size + 2, fontweight='bold')
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.93)
    
    # 保存
    output_path = self._generate_filename("summary", config)
    plt.savefig(output_path, dpi=config.dpi, bbox_inches='tight')
    plt.close()
    
    return output_path
```

## 使用示例

### 基本图表生成

```python
from visualization.chart_generator import ChartGenerator, ChartConfig
from core.video_analyzer import VideoBitrateAnalyzer
from core.audio_analyzer import AudioBitrateAnalyzer
from core.fps_analyzer import FPSAnalyzer
from core.file_processor import FileProcessor

# 处理文件和分析
processor = FileProcessor()
processed_file = processor.process_input("video.mp4")

video_analyzer = VideoBitrateAnalyzer()
audio_analyzer = AudioBitrateAnalyzer()
fps_analyzer = FPSAnalyzer()

video_result = video_analyzer.analyze(processed_file)
audio_result = audio_analyzer.analyze(processed_file)
fps_result = fps_analyzer.analyze(processed_file)

# 创建图表生成器
generator = ChartGenerator()

# 生成单个图表
config = ChartConfig(output_dir="./charts")

video_chart = generator.generate_video_bitrate_chart(video_result, config)
print(f"视频码率图表: {video_chart}")

audio_chart = generator.generate_audio_bitrate_chart(audio_result, config)
print(f"音频码率图表: {audio_chart}")

fps_chart = generator.generate_fps_chart(fps_result, config)
print(f"FPS图表: {fps_chart}")

# 生成综合图表
combined_chart = generator.generate_combined_chart(
    video_result, audio_result, fps_result, config
)
print(f"综合图表: {combined_chart}")
```

### 批量报告生成

```python
# 生成完整报告
report_files = generator.generate_full_report(
    video_result, audio_result, fps_result, output_dir="./report"
)

print("生成的图表文件:")
for chart_type, file_path in report_files.items():
    print(f"  {chart_type}: {file_path}")

# 生成统计汇总图
summary_chart = generator.generate_summary_chart(
    video_result, audio_result, fps_result, config
)
print(f"统计汇总图: {summary_chart}")
```

### 高分辨率输出

```python
from visualization.chart_generator import ChartStyles

# 使用高分辨率配置
high_res_config = ChartStyles.get_high_res_config()
high_res_config.output_dir = "./high_res_charts"
high_res_config.title = "高清视频分析报告"

high_res_chart = generator.generate_combined_chart(
    video_result, audio_result, fps_result, high_res_config
)

print(f"高分辨率图表: {high_res_chart}")
```

这个模块提供了简单有效的图表可视化功能，专注于生成清晰易读的PNG图表，满足基本的数据展示需求。