#!/usr/bin/env python3
"""
CLI Main Entry Point
Main entry and configuration for the video analytics CLI.
"""

import typer
from rich.console import Console
from ..utils.logger import setup_logging

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
    batch_chart_command,
    config_show_command,
    config_set_command,
    config_reset_command,
    download_command,
    cache_list_command,
    cache_clear_command,
    cache_info_command,
    cache_remove_command,
    parallel_analysis_command,
    batch_parallel_command,
    performance_test_command
)

app = typer.Typer(
    help="Video analytics tool - analyze bitrate, FPS and more",
    add_completion=False,
    no_args_is_help=True
)

# Global console
console = Console()

# Core analysis commands
app.command("info", help="Show basic video file information")(info_command)
app.command("validate", help="Validate that a video file can be processed")(validate_command)
app.command("check", help="Check system dependencies")(check_command)
app.command("bitrate", help="Analyze video bitrate over time")(bitrate_command)
app.command("batch_bitrate", help="Analyze bitrate for multiple videos")(batch_bitrate_command)
app.command("audio", help="Analyze audio bitrate over time")(audio_command)
app.command("batch_audio", help="Analyze audio bitrate for multiple videos")(batch_audio_command)
app.command("fps", help="Analyze FPS and dropped frames")(fps_command)
app.command("batch_fps", help="Analyze FPS for multiple videos")(batch_fps_command)
app.command("chart", help="Generate analysis charts")(chart_command)
app.command("batch_chart", help="Generate charts for multiple videos")(batch_chart_command)

# Parallel analysis commands (NEW - Performance optimized)
app.command("parallel", help="Run comprehensive parallel analysis (video+audio+fps)")(parallel_analysis_command)
app.command("batch_parallel", help="Run parallel analysis on multiple videos")(batch_parallel_command)
app.command("performance", help="Performance test comparing parallel vs sequential analysis")(performance_test_command)

# Download and cache management commands
app.command("download", help="Download video from HTTP URL or HLS stream")(download_command)

# Configuration management commands
config_app = typer.Typer(help="Configuration management")
config_app.command("show", help="Show current configuration")(config_show_command)
config_app.command("set", help="Set a configuration value")(config_set_command)
config_app.command("reset", help="Reset configuration to defaults")(config_reset_command)
app.add_typer(config_app, name="config")

# Cache management commands
cache_app = typer.Typer(help="Download cache management")
cache_app.command("list", help="List all cached files")(cache_list_command)
cache_app.command("clear", help="Clear all cached files")(cache_clear_command)
cache_app.command("info", help="Show cache information")(cache_info_command)
cache_app.command("remove", help="Remove specific cached file")(cache_remove_command)
app.add_typer(cache_app, name="cache")


def main():
    """Main entry point"""
    try:
        # Initialize logging early with sensible defaults
        setup_logging()
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation canceled by user[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    main()