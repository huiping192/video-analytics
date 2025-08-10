# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **professional video chart generator** - specialized tool for creating high-quality video analysis charts.

**CURRENT STATUS: ULTRA-SIMPLIFIED CLI** - Dramatically simplified from 29 commands to 1 single command, with intelligent defaults and zero configuration required.

**Core functionality:**
- **Single command operation** - One command does everything: analyze + generate charts
- **Smart defaults** - Auto-detects best settings based on video characteristics
- **Universal input support** - Local files, HTTP URLs, HLS streams
- **Intelligent chart selection** - Detailed charts for short videos, combined for longer ones
- **Automatic parallel processing** - Video + audio + fps analysis in parallel
- **Zero configuration** - Works perfectly out of the box
- **Professional visualization** - High-quality charts with optimal layouts
- **Batch processing** - Multiple files processed automatically

## CLI Architecture (Ultra-Simplified)

**Entry Point:** `python -m video_analytics <files...>` - Single command, zero configuration

**CLI Structure:**
```
video_analytics/cli/
├── main.py       # Single command registration (~25 lines)
└── commands.py   # One core function (~200 lines, was 1992 lines)
```

**Core philosophy:** Complement ffprobe - ffprobe shows info, we generate professional charts.

## Development Commands

**Installation and Setup:**
```bash
pip install -e .                 # Development install
pip install -r requirements.txt  # Install dependencies only
```

**Running the Ultra-Simplified CLI:**
```bash
python -m video_analytics --help                    # Show help (single command)
python -m video_analytics <file1> [file2]...        # Generate charts (default)
video-analytics <file1> [file2]...                  # If installed globally
```

**Single Command Usage:**
```bash
# Basic usage - auto analysis + auto charts
python -m video_analytics video.mp4                              # Local file
python -m video_analytics https://example.com/video.mp4          # HTTP URL  
python -m video_analytics https://stream.example.com/live.m3u8   # HLS stream
python -m video_analytics file1.mp4 file2.mp4 file3.mp4         # Multiple files (auto batch)

# Optional parameters (only 2)
python -m video_analytics video.mp4 --output ./my-charts         # Custom output directory
python -m video_analytics video.mp4 --verbose                    # Detailed progress

# Examples of smart behavior
python -m video_analytics short_clip.mp4        # → Detailed charts (< 5 min)
python -m video_analytics movie.mp4             # → Combined charts (> 5 min) 
python -m video_analytics *.mp4                 # → Batch process all MP4s
```

**Radical Simplification:**
- **29 commands → 1 command**: Ultimate simplification (-97% complexity reduction)
- **1992 lines → 199 lines**: 90% code reduction in commands.py
- **Zero learning curve**: One command does everything
- **Intelligent automation**: Best practices built-in as defaults

**Ultra-Simple Options (Only 2):**
```bash
--output ./path          # Output directory (default: ./charts)
--verbose               # Show detailed information (default: concise)
```

**Completely Automated Behavior:**
- **Analysis type selection**: Always runs video+audio+fps (best charts)
- **Chart type selection**: Auto-selected based on video duration
- **Parallel processing**: Always enabled with optimal worker counts
- **Sampling intervals**: Auto-optimized for video length and memory
- **Batch processing**: Automatic for multiple files
- **Download caching**: Transparent for HTTP/HLS streams
- **Directory structure**: Smart organization for multi-file processing

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
- **ParallelAnalysisEngine**: Concurrent execution of multiple analysis types
- **CombinedAnalysis**: Unified results container for parallel analysis
- **MetadataCache**: Shared metadata optimization for concurrent tasks
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

### 7. Parallel Processing (`video_analytics.core.parallel_analyzer`)
- **ParallelConfig**: Configuration for concurrent analysis (worker counts, timeouts, intervals)
- **Async/await pattern**: Using asyncio with ThreadPoolExecutor for CPU-bound tasks
- **Performance optimization**: Metadata sharing, configurable sampling intervals
- **Error resilience**: Individual task failure handling with comprehensive logging
- **Smart configuration**: Auto-optimization for different video durations

## Key Implementation Notes

When working with the simplified CLI:

1. **FFmpeg dependency** - Always check FFmpeg availability first with `python -m video_analytics check`
2. **Universal input support** - All commands seamlessly support local files, HTTP URLs, and HLS streams
3. **Automatic optimization** - Smart sampling intervals based on file type and duration (no manual tuning needed)
4. **Intelligent caching** - Automatic download caching for HTTP/HLS streams
5. **Default parallel processing** - All analysis uses optimized parallel execution automatically
6. **Multi-file processing** - Built-in batch processing when multiple files are provided
7. **Zero configuration** - Works optimally out of the box without any setup
8. **Smart error handling** - Comprehensive error handling with user-friendly messages
9. **Memory efficient** - Streaming processing for large videos with automatic optimization
10. **Export capabilities** - JSON export available via --output directory

## Development Workflow

**Simplified testing** - With the ultra-simplified CLI, testing is now straightforward:
- **Single command testing**: Only one main function to test
- **Built-in validation**: Automatic dependency checking and error handling  
- **Real-world testing**: Test with actual video files to verify end-to-end functionality

**Testing commands:**
```bash
python -m video_analytics --help                    # Verify CLI works
python -m video_analytics test_video2.mp4           # Test single file processing
python -m video_analytics test_video2.mp4 --verbose # Test with detailed output
python -m video_analytics *.mp4 --output ./test     # Test batch processing
```

## Critical Dependencies and Requirements

- **FFmpeg**: Essential for full functionality - install from https://ffmpeg.org/download.html
- **Python 3.8+**: Required for modern type hints and dataclass support
- **System memory**: Sufficient RAM for processing large video files (recommended 4GB+ for 3+ hour videos)
- **Disk space**: Chart generation and export files require adequate storage

**Dependency validation:**
- FFmpeg automatically checked at startup - no separate command needed
- Clear error messages with installation instructions if FFmpeg missing
- Python package dependencies handled via requirements.txt

## Parallel Analysis Architecture

The parallel analysis engine is designed for performance optimization of long video processing:

**Core Components:**
- **ParallelAnalysisEngine**: Main coordinator for concurrent analysis tasks
- **CombinedAnalysis**: Results container with performance metrics
- **MetadataCache**: Shared metadata to avoid redundant ffprobe calls
- **ParallelConfig**: Fine-grained configuration for optimization

**Performance Features:**
```python
# Smart configuration based on video duration
config = create_fast_config(duration=7200)  # 2-hour video optimized settings
config = create_detailed_config()           # High-precision analysis
config = create_memory_optimized_config()   # Low-memory environments

# Manual configuration example
config = ParallelConfig(
    max_workers=3,          # Concurrent tasks
    video_interval=30.0,    # Video bitrate sampling
    audio_interval=45.0,    # Audio bitrate sampling  
    fps_interval=60.0,      # FPS analysis sampling
    task_timeout=3600.0     # 1-hour timeout per task
)
```

**Best Practices:**
1. **Memory management** - Enable metadata sharing for multiple analysis types
2. **Performance monitoring** - Use parallel_efficiency and success_rate metrics
3. **Error handling** - Individual task failures don't affect other analyses
4. **Timeout configuration** - Adjust task_timeout based on video length and system specs