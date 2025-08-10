#!/usr/bin/env python3
"""
CLI Main Entry Point
Main entry and configuration for the video analytics CLI.
"""

import typer
from rich.console import Console
from ..utils.logger import setup_logging

from .commands import (
    generate_command
)

app = typer.Typer(
    help="Professional video chart generator - one command, smart defaults",
    add_completion=False,
    no_args_is_help=True
)

# Global console
console = Console()

# Single main command - auto-analysis + auto-chart generation
app.command()(generate_command)


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