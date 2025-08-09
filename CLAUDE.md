# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **design-phase** Python-based command-line video analysis tool project. 

**CURRENT STATUS: NO CODE IMPLEMENTED YET** - Only documentation and technical specifications exist in the `documents/` directory (written in Chinese).

**Planned functionality:**
- Video bitrate analysis and visualization
- Audio bitrate analysis and visualization  
- FPS (frame rate) analysis and drop detection for large video files (3+ hours)

## Current Architecture

**WARNING: The project structure below does NOT exist yet - it's a planned design**

```
video_analytics/          # ❌ NOT CREATED
├── cli/                 # ❌ NOT CREATED  
├── core/                # ❌ NOT CREATED
├── visualization/       # ❌ NOT CREATED
└── utils/               # ❌ NOT CREATED
```

**What actually exists:**
```
video-analytics/
├── CLAUDE.md           # This file
├── LICENSE             # MIT license
└── documents/          # Chinese technical specs
    ├── 00-project-overview.md
    ├── 01-file-processing.md  
    ├── 02-video-bitrate-analysis.md
    ├── 03-audio-bitrate-analysis.md
    ├── 04-fps-analysis.md
    ├── 05-visualization.md
    └── 06-cli-interface.md
```

## Development Commands

**CRITICAL: No development commands exist yet** because no code has been written.

When starting implementation, you should:

1. **First create basic project structure:**
   ```bash
   mkdir -p video_analytics/{cli,core,visualization,utils,tests}
   touch video_analytics/__init__.py
   ```

2. **Create essential project files:**
   ```bash
   # Create requirements.txt
   # Create setup.py or pyproject.toml  
   # Create basic test structure
   ```

3. **Planned development commands** (when implemented):
   ```bash
   pip install -e .              # Development install
   python -m video_analytics     # Run CLI
   pytest tests/                 # Run tests  
   ruff check video_analytics/   # Linting
   mypy video_analytics/         # Type checking
   ```

## Technology Stack (Planned)

- **Python 3.8+** - Main language
- **FFmpeg/ffprobe** - Video analysis engine  
- **ffmpeg-python** - Python FFmpeg interface
- **matplotlib** - Chart generation
- **typer** - CLI framework
- **rich** - CLI enhancement

## Key Implementation Notes

When building this project:

1. **Start with MVP** - Don't implement everything at once
2. **FFmpeg dependency** - Ensure proper FFmpeg installation handling
3. **Large file handling** - Design for 3+ hour video files from day one
4. **Chinese documentation** - Technical specs are in Chinese, understand them first
5. **CLI-first approach** - Build command-line interface as primary interaction method

## Critical Warnings

- **Don't assume any code exists** - Start from scratch
- **Check Chinese docs first** - All detailed specs are in `documents/` directory  
- **FFmpeg is essential** - Nothing will work without proper FFmpeg setup
- **Large file optimization** - Memory management is critical for 3+ hour videos