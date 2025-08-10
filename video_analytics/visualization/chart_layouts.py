"""
Chart layout management module
Handles complex chart layouts for enhanced visualization.
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.figure import Figure
from typing import Tuple, Dict, Any, Optional

from ..core.enhanced_analysis import EnhancedAnalysisInfo


class ChartLayoutManager:
    """图表布局管理器"""
    
    def __init__(self, width: float = 16, height: float = 12):
        """
        初始化布局管理器
        
        Args:
            width: 图表宽度 (inches)
            height: 图表高度 (inches)
        """
        self.width = width
        self.height = height
        self.fig = None
        self.gridspec = None
        
        # 布局配置
        self.layout_config = {
            'main_chart_height_ratio': 0.6,    # 主图表占60%高度
            'info_panels_height_ratio': 0.4,   # 信息面板占40%高度  
            'title_height': 0.08,               # 标题区域高度
            'padding': 0.02,                    # 边距
        }
    
    def create_enhanced_layout(self, title: str = "") -> Tuple[Figure, Dict[str, Any]]:
        """
        Create enhanced chart layout with 3-subplot main chart (like combined_analysis)
        
        Args:
            title: Chart title
            
        Returns:
            Tuple[Figure, Dict]: (matplotlib figure object, layout info dict)
        """
        # Create figure
        self.fig = plt.figure(figsize=(self.width, self.height))
        self.fig.patch.set_facecolor('white')
        
        # Main layout using GridSpec
        main_gs = gridspec.GridSpec(
            2, 1, 
            figure=self.fig,
            height_ratios=[
                self.layout_config['main_chart_height_ratio'], 
                self.layout_config['info_panels_height_ratio']
            ],
            hspace=0.15  # Row spacing
        )
        
        # Main chart area - 3 subplots (video, audio, fps)
        main_charts_gs = gridspec.GridSpecFromSubplotSpec(
            3, 1,  # 3 rows, 1 column
            main_gs[0, 0],  # In the first row of main grid
            hspace=0.5,  # Increase spacing between subplots to avoid title overlap
        )
        
        # Create 3 main chart subplots
        main_charts = {
            'video_bitrate': self.fig.add_subplot(main_charts_gs[0, 0]),
            'audio_bitrate': self.fig.add_subplot(main_charts_gs[1, 0]),
            'fps': self.fig.add_subplot(main_charts_gs[2, 0]),
        }
        
        # Configure main chart subplots
        main_charts['video_bitrate'].set_title('Video Bitrate Changes', fontweight='bold', fontsize=12, pad=10)
        main_charts['video_bitrate'].set_ylabel('Video Bitrate (Mbps)', fontsize=11)
        main_charts['video_bitrate'].grid(True, alpha=0.3)
        
        main_charts['audio_bitrate'].set_title('Audio Bitrate Changes', fontweight='bold', fontsize=12, pad=10)
        main_charts['audio_bitrate'].set_ylabel('Audio Bitrate (kbps)', fontsize=11)
        main_charts['audio_bitrate'].grid(True, alpha=0.3)
        
        main_charts['fps'].set_title('FPS Changes', fontweight='bold', fontsize=12, pad=10)
        main_charts['fps'].set_ylabel('FPS', fontsize=11)
        main_charts['fps'].set_xlabel('Time (minutes)', fontsize=11)
        main_charts['fps'].grid(True, alpha=0.3)
        
        # Info panels area - nested GridSpec for 2x2 grid
        info_panels_gs = gridspec.GridSpecFromSubplotSpec(
            2, 2,  # 2 rows, 2 columns
            main_gs[1, 0],  # In the second row of main grid
            wspace=0.2,  # Column spacing
            hspace=0.25    # Row spacing
        )
        
        # Create 4 info panel subplots
        info_panels = {
            'file_info': self.fig.add_subplot(info_panels_gs[0, 0]),      # Top-left
            'codec_info': self.fig.add_subplot(info_panels_gs[0, 1]),     # Top-right
            'quality': self.fig.add_subplot(info_panels_gs[1, 0]),        # Bottom-left
            'issues': self.fig.add_subplot(info_panels_gs[1, 1]),         # Bottom-right
        }
        
        # Configure info panels
        for panel_ax in info_panels.values():
            panel_ax.set_xlim(0, 1)
            panel_ax.set_ylim(0, 1) 
            panel_ax.axis('off')
            # Add panel border
            panel_ax.add_patch(plt.Rectangle(
                (0, 0), 1, 1, 
                fill=False, edgecolor='lightgray', linewidth=1
            ))
        
        # Add overall title
        if title:
            self.fig.suptitle(title, fontsize=18, fontweight='bold', y=0.97)
        
        # Return layout info
        layout_info = {
            'main_charts': main_charts,  # Changed from 'main_chart' to 'main_charts'
            'info_panels': info_panels,
            'gridspec': main_gs,
            'main_charts_gridspec': main_charts_gs,
            'info_gridspec': info_panels_gs,
            'config': self.layout_config
        }
        
        return self.fig, layout_info
    
    def create_standard_layout(self) -> Tuple[Figure, Dict[str, Any]]:
        """
        创建标准图表布局(向下兼容)
        
        Returns:
            Tuple[Figure, Dict]: (matplotlib图表对象, 布局信息字典)
        """
        self.fig = plt.figure(figsize=(self.width, self.height))
        self.fig.patch.set_facecolor('white')
        
        # 简单的单图表布局
        main_ax = self.fig.add_subplot(1, 1, 1)
        
        layout_info = {
            'main_chart': main_ax,
            'info_panels': {},  # 标准布局没有信息面板
            'config': self.layout_config
        }
        
        return self.fig, layout_info
    
    def optimize_layout_for_content(self, enhanced_info: EnhancedAnalysisInfo) -> Dict[str, Any]:
        """
        根据内容优化布局参数
        
        Args:
            enhanced_info: 增强分析信息
            
        Returns:
            Dict: 优化后的布局配置
        """
        optimized_config = self.layout_config.copy()
        
        # 根据问题数量调整面板高度
        issue_count = sum([
            enhanced_info.issue_detection.has_dropped_frames,
            enhanced_info.issue_detection.severe_dropped_frames,
            enhanced_info.issue_detection.has_bitrate_spikes,
            enhanced_info.issue_detection.has_audio_issues
        ])
        
        # 如果问题较多，增加信息面板的高度比例
        if issue_count >= 3:
            optimized_config['info_panels_height_ratio'] = 0.45
            optimized_config['main_chart_height_ratio'] = 0.55
        elif issue_count == 0:
            # 如果没有问题，减少信息面板高度
            optimized_config['info_panels_height_ratio'] = 0.35
            optimized_config['main_chart_height_ratio'] = 0.65
        
        # 根据文件名长度调整标题高度
        filename_length = len(enhanced_info.file_basic_info.filename)
        if filename_length > 50:
            optimized_config['title_height'] = 0.10
        elif filename_length < 20:
            optimized_config['title_height'] = 0.06
        
        return optimized_config
    
    def add_watermark(self, text: str = "Enhanced Video Analytics", 
                     position: Tuple[float, float] = (0.99, 0.01), 
                     alpha: float = 0.3):
        """
        添加水印
        
        Args:
            text: 水印文字
            position: 水印位置 (x, y) 相对于整个图表
            alpha: 透明度
        """
        if self.fig:
            self.fig.text(
                position[0], position[1], text,
                ha='right', va='bottom',
                fontsize=8, alpha=alpha, color='gray',
                transform=self.fig.transFigure
            )
    
    def save_layout(self, filename: str, dpi: int = 300, bbox_inches: str = 'tight'):
        """
        保存图表
        
        Args:
            filename: 文件名
            dpi: 分辨率
            bbox_inches: 边界框设置
        """
        if self.fig:
            self.fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches, 
                           facecolor='white', edgecolor='none')
    
    def close(self):
        """关闭图表"""
        if self.fig:
            plt.close(self.fig)
            self.fig = None


def create_enhanced_chart_layout(width: float = 16, height: float = 12, 
                                title: str = "") -> Tuple[Figure, Dict[str, Any]]:
    """
    便捷函数：创建增强图表布局
    
    Args:
        width: 图表宽度
        height: 图表高度  
        title: 标题
        
    Returns:
        Tuple[Figure, Dict]: (matplotlib图表对象, 布局信息字典)
    """
    layout_manager = ChartLayoutManager(width, height)
    return layout_manager.create_enhanced_layout(title)


def create_responsive_layout(enhanced_info: EnhancedAnalysisInfo, 
                           base_width: float = 16, base_height: float = 12) -> Tuple[Figure, Dict[str, Any]]:
    """
    创建响应式布局（根据内容自动调整）
    
    Args:
        enhanced_info: 增强分析信息
        base_width: 基础宽度
        base_height: 基础高度
        
    Returns:
        Tuple[Figure, Dict]: (matplotlib图表对象, 布局信息字典)
    """
    layout_manager = ChartLayoutManager(base_width, base_height)
    
    # 根据内容优化配置
    optimized_config = layout_manager.optimize_layout_for_content(enhanced_info)
    layout_manager.layout_config.update(optimized_config)
    
    # 生成标题
    filename = enhanced_info.file_basic_info.filename
    title = f"Enhanced Video Analysis - {filename}"
    
    fig, layout_info = layout_manager.create_enhanced_layout(title)
    layout_info['manager'] = layout_manager  # 保存管理器引用以便后续操作
    
    return fig, layout_info