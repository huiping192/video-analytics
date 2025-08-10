"""
Visual elements module
Provides custom visual components like gauges, annotations, and indicators.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, Wedge, Rectangle, FancyBboxPatch
import matplotlib.lines as mlines
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
import math

from ..core.enhanced_analysis import VideoQuality, BitrateType


class GaugeChart:
    """仪表盘图表组件"""
    
    def __init__(self, ax, center: Tuple[float, float], radius: float):
        """
        初始化仪表盘
        
        Args:
            ax: matplotlib axis对象
            center: 中心点坐标 (x, y)
            radius: 半径
        """
        self.ax = ax
        self.center = center
        self.radius = radius
        
        # 颜色配置
        self.colors = {
            'excellent': '#2ecc71',  # 绿色
            'good': '#3498db',       # 蓝色
            'fair': '#f39c12',       # 橙色
            'poor': '#e74c3c',       # 红色
            'background': '#ecf0f1', # 背景色
            'text': '#2c3e50'        # 文字色
        }
    
    def draw_score_gauge(self, score: int, title: str = "Quality Score"):
        """Draw score gauge"""
        x, y = self.center
        
        # Background semicircle
        bg_wedge = Wedge(
            self.center, self.radius, 0, 180,
            facecolor=self.colors['background'],
            edgecolor='gray', linewidth=1
        )
        self.ax.add_patch(bg_wedge)
        
        # Calculate score angle and color
        score_angle = (score / 100) * 180
        score_color = self._get_score_color(score)
        
        # Score wedge
        score_wedge = Wedge(
            self.center, self.radius * 0.9, 0, score_angle,
            facecolor=score_color, alpha=0.8
        )
        self.ax.add_patch(score_wedge)
        
        # Center text
        self.ax.text(x, y - self.radius * 0.2, str(score),
                    ha='center', va='center', fontsize=16, fontweight='bold',
                    color=score_color)
        
        self.ax.text(x, y - self.radius * 0.5, title,
                    ha='center', va='center', fontsize=10,
                    color=self.colors['text'])
        
        # Gauge ticks
        self._draw_gauge_ticks()
    
    def draw_stability_gauge(self, stability: float, title: str = "Stability"):
        """Draw stability gauge"""
        x, y = self.center
        
        # Background
        bg_circle = Circle(self.center, self.radius, 
                          facecolor=self.colors['background'], 
                          edgecolor='gray', linewidth=1)
        self.ax.add_patch(bg_circle)
        
        # Stability arc
        angle = stability * 360
        stability_color = self._get_stability_color(stability)
        
        # Create stability indicator
        theta = np.linspace(0, np.radians(angle), 100)
        r_inner = self.radius * 0.6
        r_outer = self.radius * 0.9
        
        for i, t in enumerate(theta[:-1]):
            wedge = Wedge(
                self.center, r_outer, np.degrees(t), np.degrees(theta[i+1]),
                width=r_outer - r_inner, facecolor=stability_color, alpha=0.7
            )
            self.ax.add_patch(wedge)
        
        # Center text
        self.ax.text(x, y, f"{stability:.1%}",
                    ha='center', va='center', fontsize=12, fontweight='bold',
                    color=stability_color)
        
        self.ax.text(x, y - self.radius * 0.4, title,
                    ha='center', va='center', fontsize=9,
                    color=self.colors['text'])
    
    def _get_score_color(self, score: int) -> str:
        """Get color based on score"""
        if score >= 85:
            return self.colors['excellent']
        elif score >= 70:
            return self.colors['good']
        elif score >= 50:
            return self.colors['fair']
        else:
            return self.colors['poor']
    
    def _get_stability_color(self, stability: float) -> str:
        """Get color based on stability"""
        if stability >= 0.9:
            return self.colors['excellent']
        elif stability >= 0.7:
            return self.colors['good']
        elif stability >= 0.5:
            return self.colors['fair']
        else:
            return self.colors['poor']
    
    def _draw_gauge_ticks(self):
        """Draw gauge ticks"""
        x, y = self.center
        
        # Major ticks (0, 25, 50, 75, 100)
        for score in [0, 25, 50, 75, 100]:
            angle = np.radians(score / 100 * 180)
            x1 = x + (self.radius * 1.05) * np.cos(angle)
            y1 = y + (self.radius * 1.05) * np.sin(angle)
            x2 = x + (self.radius * 1.15) * np.cos(angle)
            y2 = y + (self.radius * 1.15) * np.sin(angle)
            
            self.ax.plot([x1, x2], [y1, y2], 'k-', linewidth=2)
            
            # Tick labels
            x_label = x + (self.radius * 1.25) * np.cos(angle)
            y_label = y + (self.radius * 1.25) * np.sin(angle)
            self.ax.text(x_label, y_label, str(score),
                        ha='center', va='center', fontsize=8,
                        color=self.colors['text'])


class ProgressBar:
    """Progress bar component"""
    
    def __init__(self, ax, position: Tuple[float, float], size: Tuple[float, float]):
        """
        Initialize progress bar
        
        Args:
            ax: matplotlib axis object
            position: position (x, y)
            size: size (width, height)
        """
        self.ax = ax
        self.position = position
        self.size = size
        
        self.colors = {
            'background': '#ecf0f1',
            'excellent': '#2ecc71',
            'good': '#3498db',
            'fair': '#f39c12',
            'poor': '#e74c3c'
        }
    
    def draw(self, value: float, color: str = None, label: str = "", show_percentage: bool = True):
        """
        Draw progress bar
        
        Args:
            value: progress value (0.0 - 1.0)
            color: progress bar color
            label: label text
            show_percentage: whether to show percentage
        """
        x, y = self.position
        w, h = self.size
        
        # Auto-select color
        if color is None:
            color = self._get_progress_color(value)
        
        # Background
        bg_rect = Rectangle((x, y), w, h,
                           facecolor=self.colors['background'],
                           edgecolor='gray', linewidth=0.5)
        self.ax.add_patch(bg_rect)
        
        # Progress bar
        progress_w = w * value
        progress_rect = Rectangle((x, y), progress_w, h,
                                 facecolor=color, alpha=0.8)
        self.ax.add_patch(progress_rect)
        
        # Label
        if label:
            self.ax.text(x - 0.01, y + h/2, label,
                        ha='right', va='center', fontsize=9,
                        color='black')
        
        # Percentage
        if show_percentage:
            self.ax.text(x + w + 0.01, y + h/2, f"{value:.0%}",
                        ha='left', va='center', fontsize=9,
                        color='black')
    
    def _get_progress_color(self, value: float) -> str:
        """Get color based on value"""
        if value >= 0.9:
            return self.colors['excellent']
        elif value >= 0.7:
            return self.colors['good']
        elif value >= 0.5:
            return self.colors['fair']
        else:
            return self.colors['poor']


class StatusIndicator:
    """Status indicator component"""
    
    def __init__(self, ax):
        """Initialize status indicator"""
        self.ax = ax
        
        self.colors = {
            'success': '#2ecc71',
            'warning': '#f39c12',
            'error': '#e74c3c',
            'info': '#3498db'
        }
        
        self.symbols = {
            'success': '✅',
            'warning': '⚠️', 
            'error': '❌',
            'info': 'ℹ️'
        }
    
    def draw_status_grid(self, statuses: List[Dict[str, Any]], position: Tuple[float, float]):
        """
        绘制状态网格
        
        Args:
            statuses: 状态列表，每个状态包含 {'name': str, 'status': str, 'value': Any}
            position: 起始位置 (x, y)
        """
        x_start, y_start = position
        row_height = 0.08
        
        for i, status_info in enumerate(statuses):
            y = y_start - i * row_height
            
            name = status_info['name']
            status = status_info['status']  # 'success', 'warning', 'error', 'info'
            value = status_info.get('value', '')
            
            # 状态符号
            symbol = self.symbols.get(status, '◯')
            color = self.colors.get(status, 'gray')
            
            self.ax.text(x_start, y, symbol, ha='left', va='center',
                        fontsize=12, color=color)
            
            # 状态名称
            self.ax.text(x_start + 0.08, y, name, ha='left', va='center',
                        fontsize=10, color='black')
            
            # 状态值
            if value:
                self.ax.text(x_start + 0.6, y, str(value), ha='left', va='center',
                            fontsize=10, color=color, fontweight='bold')
    
    def draw_simple_indicator(self, position: Tuple[float, float], 
                            status: str, text: str = ""):
        """
        绘制简单状态指示器
        
        Args:
            position: 位置 (x, y)
            status: 状态类型
            text: 显示文字
        """
        x, y = position
        
        symbol = self.symbols.get(status, '◯')
        color = self.colors.get(status, 'gray')
        
        # 状态符号
        self.ax.text(x, y, symbol, ha='center', va='center',
                    fontsize=14, color=color)
        
        # 文字
        if text:
            self.ax.text(x, y - 0.05, text, ha='center', va='center',
                        fontsize=9, color='black')


class AnnotationHelper:
    """标注助手"""
    
    def __init__(self, ax):
        """初始化标注助手"""
        self.ax = ax
        
        self.colors = {
            'highlight': '#e74c3c',
            'info': '#3498db',
            'warning': '#f39c12',
            'success': '#2ecc71'
        }
    
    def add_peak_annotation(self, x: float, y: float, value: Any, 
                           annotation_type: str = 'highlight'):
        """
        添加峰值标注
        
        Args:
            x, y: 标注点坐标
            value: 显示值
            annotation_type: 标注类型
        """
        color = self.colors.get(annotation_type, self.colors['highlight'])
        
        # 标注点
        self.ax.scatter(x, y, color=color, s=50, zorder=5)
        
        # 标注文字
        self.ax.annotate(
            str(value), 
            xy=(x, y), 
            xytext=(x, y + (self.ax.get_ylim()[1] - self.ax.get_ylim()[0]) * 0.1),
            ha='center', va='bottom',
            fontsize=8, color=color,
            arrowprops=dict(arrowstyle='->', color=color, lw=1),
            bbox=dict(boxstyle="round,pad=0.2", facecolor='white', 
                     edgecolor=color, alpha=0.8)
        )
    
    def highlight_time_range(self, x_start: float, x_end: float, 
                           color: str = 'warning', alpha: float = 0.3,
                           label: str = ""):
        """
        高亮显示时间范围
        
        Args:
            x_start, x_end: 时间范围
            color: 高亮颜色类型
            alpha: 透明度
            label: 标签
        """
        highlight_color = self.colors.get(color, color)
        
        # 高亮区域
        y_min, y_max = self.ax.get_ylim()
        self.ax.axvspan(x_start, x_end, alpha=alpha, color=highlight_color, 
                       zorder=1, label=label)
    
    def add_threshold_line(self, y_value: float, color: str = 'warning',
                          line_style: str = '--', label: str = ""):
        """
        添加阈值线
        
        Args:
            y_value: Y轴阈值
            color: 线条颜色类型
            line_style: 线条样式
            label: 标签
        """
        line_color = self.colors.get(color, color)
        
        self.ax.axhline(y_value, color=line_color, linestyle=line_style,
                       alpha=0.7, linewidth=2, label=label)


def create_info_card(ax, position: Tuple[float, float], size: Tuple[float, float],
                    title: str, content: List[str], card_color: str = 'info'):
    """
    创建信息卡片
    
    Args:
        ax: matplotlib axis对象
        position: 卡片位置 (x, y)
        size: 卡片大小 (width, height)
        title: 卡片标题
        content: 内容列表
        card_color: 卡片颜色类型
    """
    x, y = position
    w, h = size
    
    colors = {
        'info': '#3498db',
        'success': '#2ecc71', 
        'warning': '#f39c12',
        'error': '#e74c3c'
    }
    
    card_color_hex = colors.get(card_color, colors['info'])
    
    # 卡片背景
    card_bg = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02",
        facecolor='white',
        edgecolor=card_color_hex,
        linewidth=2,
        alpha=0.9
    )
    ax.add_patch(card_bg)
    
    # 标题
    ax.text(x + w/2, y + h - 0.03, title,
           ha='center', va='top', fontsize=11, fontweight='bold',
           color=card_color_hex)
    
    # 内容
    content_y = y + h - 0.08
    line_height = 0.04
    
    for line in content:
        ax.text(x + 0.02, content_y, line,
               ha='left', va='top', fontsize=9,
               color='black')
        content_y -= line_height