"""
Enhanced chart panels module
Implements information panels for enhanced video analysis visualization.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, Wedge
import numpy as np
from typing import Tuple, List, Dict, Any
import math

from ..core.enhanced_analysis import (
    EnhancedAnalysisInfo, 
    VideoQuality, 
    BitrateType,
    FileBasicInfo,
    CodecTechInfo, 
    QualityAssessment,
    IssueDetection
)


class EnhancedPanelDrawer:
    """增强信息面板绘制器"""
    
    def __init__(self, fig, panel_height_ratio: float = 0.4):
        """
        初始化面板绘制器
        
        Args:
            fig: matplotlib figure对象
            panel_height_ratio: 信息面板占总高度的比例
        """
        self.fig = fig
        self.panel_height_ratio = panel_height_ratio
        
        # 颜色配置
        self.colors = {
            'excellent': '#2ecc71',    # 绿色 - 优秀
            'good': '#3498db',         # 蓝色 - 良好  
            'fair': '#f39c12',         # 橙色 - 一般
            'poor': '#e74c3c',         # 红色 - 较差
            'background': '#f8f9fa',   # 背景色
            'text': '#2c3e50',         # 文字色
            'border': '#bdc3c7',       # 边框色
            'panel_bg': '#ffffff',     # 面板背景
        }
        
        # 字体配置
        self.font_sizes = {
            'title': 12,
            'subtitle': 10,
            'content': 9,
            'small': 8
        }
    
    def _apply_info_level(self, info_level: str):
        """根据信息级别调整字体与密度"""
        level = (info_level or 'standard').lower()
        if level == 'basic':
            self.font_sizes = {
                'title': 11,
                'subtitle': 9,
                'content': 8,
                'small': 7
            }
        elif level == 'detailed':
            self.font_sizes = {
                'title': 13,
                'subtitle': 11,
                'content': 10,
                'small': 9
            }
        else:
            self.font_sizes = {
                'title': 12,
                'subtitle': 10,
                'content': 9,
                'small': 8
            }
    
    def draw_all_panels(self, enhanced_info: EnhancedAnalysisInfo,
                       start_y: float = 0.0, panel_height: float = 0.4,
                       axes: Dict[str, Any] = None,
                       show_panels: List[str] = None,
                       info_level: str = 'standard'):
        """绘制所有信息面板
        
        Args:
            enhanced_info: 增强分析信息
            start_y: 起始Y（仅在未提供axes时生效）
            panel_height: 面板高度比例（仅在未提供axes时生效）
            axes: 可选，提供现有的axes字典 {'file_info': ax, ...}
            show_panels: 需要显示的面板列表（默认全部）
            info_level: 信息详细程度 basic/standard/detailed
        """
        self._apply_info_level(info_level)
        
        # 默认显示全部
        if show_panels is None:
            show_panels = ['file_info', 'codec_info', 'quality', 'issues']
        show_set = set(show_panels)
        
        # 计算4个面板的布局 (2x2网格)（仅在未提供axes时使用）
        panel_width = 0.25
        panel_height_each = panel_height / 2
        panels = [
            {'pos': (0.0, start_y + panel_height_each), 'size': (panel_width, panel_height_each), 'type': 'file_info'},
            {'pos': (0.25, start_y + panel_height_each), 'size': (panel_width, panel_height_each), 'type': 'codec_info'},
            {'pos': (0.5, start_y + panel_height_each), 'size': (panel_width, panel_height_each), 'type': 'quality'},
            {'pos': (0.75, start_y + panel_height_each), 'size': (panel_width, panel_height_each), 'type': 'issues'},
        ]
        
        # 绘制各个面板
        for panel_config in panels:
            panel_type = panel_config['type']
            if panel_type not in show_set:
                continue
            
            # 复用现有axes或创建
            if axes and panel_type in axes:
                ax = axes[panel_type]
                ax.clear()
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis('off')
            else:
                x, y = panel_config['pos']
                w, h = panel_config['size']
                ax = self.fig.add_axes([x, start_y, w, h])
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis('off')
            
            # 背景
            bg_rect = Rectangle((0.02, 0.02), 0.96, 0.96,
                              facecolor=self.colors['panel_bg'],
                              edgecolor=self.colors['border'],
                              linewidth=1, alpha=0.9)
            ax.add_patch(bg_rect)
            
            # 内容
            if panel_type == 'file_info':
                self._draw_file_info_panel(ax, enhanced_info.file_basic_info)
            elif panel_type == 'codec_info':
                self._draw_codec_info_panel(ax, enhanced_info.codec_tech_info)
            elif panel_type == 'quality':
                self._draw_quality_panel(ax, enhanced_info.quality_assessment)
            elif panel_type == 'issues':
                self._draw_issues_panel(ax, enhanced_info.issue_detection)
    
    def _draw_file_info_panel(self, ax, file_info: FileBasicInfo):
        """Draw file basic information panel"""
        
        # Panel title
        ax.text(0.5, 0.9, 'File Information', 
                ha='center', va='center', fontsize=self.font_sizes['title'],
                fontweight='bold', color=self.colors['text'])
        
        # Information items
        info_items = [
            ('Filename', self._truncate_filename(file_info.filename)),
            ('Resolution', file_info.resolution),
            ('Duration', file_info.duration_str),
            ('File Size', f"{file_info.file_size_mb} MB"),
            ('Bitrate', f"{file_info.overall_bitrate_mbps:.1f} Mbps"),
        ]
        
        # Draw information items
        y_positions = np.linspace(0.75, 0.15, len(info_items))
        
        for i, (label, value) in enumerate(info_items):
            y = y_positions[i]
            
            # Label
            ax.text(0.05, y, label + ':', 
                   ha='left', va='center', fontsize=self.font_sizes['content'],
                   fontweight='bold', color=self.colors['text'])
            
            # Value
            ax.text(0.95, y, str(value),
                   ha='right', va='center', fontsize=self.font_sizes['content'],
                   color=self.colors['text'])
    
    def _draw_codec_info_panel(self, ax, codec_info: CodecTechInfo):
        """Draw codec technology information panel"""
        
        # Panel title
        ax.text(0.5, 0.9, 'Codec Information', 
                ha='center', va='center', fontsize=self.font_sizes['title'],
                fontweight='bold', color=self.colors['text'])
        
        # Information items
        info_items = [
            ('Video Codec', codec_info.video_codec_full),
            ('Audio Codec', codec_info.audio_codec_full),
            ('Container', codec_info.container_format.upper()),
            ('Audio Channels', codec_info.audio_channels_str),
            ('Sample Rate', codec_info.sample_rate_str),
        ]
        
        # Draw information items
        y_positions = np.linspace(0.75, 0.15, len(info_items))
        
        for i, (label, value) in enumerate(info_items):
            y = y_positions[i]
            
            # Label
            ax.text(0.05, y, label + ':', 
                   ha='left', va='center', fontsize=self.font_sizes['content'],
                   fontweight='bold', color=self.colors['text'])
            
            # Value (may need to truncate long text)
            display_value = self._truncate_text(str(value), 20)
            ax.text(0.95, y, display_value,
                   ha='right', va='center', fontsize=self.font_sizes['content'],
                   color=self.colors['text'])
    
    def _draw_quality_panel(self, ax, quality_info: QualityAssessment):
        """Draw quality assessment panel"""
        
        # Panel title
        ax.text(0.5, 0.9, 'Quality Assessment', 
                ha='center', va='center', fontsize=self.font_sizes['title'],
                fontweight='bold', color=self.colors['text'])
        
        # Quality level color mapping
        quality_color_map = {
            VideoQuality.EXCELLENT: self.colors['excellent'],
            VideoQuality.GOOD: self.colors['good'],
            VideoQuality.FAIR: self.colors['fair'],
            VideoQuality.POOR: self.colors['poor']
        }
        
        # Overall quality display
        quality_color = quality_color_map[quality_info.overall_quality]
        ax.text(0.5, 0.75, quality_info.overall_quality.value,
                ha='center', va='center', fontsize=self.font_sizes['subtitle'],
                fontweight='bold', color=quality_color,
                bbox=dict(boxstyle="round,pad=0.3", facecolor=quality_color, alpha=0.2))
        
        # Quality score gauge
        self._draw_score_gauge(ax, quality_info.quality_score, 
                              center=(0.25, 0.45), radius=0.15)
        
        # Stability indicators
        stability_items = [
            ('Bitrate Stability', quality_info.bitrate_stability, self.colors['good']),
            ('FPS Stability', quality_info.fps_stability, self.colors['fair']),
        ]
        
        y_pos = 0.55
        for label, value, color in stability_items:
            # Label
            ax.text(0.55, y_pos, label + ':', 
                   ha='left', va='center', fontsize=self.font_sizes['small'],
                   color=self.colors['text'])
            
            # Progress bar
            self._draw_progress_bar(ax, value, 
                                  pos=(0.55, y_pos - 0.08), size=(0.35, 0.03),
                                  color=color)
            
            # Percentage
            ax.text(0.92, y_pos, f"{value:.0%}",
                   ha='center', va='center', fontsize=self.font_sizes['small'],
                   color=self.colors['text'])
            
            y_pos -= 0.18
        
        # Bitrate type
        ax.text(0.5, 0.15, quality_info.bitrate_type.value,
                ha='center', va='center', fontsize=self.font_sizes['small'],
                color=self.colors['text'], style='italic')
    
    def _draw_issues_panel(self, ax, issue_info: IssueDetection):
        """Draw issues detection panel"""
        
        # Panel title
        ax.text(0.5, 0.9, 'Issues Detection', 
                ha='center', va='center', fontsize=self.font_sizes['title'],
                fontweight='bold', color=self.colors['text'])
        
        # Issue indicators
        issues = [
            ('Dropped Frames', issue_info.has_dropped_frames),
            ('Severe Drops', issue_info.severe_dropped_frames),
            ('Bitrate Spikes', issue_info.has_bitrate_spikes),
            ('Audio Issues', issue_info.has_audio_issues),
        ]
        
        # Draw issue status
        y_positions = np.linspace(0.75, 0.3, len(issues))
        
        for i, (issue_name, has_issue) in enumerate(issues):
            y = y_positions[i]
            
            # Status indicator
            status_color = self.colors['poor'] if has_issue else self.colors['excellent']
            status_symbol = '⚠️' if has_issue else '✅'
            
            ax.text(0.1, y, status_symbol,
                   ha='center', va='center', fontsize=self.font_sizes['content'])
            
            # Issue name
            ax.text(0.2, y, issue_name,
                   ha='left', va='center', fontsize=self.font_sizes['small'],
                   color=self.colors['text'])
            
            # Status text
            status_text = 'Yes' if has_issue else 'No'
            ax.text(0.85, y, status_text,
                   ha='center', va='center', fontsize=self.font_sizes['small'],
                   color=status_color, fontweight='bold')
        
        # Statistics
        if issue_info.has_dropped_frames:
            stats_text = f"Dropped: {issue_info.dropped_frame_percentage:.1f}%"
            ax.text(0.5, 0.15, stats_text,
                   ha='center', va='center', fontsize=self.font_sizes['small'],
                   color=self.colors['poor'])
        else:
            ax.text(0.5, 0.15, 'No Major Issues',
                   ha='center', va='center', fontsize=self.font_sizes['small'],
                   color=self.colors['excellent'])
    
    def _draw_score_gauge(self, ax, score: int, center: Tuple[float, float], radius: float):
        """Draw score gauge"""
        x, y = center
        
        # Background arc
        bg_arc = Wedge(center, radius, 0, 180, 
                       facecolor=self.colors['background'], 
                       edgecolor=self.colors['border'], linewidth=1)
        ax.add_patch(bg_arc)
        
        # Score arc
        score_angle = score / 100 * 180  # Angle corresponding to score
        
        # Choose color based on score
        if score >= 85:
            score_color = self.colors['excellent']
        elif score >= 70:
            score_color = self.colors['good'] 
        elif score >= 50:
            score_color = self.colors['fair']
        else:
            score_color = self.colors['poor']
        
        score_arc = Wedge(center, radius * 0.8, 0, score_angle,
                         facecolor=score_color, alpha=0.8)
        ax.add_patch(score_arc)
        
        # Score text
        ax.text(x, y - radius * 0.3, f"{score}",
                ha='center', va='center', fontsize=self.font_sizes['subtitle'],
                fontweight='bold', color=score_color)
        
        ax.text(x, y - radius * 0.6, "Score",
                ha='center', va='center', fontsize=self.font_sizes['small'],
                color=self.colors['text'])
    
    def _draw_progress_bar(self, ax, value: float, pos: Tuple[float, float], 
                          size: Tuple[float, float], color: str):
        """Draw progress bar"""
        x, y = pos
        w, h = size
        
        # Background bar
        bg_rect = Rectangle((x, y), w, h, 
                           facecolor=self.colors['background'],
                           edgecolor=self.colors['border'], linewidth=0.5)
        ax.add_patch(bg_rect)
        
        # Progress bar
        progress_w = w * value
        progress_rect = Rectangle((x, y), progress_w, h,
                                 facecolor=color, alpha=0.7)
        ax.add_patch(progress_rect)
    
    def _truncate_filename(self, filename: str, max_length: int = 20) -> str:
        """Truncate filename"""
        if len(filename) <= max_length:
            return filename
        
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        available = max_length - len(ext) - 4  # Reserve space for extension and ellipsis
        
        if available > 0:
            return f"{name[:available]}...{ext}"
        else:
            return f"{filename[:max_length-3]}..."
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text"""
        if len(text) <= max_length:
            return text
        return f"{text[:max_length-3]}..."