#!/usr/bin/env python3
"""
CLI Commands - Command implementations for the video analytics tool.
Provides all command-line interfaces for video, audio, FPS analysis and charting.
"""

import sys
import os
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table

from ..core import FileProcessor, safe_process_file
from ..core.video_analyzer import VideoBitrateAnalyzer
from ..core.audio_analyzer import AudioBitrateAnalyzer
from ..core.fps_analyzer import FPSAnalyzer
from ..visualization import ChartGenerator, ChartConfig, ChartStyles
from ..utils import ConfigManager, AnalysisConfig, get_merged_config

console = Console()


def info_command(
    input_path: str = typer.Argument(..., help="Video file path, HTTP URL, or HLS stream URL"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
    simple: bool = typer.Option(False, "--simple", "-s", help="Use simple mode (no FFmpeg)"),
    force_download: bool = typer.Option(False, "--force-download", help="Force re-download even if cached"),
    max_workers: int = typer.Option(10, "--workers", help="Maximum download threads for HLS")
):
    """
    Show basic information about the video file, URL, or HLS stream.
    """
    console.print(f"[blue]Analyzing input:[/blue] {input_path}")
    
    if simple:
        # Use simple mode for local files only
        from ..core.simple_processor import SimpleProcessedFile
        from ..utils.validators import is_url
        
        if is_url(input_path):
            console.print("[red]Simple mode not supported for URLs/HLS streams[/red]")
            raise typer.Exit(1)
            
        processed_file = SimpleProcessedFile(input_path)
    else:
        # Use full processing mode with download support
        processed_file = safe_process_file(
            input_path, 
            force_download=force_download,
            max_workers=max_workers
        )
        if processed_file is None:
            console.print("[red]Input processing failed[/red]")
            raise typer.Exit(1)
    
    metadata = processed_file.load_metadata()
    
    # Create info table
    table = Table(title="Video File Information")
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    
    # Basic information
    table.add_row("File Path", metadata.file_path)
    if metadata.original_url:
        table.add_row("Original URL", metadata.original_url[:60] + "..." if len(metadata.original_url) > 60 else metadata.original_url)
        table.add_row("Cached", "Yes" if metadata.is_cached else "No")
    table.add_row("File Size", f"{metadata.file_size / 1024 / 1024:.1f} MB")
    table.add_row("Duration", f"{metadata.duration:.1f} s ({metadata.duration/60:.1f} min)")
    table.add_row("Container Format", metadata.format_name)
    table.add_row("Overall Bitrate", f"{metadata.bit_rate / 1000:.0f} kbps")
    
    # Video information
    table.add_row("", "")  # spacer
    table.add_row("[bold]Video[/bold]", "")
    table.add_row("Codec", metadata.video_codec)
    table.add_row("Resolution", f"{metadata.width}x{metadata.height}")
    table.add_row("Frame Rate", f"{metadata.fps:.2f} fps")
    if metadata.video_bitrate > 0:
        table.add_row("Video Bitrate", f"{metadata.video_bitrate / 1000:.0f} kbps")
    
    # Audio information  
    table.add_row("", "")  # spacer
    table.add_row("[bold]Audio[/bold]", "")
    table.add_row("Codec", metadata.audio_codec)
    table.add_row("Channels", str(metadata.channels))
    table.add_row("Sample Rate", f"{metadata.sample_rate} Hz")
    if metadata.audio_bitrate > 0:
        table.add_row("Audio Bitrate", f"{metadata.audio_bitrate / 1000:.0f} kbps")
    
    console.print(table)
    
    if verbose:
        console.print("\n[green]✓ File analysis complete[/green]")


def validate_command(
    file_path: str = typer.Argument(..., help="Video file path")
):
    """
    Validate whether a video file can be processed.
    """
    console.print(f"[blue]Validating file:[/blue] {file_path}")
    
    try:
        processor = FileProcessor()
        processed_file = processor.process_input(file_path)
        metadata = processed_file.load_metadata()
        
        console.print(f"[green]✓ Validation successful[/green]")
        console.print(f"  Duration: {metadata.duration:.1f}s")
        console.print(f"  Resolution: {metadata.width}x{metadata.height}")
        console.print(f"  Codec: {metadata.video_codec}")
        
    except Exception as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        raise typer.Exit(1)


def check_command():
    """
    Check required system dependencies.
    """
    console.print("[blue]Checking system dependencies...[/blue]")
    
    # Check FFmpeg
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
            console.print(f"[green]✓ FFmpeg installed ({version_line})[/green]")
        else:
            console.print("[red]✗ FFmpeg not installed correctly[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]✗ FFmpeg timed out[/red]")
    except FileNotFoundError:
        console.print("[red]✗ FFmpeg not found[/red]")
        console.print("Please install FFmpeg: https://ffmpeg.org/download.html")
    
    # Check Python deps
    try:
        import ffmpeg
        console.print("[green]✓ ffmpeg-python installed[/green]")
    except ImportError:
        console.print("[red]✗ ffmpeg-python not installed[/red]")
        console.print("Run: pip install ffmpeg-python")
    
    try:
        import matplotlib
        console.print("[green]✓ matplotlib installed[/green]")
    except ImportError:
        console.print("[red]✗ matplotlib not installed[/red]")
        console.print("Run: pip install matplotlib")


def bitrate_command(
    input_path: str = typer.Argument(..., help="Video file path, HTTP URL, or HLS stream URL"),
    interval: Optional[float] = typer.Option(None, "--interval", "-i", help="Sampling interval (seconds)"),
    export_json: Optional[str] = typer.Option(None, "--json", help="Export JSON file path"),
    export_csv: Optional[str] = typer.Option(None, "--csv", help="Export CSV file path"),
    verbose: Optional[bool] = typer.Option(None, "--verbose", "-v", help="Show verbose output"),
    force_download: bool = typer.Option(False, "--force-download", help="Force re-download even if cached"),
    max_workers: int = typer.Option(10, "--workers", help="Maximum download threads for HLS")
):
    """
    Analyze video bitrate over time.
    Uses configuration file settings when CLI parameters are not provided.
    """
    # Merge CLI args with config file
    cli_args = {
        'interval': interval,
        'export_json': export_json is not None,
        'export_csv': export_csv is not None,
        'verbose': verbose
    }
    config = get_merged_config(cli_args)
    
    console.print(f"[blue]Analyzing video bitrate:[/blue] {input_path}")
    
    # Auto-optimize interval for large files based on URL type
    from ..utils.validators import is_hls_url
    if config.interval is None and is_hls_url(input_path):
        # Default to larger intervals for HLS streams (likely long videos)
        config.interval = 60.0  # 1 minute for HLS
        console.print("[dim]Auto-optimized sampling interval for HLS: 60s[/dim]")
    
    if config.verbose:
        console.print(f"[dim]Using interval: {config.interval}s[/dim]")
    
    try:
        # Process video file with download support
        processed_file = safe_process_file(
            input_path, 
            force_download=force_download,
            max_workers=max_workers
        )
        if processed_file is None:
            console.print("[red]Input processing failed[/red]")
            raise typer.Exit(1)
        
        # Create analyzer and run analysis
        analyzer = VideoBitrateAnalyzer(sample_interval=config.interval)
        analysis = analyzer.analyze(processed_file)
        
        # Show analysis results
        table = Table(title="Video Bitrate Analysis")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        table.add_row("File Path", analysis.file_path)
        table.add_row("Video Duration", f"{analysis.duration:.1f} s ({analysis.duration/60:.1f} min)")
        table.add_row("Sampling Interval", f"{analysis.sample_interval:.1f} s")
        table.add_row("Sample Points", str(len(analysis.data_points)))
        table.add_row("", "")  # spacer
        
        # Bitrate statistics
        table.add_row("[bold]Bitrate Statistics[/bold]", "")
        table.add_row("Average Bitrate", f"{analysis.average_bitrate/1000000:.2f} Mbps")
        table.add_row("Max Bitrate", f"{analysis.max_bitrate/1000000:.2f} Mbps")
        table.add_row("Min Bitrate", f"{analysis.min_bitrate/1000000:.2f} Mbps")
        table.add_row("Bitrate Variance", f"{analysis.bitrate_variance/1000000000000:.2f} (Mbps²)")
        table.add_row("Encoding Type", analysis.encoding_type)
        
        console.print(table)
        
        # Export data
        if export_json or config.export_json:
            json_path = export_json or f"{os.path.splitext(os.path.basename(input_path))[0]}_bitrate.json"
            analyzer.export_analysis_data(analysis, json_path)
            console.print(f"[green]✓ JSON exported: {json_path}[/green]")
        
        if export_csv or config.export_csv:
            csv_path = export_csv or f"{os.path.splitext(os.path.basename(input_path))[0]}_bitrate.csv"
            analyzer.export_to_csv(analysis, csv_path)
            console.print(f"[green]✓ CSV exported: {csv_path}[/green]")
        
        if config.verbose:
            console.print("\n[green]✓ Bitrate analysis complete[/green]")
            console.print(f"Data range: {analysis.data_points[0].timestamp:.1f}s - {analysis.data_points[-1].timestamp:.1f}s")
            
    except Exception as e:
        console.print(f"[red]✗ Analysis failed: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


def batch_bitrate_command(
    files: List[str] = typer.Argument(..., help="List of video files to analyze"),
    interval: float = typer.Option(10.0, "--interval", "-i", help="Sampling interval (seconds)"),
    output_dir: str = typer.Option("./output", "--output", "-o", help="Output directory")
):
    """
    Analyze bitrate for multiple videos.
    """
    console.print(f"[blue]Starting batch analysis of {len(files)} video(s)[/blue]")
    
    import os
    from ..core.video_analyzer import analyze_multiple_videos
    
    # Ensure output dir exists
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        results = analyze_multiple_videos(files, interval)
        
        # Create summary table
        summary_table = Table(title="Batch Analysis Summary")
        summary_table.add_column("Filename", style="cyan")
        summary_table.add_column("Duration (min)", style="blue")
        summary_table.add_column("Avg Bitrate (Mbps)", style="green")
        summary_table.add_column("Encoding", style="yellow")
        
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
            
            # Export each file's analysis results
            base_name = os.path.splitext(filename)[0]
            json_path = os.path.join(output_dir, f"{base_name}_bitrate.json")
            csv_path = os.path.join(output_dir, f"{base_name}_bitrate.csv")
            
            analyzer.export_analysis_data(result, json_path)
            analyzer.export_to_csv(result, csv_path)
        
        console.print(summary_table)
        console.print(f"\n[green]✓ Batch analysis complete. Results saved to {output_dir}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Batch analysis failed: {e}[/red]")
        raise typer.Exit(1)


def audio_command(
    input_path: str = typer.Argument(..., help="Video file path, HTTP URL, or HLS stream URL"),
    interval: float = typer.Option(15.0, "--interval", "-i", help="Sampling interval (seconds)"),
    export_json: Optional[str] = typer.Option(None, "--json", help="Export JSON file path"),
    export_csv: Optional[str] = typer.Option(None, "--csv", help="Export CSV file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
    force_download: bool = typer.Option(False, "--force-download", help="Force re-download even if cached"),
    max_workers: int = typer.Option(10, "--workers", help="Maximum download threads for HLS")
):
    """
    Analyze audio bitrate over time.
    """
    console.print(f"[blue]Analyzing audio bitrate:[/blue] {input_path}")
    
    # Auto-optimize interval for large files
    from ..utils.validators import is_hls_url
    if is_hls_url(input_path) and interval == 15.0:  # Default value
        interval = 30.0  # Larger interval for HLS
        console.print("[dim]Auto-optimized sampling interval for HLS: 30s[/dim]")
    
    try:
        # Process video file with download support
        processed_file = safe_process_file(
            input_path,
            force_download=force_download,
            max_workers=max_workers
        )
        if processed_file is None:
            console.print("[red]Input processing failed[/red]")
            raise typer.Exit(1)
        
        # Create analyzer and run analysis
        analyzer = AudioBitrateAnalyzer(sample_interval=interval)
        analysis = analyzer.analyze(processed_file)
        
        # Show analysis results
        table = Table(title="Audio Bitrate Analysis")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        table.add_row("File Path", analysis.file_path)
        table.add_row("Audio Duration", f"{analysis.duration:.1f} s ({analysis.duration/60:.1f} min)")
        table.add_row("Sampling Interval", f"{analysis.sample_interval:.1f} s")
        table.add_row("Sample Points", str(len(analysis.data_points)))
        table.add_row("", "")  # spacer
        
        # Audio info
        table.add_row("[bold]Audio Info[/bold]", "")
        table.add_row("Codec", analysis.codec)
        table.add_row("Channels", f"{analysis.channels}ch ({analyzer.get_channel_layout(analysis.channels)})")
        table.add_row("Sample Rate", f"{analysis.sample_rate} Hz")
        table.add_row("", "")  # spacer
        
        # Bitrate statistics
        table.add_row("[bold]Bitrate Statistics[/bold]", "")
        table.add_row("Average Bitrate", f"{analysis.average_bitrate/1000:.1f} kbps")
        table.add_row("Max Bitrate", f"{analysis.max_bitrate/1000:.1f} kbps")
        table.add_row("Min Bitrate", f"{analysis.min_bitrate/1000:.1f} kbps")
        table.add_row("Bitrate Stability", f"{analysis.bitrate_stability:.1%}")
        table.add_row("Quality Level", analysis.quality_level)
        
        console.print(table)
        
        # Show quality assessment
        quality = analyzer.assess_audio_quality(analysis)
        if verbose:
            console.print("\n[bold]Quality Assessment:[/bold]")
            console.print(f"Codec rating: {quality['codec_rating']}")
            console.print(f"Sample rate rating: {quality['sample_rate_rating']}")
            console.print(f"Stability: {quality['stability']}")
            
            if quality['recommendations']:
                console.print("\n[yellow]Recommendations:[/yellow]")
                for rec in quality['recommendations']:
                    console.print(f"• {rec}")
        
        # Export data
        if export_json:
            analyzer.export_analysis_data(analysis, export_json)
        
        if export_csv:
            analyzer.export_to_csv(analysis, export_csv)
        
        if verbose:
            console.print("\n[green]✓ Audio analysis complete[/green]")
            console.print(f"Data range: {analysis.data_points[0].timestamp:.1f}s - {analysis.data_points[-1].timestamp:.1f}s")
            
    except Exception as e:
        console.print(f"[red]✗ Analysis failed: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


def batch_audio_command(
    files: List[str] = typer.Argument(..., help="List of video files to analyze"),
    interval: float = typer.Option(15.0, "--interval", "-i", help="Sampling interval (seconds)"),
    output_dir: str = typer.Option("./output", "--output", "-o", help="Output directory")
):
    """
    Analyze audio bitrate for multiple videos.
    """
    console.print(f"[blue]Starting batch audio analysis of {len(files)} file(s)[/blue]")
    
    import os
    from ..core.audio_analyzer import analyze_multiple_audio
    
    # Ensure output dir exists
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        results = analyze_multiple_audio(files, interval)
        
        # Create summary table
        summary_table = Table(title="Batch Audio Analysis Summary")
        summary_table.add_column("Filename", style="cyan")
        summary_table.add_column("Codec", style="blue")
        summary_table.add_column("Channels", style="green")
        summary_table.add_column("Sample Rate", style="yellow")
        summary_table.add_column("Avg Bitrate (kbps)", style="magenta")
        summary_table.add_column("Quality", style="red")
        
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
            
            # Export each file's analysis results
            base_name = os.path.splitext(filename)[0]
            json_path = os.path.join(output_dir, f"{base_name}_audio.json")
            csv_path = os.path.join(output_dir, f"{base_name}_audio.csv")
            
            analyzer.export_analysis_data(result, json_path)
            analyzer.export_to_csv(result, csv_path)
        
        console.print(summary_table)
        console.print(f"\n[green]✓ Batch audio analysis complete. Results saved to {output_dir}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Batch audio analysis failed: {e}[/red]")
        raise typer.Exit(1)


def fps_command(
    input_path: str = typer.Argument(..., help="Video file path, HTTP URL, or HLS stream URL"),
    interval: float = typer.Option(10.0, "--interval", "-i", help="Sampling interval (seconds)"),
    export_json: Optional[str] = typer.Option(None, "--json", help="Export JSON file path"),
    export_csv: Optional[str] = typer.Option(None, "--csv", help="Export CSV file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
    force_download: bool = typer.Option(False, "--force-download", help="Force re-download even if cached"),
    max_workers: int = typer.Option(10, "--workers", help="Maximum download threads for HLS")
):
    """
    Analyze video FPS and dropped frames.
    """
    console.print(f"[blue]Analyzing FPS and dropped frames:[/blue] {input_path}")
    
    # Auto-optimize interval for large files
    from ..utils.validators import is_hls_url
    if is_hls_url(input_path) and interval == 10.0:  # Default value
        interval = 30.0  # Larger interval for HLS  
        console.print("[dim]Auto-optimized sampling interval for HLS: 30s[/dim]")
    
    try:
        # Process video file with download support
        processed_file = safe_process_file(
            input_path,
            force_download=force_download, 
            max_workers=max_workers
        )
        if processed_file is None:
            console.print("[red]Input processing failed[/red]")
            raise typer.Exit(1)
        
        # Create analyzer and run analysis
        analyzer = FPSAnalyzer(sample_interval=interval)
        analysis = analyzer.analyze(processed_file)
        
        # Show analysis results
        table = Table(title="FPS Analysis")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        table.add_row("File Path", analysis.file_path)
        table.add_row("Video Duration", f"{analysis.duration:.1f} s ({analysis.duration/60:.1f} min)")
        table.add_row("Sampling Interval", f"{analysis.sample_interval:.1f} s")
        table.add_row("Sample Points", str(len(analysis.data_points)))
        table.add_row("", "")  # spacer
        
        # FPS stats
        table.add_row("[bold]FPS Statistics[/bold]", "")
        table.add_row("Declared FPS", f"{analysis.declared_fps:.2f} fps")
        table.add_row("Actual Avg FPS", f"{analysis.actual_average_fps:.2f} fps")
        table.add_row("Max Instant FPS", f"{analysis.max_fps:.2f} fps")
        table.add_row("Min Instant FPS", f"{analysis.min_fps:.2f} fps")
        table.add_row("FPS Stability", f"{analysis.fps_stability:.1%}")
        table.add_row("", "")  # spacer
        
        # Drop statistics
        table.add_row("[bold]Dropped Frames[/bold]", "")
        table.add_row("Total Frames", str(analysis.total_frames))
        table.add_row("Dropped Frames", str(analysis.total_dropped_frames))
        table.add_row("Drop Rate", f"{analysis.drop_rate:.2%}")
        table.add_row("Performance Grade", analysis.performance_grade)
        
        console.print(table)
        
        # Show quality assessment
        if verbose:
            quality = analyzer.analyze_fps_quality(analysis)
            console.print("\n[bold]FPS Quality Assessment:[/bold]")
            console.print(f"Performance grade: {quality['performance_grade']}")
            console.print(f"FPS consistency: {quality['fps_consistency']}")
            console.print(f"FPS accuracy: {quality['fps_accuracy']}")
            console.print(f"Drop rate: {quality['drop_rate']}")
            
            if quality['issues']:
                console.print("\n[yellow]Detected issues:[/yellow]")
                for issue in quality['issues']:
                    console.print(f"• {issue}")
            
            if quality['recommendations']:
                console.print("\n[green]Recommendations:[/green]")
                for rec in quality['recommendations']:
                    console.print(f"• {rec}")
            
            # Drop severity analysis
            drop_analysis = analyzer.analyze_drop_severity(analysis)
            if drop_analysis['worst_segments']:
                console.print(f"\n[red]Worst dropped-frame segments (Severity: {drop_analysis['severity']}):[/red]")
                for timestamp, drops in drop_analysis['worst_segments'][:3]:
                    console.print(f"• {timestamp:.1f}s: {drops} frames")
        
        # Export data
        if export_json:
            analyzer.export_analysis_data(analysis, export_json)
        
        if export_csv:
            analyzer.export_to_csv(analysis, export_csv)
        
        if verbose:
            console.print("\n[green]✓ FPS analysis complete[/green]")
            console.print(f"Data range: {analysis.data_points[0].timestamp:.1f}s - {analysis.data_points[-1].timestamp:.1f}s")
            
    except Exception as e:
        console.print(f"[red]✗ FPS analysis failed: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


def batch_fps_command(
    files: List[str] = typer.Argument(..., help="List of video files to analyze"),
    interval: float = typer.Option(10.0, "--interval", "-i", help="Sampling interval (seconds)"),
    output_dir: str = typer.Option("./output", "--output", "-o", help="Output directory")
):
    """
    Analyze FPS and dropped frames for multiple videos.
    """
    console.print(f"[blue]Starting batch FPS analysis of {len(files)} video(s)[/blue]")
    
    import os
    from ..core.fps_analyzer import analyze_multiple_fps
    
    # Ensure output dir exists
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        results = analyze_multiple_fps(files, interval)
        
        # Create summary table
        summary_table = Table(title="Batch FPS Analysis Summary")
        summary_table.add_column("Filename", style="cyan")
        summary_table.add_column("Duration (min)", style="blue")
        summary_table.add_column("Declared FPS", style="green")
        summary_table.add_column("Actual FPS", style="yellow")
        summary_table.add_column("Drop Rate", style="red")
        summary_table.add_column("Grade", style="magenta")
        
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
            
            # Export each file's analysis results
            base_name = os.path.splitext(filename)[0]
            json_path = os.path.join(output_dir, f"{base_name}_fps.json")
            csv_path = os.path.join(output_dir, f"{base_name}_fps.csv")
            
            analyzer.export_analysis_data(result, json_path)
            analyzer.export_to_csv(result, csv_path)
        
        console.print(summary_table)
        console.print(f"\n[green]✓ Batch FPS analysis complete. Results saved to {output_dir}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Batch FPS analysis failed: {e}[/red]")
        raise typer.Exit(1)


def chart_command(
    input_path: str = typer.Argument(..., help="Video file path, HTTP URL, or HLS stream URL"),
    output_dir: str = typer.Option("./charts", "--output", "-o", help="Charts output directory"),
    chart_type: str = typer.Option("combined", "--type", "-t", help="Chart type: video, audio, fps, combined, summary, all"),
    config_type: str = typer.Option("default", "--config", "-c", help="Chart config: default, high_res, compact"),
    video_interval: float = typer.Option(30.0, "--video-interval", help="Video sampling interval (seconds)"),
    audio_interval: float = typer.Option(15.0, "--audio-interval", help="Audio sampling interval (seconds)"),
    fps_interval: float = typer.Option(10.0, "--fps-interval", help="FPS sampling interval (seconds)"),
    force_download: bool = typer.Option(False, "--force-download", help="Force re-download even if cached"),
    max_workers: int = typer.Option(10, "--workers", help="Maximum download threads for HLS")
):
    """
    Generate video analysis charts.
    """
    console.print(f"[blue]Generating charts for:[/blue] {input_path}")
    console.print(f"Type: {chart_type}, Config: {config_type}")
    
    # Auto-optimize intervals for HLS
    from ..utils.validators import is_hls_url
    if is_hls_url(input_path):
        # Use larger intervals for HLS streams
        if video_interval == 30.0:  # Default value
            video_interval = 120.0  # 2 minutes
        if audio_interval == 15.0:  # Default value
            audio_interval = 60.0   # 1 minute
        if fps_interval == 10.0:  # Default value
            fps_interval = 60.0     # 1 minute
        console.print("[dim]Auto-optimized sampling intervals for HLS[/dim]")
    
    try:
        # Process video file with download support
        processed_file = safe_process_file(
            input_path,
            force_download=force_download,
            max_workers=max_workers
        )
        if processed_file is None:
            console.print("[red]Input processing failed[/red]")
            raise typer.Exit(1)
        
        # Decide which analyses are needed by chart type
        need_video = chart_type in ['video', 'combined', 'summary', 'all']
        need_audio = chart_type in ['audio', 'combined', 'summary', 'all'] 
        need_fps = chart_type in ['fps', 'combined', 'summary', 'all']
        
        # Perform required analyses
        video_analysis = None
        audio_analysis = None
        fps_analysis = None
        
        if need_video:
            console.print("[yellow]Analyzing video bitrate...[/yellow]")
            video_analyzer = VideoBitrateAnalyzer(sample_interval=video_interval)
            video_analysis = video_analyzer.analyze(processed_file)
        
        if need_audio:
            console.print("[yellow]Analyzing audio bitrate...[/yellow]")
            audio_analyzer = AudioBitrateAnalyzer(sample_interval=audio_interval)
            audio_analysis = audio_analyzer.analyze(processed_file)
        
        if need_fps:
            console.print("[yellow]Analyzing FPS...[/yellow]")
            fps_analyzer = FPSAnalyzer(sample_interval=fps_interval)
            fps_analysis = fps_analyzer.analyze(processed_file)
        
        # Create chart generator
        chart_generator = ChartGenerator()
        
        # Get chart config
        if config_type == "high_res":
            config = ChartStyles.get_high_res_config()
        elif config_type == "compact":
            config = ChartStyles.get_compact_config()
        else:
            config = ChartStyles.get_default_config()
        
        config.output_dir = output_dir
        
        # Generate charts
        results = {}
        
        if chart_type == "video" and video_analysis:
            config.title = f"Video Bitrate Analysis - {os.path.basename(input_path)}"
            chart_path = chart_generator.generate_video_bitrate_chart(video_analysis, config)
            results['video'] = chart_path
            console.print(f"✓ Video bitrate chart generated: {chart_path}")
            
        elif chart_type == "audio" and audio_analysis:
            config.title = f"Audio Bitrate Analysis - {os.path.basename(input_path)}"
            chart_path = chart_generator.generate_audio_bitrate_chart(audio_analysis, config)
            results['audio'] = chart_path
            console.print(f"✓ Audio bitrate chart generated: {chart_path}")
            
        elif chart_type == "fps" and fps_analysis:
            config.title = f"FPS Analysis - {os.path.basename(input_path)}"
            chart_path = chart_generator.generate_fps_chart(fps_analysis, config)
            results['fps'] = chart_path
            console.print(f"✓ FPS chart generated: {chart_path}")
            
        elif chart_type == "combined" and all([video_analysis, audio_analysis, fps_analysis]):
            config.title = f"Combined Analysis - {os.path.basename(input_path)}"
            chart_path = chart_generator.generate_combined_chart(
                video_analysis, audio_analysis, fps_analysis, config
            )
            results['combined'] = chart_path
            console.print(f"✓ Combined analysis chart generated: {chart_path}")
            
        elif chart_type == "summary" and all([video_analysis, audio_analysis, fps_analysis]):
            config.title = f"Analysis Summary - {os.path.basename(input_path)}"
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
            console.print(f"[red]Unable to generate chart: missing analysis data or unsupported chart type[/red]")
            raise typer.Exit(1)
        
        # Show results summary
        if results:
            table = Table(title="Generated Chart Files")
            table.add_column("Chart Type", style="cyan")
            table.add_column("File Path", style="green")
            
            for chart_name, chart_path in results.items():
                table.add_row(chart_name, chart_path)
            
            console.print(table)
            console.print(f"\n[green]✓ Chart generation complete. Saved to: {output_dir}[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Chart generation failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


def batch_chart_command(
    files: List[str] = typer.Argument(..., help="List of video files to analyze"),
    output_dir: str = typer.Option("./batch_charts", "--output", "-o", help="Charts output directory"),
    chart_type: str = typer.Option("combined", "--type", "-t", help="Chart type: combined, summary, all"),
    config_type: str = typer.Option("default", "--config", "-c", help="Chart config: default, high_res, compact")
):
    """
    Generate charts for multiple video files.
    """
    console.print(f"[blue]Starting batch chart generation for {len(files)} file(s)[/blue]")
    console.print(f"Type: {chart_type}, Config: {config_type}")
    
    import os
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
        # Get config
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
            console.print(f"\n[blue]Processing file {i}/{len(files)}:[/blue] {os.path.basename(file_path)}")
            
            try:
                # Process file
                processed_file = safe_process_file(file_path)
                if processed_file is None:
                    console.print(f"[red]✗ File processing failed: {file_path}[/red]")
                    continue
                
                # Run three analyses
                video_analyzer = VideoBitrateAnalyzer()
                audio_analyzer = AudioBitrateAnalyzer()
                fps_analyzer = FPSAnalyzer()
                
                video_analysis = video_analyzer.analyze(processed_file)
                audio_analysis = audio_analyzer.analyze(processed_file)
                fps_analysis = fps_analyzer.analyze(processed_file)
                
                # Create subdirectory for each file
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
                
                # Generate charts
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
                console.print(f"[red]✗ Failed to process file {file_path}: {e}[/red]")
                continue
        
        # Final results
        console.print(f"\n[green]✓ Batch chart generation complete[/green]")
        console.print(f"Processed: {success_count}/{len(files)} file(s)")
        console.print(f"Charts generated: {total_charts}")
        console.print(f"Output directory: {output_dir}")
        
    except Exception as e:
        console.print(f"[red]✗ Batch chart generation failed: {e}[/red]")
        raise typer.Exit(1)


# ================================================================================
# Configuration Management Commands
# ================================================================================

def config_show_command():
    """Show current configuration settings."""
    try:
        config_manager = ConfigManager()
        config = config_manager.show_config()
        
        # Display config table
        table = Table(title="Current Configuration")
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        for key, value in config.items():
            table.add_row(key, str(value))
        
        console.print(table)
        console.print(f"\nConfig file: {config_manager.get_config_path()}")
        
    except Exception as e:
        console.print(f"[red]✗ Failed to show config: {e}[/red]")
        raise typer.Exit(1)


def config_set_command(
    key: str = typer.Argument(..., help="Configuration key to set"),
    value: str = typer.Argument(..., help="Configuration value to set")
):
    """Set a configuration value."""
    try:
        config_manager = ConfigManager()
        
        # Convert value to appropriate type
        converted_value = _convert_config_value(key, value)
        
        # Update config
        success = config_manager.update_config({key: converted_value})
        
        if success:
            console.print(f"[green]✓ Set {key} = {converted_value}[/green]")
        else:
            console.print(f"[red]✗ Failed to set {key}[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Failed to set config: {e}[/red]")
        raise typer.Exit(1)


def config_reset_command():
    """Reset configuration to defaults."""
    try:
        config_manager = ConfigManager()
        success = config_manager.reset_config()
        
        if success:
            console.print("[green]✓ Configuration reset to defaults[/green]")
        else:
            console.print("[red]✗ Failed to reset configuration[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Failed to reset config: {e}[/red]")
        raise typer.Exit(1)


def _convert_config_value(key: str, value: str):
    """Convert string value to appropriate type based on key."""
    # Boolean fields
    if key in ['verbose', 'export_json', 'export_csv']:
        return value.lower() in ['true', '1', 'yes', 'on']
    
    # Float fields
    if key in ['interval']:
        return float(value)
    
    # Integer fields
    if key in ['ffmpeg_timeout']:
        return int(value)
    
    # String fields (default)
    return value


# ================================================================================
# Download and Cache Management Commands
# ================================================================================

def download_command(
    url: str = typer.Argument(..., help="HTTP URL or HLS stream URL to download"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    max_workers: int = typer.Option(10, "--workers", help="Maximum download threads for HLS"),
    force: bool = typer.Option(False, "--force", help="Force re-download even if cached")
):
    """
    Download video from HTTP URL or HLS stream.
    """
    from ..utils.validators import is_url, is_hls_url
    from ..core.hls_downloader import HLSDownloader
    from ..utils.download_cache import get_download_cache
    import requests
    from rich.progress import Progress, BarColumn, TextColumn, DownloadColumn
    
    if not is_url(url):
        console.print(f"[red]Invalid URL: {url}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]Downloading:[/blue] {url}")
    
    try:
        # Check cache first
        cache = get_download_cache()
        if not force:
            cached_path = cache.get_cached_file(url)
            if cached_path:
                console.print(f"[green]✓ Using cached file: {cached_path}[/green]")
                
                if output:
                    import shutil
                    shutil.copy2(cached_path, output)
                    console.print(f"[green]✓ Copied to: {output}[/green]")
                
                return
        
        # Download based on URL type
        if is_hls_url(url):
            # HLS download
            downloader = HLSDownloader(max_workers=max_workers)
            result = downloader.download_hls_stream(url, output)
            
            if result.success:
                # Add to cache
                cache.add_to_cache(
                    url=url,
                    file_path=result.local_file_path,
                    duration=result.duration,
                    format_name='mp4'
                )
                
                console.print(f"[green]✓ HLS download complete: {result.local_file_path}[/green]")
                console.print(f"  Size: {result.total_size/1024/1024:.1f} MB")
                console.print(f"  Duration: {result.duration/60:.1f} min")
                console.print(f"  Segments: {result.segments_count}")
            else:
                console.print(f"[red]✗ HLS download failed: {result.error_message}[/red]")
                raise typer.Exit(1)
        
        else:
            # HTTP download
            from urllib.parse import urlparse
            import os
            import tempfile
            
            if not output:
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path) or 'video.mp4'
                output = os.path.join(tempfile.gettempdir(), filename)
            
            with requests.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    DownloadColumn(),
                    console=console
                ) as progress:
                    
                    download_task = progress.add_task("Downloading", total=total_size)
                    
                    with open(output, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                progress.update(download_task, advance=len(chunk))
            
            # Add to cache
            cache.add_to_cache(url=url, file_path=output)
            
            console.print(f"[green]✓ Download complete: {output}[/green]")
            console.print(f"  Size: {os.path.getsize(output)/1024/1024:.1f} MB")
            
    except Exception as e:
        console.print(f"[red]✗ Download failed: {e}[/red]")
        raise typer.Exit(1)


def cache_list_command():
    """List all cached files."""
    from ..utils.download_cache import get_download_cache
    
    cache = get_download_cache()
    cached_files = cache.list_cached_files()
    
    if not cached_files:
        console.print("[yellow]No cached files found[/yellow]")
        return
    
    # Create cache listing table
    table = Table(title="Cached Files")
    table.add_column("Cache Key", style="cyan", no_wrap=True)
    table.add_column("URL", style="blue")
    table.add_column("Size (MB)", style="green", justify="right")
    table.add_column("Duration", style="yellow", justify="right")
    table.add_column("Format", style="magenta")
    table.add_column("Downloaded", style="dim")
    table.add_column("Valid", style="red")
    
    for file_info in cached_files:
        duration_str = f"{file_info['duration_min']:.1f}m" if file_info['duration_min'] > 0 else "-"
        valid_str = "✓" if file_info['valid'] else "✗"
        valid_style = "green" if file_info['valid'] else "red"
        
        table.add_row(
            file_info['cache_key'],
            file_info['url'],
            str(file_info['size_mb']),
            duration_str,
            file_info['format'] or "-",
            file_info['download_time'],
            f"[{valid_style}]{valid_str}[/{valid_style}]"
        )
    
    console.print(table)
    
    # Show cache info
    cache_info = cache.get_cache_info()
    console.print(f"\n[dim]Cache directory: {cache_info['cache_dir']}[/dim]")
    console.print(f"[dim]Total: {cache_info['valid_files']}/{cache_info['total_files']} files, {cache_info['total_size_mb']} MB ({cache_info['usage_percent']:.1f}% of limit)[/dim]")


def cache_clear_command(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """Clear all cached files."""
    from ..utils.download_cache import get_download_cache
    
    cache = get_download_cache()
    cache_info = cache.get_cache_info()
    
    if cache_info['total_files'] == 0:
        console.print("[yellow]No cached files to clear[/yellow]")
        return
    
    # Show what will be cleared
    console.print(f"[yellow]This will remove {cache_info['total_files']} cached files ({cache_info['total_size_mb']} MB)[/yellow]")
    
    if not confirm:
        import typer
        confirm = typer.confirm("Are you sure you want to clear the cache?")
        
    if not confirm:
        console.print("Cache clear cancelled")
        return
    
    try:
        files_removed, size_freed = cache.clear_cache()
        console.print(f"[green]✓ Cache cleared: {files_removed} files, {size_freed} MB freed[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Failed to clear cache: {e}[/red]")
        raise typer.Exit(1)


def cache_info_command():
    """Show cache information and statistics."""
    from ..utils.download_cache import get_download_cache
    
    cache = get_download_cache()
    cache_info = cache.get_cache_info()
    
    # Create info table
    table = Table(title="Cache Information")
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    
    table.add_row("Cache Directory", cache_info['cache_dir'])
    table.add_row("Total Files", str(cache_info['total_files']))
    table.add_row("Valid Files", str(cache_info['valid_files']))
    table.add_row("Total Size", f"{cache_info['total_size_mb']} MB")
    table.add_row("Size Limit", f"{cache_info['max_size_gb']} GB")
    table.add_row("Usage", f"{cache_info['usage_percent']:.1f}%")
    
    console.print(table)
    
    # Check if cleanup needed
    if cache_info['usage_percent'] > 80:
        console.print(f"\n[yellow]⚠ Cache usage is high ({cache_info['usage_percent']:.1f}%). Consider cleaning up old files.[/yellow]")


def cache_remove_command(
    url: str = typer.Argument(..., help="URL of cached file to remove")
):
    """Remove specific cached file."""
    from ..utils.download_cache import get_download_cache
    
    cache = get_download_cache()
    
    # Check if file is cached
    cached_path = cache.get_cached_file(url)
    if not cached_path:
        console.print(f"[yellow]File not found in cache: {url}[/yellow]")
        return
    
    try:
        success = cache.remove_from_cache(url)
        if success:
            console.print(f"[green]✓ Removed from cache: {url[:50]}...[/green]")
        else:
            console.print(f"[red]✗ Failed to remove from cache[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ Error removing from cache: {e}[/red]")
        raise typer.Exit(1)