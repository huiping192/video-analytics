#!/usr/bin/env python3
"""
CLI Commands - CLI命令实现
包含所有视频分析工具的命令行接口实现
"""

import sys
import os
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table

from ..core import FileProcessor, safe_process_file
from ..core.video_bitrate_analyzer import VideoBitrateAnalyzer
from ..core.audio_bitrate_analyzer import AudioBitrateAnalyzer
from ..core.fps_analyzer import FPSAnalyzer
from ..visualization import ChartGenerator, ChartConfig, ChartStyles

console = Console()


def info_command(
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
        from ..core.simple_processor import SimpleProcessedFile
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


def validate_command(
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


def check_command():
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


def bitrate_command(
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


def batch_bitrate_command(
    files: List[str] = typer.Argument(..., help="要分析的视频文件列表"),
    interval: float = typer.Option(10.0, "--interval", "-i", help="采样间隔(秒)"),
    output_dir: str = typer.Option("./output", "--output", "-o", help="输出目录")
):
    """
    批量分析多个视频文件的码率
    """
    console.print(f"[blue]开始批量分析 {len(files)} 个视频文件[/blue]")
    
    import os
    from ..core.video_bitrate_analyzer import analyze_multiple_videos
    
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


def audio_command(
    file_path: str = typer.Argument(..., help="视频文件路径"),
    interval: float = typer.Option(15.0, "--interval", "-i", help="采样间隔(秒)"),
    export_json: Optional[str] = typer.Option(None, "--json", help="导出JSON文件路径"),
    export_csv: Optional[str] = typer.Option(None, "--csv", help="导出CSV文件路径"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息")
):
    """
    分析音频码率变化情况
    """
    console.print(f"[blue]正在分析音频码率:[/blue] {file_path}")
    
    try:
        # 处理视频文件
        processed_file = safe_process_file(file_path)
        if processed_file is None:
            console.print("[red]文件处理失败[/red]")
            raise typer.Exit(1)
        
        # 创建分析器并执行分析
        analyzer = AudioBitrateAnalyzer(sample_interval=interval)
        analysis = analyzer.analyze(processed_file)
        
        # 显示分析结果
        table = Table(title="音频码率分析结果")
        table.add_column("统计项", style="cyan", no_wrap=True)
        table.add_column("值", style="magenta")
        
        table.add_row("文件路径", analysis.file_path)
        table.add_row("音频时长", f"{analysis.duration:.1f} 秒 ({analysis.duration/60:.1f} 分钟)")
        table.add_row("采样间隔", f"{analysis.sample_interval:.1f} 秒")
        table.add_row("采样点数", str(len(analysis.data_points)))
        table.add_row("", "")  # 空行分隔
        
        # 音频基本信息
        table.add_row("[bold]音频信息[/bold]", "")
        table.add_row("音频编码", analysis.codec)
        table.add_row("声道配置", f"{analysis.channels}ch ({analyzer.get_channel_layout(analysis.channels)})")
        table.add_row("采样率", f"{analysis.sample_rate} Hz")
        table.add_row("", "")  # 空行分隔
        
        # 码率统计
        table.add_row("[bold]码率统计[/bold]", "")
        table.add_row("平均码率", f"{analysis.average_bitrate/1000:.1f} kbps")
        table.add_row("最大码率", f"{analysis.max_bitrate/1000:.1f} kbps")
        table.add_row("最小码率", f"{analysis.min_bitrate/1000:.1f} kbps")
        table.add_row("码率稳定性", f"{analysis.bitrate_stability:.1%}")
        table.add_row("音质等级", analysis.quality_level)
        
        console.print(table)
        
        # 显示质量评估
        quality = analyzer.assess_audio_quality(analysis)
        if verbose:
            console.print("\n[bold]质量评估:[/bold]")
            console.print(f"编码格式评价: {quality['codec_rating']}")
            console.print(f"采样率评价: {quality['sample_rate_rating']}")
            console.print(f"码率稳定性: {quality['stability']}")
            
            if quality['recommendations']:
                console.print("\n[yellow]改进建议:[/yellow]")
                for rec in quality['recommendations']:
                    console.print(f"• {rec}")
        
        # 导出数据
        if export_json:
            analyzer.export_analysis_data(analysis, export_json)
        
        if export_csv:
            analyzer.export_to_csv(analysis, export_csv)
        
        if verbose:
            console.print("\n[green]✓ 音频分析完成[/green]")
            console.print(f"数据点范围: {analysis.data_points[0].timestamp:.1f}s - {analysis.data_points[-1].timestamp:.1f}s")
            
    except Exception as e:
        console.print(f"[red]✗ 分析失败: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


def batch_audio_command(
    files: List[str] = typer.Argument(..., help="要分析的视频文件列表"),
    interval: float = typer.Option(15.0, "--interval", "-i", help="采样间隔(秒)"),
    output_dir: str = typer.Option("./output", "--output", "-o", help="输出目录")
):
    """
    批量分析多个视频文件的音频码率
    """
    console.print(f"[blue]开始批量分析 {len(files)} 个文件的音频[/blue]")
    
    import os
    from ..core.audio_bitrate_analyzer import analyze_multiple_audio
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        results = analyze_multiple_audio(files, interval)
        
        # 创建汇总表格
        summary_table = Table(title="音频批量分析结果汇总")
        summary_table.add_column("文件名", style="cyan")
        summary_table.add_column("编码", style="blue")
        summary_table.add_column("声道", style="green")
        summary_table.add_column("采样率", style="yellow")
        summary_table.add_column("平均码率(kbps)", style="magenta")
        summary_table.add_column("音质", style="red")
        
        analyzer = AudioBitrateAnalyzer()
        for result in results:
            filename = os.path.basename(result.file_path)
            avg_bitrate_kbps = result.average_bitrate / 1000
            
            summary_table.add_row(
                filename, 
                result.codec,
                f"{result.channels}ch",
                f"{result.sample_rate}Hz",
                f"{avg_bitrate_kbps:.1f}",
                result.quality_level
            )
            
            # 导出每个文件的分析结果
            base_name = os.path.splitext(filename)[0]
            json_path = os.path.join(output_dir, f"{base_name}_audio.json")
            csv_path = os.path.join(output_dir, f"{base_name}_audio.csv")
            
            analyzer.export_analysis_data(result, json_path)
            analyzer.export_to_csv(result, csv_path)
        
        console.print(summary_table)
        console.print(f"\n[green]✓ 音频批量分析完成，结果已保存到 {output_dir}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ 音频批量分析失败: {e}[/red]")
        raise typer.Exit(1)


def fps_command(
    file_path: str = typer.Argument(..., help="视频文件路径"),
    interval: float = typer.Option(10.0, "--interval", "-i", help="采样间隔(秒)"),
    export_json: Optional[str] = typer.Option(None, "--json", help="导出JSON文件路径"),
    export_csv: Optional[str] = typer.Option(None, "--csv", help="导出CSV文件路径"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息")
):
    """
    分析视频FPS和掉帧情况
    """
    console.print(f"[blue]正在分析FPS和掉帧情况:[/blue] {file_path}")
    
    try:
        # 处理视频文件
        processed_file = safe_process_file(file_path)
        if processed_file is None:
            console.print("[red]文件处理失败[/red]")
            raise typer.Exit(1)
        
        # 创建分析器并执行分析
        analyzer = FPSAnalyzer(sample_interval=interval)
        analysis = analyzer.analyze(processed_file)
        
        # 显示分析结果
        table = Table(title="FPS分析结果")
        table.add_column("统计项", style="cyan", no_wrap=True)
        table.add_column("值", style="magenta")
        
        table.add_row("文件路径", analysis.file_path)
        table.add_row("视频时长", f"{analysis.duration:.1f} 秒 ({analysis.duration/60:.1f} 分钟)")
        table.add_row("采样间隔", f"{analysis.sample_interval:.1f} 秒")
        table.add_row("采样点数", str(len(analysis.data_points)))
        table.add_row("", "")  # 空行分隔
        
        # FPS统计
        table.add_row("[bold]FPS统计[/bold]", "")
        table.add_row("声明帧率", f"{analysis.declared_fps:.2f} fps")
        table.add_row("实际平均帧率", f"{analysis.actual_average_fps:.2f} fps")
        table.add_row("最大瞬时帧率", f"{analysis.max_fps:.2f} fps")
        table.add_row("最小瞬时帧率", f"{analysis.min_fps:.2f} fps")
        table.add_row("帧率稳定性", f"{analysis.fps_stability:.1%}")
        table.add_row("", "")  # 空行分隔
        
        # 掉帧统计
        table.add_row("[bold]掉帧统计[/bold]", "")
        table.add_row("总帧数", str(analysis.total_frames))
        table.add_row("掉帧数", str(analysis.total_dropped_frames))
        table.add_row("掉帧率", f"{analysis.drop_rate:.2%}")
        table.add_row("性能等级", analysis.performance_grade)
        
        console.print(table)
        
        # 显示质量评估
        if verbose:
            quality = analyzer.analyze_fps_quality(analysis)
            console.print("\n[bold]FPS质量评估:[/bold]")
            console.print(f"性能等级: {quality['performance_grade']}")
            console.print(f"FPS一致性: {quality['fps_consistency']}")
            console.print(f"FPS准确性: {quality['fps_accuracy']}")
            console.print(f"掉帧率: {quality['drop_rate']}")
            
            if quality['issues']:
                console.print("\n[yellow]发现的问题:[/yellow]")
                for issue in quality['issues']:
                    console.print(f"• {issue}")
            
            if quality['recommendations']:
                console.print("\n[green]改进建议:[/green]")
                for rec in quality['recommendations']:
                    console.print(f"• {rec}")
            
            # 掉帧严重程度分析
            drop_analysis = analyzer.analyze_drop_severity(analysis)
            if drop_analysis['worst_segments']:
                console.print(f"\n[red]最严重掉帧时间段 (严重程度: {drop_analysis['severity']}):[/red]")
                for timestamp, drops in drop_analysis['worst_segments'][:3]:
                    console.print(f"• {timestamp:.1f}s: {drops}帧")
        
        # 导出数据
        if export_json:
            analyzer.export_analysis_data(analysis, export_json)
        
        if export_csv:
            analyzer.export_to_csv(analysis, export_csv)
        
        if verbose:
            console.print("\n[green]✓ FPS分析完成[/green]")
            console.print(f"数据点范围: {analysis.data_points[0].timestamp:.1f}s - {analysis.data_points[-1].timestamp:.1f}s")
            
    except Exception as e:
        console.print(f"[red]✗ FPS分析失败: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


def batch_fps_command(
    files: List[str] = typer.Argument(..., help="要分析的视频文件列表"),
    interval: float = typer.Option(10.0, "--interval", "-i", help="采样间隔(秒)"),
    output_dir: str = typer.Option("./output", "--output", "-o", help="输出目录")
):
    """
    批量分析多个视频文件的FPS和掉帧情况
    """
    console.print(f"[blue]开始批量FPS分析 {len(files)} 个视频文件[/blue]")
    
    import os
    from ..core.fps_analyzer import analyze_multiple_fps
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        results = analyze_multiple_fps(files, interval)
        
        # 创建汇总表格
        summary_table = Table(title="FPS批量分析结果汇总")
        summary_table.add_column("文件名", style="cyan")
        summary_table.add_column("时长(分钟)", style="blue")
        summary_table.add_column("声明FPS", style="green")
        summary_table.add_column("实际FPS", style="yellow")
        summary_table.add_column("掉帧率", style="red")
        summary_table.add_column("等级", style="magenta")
        
        analyzer = FPSAnalyzer()
        for result in results:
            filename = os.path.basename(result.file_path)
            duration_min = result.duration / 60
            
            summary_table.add_row(
                filename, 
                f"{duration_min:.1f}",
                f"{result.declared_fps:.1f}",
                f"{result.actual_average_fps:.1f}",
                f"{result.drop_rate:.1%}",
                result.performance_grade
            )
            
            # 导出每个文件的分析结果
            base_name = os.path.splitext(filename)[0]
            json_path = os.path.join(output_dir, f"{base_name}_fps.json")
            csv_path = os.path.join(output_dir, f"{base_name}_fps.csv")
            
            analyzer.export_analysis_data(result, json_path)
            analyzer.export_to_csv(result, csv_path)
        
        console.print(summary_table)
        console.print(f"\n[green]✓ FPS批量分析完成，结果已保存到 {output_dir}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ FPS批量分析失败: {e}[/red]")
        raise typer.Exit(1)


def chart_command(
    file_path: str = typer.Argument(..., help="视频文件路径"),
    output_dir: str = typer.Option("./charts", "--output", "-o", help="图表输出目录"),
    chart_type: str = typer.Option("combined", "--type", "-t", help="图表类型: video, audio, fps, combined, summary, all"),
    config_type: str = typer.Option("default", "--config", "-c", help="图表配置: default, high_res, compact"),
    video_interval: float = typer.Option(30.0, "--video-interval", help="视频码率采样间隔(秒)"),
    audio_interval: float = typer.Option(15.0, "--audio-interval", help="音频码率采样间隔(秒)"),
    fps_interval: float = typer.Option(10.0, "--fps-interval", help="FPS采样间隔(秒)")
):
    """
    生成视频分析图表
    """
    console.print(f"[blue]正在为视频生成图表:[/blue] {file_path}")
    console.print(f"图表类型: {chart_type}, 配置: {config_type}")
    
    try:
        # 处理视频文件
        processed_file = safe_process_file(file_path)
        if processed_file is None:
            console.print("[red]文件处理失败[/red]")
            raise typer.Exit(1)
        
        # 根据图表类型决定需要进行哪些分析
        need_video = chart_type in ['video', 'combined', 'summary', 'all']
        need_audio = chart_type in ['audio', 'combined', 'summary', 'all'] 
        need_fps = chart_type in ['fps', 'combined', 'summary', 'all']
        
        # 执行必要的分析
        video_analysis = None
        audio_analysis = None
        fps_analysis = None
        
        if need_video:
            console.print("[yellow]正在分析视频码率...[/yellow]")
            video_analyzer = VideoBitrateAnalyzer(sample_interval=video_interval)
            video_analysis = video_analyzer.analyze(processed_file)
        
        if need_audio:
            console.print("[yellow]正在分析音频码率...[/yellow]")
            audio_analyzer = AudioBitrateAnalyzer(sample_interval=audio_interval)
            audio_analysis = audio_analyzer.analyze(processed_file)
        
        if need_fps:
            console.print("[yellow]正在分析FPS...[/yellow]")
            fps_analyzer = FPSAnalyzer(sample_interval=fps_interval)
            fps_analysis = fps_analyzer.analyze(processed_file)
        
        # 创建图表生成器
        chart_generator = ChartGenerator()
        
        # 获取配置
        if config_type == "high_res":
            config = ChartStyles.get_high_res_config()
        elif config_type == "compact":
            config = ChartStyles.get_compact_config()
        else:
            config = ChartStyles.get_default_config()
        
        config.output_dir = output_dir
        
        # 生成图表
        results = {}
        
        if chart_type == "video" and video_analysis:
            config.title = f"Video Bitrate Analysis - {os.path.basename(file_path)}"
            chart_path = chart_generator.generate_video_bitrate_chart(video_analysis, config)
            results['video'] = chart_path
            console.print(f"✓ Video bitrate chart generated: {chart_path}")
            
        elif chart_type == "audio" and audio_analysis:
            config.title = f"Audio Bitrate Analysis - {os.path.basename(file_path)}"
            chart_path = chart_generator.generate_audio_bitrate_chart(audio_analysis, config)
            results['audio'] = chart_path
            console.print(f"✓ Audio bitrate chart generated: {chart_path}")
            
        elif chart_type == "fps" and fps_analysis:
            config.title = f"FPS Analysis - {os.path.basename(file_path)}"
            chart_path = chart_generator.generate_fps_chart(fps_analysis, config)
            results['fps'] = chart_path
            console.print(f"✓ FPS chart generated: {chart_path}")
            
        elif chart_type == "combined" and all([video_analysis, audio_analysis, fps_analysis]):
            config.title = f"Combined Analysis - {os.path.basename(file_path)}"
            chart_path = chart_generator.generate_combined_chart(
                video_analysis, audio_analysis, fps_analysis, config
            )
            results['combined'] = chart_path
            console.print(f"✓ Combined analysis chart generated: {chart_path}")
            
        elif chart_type == "summary" and all([video_analysis, audio_analysis, fps_analysis]):
            config.title = f"Analysis Summary - {os.path.basename(file_path)}"
            chart_path = chart_generator.generate_summary_chart(
                video_analysis, audio_analysis, fps_analysis, config
            )
            results['summary'] = chart_path
            console.print(f"✓ Summary chart generated: {chart_path}")
            
        elif chart_type == "all" and all([video_analysis, audio_analysis, fps_analysis]):
            results = chart_generator.generate_full_report(
                video_analysis, audio_analysis, fps_analysis, output_dir
            )
            console.print(f"✓ Full report generated with {len(results)} charts")
        
        else:
            console.print(f"[red]无法生成图表: 缺少必要的分析数据或不支持的图表类型[/red]")
            raise typer.Exit(1)
        
        # 显示结果汇总
        if results:
            table = Table(title="生成的图表文件")
            table.add_column("图表类型", style="cyan")
            table.add_column("文件路径", style="green")
            
            for chart_name, chart_path in results.items():
                table.add_row(chart_name, chart_path)
            
            console.print(table)
            console.print(f"\n[green]✓ 图表生成完成，保存到: {output_dir}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ 图表生成失败: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


def batch_chart_command(
    files: List[str] = typer.Argument(..., help="要分析的视频文件列表"),
    output_dir: str = typer.Option("./batch_charts", "--output", "-o", help="图表输出目录"),
    chart_type: str = typer.Option("combined", "--type", "-t", help="图表类型: combined, summary, all"),
    config_type: str = typer.Option("default", "--config", "-c", help="图表配置: default, high_res, compact")
):
    """
    批量生成多个视频文件的分析图表
    """
    console.print(f"[blue]开始批量生成 {len(files)} 个文件的图表[/blue]")
    console.print(f"图表类型: {chart_type}, 配置: {config_type}")
    
    import os
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取配置
    if config_type == "high_res":
        base_config = ChartStyles.get_high_res_config()
    elif config_type == "compact":
        base_config = ChartStyles.get_compact_config()
    else:
        base_config = ChartStyles.get_default_config()
    
    chart_generator = ChartGenerator()
    success_count = 0
    total_charts = 0
    
    try:
        for i, file_path in enumerate(files, 1):
            console.print(f"\n[blue]处理文件 {i}/{len(files)}:[/blue] {os.path.basename(file_path)}")
            
            try:
                # 处理文件
                processed_file = safe_process_file(file_path)
                if processed_file is None:
                    console.print(f"[red]✗ 文件处理失败: {file_path}[/red]")
                    continue
                
                # 执行三种分析
                video_analyzer = VideoBitrateAnalyzer()
                audio_analyzer = AudioBitrateAnalyzer()
                fps_analyzer = FPSAnalyzer()
                
                video_analysis = video_analyzer.analyze(processed_file)
                audio_analysis = audio_analyzer.analyze(processed_file)
                fps_analysis = fps_analyzer.analyze(processed_file)
                
                # 为每个文件创建子目录
                file_basename = os.path.splitext(os.path.basename(file_path))[0]
                file_output_dir = os.path.join(output_dir, file_basename)
                os.makedirs(file_output_dir, exist_ok=True)
                
                config = ChartConfig(
                    width=base_config.width,
                    height=base_config.height,
                    dpi=base_config.dpi,
                    line_width=base_config.line_width,
                    grid_alpha=base_config.grid_alpha,
                    font_size=base_config.font_size,
                    output_dir=file_output_dir
                )
                
                # 生成图表
                if chart_type == "combined":
                    config.title = f"Combined Analysis - {file_basename}"
                    chart_path = chart_generator.generate_combined_chart(
                        video_analysis, audio_analysis, fps_analysis, config
                    )
                    console.print(f"  ✓ Combined chart: {chart_path}")
                    total_charts += 1
                    
                elif chart_type == "summary":
                    config.title = f"Analysis Summary - {file_basename}"
                    chart_path = chart_generator.generate_summary_chart(
                        video_analysis, audio_analysis, fps_analysis, config
                    )
                    console.print(f"  ✓ Summary chart: {chart_path}")
                    total_charts += 1
                    
                elif chart_type == "all":
                    results = chart_generator.generate_full_report(
                        video_analysis, audio_analysis, fps_analysis, file_output_dir
                    )
                    console.print(f"  ✓ Full report: {len(results)} charts")
                    total_charts += len(results)
                
                success_count += 1
                
            except Exception as e:
                console.print(f"[red]✗ 处理文件失败 {file_path}: {e}[/red]")
                continue
        
        # 显示最终结果
        console.print(f"\n[green]✓ 批量图表生成完成[/green]")
        console.print(f"成功处理: {success_count}/{len(files)} 个文件")
        console.print(f"生成图表: {total_charts} 个")
        console.print(f"输出目录: {output_dir}")
        
    except Exception as e:
        console.print(f"[red]✗ 批量图表生成失败: {e}[/red]")
        raise typer.Exit(1)