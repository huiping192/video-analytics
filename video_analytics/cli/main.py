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
    check_command,
    analyze_command,
    chart_command,
    cache_command
)

app = typer.Typer(
    help="Video analytics tool - intelligent analysis with smart defaults",
    add_completion=False,
    no_args_is_help=True
)

# Global console
console = Console()

# Core commands (simplified from 29 to 4)
app.command("info", help="Show video file information (supports multiple files)")(info_command)
app.command("analyze", help="Smart analysis with parallel processing (video+audio+fps)")(analyze_command)
app.command("chart", help="Generate analysis charts (supports multiple files)")(chart_command)
app.command("cache", help="Cache management (list|clear|info|remove <url>)")(cache_command)

# System dependency check
app.command("check", help="Check system dependencies")(check_command)


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