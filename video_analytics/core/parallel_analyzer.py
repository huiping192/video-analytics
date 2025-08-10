"""
并行分析引擎
实现视频、音频、FPS分析的并行处理，提升长视频分析性能。
"""

import asyncio
import concurrent.futures
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from .file_processor import ProcessedFile, VideoMetadata
from .video_analyzer import VideoBitrateAnalyzer, VideoBitrateAnalysis
from .audio_analyzer import AudioBitrateAnalyzer, AudioBitrateAnalysis
from .fps_analyzer import FPSAnalyzer, FPSAnalysis
from ..utils.logger import get_logger


@dataclass
class CombinedAnalysis:
    """组合分析结果"""
    file_path: str
    duration: float
    analysis_time: datetime
    execution_time: float  # 总执行时间（秒）
    
    # 分析结果
    video_analysis: Optional[VideoBitrateAnalysis] = None
    audio_analysis: Optional[AudioBitrateAnalysis] = None
    fps_analysis: Optional[FPSAnalysis] = None
    
    # 元数据（共享）
    shared_metadata: Optional[VideoMetadata] = None
    
    # 并行统计
    parallel_efficiency: float = 0.0  # 并行效率 (0-1)
    tasks_completed: int = 0
    tasks_failed: int = 0
    
    @property
    def has_video_analysis(self) -> bool:
        return self.video_analysis is not None
    
    @property
    def has_audio_analysis(self) -> bool:
        return self.audio_analysis is not None
    
    @property
    def has_fps_analysis(self) -> bool:
        return self.fps_analysis is not None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        total_tasks = self.tasks_completed + self.tasks_failed
        if total_tasks == 0:
            return 0.0
        return self.tasks_completed / total_tasks


@dataclass
class ParallelConfig:
    """并行配置"""
    max_workers: int = 3  # 最大并发worker数
    enable_video: bool = True
    enable_audio: bool = True
    enable_fps: bool = True
    
    # 采样间隔设置
    video_interval: float = 10.0
    audio_interval: float = 15.0
    fps_interval: float = 20.0
    
    # 超时设置
    task_timeout: float = 3600.0  # 单个任务超时时间（60分钟）
    
    # 内存优化
    enable_metadata_sharing: bool = True
    enable_result_streaming: bool = False


class MetadataCache:
    """元数据缓存管理器"""
    
    def __init__(self):
        self._cache: Dict[str, VideoMetadata] = {}
        self._logger = get_logger(__name__)
    
    def get_or_load(self, processed_file: ProcessedFile) -> VideoMetadata:
        """获取或加载元数据"""
        cache_key = processed_file.file_path
        
        if cache_key in self._cache:
            self._logger.debug(f"Using cached metadata: {cache_key}")
            return self._cache[cache_key]
        
        # 加载新的元数据
        metadata = processed_file.load_metadata()
        self._cache[cache_key] = metadata
        self._logger.debug(f"Cached new metadata: {cache_key}")
        
        return metadata
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._logger.debug("Metadata cache cleared")


class ParallelAnalysisEngine:
    """并行分析引擎"""
    
    def __init__(self, config: ParallelConfig = None):
        self.config = config or ParallelConfig()
        self._metadata_cache = MetadataCache()
        self._logger = get_logger(__name__)
        
        # 初始化分析器
        self._video_analyzer = VideoBitrateAnalyzer(self.config.video_interval)
        self._audio_analyzer = AudioBitrateAnalyzer(self.config.audio_interval)
        self._fps_analyzer = FPSAnalyzer(self.config.fps_interval)
    
    async def analyze_all(self, processed_file: ProcessedFile) -> CombinedAnalysis:
        """执行全面的并行分析"""
        start_time = time.time()
        analysis_time = datetime.now()
        
        self._logger.info(f"Starting parallel analysis: {processed_file.file_path}")
        
        # 预加载并共享元数据
        if self.config.enable_metadata_sharing:
            shared_metadata = self._metadata_cache.get_or_load(processed_file)
            self._logger.debug(f"Shared metadata - duration: {shared_metadata.duration:.1f}s")
        else:
            shared_metadata = None
        
        # 构建任务列表
        tasks = []
        task_names = []
        
        if self.config.enable_video and shared_metadata and shared_metadata.video_codec:
            tasks.append(self._run_video_analysis(processed_file))
            task_names.append("Video Analysis")
        
        if self.config.enable_audio and shared_metadata and shared_metadata.audio_codec:
            tasks.append(self._run_audio_analysis(processed_file))
            task_names.append("Audio Analysis")
        
        if self.config.enable_fps and shared_metadata and shared_metadata.video_codec:
            tasks.append(self._run_fps_analysis(processed_file))
            task_names.append("FPS Analysis")
        
        if not tasks:
            raise ValueError("No executable analysis tasks")
        
        self._logger.info(f"Starting {len(tasks)} parallel tasks: {', '.join(task_names)}")
        
        # 并行执行所有任务
        results = await self._execute_parallel_tasks(tasks, task_names)
        
        # 计算执行时间和效率
        execution_time = time.time() - start_time
        theoretical_sequential_time = self._estimate_sequential_time(tasks)
        parallel_efficiency = min(1.0, theoretical_sequential_time / (execution_time * len(tasks)))
        
        # 统计成功失败任务
        completed_tasks = sum(1 for r in results if r is not None)
        failed_tasks = len(results) - completed_tasks
        
        # 构建组合分析结果
        combined_analysis = CombinedAnalysis(
            file_path=processed_file.file_path,
            duration=shared_metadata.duration if shared_metadata else 0,
            analysis_time=analysis_time,
            execution_time=execution_time,
            shared_metadata=shared_metadata,
            parallel_efficiency=parallel_efficiency,
            tasks_completed=completed_tasks,
            tasks_failed=failed_tasks
        )
        
        # 分配分析结果
        result_index = 0
        if self.config.enable_video and shared_metadata and shared_metadata.video_codec:
            combined_analysis.video_analysis = results[result_index]
            result_index += 1
        
        if self.config.enable_audio and shared_metadata and shared_metadata.audio_codec:
            combined_analysis.audio_analysis = results[result_index]
            result_index += 1
        
        if self.config.enable_fps and shared_metadata and shared_metadata.video_codec:
            combined_analysis.fps_analysis = results[result_index]
            result_index += 1
        
        # 记录性能统计
        self._logger.info(f"Parallel analysis completed - time: {execution_time:.1f}s")
        self._logger.info(f"Successful tasks: {completed_tasks}/{len(tasks)}")
        self._logger.info(f"Parallel efficiency: {parallel_efficiency:.1%}")
        
        return combined_analysis
    
    async def _execute_parallel_tasks(self, tasks: List, task_names: List[str]) -> List[Any]:
        """执行并行任务"""
        try:
            # 使用asyncio.gather进行并行执行，设置超时
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.task_timeout
            )
            
            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self._logger.error(f"{task_names[i]} failed: {result}")
                    processed_results.append(None)
                else:
                    self._logger.info(f"{task_names[i]} completed")
                    processed_results.append(result)
            
            return processed_results
            
        except asyncio.TimeoutError:
            self._logger.error(f"Parallel tasks timeout ({self.config.task_timeout}s)")
            return [None] * len(tasks)
        except Exception as e:
            self._logger.error(f"Parallel execution failed: {e}")
            return [None] * len(tasks)
    
    async def _run_video_analysis(self, processed_file: ProcessedFile) -> Optional[VideoBitrateAnalysis]:
        """执行视频分析任务"""
        loop = asyncio.get_event_loop()
        
        def _analyze():
            return self._video_analyzer.analyze(processed_file)
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                result = await loop.run_in_executor(executor, _analyze)
                return result
        except Exception as e:
            self._logger.error(f"Video analysis task exception: {e}")
            return None
    
    async def _run_audio_analysis(self, processed_file: ProcessedFile) -> Optional[AudioBitrateAnalysis]:
        """执行音频分析任务"""
        loop = asyncio.get_event_loop()
        
        def _analyze():
            return self._audio_analyzer.analyze(processed_file)
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                result = await loop.run_in_executor(executor, _analyze)
                return result
        except Exception as e:
            self._logger.error(f"Audio analysis task exception: {e}")
            return None
    
    async def _run_fps_analysis(self, processed_file: ProcessedFile) -> Optional[FPSAnalysis]:
        """执行FPS分析任务"""
        loop = asyncio.get_event_loop()
        
        def _analyze():
            return self._fps_analyzer.analyze(processed_file)
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                result = await loop.run_in_executor(executor, _analyze)
                return result
        except Exception as e:
            self._logger.error(f"FPS analysis task exception: {e}")
            return None
    
    def _estimate_sequential_time(self, tasks: List) -> float:
        """估算顺序执行时间（用于计算并行效率）"""
        # 基于任务类型和历史数据的简单估算
        base_time_per_task = 60.0  # 基础时间：60秒每任务
        return len(tasks) * base_time_per_task
    
    def analyze_single_type(self, processed_file: ProcessedFile, analysis_type: str) -> Any:
        """执行单种类型的分析（同步方法）"""
        if analysis_type.lower() == 'video':
            return self._video_analyzer.analyze(processed_file)
        elif analysis_type.lower() == 'audio':
            return self._audio_analyzer.analyze(processed_file)
        elif analysis_type.lower() == 'fps':
            return self._fps_analyzer.analyze(processed_file)
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
    
    def clear_cache(self):
        """清空所有缓存"""
        self._metadata_cache.clear()
        self._logger.info("Parallel analysis engine cache cleared")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return {
            "config": {
                "max_workers": self.config.max_workers,
                "video_interval": self.config.video_interval,
                "audio_interval": self.config.audio_interval,
                "fps_interval": self.config.fps_interval,
                "task_timeout": self.config.task_timeout,
                "metadata_sharing": self.config.enable_metadata_sharing
            },
            "cache_size": len(self._metadata_cache._cache),
            "analyzers": {
                "video": type(self._video_analyzer).__name__,
                "audio": type(self._audio_analyzer).__name__,
                "fps": type(self._fps_analyzer).__name__
            }
        }


# 便捷函数
async def analyze_file_parallel(
    processed_file: ProcessedFile,
    config: ParallelConfig = None
) -> CombinedAnalysis:
    """并行分析单个文件的便捷函数"""
    engine = ParallelAnalysisEngine(config)
    return await engine.analyze_all(processed_file)


def create_fast_config(duration: float) -> ParallelConfig:
    """根据视频时长创建快速分析配置"""
    config = ParallelConfig()
    
    if duration > 14400:  # >4小时
        config.video_interval = 60.0
        config.audio_interval = 90.0
        config.fps_interval = 120.0
    elif duration > 7200:  # >2小时
        config.video_interval = 45.0
        config.audio_interval = 60.0
        config.fps_interval = 75.0
    elif duration > 3600:  # >1小时
        config.video_interval = 30.0
        config.audio_interval = 45.0
        config.fps_interval = 60.0
    
    return config


def create_detailed_config() -> ParallelConfig:
    """创建详细分析配置"""
    return ParallelConfig(
        video_interval=5.0,
        audio_interval=10.0,
        fps_interval=15.0,
        task_timeout=3600.0  # 1小时超时
    )


def create_memory_optimized_config() -> ParallelConfig:
    """创建内存优化配置"""
    config = ParallelConfig()
    config.max_workers = 2  # 减少并发worker
    config.enable_metadata_sharing = True
    config.enable_result_streaming = True
    return config