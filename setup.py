from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read() if fh else ""

setup(
    name="video-analytics",
    version="0.1.0",
    author="Video Analytics Team",
    description="视频分析工具 - 分析视频文件的码率、FPS等关键指标",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "ffmpeg-python>=0.2.0",
        "matplotlib>=3.5.0",
        "typer>=0.9.0",
        "rich>=13.0.0",
        "tqdm>=4.64.0",
    ],
    entry_points={
        "console_scripts": [
            "video-analytics=video_analytics.main:main",
        ],
    },
)