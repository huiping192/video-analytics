# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **fully implemented** Python-based command-line video analysis tool with comprehensive CLI architecture.

**CURRENT STATUS: SIMPLIFIED CLI IMPLEMENTATION** - The project features a dramatically simplified CLI interface from 29 commands to 4 core commands, with intelligent defaults and automatic parallel processing.

**Implemented functionality:**
- **Unified analyze command** - Intelligent parallel analysis (video+audio+fps) with smart defaults
- **Multi-file support** - All commands support single or multiple files seamlessly
- **Automatic optimization** - Smart sampling intervals based on file type and duration
- **Simplified cache management** - Single cache command with list/clear/info/remove operations
- **Zero-configuration use** - Works out of the box with optimal settings
- Rich CLI interface with colored output and progress indicators
- Chart generation with automatic chart type selection
- JSON/CSV data export functionality
- FFmpeg dependency checking and validation
- **Performance-optimized by default** - Parallel processing enabled automatically

## CLI Architecture

**Entry Points:**
- Primary: `python -m video_analytics` → `video_analytics/__main__.py` → `video_analytics/cli/main.py`
- Legacy: `video_analytics/main.py` (backwards compatibility)
- Console script: `video-analytics` command (from setup.py)

**CLI Structure (Simplified):**
```
video_analytics/cli/
├── main.py       # Typer app setup with 4 core commands
└── commands.py   # Simplified command implementations (info, analyze, chart, cache)
```

## Development Commands

**Installation and Setup:**
```bash
pip install -e .                 # Development install
pip install -r requirements.txt  # Install dependencies only
```

**Running the Simplified CLI:**
```bash
python -m video_analytics --help                    # Main help (now shows 4 core commands)
python -m video_analytics check                     # Check FFmpeg dependencies
python main.py --help                               # Alternative entry point
video-analytics --help                              # If installed globally
```

**Simplified Analysis Commands (4 Core Commands):**
```bash
# 1. File information (supports multiple files)
python -m video_analytics info <file1> [file2] [file3]...        # Show video metadata for one or more files
python -m video_analytics info <file> --verbose                  # Show detailed information

# 2. Smart analysis (replaces all individual and batch analysis commands)
python -m video_analytics analyze <file1> [file2] [file3]...     # Parallel analysis (video+audio+fps)
python -m video_analytics analyze <file> --type video,audio      # Select specific analysis types
python -m video_analytics analyze <file> --output ./results      # Export results to directory
python -m video_analytics analyze <file> --verbose               # Show detailed progress

# Examples with different input types (all commands support these):
python -m video_analytics analyze /path/to/video.mp4                    # Local file
python -m video_analytics analyze https://example.com/video.mp4         # HTTP URL
python -m video_analytics analyze https://stream.example.com/live.m3u8  # HLS stream
python -m video_analytics analyze file1.mp4 file2.mp4 file3.mp4        # Multiple files (automatic batch)

# 3. Chart generation (supports multiple files)
python -m video_analytics chart <file1> [file2] [file3]...       # Generate charts for one or more files
python -m video_analytics chart <file> --type combined           # Combined analysis chart
python -m video_analytics chart <file> --type summary            # Summary chart
python -m video_analytics chart <file> --type all                # Full report


# 4. Cache management (unified operations)
python -m video_analytics cache list               # List cached downloads
python -m video_analytics cache info               # Show cache statistics
python -m video_analytics cache clear              # Clear all cache
python -m video_analytics cache remove <url>       # Remove specific cached file
```

**Key Improvements:**
- **29 commands → 4 commands**: Massive simplification (-86% complexity)
- **Automatic batch processing**: Multi-file support built into all commands
- **Parallel by default**: No need for separate parallel commands
- **Smart defaults**: Optimal settings automatically chosen
- **Zero configuration**: Works perfectly out of the box

**Simplified Options (3 Core Parameters):**
```bash
--type video,audio,fps   # Select analysis types (default: all)
--output ./path          # Output directory (default: smart location)
--verbose               # Show detailed information (default: concise)
```

**Smart Defaults (No Configuration Needed):**
- **Parallel processing**: Always enabled, auto-optimized
- **Sampling intervals**: Automatically optimized based on file type and duration
- **Batch processing**: Automatic when multiple files provided
- **Download caching**: Intelligent caching for HTTP/HLS streams
- **Output formats**: JSON export available with --output
- **Chart configuration**: Optimal settings automatically applied

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

**No formal tests** - The project currently has no test files. Quality assurance relies on:
- **Validation commands**: Built-in file validation and dependency checking
- **Error handling**: Comprehensive exception handling throughout the codebase
- **Simple mode**: Fallback processing mode when FFmpeg is not available

**Manual testing commands:**
```bash
python -m video_analytics check                     # Verify dependencies
python -m video_analytics validate <test_file>      # Test file processing
python -m video_analytics info <test_file> --simple # Test simple mode
python -m video_analytics performance_test <file>   # Performance and stress testing
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