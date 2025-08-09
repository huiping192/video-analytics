# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **fully implemented** Python-based command-line video analysis tool. 

**CURRENT STATUS: COMPLETE IMPLEMENTATION** - The project includes comprehensive video analysis capabilities with CLI interface, core analysis engines, and visualization components.

**Implemented functionality:**
- Video bitrate analysis and visualization with configurable sampling intervals
- Audio bitrate analysis and quality assessment  
- FPS (frame rate) analysis and drop detection for large video files (3+ hours)
- Rich CLI interface with colored output and progress indicators
- Chart generation (individual analysis charts, combined views, summary reports)
- Batch processing capabilities for multiple files
- JSON/CSV data export functionality
- FFmpeg dependency checking and validation

## Current Architecture

**Project structure (fully implemented):**

```
video-analytics/
├── CLAUDE.md                    # This file
├── LICENSE                      # MIT license  
├── setup.py                     # Package configuration
├── requirements.txt             # Python dependencies
├── main.py                      # Legacy entry point
├── documents/                   # Chinese technical specifications
│   ├── 00-project-overview.md
│   ├── 01-file-processing.md  
│   ├── 02-video-bitrate-analysis.md
│   ├── 03-audio-bitrate-analysis.md
│   ├── 04-fps-analysis.md
│   └── 05-visualization.md
└── video_analytics/             # Main package
    ├── __init__.py
    ├── __main__.py              # Python -m video_analytics entry
    ├── main.py                  # CLI application entry point
    ├── cli/                     # CLI components
    │   └── __init__.py
    ├── core/                    # Analysis engines
    │   ├── __init__.py
    │   ├── file_processor.py    # Video file processing and metadata
    │   ├── simple_processor.py  # Lightweight processing without FFmpeg
    │   ├── video_analyzer.py          # Video bitrate analysis
    │   ├── audio_analyzer.py          # Audio bitrate analysis  
    │   └── fps_analyzer.py      # FPS and frame drop analysis
    ├── visualization/           # Chart generation
    │   ├── __init__.py
    │   └── chart_generator.py   # Matplotlib-based chart generation
    ├── utils/                   # Utilities
    │   └── __init__.py
    └── tests/                   # Test directory (empty)
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

### 1. File Processing (`video_analytics.core`)
- **FileProcessor**: Main video file processor using FFmpeg
- **SimpleProcessor**: Lightweight processor that works without FFmpeg
- **VideoMetadata**: Dataclass for video file metadata
- **ProcessedFile**: Abstraction for processed video files

### 2. Analysis Engines (`video_analytics.core`)
- **VideoBitrateAnalyzer**: Analyzes video bitrate variations over time
- **AudioBitrateAnalyzer**: Analyzes audio bitrate and quality assessment
- **FPSAnalyzer**: Analyzes frame rate consistency and drop detection
- All analyzers support configurable sampling intervals and export to JSON/CSV

### 3. Visualization (`video_analytics.visualization`)
- **ChartGenerator**: Matplotlib-based chart generation
- **ChartConfig**: Configuration for chart styling and output
- **ChartStyles**: Predefined styles (default, high_res, compact)
- Supports individual analysis charts, combined views, and summary reports

### 4. CLI Interface (`video_analytics.main`)
- Rich CLI with typer framework and colored output
- Comprehensive command structure with help system
- Progress indication and error handling
- Batch processing capabilities for multiple files

## Key Implementation Notes

When working with this project:

1. **FFmpeg dependency** - Always check FFmpeg availability first with `python -m video_analytics check`
2. **Large file handling** - Optimized for 3+ hour video files with configurable sampling intervals
3. **Chinese documentation** - Technical specs in `documents/` provide detailed implementation guidance
4. **Error handling** - Robust error handling with informative messages and fallback modes
5. **Memory efficiency** - Streaming processing approach for large video files
6. **Export capabilities** - All analysis results can be exported to JSON/CSV formats

## Testing and Quality Assurance

Currently the project has:
- **Basic structure**: Empty `tests/` directory ready for test implementation
- **Validation commands**: Built-in file validation and dependency checking
- **Error handling**: Comprehensive exception handling throughout the codebase
- **Simple mode**: Fallback processing mode when FFmpeg is not available

**Recommended testing approach:**
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