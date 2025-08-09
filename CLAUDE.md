# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **fully implemented** Python-based command-line video analysis tool with comprehensive CLI architecture.

**CURRENT STATUS: COMPLETE IMPLEMENTATION** - The project includes comprehensive video analysis capabilities with rich CLI interface, core analysis engines, visualization components, and configuration management.

**Implemented functionality:**
- Video bitrate analysis and visualization with configurable sampling intervals
- Audio bitrate analysis and quality assessment  
- FPS (frame rate) analysis and drop detection for large video files (3+ hours)
- Rich CLI interface with colored output and progress indicators
- Chart generation (individual analysis charts, combined views, summary reports)
- Batch processing capabilities for multiple files
- JSON/CSV data export functionality
- FFmpeg dependency checking and validation
- User configuration file management system
- CLI-based configuration commands

## CLI Architecture

**Entry Points:**
- Primary: `python -m video_analytics` → `video_analytics/__main__.py` → `video_analytics/cli/main.py`
- Legacy: `video_analytics/main.py` (backwards compatibility)
- Console script: `video-analytics` command (from setup.py)

**CLI Structure:**
```
video_analytics/cli/
├── main.py       # Typer app setup and main entry point
└── commands.py   # All command implementations (info, bitrate, audio, fps, etc.)
```

## Development Commands

**Installation and Setup:**
```bash
pip install -e .                 # Development install
pip install -r requirements.txt  # Install dependencies only
```

**Running the CLI:**
```bash
python -m video_analytics --help                    # Main help
python -m video_analytics check                     # Check FFmpeg dependencies
python main.py --help                               # Alternative entry point
video-analytics --help                              # If installed globally
```

**Basic Analysis Commands:**
```bash
# File information and validation
python -m video_analytics info <video_file>         # Show video metadata
python -m video_analytics info <video_file> --simple # Use simple mode (no FFmpeg)
python -m video_analytics validate <video_file>     # Validate file processing

# Individual analysis types
python -m video_analytics bitrate <video_file>      # Video bitrate analysis
python -m video_analytics audio <video_file>        # Audio bitrate analysis  
python -m video_analytics fps <video_file>          # FPS and drop frame analysis

# Batch processing
python -m video_analytics batch_bitrate <file1> <file2> <file3>
python -m video_analytics batch_audio <file1> <file2> <file3>
python -m video_analytics batch_fps <file1> <file2> <file3>

# Chart generation
python -m video_analytics chart <video_file>        # Combined analysis chart
python -m video_analytics chart <video_file> --type summary  # Summary chart
python -m video_analytics chart <video_file> --type all     # Full report
python -m video_analytics batch_chart <file1> <file2>       # Batch chart generation
```

**Configuration Management:**
```bash
# Configuration commands (new feature)
python -m video_analytics config show          # Show current configuration
python -m video_analytics config set interval 5.0   # Set sampling interval
python -m video_analytics config reset         # Reset to defaults
```

**Common Options:**
```bash
--interval 10.0          # Sampling interval in seconds
--output ./output        # Output directory
--json output.json       # Export JSON data
--csv output.csv         # Export CSV data  
--verbose               # Show detailed information
--config high_res       # Chart configuration (default, high_res, compact)
```

## Technology Stack (Implemented)

- **Python 3.8+** - Main language
- **FFmpeg/ffprobe** - Video analysis engine  
- **ffmpeg-python>=0.2.0** - Python FFmpeg interface
- **matplotlib>=3.5.0** - Chart generation and visualization
- **typer>=0.9.0** - Modern CLI framework
- **rich>=13.0.0** - Enhanced CLI output with colors and tables
- **tqdm>=4.64.0** - Progress bars and status indicators

## Core Architecture Components

### 1. CLI Layer (`video_analytics.cli`)
- **main.py**: Typer application setup with global error handling
- **commands.py**: All command implementations with rich formatting
- Command registration via Typer decorators
- Nested configuration sub-commands under `config` group

### 2. File Processing (`video_analytics.core`)
- **FileProcessor**: Main video file processor using FFmpeg
- **SimpleProcessor**: Lightweight processor that works without FFmpeg
- **VideoMetadata**: Dataclass for video file metadata
- **ProcessedFile**: Abstraction for processed video files
- **safe_process_file()**: Error-safe file processing wrapper

### 3. Analysis Engines (`video_analytics.core`)
- **VideoBitrateAnalyzer**: Analyzes video bitrate variations over time
- **AudioBitrateAnalyzer**: Analyzes audio bitrate and quality assessment
- **FPSAnalyzer**: Analyzes frame rate consistency and drop detection
- All analyzers support configurable sampling intervals and export to JSON/CSV

### 4. Configuration Management (`video_analytics.utils.config`)
- **ConfigManager**: Persistent user configuration in `~/.video-analytics/config.json`
- **AnalysisConfig**: Dataclass with default parameters
- **get_merged_config()**: CLI arguments override config file settings
- Support for common settings: interval, output_dir, chart_config, export formats

### 5. Visualization (`video_analytics.visualization`)
- **ChartGenerator**: Matplotlib-based chart generation
- **ChartConfig**: Configuration for chart styling and output
- **ChartStyles**: Predefined styles (default, high_res, compact)
- Supports individual analysis charts, combined views, and summary reports

## Key Implementation Notes

When working with this project:

1. **FFmpeg dependency** - Always check FFmpeg availability first with `python -m video_analytics check`
2. **Large file handling** - Optimized for 3+ hour video files with configurable sampling intervals
3. **Chinese documentation** - Technical specs in `documents/` provide detailed implementation guidance
4. **Error handling** - Robust error handling with informative messages and fallback modes
5. **Memory efficiency** - Streaming processing approach for large video files
6. **Export capabilities** - All analysis results can be exported to JSON/CSV formats

## Development Workflow

**No formal tests** - The project currently has no test files. Quality assurance relies on:
- **Validation commands**: Built-in file validation and dependency checking
- **Error handling**: Comprehensive exception handling throughout the codebase
- **Simple mode**: Fallback processing mode when FFmpeg is not available

**Manual testing commands:**
```bash
python -m video_analytics check                     # Verify dependencies
python -m video_analytics validate <test_file>      # Test file processing
python -m video_analytics info <test_file> --simple # Test simple mode
```

## Critical Dependencies and Requirements

- **FFmpeg**: Essential for full functionality - install from https://ffmpeg.org/download.html
- **Python 3.8+**: Required for modern type hints and dataclass support
- **System memory**: Sufficient RAM for processing large video files (recommended 4GB+ for 3+ hour videos)
- **Disk space**: Chart generation and export files require adequate storage

**Dependency validation:**
- Use `python -m video_analytics check` to verify all dependencies
- FFmpeg installation is checked at runtime with version detection
- Python package dependencies are handled via requirements.txt