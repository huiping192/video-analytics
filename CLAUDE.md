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

# Individual analysis types (supports local files, HTTP URLs, and HLS streams)
python -m video_analytics bitrate <input>           # Video bitrate analysis
python -m video_analytics audio <input>             # Audio bitrate analysis  
python -m video_analytics fps <input>               # FPS and drop frame analysis

# Examples with different input types:
python -m video_analytics bitrate /path/to/video.mp4                    # Local file
python -m video_analytics bitrate https://example.com/video.mp4         # HTTP URL
python -m video_analytics bitrate https://stream.example.com/live.m3u8  # HLS stream

# Batch processing
python -m video_analytics batch_bitrate <file1> <file2> <file3>
python -m video_analytics batch_audio <file1> <file2> <file3>
python -m video_analytics batch_fps <file1> <file2> <file3>

# Chart generation (supports all input types)
python -m video_analytics chart <input>             # Combined analysis chart
python -m video_analytics chart <input> --type summary  # Summary chart
python -m video_analytics chart <input> --type all     # Full report
python -m video_analytics batch_chart <file1> <file2>   # Batch chart generation

# Download management
python -m video_analytics download <hls_url>        # Download HLS stream or HTTP video
```

**Download and Cache Management:**
```bash
# Download commands
python -m video_analytics download <hls_url>            # Download HLS stream
python -m video_analytics download <http_url> -o video.mp4  # Download HTTP video

# Cache management
python -m video_analytics cache list               # List cached downloads
python -m video_analytics cache info               # Show cache statistics
python -m video_analytics cache clear              # Clear all cache
python -m video_analytics cache remove <url>       # Remove specific cached file
```

**Configuration Management:**
```bash
# Configuration commands
python -m video_analytics config show              # Show current configuration
python -m video_analytics config set interval 5.0 # Set sampling interval
python -m video_analytics config reset             # Reset to defaults
```

**Common Options:**
```bash
--interval 10.0          # Sampling interval in seconds
--output ./output        # Output directory
--json output.json       # Export JSON data
--csv output.csv         # Export CSV data  
--verbose               # Show detailed information
--config high_res       # Chart configuration (default, high_res, compact)
--force-download        # Force re-download even if cached
--workers 10            # Maximum download threads for HLS (1-20)
```

## Technology Stack (Implemented)

- **Python 3.8+** - Main language
- **FFmpeg/ffprobe** - Video analysis engine  
- **ffmpeg-python>=0.2.0** - Python FFmpeg interface
- **matplotlib>=3.5.0** - Chart generation and visualization
- **typer>=0.9.0** - Modern CLI framework
- **rich>=13.0.0** - Enhanced CLI output with colors and tables
- **tqdm>=4.64.0** - Progress bars and status indicators
- **requests>=2.25.0** - HTTP downloads and URL validation
- **m3u8>=3.0.0** - HLS playlist parsing and processing

## Core Architecture Components

### 1. CLI Layer (`video_analytics.cli`)
- **main.py**: Typer application setup with global error handling
- **commands.py**: All command implementations with rich formatting
- Command registration via Typer decorators
- Nested configuration sub-commands under `config` group

### 2. File Processing (`video_analytics.core`)
- **FileProcessor**: Unified processor for local files, HTTP URLs, and HLS streams
- **HLSDownloader**: High-performance HLS stream downloader with concurrent segments
- **SimpleProcessor**: Lightweight processor that works without FFmpeg  
- **VideoMetadata**: Enhanced dataclass with URL and cache information
- **ProcessedFile**: Abstraction supporting downloaded content
- **safe_process_file()**: Error-safe processing with download support

### 3. Analysis Engines (`video_analytics.core`)
- **VideoBitrateAnalyzer**: Analyzes video bitrate variations over time
- **AudioBitrateAnalyzer**: Analyzes audio bitrate and quality assessment
- **FPSAnalyzer**: Analyzes frame rate consistency and drop detection
- All analyzers support configurable sampling intervals and export to JSON/CSV

### 4. Download and Cache System (`video_analytics.utils`)
- **DownloadCache**: Intelligent caching system for downloaded content
- **URL validators**: Comprehensive validation for HTTP/HLS URLs
- **Cache management**: Automatic cleanup, size limits, integrity checks
- **Progress tracking**: Rich progress indicators for downloads

### 5. Configuration Management (`video_analytics.utils.config`)
- **ConfigManager**: Persistent user configuration in `~/.video-analytics/config.json`
- **AnalysisConfig**: Dataclass with default parameters
- **get_merged_config()**: CLI arguments override config file settings
- Support for common settings: interval, output_dir, chart_config, export formats

### 6. Visualization (`video_analytics.visualization`)
- **ChartGenerator**: Matplotlib-based chart generation
- **ChartConfig**: Configuration for chart styling and output
- **ChartStyles**: Predefined styles (default, high_res, compact)
- Supports individual analysis charts, combined views, and summary reports

## Key Implementation Notes

When working with this project:

1. **FFmpeg dependency** - Always check FFmpeg availability first with `python -m video_analytics check`
2. **HLS and URL support** - Seamless support for local files, HTTP URLs, and HLS streams
3. **Large file optimization** - Auto-optimized sampling intervals for HLS streams (1-3 hour videos)
4. **Download caching** - Intelligent caching prevents re-downloading large HLS streams
5. **Concurrent downloads** - Multi-threaded HLS segment downloading for faster processing
6. **Error handling** - Comprehensive error handling with fallback modes and user-friendly messages
7. **Memory efficiency** - Streaming processing and temporary file management for large videos
8. **Export capabilities** - All analysis results can be exported to JSON/CSV formats

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