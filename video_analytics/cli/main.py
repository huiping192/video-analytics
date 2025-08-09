#!/usr/bin/env python3
"""
CLI Main Entry Point - CLI主入口点
视频分析工具命令行接口的主入口和配置管理
"""

import typer
from rich.console import Console

from .commands import (
    info_command,
    validate_command, 
    check_command,
    bitrate_command,
    batch_bitrate_command,
    audio_command,
    batch_audio_command,
    fps_command,
    batch_fps_command,
    chart_command,
    batch_chart_command
)

# 创建主应用
app = typer.Typer(
    help="视频分析工具 - 分析视频文件的码率、FPS等关键指标",
    add_completion=False,
    no_args_is_help=True
)

# 全局console对象
console = Console()

# 注册所有命令
app.command("info", help="显示视频文件的基本信息")(info_command)
app.command("validate", help="验证视频文件是否可以正常处理")(validate_command)
app.command("check", help="检查系统依赖是否满足")(check_command)
app.command("bitrate", help="分析视频码率变化情况")(bitrate_command)
app.command("batch_bitrate", help="批量分析多个视频文件的码率")(batch_bitrate_command)
app.command("audio", help="分析音频码率变化情况")(audio_command)
app.command("batch_audio", help="批量分析多个视频文件的音频码率")(batch_audio_command)
app.command("fps", help="分析视频FPS和掉帧情况")(fps_command)
app.command("batch_fps", help="批量分析多个视频文件的FPS和掉帧情况")(batch_fps_command)
app.command("chart", help="生成视频分析图表")(chart_command)
app.command("batch_chart", help="批量生成多个视频文件的分析图表")(batch_chart_command)


def main():
    """主入口函数"""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]用户取消操作[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]程序异常退出: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    main()