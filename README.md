# Video Chart Generator

[中文版 README](README_zh.md)

**Professional video analysis chart generator** - Generate high-quality charts for video bitrate, audio quality, and frame rate analysis with a single command.

**Ultra-simplified design:** From 29 complex commands to 1 command, zero configuration, intelligent automation.

---

## 🚀 Key Features

### **🎯 One Command Does Everything**  
- **Single command** - No complex parameter choices, automatically completes analysis + chart generation
- **Smart defaults** - Auto-selects optimal analysis and chart types based on video duration  
- **Zero configuration** - Works out of the box, no setup or learning curve required
- **Batch processing** - Supports multiple files and wildcards like `*.mp4`

### **📊 Professional Chart Visualization**
- **Intelligent chart selection** - Detailed charts for short videos, optimized charts for longer ones
- **Parallel analysis** - Simultaneously analyzes video bitrate, audio quality, frame rate (3x speed boost)
- **High-quality output** - Professional chart layouts and visual effects
- **Multiple input sources** - Supports local files, HTTP URLs, HLS streams

### **🔍 Perfect Ecosystem Integration**
- **Complements ffprobe** - ffprobe shows information, we generate professional charts
- **Focused core value** - No wheel reinventing, specialized in chart visualization  
- **Lightweight & efficient** - 90% code reduction, fewer bugs, easier maintenance

---

## 🛠 Installation

### Prerequisites

- **Python 3.8+**
- **FFmpeg** (required for functionality)
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
# Show help (automatically checks FFmpeg dependencies)
python -m video_analytics --help
```

---

## 🎯 Usage

### **🚀 Ultra-Simple Usage (One Command Does Everything)**

```bash
# Basic usage - auto analysis + auto chart generation
python -m video_analytics video.mp4

# Batch processing multiple files  
python -m video_analytics video1.mp4 video2.mp4 video3.mp4
python -m video_analytics *.mp4

# Support HTTP URLs and HLS streams
python -m video_analytics https://example.com/video.mp4
python -m video_analytics https://stream.example.com/playlist.m3u8
```

### **⚡ Optional Parameters (Only 2)**

```bash
# Specify output directory
python -m video_analytics video.mp4 --output ./my-charts

# Verbose mode (show analysis process and metrics)
python -m video_analytics video.mp4 --verbose

# Combine both options
python -m video_analytics video.mp4 --output ./charts --verbose
```

### **🧠 Smart Behavior Examples**

```bash
# Short videos (< 5 minutes) → Auto-generate detailed charts
python -m video_analytics short_clip.mp4        

# Long videos (≥ 5 minutes) → Auto-generate optimized charts  
python -m video_analytics movie.mp4             

# Multiple files → Auto-create subdirectory structure
python -m video_analytics file1.mp4 file2.mp4  
# Output: ./charts/file1/... and ./charts/file2/...
```

---

## 📊 Intelligent Chart Generation

**Fully automated** - Automatically selects optimal chart types and configurations based on video characteristics!

### **🎯 Automatic Chart Selection**
- **Short videos (< 5 minutes)**: Detailed enhanced dashboard charts - shows complete info panels and precise analysis
- **Long videos (≥ 5 minutes)**: Standard combined charts - optimized three-in-one view suitable for lengthy videos
- **Multiple file processing**: Automatically creates independent subdirectories to avoid filename conflicts

### **🎨 Chart Features**
- **Professional layouts**: Adaptive grid layouts with optimal information density
- **High-quality output**: PNG format, 150 DPI, suitable for reports and presentations
- **Smart color schemes**: Professional color palettes supporting both dark and light themes
- **Complete information**: File info, encoding parameters, quality assessment, performance metrics

### **📁 Output Organization**
```
./charts/                    # Single file output
├── enhanced_dashboard_*.png  # Short video detailed charts
└── combined_analysis_*.png   # Standard combined charts

./charts/                    # Multiple file output
├── video1/
│   └── enhanced_dashboard_*.png
└── video2/
    └── combined_analysis_*.png
```

---

## 🎛 Command Reference

### **🎯 Single Command - Ultra-Simplified Design**

```bash
python -m video_analytics <file1> [file2] [file3]... [OPTIONS]
```

**Function**: Automatic analysis + automatic professional chart generation

**Input Support**:
- Local files: `video.mp4`, `/path/to/video.mp4`
- HTTP URLs: `https://example.com/video.mp4`  
- HLS streams: `https://stream.example.com/playlist.m3u8`
- Wildcards: `*.mp4`, `video*.mp4`
- Multiple files: `video1.mp4 video2.mp4 video3.mp4`

**Parameters** (only 2):
- `--output PATH` or `-o PATH` - Specify output directory (default: `./charts`)
- `--verbose` or `-v` - Show detailed analysis process and metrics

### **🧠 Intelligent Automation Behavior**

✅ **Analysis types**: Automatically enables video + audio + fps triple analysis  
✅ **Sampling optimization**: Auto-optimizes sampling intervals based on video duration  
✅ **Chart selection**: Short videos→detailed charts, long videos→combined charts  
✅ **Parallel processing**: Automatically uses optimal number of worker threads  
✅ **Cache management**: HTTP/HLS streams automatically cached to avoid repeated downloads  
✅ **Directory organization**: Multiple files automatically create subdirectory structure  
✅ **Error handling**: Intelligently skips failed files, continues processing others

---

## 🔧 What Makes This Tool Special

### **🎯 Focused Purpose**
- **Not another video analyzer** - ffprobe already does that perfectly
- **Specialized in visualization** - Generate professional charts that ffprobe can't
- **Perfect complement** - Use ffprobe for info, use this for charts

### **🚀 Zero Learning Curve**
- **One command to remember**: `python -m video_analytics <files>`
- **No parameter confusion** - Everything is intelligently automated
- **Works immediately** - No configuration files or setup needed

### **📊 Professional Results**
- **Publication-ready charts** - High-resolution, professionally styled
- **Comprehensive analysis** - Video bitrate, audio quality, frame rate in one chart  
- **Smart layouts** - Automatically optimized for different video characteristics

---

## 🛠 Technical Details

### **System Requirements**
- **Python 3.8+** - Required for modern type hints and dataclass support
- **FFmpeg** - Essential for video analysis functionality
- **4GB+ RAM** - Recommended for processing videos longer than 3 hours
- **Adequate disk space** - For chart generation and temporary files

### **Supported Input Formats**
- **Video files**: MP4, AVI, MKV, MOV, WMV, FLV, and more (anything ffprobe supports)
- **HTTP URLs**: Direct links to video files
- **HLS streams**: M3U8 playlist URLs for live streams
- **Batch processing**: Multiple files, wildcards, mixed local/remote sources

### **Performance Features**
- **Parallel processing** - Video, audio, and FPS analysis run simultaneously
- **Smart sampling** - Automatically adjusts analysis intervals based on video length
- **Memory optimization** - Efficient processing of large video files
- **Caching system** - Downloaded streams cached for repeated analysis

---

## 📈 Example Outputs

The tool generates different chart types based on your video:

- **Short videos (< 5 min)**: Enhanced dashboard with detailed panels
- **Medium videos (5-60 min)**: Combined analysis chart with three subplots  
- **Long videos (> 60 min)**: Memory-optimized charts with smart sampling

All charts include:
- Video bitrate analysis over time
- Audio quality assessment and bitrate
- Frame rate consistency and drop detection
- File information and encoding details
- Quality metrics and recommendations

---

## 💡 Quick Tips

### **Best Practices**
```bash
# For single video analysis
python -m video_analytics video.mp4

# For project-wide batch analysis
python -m video_analytics /path/to/project/*.mp4 --output ./project-analysis

# For detailed troubleshooting
python -m video_analytics problematic_video.mp4 --verbose
```

### **Common Use Cases**
- **Quality assurance** - Analyze encoded videos for bitrate consistency
- **Stream analysis** - Monitor live streams for quality issues
- **Batch processing** - Analyze entire video libraries
- **Performance debugging** - Identify frame drops and quality issues

---

## 🤝 Contributing

This tool focuses on doing one thing exceptionally well: generating professional video analysis charts. 

If you have suggestions for chart improvements, visualization enhancements, or smart automation features, contributions are welcome!

---

## 📄 License

[License information here]

---

## 🔗 Related Tools

- **ffprobe** - For detailed video information and metadata
- **ffmpeg** - For video processing and conversion  
- **This tool** - For professional chart visualization of video analysis

**Perfect workflow**: Use ffprobe for info → Use this tool for charts → Use ffmpeg for processing