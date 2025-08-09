#!/usr/bin/env python3
"""
Video Analytics Main Entry Point
视频分析工具主入口 - 向后兼容入口点
"""

from .cli.main import main

# 保持向后兼容
if __name__ == "__main__":
    main()