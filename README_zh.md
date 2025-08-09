# Video Analytics 视频分析工具

[English README](README.md)

一个强大的基于Python的命令行视频分析工具，提供视频文件的综合分析功能，包括码率、音频质量和帧率分析。

## 🚀 功能特性

- **视频码率分析**：监控视频码率随时间的变化，支持可配置的采样间隔
- **音频码率分析**：分析音频码率和质量评估
- **FPS分析**：帧率一致性和掉帧检测，针对大型视频文件（3小时以上）进行优化
- **丰富的CLI界面**：美观的彩色输出和进度指示器
- **图表生成**：创建单独的分析图表、组合视图和摘要报告
- **批处理**：同时处理多个文件
- **数据导出**：将分析结果导出为JSON/CSV格式
- **配置管理**：持久化用户配置系统
- **FFmpeg集成**：强大的FFmpeg依赖检查和验证

## 🛠 安装

### 前置要求

- **Python 3.8+**
- **FFmpeg**（完整功能必需）
  - 从 [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) 安装
  - 或使用包管理器：`brew install ffmpeg`（macOS）、`apt install ffmpeg`（Ubuntu）

### 安装工具

```bash
# 克隆仓库
git clone <repository-url>
cd video-analytics

# 开发模式安装
pip install -e .

# 或仅安装依赖
pip install -r requirements.txt
```

### 验证安装

```bash
# 检查FFmpeg和依赖项
python -m video_analytics check

# 显示帮助
python -m video_analytics --help
```

## 🎯 快速开始

### 基本用法

```bash
# 显示视频信息
python -m video_analytics info video.mp4

# 分析视频码率
python -m video_analytics bitrate video.mp4

# 分析音频码率
python -m video_analytics audio video.mp4

# 分析帧率并检测掉帧
python -m video_analytics fps video.mp4

# 生成组合分析图表
python -m video_analytics chart video.mp4
```

### 高级用法

```bash
# 自定义采样间隔（10秒）
python -m video_analytics bitrate video.mp4 --interval 10.0

# 导出分析数据
python -m video_analytics bitrate video.mp4 --json results.json --csv results.csv

# 批处理
python -m video_analytics batch_bitrate video1.mp4 video2.mp4 video3.mp4

# 高分辨率图表
python -m video_analytics chart video.mp4 --config high_res

# 指定输出目录
python -m video_analytics bitrate video.mp4 --output ./analysis_results
```

## 🔧 配置

工具支持持久化用户配置：

```bash
# 显示当前配置
python -m video_analytics config show

# 设置默认采样间隔
python -m video_analytics config set interval 5.0

# 设置默认输出目录
python -m video_analytics config set output_dir ./my_output

# 设置默认图表配置
python -m video_analytics config set chart_config high_res

# 重置为默认值
python -m video_analytics config reset
```

配置存储在 `~/.video-analytics/config.json` 中，可通过命令行参数覆盖。

## 📊 图表类型

- **单独图表**：码率、音频和FPS分析的独立图表
- **组合图表**：单一视图中的所有分析结果
- **摘要图表**：包含关键指标的精简概览
- **批量图表**：为多个文件一次性生成图表

图表配置：
- `default`：标准分辨率和样式
- `high_res`：适合演示的高分辨率图表
- `compact`：快速预览的极简图表

## 🎛 命令参考

### 文件操作
- `info <file>` - 显示视频元数据和文件信息
- `validate <file>` - 验证文件处理能力
- `check` - 验证FFmpeg安装和依赖项

### 分析命令
- `bitrate <file>` - 分析视频码率变化
- `audio <file>` - 分析音频码率和质量
- `fps <file>` - 分析帧率并检测掉帧

### 批处理操作
- `batch_bitrate <files...>` - 批量视频码率分析
- `batch_audio <files...>` - 批量音频分析
- `batch_fps <files...>` - 批量FPS分析
- `batch_chart <files...>` - 批量图表生成

### 可视化
- `chart <file>` - 生成分析图表
  - `--type summary` - 仅摘要图表
  - `--type all` - 完整分析报告

### 配置管理
- `config show` - 显示当前配置
- `config set <key> <value>` - 设置配置值
- `config reset` - 重置为默认配置

### 全局选项
- `--interval <seconds>` - 采样间隔（默认：1.0）
- `--output <directory>` - 结果输出目录
- `--json <file>` - 导出JSON数据
- `--csv <file>` - 导出CSV数据
- `--verbose` - 显示详细信息
- `--config <style>` - 图表配置（default、high_res、compact）

## 🏗 架构

### 入口点
- **主要**：`python -m video_analytics` → `video_analytics/__main__.py`
- **控制台脚本**：`video-analytics` 命令（安装后）
- **旧版**：`video_analytics/main.py`（向后兼容）

### 核心组件
- **CLI层**（`video_analytics.cli`）：基于Typer的命令接口
- **文件处理**（`video_analytics.core`）：FFmpeg集成和元数据处理
- **分析引擎**（`video_analytics.core`）：码率、音频和FPS分析器
- **可视化**（`video_analytics.visualization`）：基于Matplotlib的图表生成
- **配置管理**（`video_analytics.utils.config`）：用户设置管理

### 技术栈
- **Python 3.8+** - 核心语言
- **FFmpeg/ffprobe** - 视频分析后端
- **ffmpeg-python** - Python FFmpeg接口
- **matplotlib** - 图表生成
- **typer** - 现代CLI框架
- **rich** - 增强的终端输出
- **tqdm** - 进度指示器

## 🎥 支持的格式

该工具支持所有FFmpeg可以处理的视频格式，包括：
- MP4、AVI、MKV、MOV、WMV
- WebM、FLV、3GP、M4V
- 以及更多...

## ⚡ 性能

- 针对大型视频文件（3小时以上）进行优化
- 可配置的采样间隔以平衡精度和速度
- 内存高效的流式处理方法
- 并行批处理能力

## 🔍 错误处理

- **依赖检查**：自动FFmpeg可用性验证
- **文件验证**：预处理文件格式和可访问性检查
- **优雅降级**：FFmpeg不可用时的简单模式
- **详细错误消息**：清晰的故障排除反馈

## 🤝 贡献

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

## 📝 许可证

本项目采用MIT许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

## 🐛 故障排除

### 常见问题

**找不到FFmpeg：**
```bash
# 首先安装FFmpeg
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Ubuntu/Debian

# 验证安装
python -m video_analytics check
```

**大文件内存问题：**
```bash
# 增加采样间隔
python -m video_analytics bitrate large_video.mp4 --interval 10.0
```

**权限错误：**
```bash
# 确保输出目录可写
python -m video_analytics bitrate video.mp4 --output ~/Desktop/analysis
```

## 📈 示例

### 分析会议录像

```bash
# 3小时会议视频的完整分析
python -m video_analytics info conference.mp4
python -m video_analytics bitrate conference.mp4 --interval 30.0
python -m video_analytics fps conference.mp4 --json conference_fps.json
python -m video_analytics chart conference.mp4 --config high_res --output ./conference_analysis
```

### 批量处理多个视频

```bash
# 分析当前目录中的所有视频
python -m video_analytics batch_bitrate *.mp4 --output ./batch_results
python -m video_analytics batch_chart *.mp4 --config compact
```

### 导出分析数据

```bash
# 导出综合数据以供外部分析
python -m video_analytics bitrate video.mp4 --json bitrate.json --csv bitrate.csv
python -m video_analytics audio video.mp4 --json audio.json
python -m video_analytics fps video.mp4 --csv fps.csv --verbose
```

---

**注意**: 这是一个专业的视频分析工具，特别适合需要深入了解视频质量和性能特征的用户。工具提供了丰富的配置选项和导出功能，可以满足从简单检查到深度分析的各种需求。