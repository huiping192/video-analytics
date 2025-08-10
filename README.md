# Video Analytics

[中文版 README](README_zh.md)

A powerful Python-based command-line video analysis tool that provides comprehensive analysis of video files including bitrate, audio quality, and frame rate analysis.

## 🚀 Features

- **Video Bitrate Analysis**: Monitor video bitrate variations over time with configurable sampling intervals
- **Audio Bitrate Analysis**: Analyze audio bitrate and quality assessment
- **FPS Analysis**: Frame rate consistency and drop detection, optimized for large video files (3+ hours)
- **⚡ Parallel Analysis**: Concurrent video/audio/FPS analysis for maximum performance
- **Rich CLI Interface**: Beautiful colored output with progress indicators
- **Chart Generation**: Create individual analysis charts, combined views, and summary reports
- **Batch Processing**: Process multiple files simultaneously
- **Performance Profiling**: Built-in performance testing and analysis tools
- **Data Export**: Export analysis results to JSON/CSV formats
- **Configuration Management**: Persistent user configuration system
- **FFmpeg Integration**: Robust FFmpeg dependency checking and validation

## 🛠 Installation

### Prerequisites

- **Python 3.8+**
- **FFmpeg** (required for full functionality)
  - Install from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
  - Or use package managers: `brew install ffmpeg` (macOS), `apt install ffmpeg` (Ubuntu)

### Install the Tool

```bash
# Clone the repository
git clone <repository-url>
cd video-analytics

# Install in development mode
pip install -e .

# Or install dependencies only
pip install -r requirements.txt
```

### Verify Installation

```bash
# Check FFmpeg and dependencies
python -m video_analytics check

# Show help
python -m video_analytics --help
```

## 🎯 Quick Start

### Basic Usage

```bash
# Show video information
python -m video_analytics info video.mp4

# Analyze video bitrate
python -m video_analytics bitrate video.mp4

# Analyze audio bitrate  
python -m video_analytics audio video.mp4

# Analyze frame rate and detect drops
python -m video_analytics fps video.mp4

# Generate combined analysis chart
python -m video_analytics chart video.mp4

# 🆕 Run all analyses in parallel (fastest option)
python -m video_analytics parallel video.mp4
```

### Advanced Usage

```bash
# Custom sampling interval (10 seconds)
python -m video_analytics bitrate video.mp4 --interval 10.0

# Export analysis data
python -m video_analytics bitrate video.mp4 --json results.json --csv results.csv

# Batch processing
python -m video_analytics batch_bitrate video1.mp4 video2.mp4 video3.mp4

# High resolution charts
python -m video_analytics chart video.mp4 --config high_res

# Specify output directory
python -m video_analytics bitrate video.mp4 --output ./analysis_results

# 🆕 Parallel analysis with custom configuration
python -m video_analytics parallel video.mp4 --max-workers 3 --output ./results

# 🆕 Performance testing and profiling
python -m video_analytics performance_test video.mp4
```

## 🔧 Configuration

The tool supports persistent user configuration:

```bash
# Show current configuration
python -m video_analytics config show

# Set default sampling interval
python -m video_analytics config set interval 5.0

# Set default output directory
python -m video_analytics config set output_dir ./my_output

# Set default chart configuration
python -m video_analytics config set chart_config high_res

# Reset to defaults
python -m video_analytics config reset
```

Configuration is stored in `~/.video-analytics/config.json` and can be overridden by command-line arguments.

## 📊 Chart Types

- **Individual Charts**: Separate charts for bitrate, audio, and FPS analysis
- **Combined Charts**: All analysis results in a single view
- **Summary Charts**: Condensed overview with key metrics
- **Batch Charts**: Generate charts for multiple files at once

Chart configurations:
- `default`: Standard resolution and styling
- `high_res`: High-resolution charts suitable for presentations
- `compact`: Minimalist charts for quick overview

## 🎛 Command Reference

### File Operations
- `info <file>` - Display video metadata and file information
- `validate <file>` - Validate file processing capabilities
- `check` - Verify FFmpeg installation and dependencies

### Analysis Commands
- `bitrate <file>` - Analyze video bitrate variations
- `audio <file>` - Analyze audio bitrate and quality
- `fps <file>` - Analyze frame rate and detect dropped frames
- `parallel <file>` - 🆕 Run all analyses concurrently for maximum performance

### Batch Operations
- `batch_bitrate <files...>` - Batch video bitrate analysis
- `batch_audio <files...>` - Batch audio analysis
- `batch_fps <files...>` - Batch FPS analysis
- `batch_chart <files...>` - Batch chart generation
- `batch_parallel <files...>` - 🆕 Batch parallel analysis processing

### Visualization
- `chart <file>` - Generate analysis charts
  - `--type summary` - Summary chart only
  - `--type all` - Full analysis report

### Configuration
- `config show` - Display current configuration
- `config set <key> <value>` - Set configuration value
- `config reset` - Reset to default configuration

### Performance & Testing
- `performance_test <file>` - 🆕 Performance testing and profiling
- `check` - Verify system dependencies and performance

### Global Options
- `--interval <seconds>` - Sampling interval (default: 1.0)
- `--output <directory>` - Output directory for results
- `--json <file>` - Export JSON data
- `--csv <file>` - Export CSV data
- `--verbose` - Show detailed information
- `--config <style>` - Chart configuration (default, high_res, compact)
- `--max-workers <n>` - 🆕 Maximum parallel workers for concurrent analysis
- `--parallel` - 🆕 Enable parallel processing mode

## 🏗 Architecture

### Entry Points
- **Primary**: `python -m video_analytics` → `video_analytics/__main__.py`
- **Console Script**: `video-analytics` command (after installation)
- **Legacy**: `video_analytics/main.py` (backwards compatibility)

### Core Components
- **CLI Layer** (`video_analytics.cli`): Typer-based command interface
- **File Processing** (`video_analytics.core`): FFmpeg integration and metadata handling
- **Analysis Engines** (`video_analytics.core`): Bitrate, audio, and FPS analyzers
- **⚡ Parallel Engine** (`video_analytics.core.parallel_analyzer`): Concurrent analysis coordinator
- **Visualization** (`video_analytics.visualization`): Matplotlib-based chart generation
- **Configuration** (`video_analytics.utils.config`): User settings management

### Technology Stack
- **Python 3.8+** - Core language
- **FFmpeg/ffprobe** - Video analysis backend
- **ffmpeg-python** - Python FFmpeg interface
- **matplotlib** - Chart generation
- **typer** - Modern CLI framework
- **rich** - Enhanced terminal output
- **tqdm** - Progress indicators

## 🎥 Supported Formats

The tool supports all video formats that FFmpeg can process, including:
- MP4, AVI, MKV, MOV, WMV
- WebM, FLV, 3GP, M4V
- And many more...

## ⚡ Performance

- **Parallel Analysis**: Concurrent video/audio/FPS processing for up to 3x speed improvement
- **Smart Configuration**: Auto-optimized settings based on video duration
- **Metadata Sharing**: Efficient memory usage through shared video metadata
- **Optimized for large video files (3+ hours)**
- **Configurable sampling intervals** to balance accuracy and speed
- **Streaming processing approach** for memory efficiency
- **Built-in performance profiling** and testing tools

## 🔍 Error Handling

- **Dependency Checking**: Automatic FFmpeg availability verification
- **File Validation**: Pre-processing file format and accessibility checks
- **Graceful Degradation**: Simple mode when FFmpeg is not available
- **Detailed Error Messages**: Clear feedback for troubleshooting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Troubleshooting

### Common Issues

**FFmpeg not found:**
```bash
# Install FFmpeg first
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Ubuntu/Debian

# Verify installation
python -m video_analytics check
```

**Memory issues with large files:**
```bash
# Increase sampling interval
python -m video_analytics bitrate large_video.mp4 --interval 10.0
```

**Permission errors:**
```bash
# Ensure output directory is writable
python -m video_analytics bitrate video.mp4 --output ~/Desktop/analysis
```

## 📈 Examples

### Analyzing a Conference Recording

```bash
# 🆕 Fast parallel analysis (recommended for large files)
python -m video_analytics parallel conference.mp4 --output ./conference_analysis

# Traditional step-by-step analysis
python -m video_analytics info conference.mp4
python -m video_analytics bitrate conference.mp4 --interval 30.0
python -m video_analytics fps conference.mp4 --json conference_fps.json
python -m video_analytics chart conference.mp4 --config high_res --output ./conference_analysis
```

### Batch Processing Multiple Videos

```bash
# 🆕 Fast batch parallel processing (recommended)
python -m video_analytics batch_parallel *.mp4 --output ./batch_results

# Traditional batch processing
python -m video_analytics batch_bitrate *.mp4 --output ./batch_results
python -m video_analytics batch_chart *.mp4 --config compact
```

### Export Analysis Data

```bash
# Export comprehensive data for external analysis
python -m video_analytics bitrate video.mp4 --json bitrate.json --csv bitrate.csv
python -m video_analytics audio video.mp4 --json audio.json
python -m video_analytics fps video.mp4 --csv fps.csv --verbose
```

## 🚀 Parallel Analysis Guide

The parallel analysis feature provides significant performance improvements for comprehensive video analysis.

### Performance Comparison

| Analysis Method | 3-hour Video | Performance Gain |
|----------------|--------------|------------------|
| Sequential     | ~8-12 minutes | Baseline |
| **Parallel**   | **~3-4 minutes** | **3x faster** |

### Usage Recommendations

**For Large Videos (>2 hours):**
```bash
# Use parallel analysis with optimized intervals
python -m video_analytics parallel large_video.mp4 --max-workers 3
```

**For Detailed Analysis:**
```bash
# High precision parallel analysis
python -m video_analytics parallel video.mp4 --interval 5.0
```

**Performance Testing:**
```bash
# Test and profile your system's performance
python -m video_analytics performance_test video.mp4
```

### Configuration Tips

- **Worker Count**: Default is 3 workers (video, audio, FPS). Adjust based on CPU cores
- **Memory Usage**: Parallel analysis uses ~1.5x memory compared to sequential
- **Optimal Settings**: Tool auto-configures based on video duration
- **Error Resilience**: Individual analysis failures don't affect other concurrent tasks