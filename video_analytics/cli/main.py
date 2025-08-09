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
    config_reset_command
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

# Configuration management commands
config_app = typer.Typer(help="Configuration management")
config_app.command("show", help="Show current configuration")(config_show_command)
config_app.command("set", help="Set a configuration value")(config_set_command)
config_app.command("reset", help="Reset configuration to defaults")(config_reset_command)
app.add_typer(config_app, name="config")


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