"""
简化的文件处理器 - 用于测试基础功能
不依赖FFmpeg，主要验证代码结构是否正确
"""

import os
from .file_processor import VideoMetadata, ProcessedFile


class SimpleProcessedFile(ProcessedFile):
    """简化的处理文件对象 - 用于测试"""
    
    def _extract_metadata(self) -> VideoMetadata:
        """模拟提取视频元数据"""
        file_size = os.path.getsize(self.file_path)
        
        # 返回模拟的元数据
        return VideoMetadata(
            file_path=self.file_path,
            duration=120.0,  # 模拟2分钟视频
            file_size=file_size,
            format_name="mp4",
            bit_rate=2000000,  # 2Mbps
            
            # 视频流信息
            video_codec="h264",
            width=1920,
            height=1080,
            fps=30.0,
            video_bitrate=1800000,
            
            # 音频流信息
            audio_codec="aac",
            channels=2,
            sample_rate=48000,
            audio_bitrate=200000,
        )