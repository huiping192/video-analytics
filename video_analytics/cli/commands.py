#!/usr/bin/env python3
"""
CLI Commands - Simplified video chart generator.
Single command for auto-analysis + auto-chart generation.
"""

import sys
import os
import asyncio
from typing import List
import typer
from rich.console import Console
from rich.table import Table

from ..core import safe_process_file
from ..core.parallel_analyzer import ParallelAnalysisEngine, create_fast_config, create_detailed_config, create_memory_optimized_config
from ..visualization import ChartGenerator, ChartStyles

console = Console()


def create_smart_config(metadata):
    """Create optimized configuration based on video duration."""
    duration = metadata.duration
    if duration < 300:  # < 5 min - detailed analysis
        return create_detailed_config()
    elif duration < 3600:  # < 1 hour - standard fast analysis
        return create_fast_config(duration)
    else:  # > 1 hour - memory optimized
        return create_memory_optimized_config()


def generate_smart_chart(video_analysis, audio_analysis, fps_analysis, metadata, output_dir, input_path, chart_type="detailed"):
    """Generate specified chart type."""
    chart_generator = ChartGenerator()
    
    # Use user-specified chart type (default: detailed)
    if chart_type == "detailed":
        config = ChartStyles.get_enhanced_preset(info_level='detailed')
        chart_type_name = "detailed"
    else:  # combined chart
        config = ChartStyles.get_default_config()
        chart_type_name = "combined"
    
    # Setup output
    config.output_dir = output_dir
    config.title = f"Video Analysis - {os.path.basename(input_path)}"
    
    # Generate appropriate chart
    if chart_type_name == "detailed":
        chart_path = chart_generator.generate_enhanced_chart(
            metadata, video_analysis, audio_analysis, fps_analysis, config
        )
    else:
        chart_path = chart_generator.generate_combined_chart(
            video_analysis, audio_analysis, fps_analysis, config
        )
    
    return chart_path, chart_type_name


def generate_command(
    input_paths: List[str] = typer.Argument(..., help="Video file paths, HTTP URLs, or HLS stream URLs"),
    output_dir: str = typer.Option("./charts", "--output", "-o", help="Charts output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed progress"),
    chart_type: str = typer.Option("detailed", "--chart-type", help="Chart type: 'detailed' or 'combined'")
):
    """
    Generate professional video analysis charts with smart defaults.
    
    Automatically analyzes video files and generates optimized charts:
    - Auto-detects best analysis settings based on video duration
    - Parallel processing (video + audio + fps analysis) 
    - Default to detailed charts, with option to specify combined charts
    - Supports single/multiple files, HTTP URLs, HLS streams
    - Zero configuration required - works perfectly out of the box
    """
    
    # Validate chart type
    if chart_type not in ["detailed", "combined"]:
        console.print(f"[red]Error: Invalid chart type '{chart_type}'. Must be 'detailed' or 'combined'.[/red]")
        raise typer.Exit(1)
    
    # Check dependencies first
    try:
        import subprocess
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("[red]Error: FFmpeg not found. Please install FFmpeg first.[/red]")
        console.print("Install from: https://ffmpeg.org/download.html")
        raise typer.Exit(1)
    
    console.print(f"[blue]🎬 Generating professional charts for {len(input_paths)} file(s)...[/blue]")
    
    # Setup output directory
    os.makedirs(output_dir, exist_ok=True)
    console.print(f"[green]📁 Output directory:[/green] {output_dir}")
    
    successful_files = []
    failed_files = []
    total_charts = []
    
    for i, input_path in enumerate(input_paths, 1):
        console.print(f"\n[blue]🔄 Processing {i}/{len(input_paths)}:[/blue] {os.path.basename(input_path)}")
        
        if verbose:
            console.print(f"[dim]   Full path: {input_path}[/dim]")
        
        try:
            # Step 1: Process file (handles local files, HTTP URLs, HLS streams)
            with console.status(f"[bold blue]Processing file..."):
                processed_file = safe_process_file(input_path)
                if processed_file is None:
                    console.print(f"[red]✗ Failed to process: {input_path}[/red]")
                    failed_files.append(input_path)
                    continue
            
            # Step 2: Load metadata and optimize configuration  
            metadata = processed_file.load_metadata()
            config = create_smart_config(metadata)
            
            # Always enable all analysis types for best charts
            config.enable_video = True
            config.enable_audio = True  
            config.enable_fps = True
            
            if verbose:
                console.print(f"[dim]   Duration: {metadata.duration:.1f}s ({metadata.duration/60:.1f} min)[/dim]")
                console.print(f"[dim]   Resolution: {metadata.width}x{metadata.height}[/dim]")
                console.print(f"[dim]   Analysis mode: {config.__class__.__name__}[/dim]")
            
            # Step 3: Run parallel analysis
            async def run_analysis():
                engine = ParallelAnalysisEngine(config)
                return await engine.analyze_all(processed_file)
            
            with console.status(f"[bold green]🔍 Running smart analysis..."):
                combined_result = asyncio.run(run_analysis())
            
            # Check analysis success
            if not all([combined_result.video_analysis, combined_result.audio_analysis, combined_result.fps_analysis]):
                console.print(f"[red]✗ Analysis incomplete for: {input_path}[/red]")
                failed_files.append(input_path)
                continue
            
            # Step 4: Generate optimized charts
            file_output_dir = output_dir
            if len(input_paths) > 1:  # Create subdirectories for multiple files
                file_basename = os.path.splitext(os.path.basename(input_path))[0]
                file_output_dir = os.path.join(output_dir, file_basename)
                os.makedirs(file_output_dir, exist_ok=True)
            
            with console.status(f"[bold magenta]📊 Generating smart charts..."):
                chart_path, actual_chart_type = generate_smart_chart(
                    combined_result.video_analysis,
                    combined_result.audio_analysis, 
                    combined_result.fps_analysis,
                    metadata,
                    file_output_dir,
                    input_path,
                    chart_type
                )
            
            # Success summary
            console.print(f"[green]✅ Completed in {combined_result.execution_time:.1f}s[/green]")
            console.print(f"   📊 Chart type: {actual_chart_type}")
            console.print(f"   💾 Saved: {os.path.basename(chart_path)}")
            
            if verbose:
                # Show key analysis metrics
                video = combined_result.video_analysis
                audio = combined_result.audio_analysis
                fps = combined_result.fps_analysis
                console.print(f"[dim]   Video: {video.average_bitrate/1000000:.1f} Mbps ({video.encoding_type.split()[0]})[/dim]")
                console.print(f"[dim]   Audio: {audio.average_bitrate/1000:.0f} kbps ({audio.quality_level})[/dim]")
                console.print(f"[dim]   FPS: {fps.actual_average_fps:.1f} fps ({fps.total_dropped_frames} drops)[/dim]")
            
            successful_files.append(input_path)
            total_charts.append(chart_path)
            
        except Exception as e:
            console.print(f"[red]✗ Error processing {input_path}: {str(e)}[/red]")
            failed_files.append(input_path)
            if verbose:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    # Final summary
    console.print(f"\n[bold blue]📈 Generation Summary:[/bold blue]")
    console.print(f"[green]✅ Successful: {len(successful_files)}/{len(input_paths)} files[/green]")
    
    if failed_files:
        console.print(f"[red]❌ Failed: {len(failed_files)} files[/red]")
        if verbose:
            for failed_file in failed_files:
                console.print(f"[dim]   - {failed_file}[/dim]")
    
    console.print(f"[blue]📊 Total charts generated: {len(total_charts)}[/blue]")
    console.print(f"[green]📁 Output location: {output_dir}[/green]")
    
    if successful_files and not verbose:
        console.print(f"\n[dim]💡 Use --verbose (-v) for detailed analysis metrics[/dim]")
    
    # Exit with error code if any files failed
    if failed_files:
        raise typer.Exit(1)