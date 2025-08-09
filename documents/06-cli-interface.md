# CLI接口设计 - 技术文档

## 模块概述

CLI接口是用户与视频分析工具交互的主要方式，提供简单直观的命令行界面，专注于核心的分析功能。

## 核心功能

- 单文件视频分析
- 基础文件信息查看
- PNG图表输出
- 简单的进度反馈

## 技术实现

### 核心依赖

```python
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from typing import Optional
import os
from pathlib import Path

# 创建Typer应用
app = typer.Typer(
    name="video-analyzer",
    help="🎥 视频分析工具 - 分析视频码率、音频码率和FPS",
    add_completion=False
)

# Rich控制台
console = Console()
```

### 主要分析命令

```python
@app.command()
def analyze(
    input_path: str = typer.Argument(..., help="视频文件路径"),
    
    # 功能开关
    video: bool = typer.Option(True, "--video/--no-video", help="分析视频码率"),
    audio: bool = typer.Option(True, "--audio/--no-audio", help="分析音频码率"),
    fps: bool = typer.Option(True, "--fps/--no-fps", help="分析FPS"),
    
    # 输出选项
    output_dir: Optional[str] = typer.Option(
        "./output", "--output", "-o",
        help="输出目录 (默认: ./output)"
    ),
    
    # 采样间隔
    video_interval: float = typer.Option(10.0, "--video-interval", help="视频码率采样间隔(秒)"),
    audio_interval: float = typer.Option(15.0, "--audio-interval", help="音频码率采样间隔(秒)"),
    fps_interval: float = typer.Option(10.0, "--fps-interval", help="FPS采样间隔(秒)"),
    
    # 其他选项
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
):
    """分析视频文件"""
    
    if quiet and verbose:
        console.print("[red]错误: --quiet 和 --verbose 不能同时使用[/red]")
        raise typer.Exit(1)
    
    try:
        # 检查输入文件
        if not os.path.exists(input_path):
            console.print(f"[red]错误: 文件不存在 - {input_path}[/red]")
            raise typer.Exit(1)
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=not verbose
        ) as progress:
            
            # 初始化
            task = progress.add_task("初始化分析器...", total=None)
            
            from core.file_processor import FileProcessor
            from core.video_analyzer import VideoBitrateAnalyzer
            from core.audio_analyzer import AudioBitrateAnalyzer  
            from core.fps_analyzer import FPSAnalyzer
            from visualization.chart_generator import ChartGenerator, ChartConfig
            
            # 处理文件
            progress.update(task, description="处理输入文件...")
            processor = FileProcessor()
            processed_file = processor.process_input(input_path)
            
            results = {}
            
            # 视频码率分析
            if video:
                progress.update(task, description="分析视频码率...")
                video_analyzer = VideoBitrateAnalyzer(sample_interval=video_interval)
                results['video'] = video_analyzer.analyze(processed_file)
                if not quiet:
                    console.print("✓ 视频码率分析完成")
            
            # 音频码率分析
            if audio:
                progress.update(task, description="分析音频码率...")
                audio_analyzer = AudioBitrateAnalyzer(sample_interval=audio_interval)
                results['audio'] = audio_analyzer.analyze(processed_file)
                if not quiet:
                    console.print("✓ 音频码率分析完成")
            
            # FPS分析
            if fps:
                progress.update(task, description="分析FPS...")
                fps_analyzer = FPSAnalyzer(sample_interval=fps_interval)
                results['fps'] = fps_analyzer.analyze(processed_file)
                if not quiet:
                    console.print("✓ FPS分析完成")
            
            # 生成图表
            if results:
                progress.update(task, description="生成图表...")
                generator = ChartGenerator()
                config = ChartConfig(output_dir=output_dir)
                
                output_files = []
                
                # 生成单个图表
                if 'video' in results:
                    chart_path = generator.generate_video_bitrate_chart(results['video'], config)
                    output_files.append(("视频码率图表", chart_path))
                
                if 'audio' in results:
                    chart_path = generator.generate_audio_bitrate_chart(results['audio'], config)
                    output_files.append(("音频码率图表", chart_path))
                
                if 'fps' in results:
                    chart_path = generator.generate_fps_chart(results['fps'], config)
                    output_files.append(("FPS分析图表", chart_path))
                
                # 生成综合图表（如果有多个分析结果）
                if len(results) > 1 and 'video' in results and 'audio' in results and 'fps' in results:
                    combined_path = generator.generate_combined_chart(
                        results['video'], results['audio'], results['fps'], config
                    )
                    output_files.append(("综合分析图表", combined_path))
        
        # 显示结果
        if not quiet:
            display_analysis_results(results, output_files)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]分析被用户中断[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]分析失败: {e}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)

def display_analysis_results(results: dict, output_files: list):
    """显示分析结果摘要"""
    console.print("\n" + "="*50)
    console.print("[bold green]分析完成！[/bold green]")
    
    # 结果统计表
    stats_table = Table(title="分析结果")
    stats_table.add_column("指标", style="cyan")
    stats_table.add_column("结果", style="green")
    
    if 'video' in results:
        video_result = results['video']
        stats_table.add_row("视频平均码率", f"{video_result.average_bitrate/1000000:.2f} Mbps")
        stats_table.add_row("编码类型", "CBR" if video_result.is_cbr else "VBR")
    
    if 'audio' in results:
        audio_result = results['audio']
        stats_table.add_row("音频平均码率", f"{audio_result.average_bitrate/1000:.0f} kbps")
        stats_table.add_row("音质等级", audio_result.quality_level)
    
    if 'fps' in results:
        fps_result = results['fps']
        stats_table.add_row("平均FPS", f"{fps_result.actual_average_fps:.1f}")
        stats_table.add_row("FPS稳定性", f"{fps_result.fps_stability:.1%}")
        stats_table.add_row("性能等级", fps_result.performance_grade)
    
    console.print(stats_table)
    
    # 输出文件列表
    if output_files:
        console.print("\n[bold]生成的图表:[/bold]")
        for file_type, file_path in output_files:
            console.print(f"  📊 {file_type}: {file_path}")
```

## 文件信息命令

### 基础信息查看

```python
@app.command()
def info(
    file_path: str = typer.Argument(..., help="视频文件路径")
):
    """显示视频文件基本信息"""
    
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            console.print(f"[red]错误: 文件不存在 - {file_path}[/red]")
            raise typer.Exit(1)
        
        with console.status("获取文件信息..."):
            from core.file_processor import FileProcessor
            
            processor = FileProcessor()
            processed_file = processor.process_input(file_path)
            metadata = processed_file.load_metadata()
        
        # 创建信息表格
        info_table = Table(title=f"文件信息 - {os.path.basename(file_path)}")
        info_table.add_column("属性", style="cyan", width=16)
        info_table.add_column("值", style="green")
        
        # 基本信息
        info_table.add_row("文件大小", f"{metadata.file_size / (1024**2):.1f} MB")
        info_table.add_row("时长", f"{metadata.duration:.1f} 秒")
        info_table.add_row("容器格式", metadata.format_name)
        
        # 视频信息
        if metadata.video_codec:
            info_table.add_row("视频编码", metadata.video_codec)
            info_table.add_row("分辨率", f"{metadata.width}x{metadata.height}")
            info_table.add_row("帧率", f"{metadata.fps:.2f} fps")
            if metadata.video_bitrate > 0:
                info_table.add_row("视频码率", f"{metadata.video_bitrate / 1000:.0f} kbps")
        
        # 音频信息
        if metadata.audio_codec:
            info_table.add_row("音频编码", metadata.audio_codec)
            info_table.add_row("声道数", f"{metadata.channels}")
            info_table.add_row("采样率", f"{metadata.sample_rate} Hz")
            if metadata.audio_bitrate > 0:
                info_table.add_row("音频码率", f"{metadata.audio_bitrate / 1000:.0f} kbps")
        
        console.print(info_table)
        
    except Exception as e:
        console.print(f"[red]获取文件信息失败: {e}[/red]")
        raise typer.Exit(1)
```

## 帮助命令

### 使用示例

```python
@app.command()
def examples():
    """显示使用示例"""
    
    examples_text = """
[bold cyan]🎥 Video Analyzer 使用示例[/bold cyan]

[bold]基本分析:[/bold]
  video-analyzer analyze video.mp4

[bold]指定输出目录:[/bold]
  video-analyzer analyze video.mp4 -o ./results

[bold]只分析视频码率:[/bold]
  video-analyzer analyze video.mp4 --no-audio --no-fps

[bold]自定义采样间隔:[/bold]
  video-analyzer analyze video.mp4 --video-interval 5

[bold]查看文件信息:[/bold]
  video-analyzer info video.mp4

[bold]静默模式:[/bold]
  video-analyzer analyze video.mp4 -q

[bold yellow]说明:[/bold yellow]
- 默认会分析视频码率、音频码率和FPS
- 图表保存为PNG格式在指定目录
- 默认输出目录为 ./output
- 视频码率默认10秒采样，音频15秒，FPS 10秒
"""
    
    console.print(examples_text)
```

## 错误处理

### 统一错误处理

```python
def handle_cli_errors(func):
    """CLI错误处理装饰器"""
    
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            console.print(f"[red]文件不存在: {e}[/red]")
            raise typer.Exit(1)
        except PermissionError as e:
            console.print(f"[red]权限不足: {e}[/red]")
            raise typer.Exit(1)
        except ValueError as e:
            if "FFmpeg" in str(e):
                console.print(f"[red]FFmpeg错误: {e}[/red]")
                console.print("[yellow]请确保FFmpeg已正确安装[/yellow]")
            else:
                console.print(f"[red]参数错误: {e}[/red]")
            raise typer.Exit(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]操作被用户中断[/yellow]")
            raise typer.Exit(130)
        except Exception as e:
            console.print(f"[red]未知错误: {e}[/red]")
            raise typer.Exit(1)
    
    return wrapper

# 应用错误处理
analyze = handle_cli_errors(analyze)
info = handle_cli_errors(info)
```

## 主入口

### 应用启动

```python
def main():
    """主入口函数"""
    
    # 基础环境检查
    if not check_ffmpeg():
        console.print("[red]错误: 未找到FFmpeg[/red]")
        console.print("[yellow]请安装FFmpeg: https://ffmpeg.org/[/yellow]")
        return 1
    
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]再见！[/yellow]")
    except Exception as e:
        console.print(f"[red]启动失败: {e}[/red]")
        return 1
    
    return 0

def check_ffmpeg() -> bool:
    """检查FFmpeg是否可用"""
    try:
        import subprocess
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

if __name__ == "__main__":
    exit(main())
```

## 使用示例

### 常用命令

```bash
# 基本分析
video-analyzer analyze video.mp4

# 查看文件信息
video-analyzer info video.mp4

# 指定输出目录
video-analyzer analyze video.mp4 -o ./charts

# 只分析视频码率
video-analyzer analyze video.mp4 --no-audio --no-fps

# 调整采样间隔
video-analyzer analyze video.mp4 --video-interval 5 --fps-interval 5

# 静默模式
video-analyzer analyze video.mp4 -q

# 查看使用示例
video-analyzer examples

# 查看帮助
video-analyzer --help
video-analyzer analyze --help
```

这个简化版CLI接口专注于核心功能，提供简单易用的命令行体验，满足基本的视频分析需求。