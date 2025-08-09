from dataclasses import dataclass
from typing import List, Optional
import os
import ffmpeg


@dataclass
class VideoMetadata:
    """视频元数据"""
    file_path: str
    duration: float          # 视频时长(秒)
    file_size: int          # 文件大小(字节)
    format_name: str        # 容器格式
    bit_rate: int           # 总码率(bps)
    
    # 视频流信息
    video_codec: str        # 视频编码
    width: int             # 视频宽度
    height: int            # 视频高度
    fps: float             # 帧率
    video_bitrate: int     # 视频码率(bps)
    
    # 音频流信息
    audio_codec: str       # 音频编码
    channels: int          # 声道数
    sample_rate: int       # 采样率
    audio_bitrate: int     # 音频码率(bps)


class ProcessedFile:
    """处理后的视频文件对象"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.metadata = None
    
    def load_metadata(self) -> VideoMetadata:
        """加载视频元数据"""
        if self.metadata is None:
            self.metadata = self._extract_metadata()
        return self.metadata
    
    def _extract_metadata(self) -> VideoMetadata:
        """提取视频元数据"""
        try:
            probe = ffmpeg.probe(self.file_path)
            format_info = probe['format']
            
            # 查找视频流和音频流
            video_stream = None
            audio_stream = None
            
            for stream in probe['streams']:
                if stream['codec_type'] == 'video' and video_stream is None:
                    video_stream = stream
                elif stream['codec_type'] == 'audio' and audio_stream is None:
                    audio_stream = stream
            
            return VideoMetadata(
                file_path=self.file_path,
                duration=float(format_info['duration']),
                file_size=int(format_info['size']),
                format_name=format_info['format_name'],
                bit_rate=int(format_info.get('bit_rate', 0)),
                
                # 视频流信息
                video_codec=video_stream['codec_name'] if video_stream else '',
                width=video_stream.get('width', 0) if video_stream else 0,
                height=video_stream.get('height', 0) if video_stream else 0,
                fps=self._parse_fps(video_stream) if video_stream else 0.0,
                video_bitrate=int(video_stream.get('bit_rate', 0)) if video_stream else 0,
                
                # 音频流信息
                audio_codec=audio_stream['codec_name'] if audio_stream else '',
                channels=audio_stream.get('channels', 0) if audio_stream else 0,
                sample_rate=audio_stream.get('sample_rate', 0) if audio_stream else 0,
                audio_bitrate=int(audio_stream.get('bit_rate', 0)) if audio_stream else 0,
            )
            
        except ffmpeg.Error as e:
            raise ValueError(f"FFmpeg解析失败: {e}")
    
    def _parse_fps(self, video_stream: dict) -> float:
        """解析帧率"""
        fps_str = video_stream.get('r_frame_rate', '0/1')
        try:
            num, den = fps_str.split('/')
            return float(num) / float(den) if float(den) != 0 else 0.0
        except:
            return 0.0


class FileProcessor:
    """文件处理器"""
    
    def process_input(self, file_path: str) -> ProcessedFile:
        """处理输入文件"""
        # 验证文件
        self._validate_file(file_path)
        
        # 创建处理对象
        processed_file = ProcessedFile(file_path)
        
        # 加载元数据进行验证
        metadata = processed_file.load_metadata()
        
        # 验证视频内容
        self._validate_video_content(metadata)
        
        return processed_file
    
    def _validate_file(self, file_path: str):
        """验证文件基本信息"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"文件无读取权限: {file_path}")
        
        file_size = os.path.getsize(file_path)
        if file_size < 1024:  # 小于1KB
            raise ValueError("文件太小，可能不是有效的视频文件")
    
    def _validate_video_content(self, metadata: VideoMetadata):
        """验证视频内容"""
        if metadata.duration <= 0:
            raise ValueError("无法获取视频时长")
        
        if metadata.width <= 0 or metadata.height <= 0:
            raise ValueError("无法获取视频分辨率")
        
        if not metadata.video_codec:
            raise ValueError("文件不包含视频流")


class FileProcessingError(Exception):
    """文件处理基础异常"""
    pass


class InvalidFormatError(FileProcessingError):
    """不支持的文件格式"""
    pass


class CorruptedFileError(FileProcessingError):
    """文件损坏"""
    pass


def safe_process_file(file_path: str) -> Optional[ProcessedFile]:
    """安全的文件处理"""
    try:
        processor = FileProcessor()
        return processor.process_input(file_path)
        
    except FileNotFoundError:
        print(f"错误: 文件不存在 - {file_path}")
        return None
        
    except PermissionError:
        print(f"错误: 没有文件访问权限 - {file_path}")
        return None
        
    except ValueError as e:
        print(f"错误: 文件格式问题 - {e}")
        return None
        
    except Exception as e:
        print(f"未知错误: {e}")
        return None