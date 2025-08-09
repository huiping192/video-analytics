#!/usr/bin/env python3
"""
Video Analytics Main Entry Point
视频分析工具主入口
"""

import sys
import os
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table

from .core import FileProcessor, safe_process_file
from .core.video_bitrate_analyzer import VideoBitrateAnalyzer

app = typer.Typer(help="视频分析工具 - 分析视频文件的码率、FPS等关键指标")
console = Console()


@app.command()
def info(
    file_path: str = typer.Argument(..., help="视频文件路径"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
    simple: bool = typer.Option(False, "--simple", "-s", help="使用简化模式（不需要FFmpeg）")
):
    """
    显示视频文件的基本信息
    """
    console.print(f"[blue]正在分析文件:[/blue] {file_path}")
    
    if simple:
        # 使用简化模式
        from .core.simple_processor import SimpleProcessedFile
        processed_file = SimpleProcessedFile(file_path)
    else:
        # 使用完整的FFmpeg模式
        processed_file = safe_process_file(file_path)
        if processed_file is None:
            console.print("[red]文件处理失败[/red]")
            raise typer.Exit(1)
    
    metadata = processed_file.load_metadata()
    
    # 创建信息表格
    table = Table(title="视频文件信息")
    table.add_column("属性", style="cyan", no_wrap=True)
    table.add_column("值", style="magenta")
    
    # 基本信息
    table.add_row("文件路径", metadata.file_path)
    table.add_row("文件大小", f"{metadata.file_size / 1024 / 1024:.1f} MB")
    table.add_row("时长", f"{metadata.duration:.1f} 秒 ({metadata.duration/60:.1f} 分钟)")
    table.add_row("容器格式", metadata.format_name)
    table.add_row("总码率", f"{metadata.bit_rate / 1000:.0f} kbps")
    
    # 视频信息
    table.add_row("", "")  # 空行分隔
    table.add_row("[bold]视频信息[/bold]", "")
    table.add_row("视频编码", metadata.video_codec)
    table.add_row("分辨率", f"{metadata.width}x{metadata.height}")
    table.add_row("帧率", f"{metadata.fps:.2f} fps")
    if metadata.video_bitrate > 0:
        table.add_row("视频码率", f"{metadata.video_bitrate / 1000:.0f} kbps")
    
    # 音频信息  
    table.add_row("", "")  # 空行分隔
    table.add_row("[bold]音频信息[/bold]", "")
    table.add_row("音频编码", metadata.audio_codec)
    table.add_row("声道数", str(metadata.channels))
    table.add_row("采样率", f"{metadata.sample_rate} Hz")
    if metadata.audio_bitrate > 0:
        table.add_row("音频码率", f"{metadata.audio_bitrate / 1000:.0f} kbps")
    
    console.print(table)
    
    if verbose:
        console.print("\n[green]✓ 文件分析完成[/green]")


@app.command()
def validate(
    file_path: str = typer.Argument(..., help="视频文件路径")
):
    """
    验证视频文件是否可以正常处理
    """
    console.print(f"[blue]正在验证文件:[/blue] {file_path}")
    
    try:
        processor = FileProcessor()
        processed_file = processor.process_input(file_path)
        metadata = processed_file.load_metadata()
        
        console.print(f"[green]✓ 验证成功[/green]")
        console.print(f"  时长: {metadata.duration:.1f}秒")
        console.print(f"  分辨率: {metadata.width}x{metadata.height}")
        console.print(f"  编码: {metadata.video_codec}")
        
    except Exception as e:
        console.print(f"[red]✗ 验证失败: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def check():
    """
    检查系统依赖是否满足
    """
    console.print("[blue]检查系统依赖...[/blue]")
    
    # 检查FFmpeg
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0] if result.stdout else "未知版本"
            console.print(f"[green]✓ FFmpeg 已安装 ({version_line})[/green]")
        else:
            console.print("[red]✗ FFmpeg 未正确安装[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]✗ FFmpeg 响应超时[/red]")
    except FileNotFoundError:
        console.print("[red]✗ FFmpeg 未找到[/red]")
        console.print("请安装 FFmpeg: https://ffmpeg.org/download.html")
    
    # 检查Python依赖
    try:
        import ffmpeg
        console.print("[green]✓ ffmpeg-python 已安装[/green]")
    except ImportError:
        console.print("[red]✗ ffmpeg-python 未安装[/red]")
        console.print("请运行: pip install ffmpeg-python")
    
    try:
        import matplotlib
        console.print("[green]✓ matplotlib 已安装[/green]")
    except ImportError:
        console.print("[red]✗ matplotlib 未安装[/red]")
        console.print("请运行: pip install matplotlib")


@app.command()
def bitrate(
    file_path: str = typer.Argument(..., help="视频文件路径"),
    interval: float = typer.Option(10.0, "--interval", "-i", help="采样间隔(秒)"),
    export_json: Optional[str] = typer.Option(None, "--json", help="导出JSON文件路径"),
    export_csv: Optional[str] = typer.Option(None, "--csv", help="导出CSV文件路径"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息")
):
    """
    分析视频码率变化情况
    """
    console.print(f"[blue]正在分析视频码率:[/blue] {file_path}")
    
    try:
        # 处理视频文件
        processed_file = safe_process_file(file_path)
        if processed_file is None:
            console.print("[red]文件处理失败[/red]")
            raise typer.Exit(1)
        
        # 创建分析器并执行分析
        analyzer = VideoBitrateAnalyzer(sample_interval=interval)
        analysis = analyzer.analyze(processed_file)
        
        # 显示分析结果
        table = Table(title="视频码率分析结果")
        table.add_column("统计项", style="cyan", no_wrap=True)
        table.add_column("值", style="magenta")
        
        table.add_row("文件路径", analysis.file_path)
        table.add_row("视频时长", f"{analysis.duration:.1f} 秒 ({analysis.duration/60:.1f} 分钟)")
        table.add_row("采样间隔", f"{analysis.sample_interval:.1f} 秒")
        table.add_row("采样点数", str(len(analysis.data_points)))
        table.add_row("", "")  # 空行分隔
        
        # 码率统计
        table.add_row("[bold]码率统计[/bold]", "")
        table.add_row("平均码率", f"{analysis.average_bitrate/1000000:.2f} Mbps")
        table.add_row("最大码率", f"{analysis.max_bitrate/1000000:.2f} Mbps")
        table.add_row("最小码率", f"{analysis.min_bitrate/1000000:.2f} Mbps")
        table.add_row("码率方差", f"{analysis.bitrate_variance/1000000000000:.2f} (Mbps²)")
        table.add_row("编码类型", analysis.encoding_type)
        
        console.print(table)
        
        # 导出数据
        if export_json:
            analyzer.export_analysis_data(analysis, export_json)
        
        if export_csv:
            analyzer.export_to_csv(analysis, export_csv)
        
        if verbose:
            console.print("\n[green]✓ 码率分析完成[/green]")
            console.print(f"数据点范围: {analysis.data_points[0].timestamp:.1f}s - {analysis.data_points[-1].timestamp:.1f}s")
            
    except Exception as e:
        console.print(f"[red]✗ 分析失败: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def batch_bitrate(
    files: List[str] = typer.Argument(..., help="要分析的视频文件列表"),
    interval: float = typer.Option(10.0, "--interval", "-i", help="采样间隔(秒)"),
    output_dir: str = typer.Option("./output", "--output", "-o", help="输出目录")
):
    """
    批量分析多个视频文件的码率
    """
    console.print(f"[blue]开始批量分析 {len(files)} 个视频文件[/blue]")
    
    import os
    from .core.video_bitrate_analyzer import analyze_multiple_videos
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        results = analyze_multiple_videos(files, interval)
        
        # 创建汇总表格
        summary_table = Table(title="批量分析结果汇总")
        summary_table.add_column("文件名", style="cyan")
        summary_table.add_column("时长(分钟)", style="blue")
        summary_table.add_column("平均码率(Mbps)", style="green")
        summary_table.add_column("编码类型", style="yellow")
        
        analyzer = VideoBitrateAnalyzer()
        for result in results:
            filename = os.path.basename(result.file_path)
            duration_min = result.duration / 60
            avg_bitrate_mbps = result.average_bitrate / 1000000
            encoding_type = "CBR" if result.is_cbr else "VBR"
            
            summary_table.add_row(
                filename, 
                f"{duration_min:.1f}",
                f"{avg_bitrate_mbps:.2f}",
                encoding_type
            )
            
            # 导出每个文件的分析结果
            base_name = os.path.splitext(filename)[0]
            json_path = os.path.join(output_dir, f"{base_name}_bitrate.json")
            csv_path = os.path.join(output_dir, f"{base_name}_bitrate.csv")
            
            analyzer.export_analysis_data(result, json_path)
            analyzer.export_to_csv(result, csv_path)
        
        console.print(summary_table)
        console.print(f"\n[green]✓ 批量分析完成，结果已保存到 {output_dir}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ 批量分析失败: {e}[/red]")
        raise typer.Exit(1)


def main():
    """主入口函数"""
    app()


if __name__ == "__main__":
    main()