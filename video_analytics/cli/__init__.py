"""
CLI module - 命令行接口模块

提供命令行交互功能，包含主入口点和命令实现。
"""

from .main import main, app
from .commands import *

__all__ = ['main', 'app']