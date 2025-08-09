"""
Download Cache System - Manages cached downloads for HLS streams and remote URLs.
Provides intelligent caching, validation, and cleanup mechanisms.
"""

import os
import json
import hashlib
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry metadata"""
    url: str
    local_path: str
    file_size: int
    download_time: float
    last_accessed: float
    duration: float = 0.0
    format_name: str = ""
    is_valid: bool = True


class DownloadCache:
    """Manages download cache for HLS streams and remote files"""
    
    def __init__(self, cache_dir: Optional[str] = None, max_size_gb: float = 10.0):
        """
        Initialize download cache
        
        Args:
            cache_dir: Cache directory path (default: ~/.video-analytics-cache)
            max_size_gb: Maximum cache size in GB
        """
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.video-analytics-cache")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        
        # Load existing cache metadata
        self.entries: Dict[str, CacheEntry] = self._load_metadata()
        
        # Clean up invalid entries on init
        self._cleanup_invalid_entries()
    
    def get_cache_key(self, url: str) -> str:
        """Generate cache key from URL"""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    def get_cached_file(self, url: str) -> Optional[str]:
        """
        Get cached file path if exists and valid
        
        Args:
            url: Original URL
            
        Returns:
            Local file path if cached and valid, None otherwise
        """
        cache_key = self.get_cache_key(url)
        
        if cache_key not in self.entries:
            return None
        
        entry = self.entries[cache_key]
        
        # Check if file exists and is valid
        if not os.path.exists(entry.local_path):
            logger.info(f"Cache file missing, removing entry: {cache_key}")
            self._remove_entry(cache_key)
            return None
        
        # Check file integrity
        current_size = os.path.getsize(entry.local_path)
        if current_size != entry.file_size:
            logger.warning(f"Cache file size mismatch, removing entry: {cache_key}")
            self._remove_entry(cache_key)
            return None
        
        # Update last accessed time
        entry.last_accessed = time.time()
        self._save_metadata()
        
        logger.info(f"Using cached file for {url[:50]}...")
        return entry.local_path
    
    def add_to_cache(self, url: str, file_path: str, duration: float = 0.0, 
                     format_name: str = "") -> bool:
        """
        Add file to cache
        
        Args:
            url: Original URL
            file_path: Local file path to cache
            duration: Video duration in seconds
            format_name: Video format
            
        Returns:
            True if successfully added to cache
        """
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return False
        
        try:
            cache_key = self.get_cache_key(url)
            file_size = os.path.getsize(file_path)
            
            # Create cached filename
            file_ext = os.path.splitext(file_path)[1] or '.mp4'
            cached_filename = f"{cache_key}{file_ext}"
            cached_path = self.cache_dir / cached_filename
            
            # Copy file to cache directory (if not already there)
            if not cached_path.exists():
                shutil.copy2(file_path, cached_path)
                logger.info(f"Added to cache: {cached_path} ({file_size/1024/1024:.1f} MB)")
            
            # Create cache entry
            entry = CacheEntry(
                url=url,
                local_path=str(cached_path),
                file_size=file_size,
                download_time=time.time(),
                last_accessed=time.time(),
                duration=duration,
                format_name=format_name,
                is_valid=True
            )
            
            self.entries[cache_key] = entry
            self._save_metadata()
            
            # Clean up cache if needed
            self._enforce_cache_limits()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add file to cache: {e}")
            return False
    
    def remove_from_cache(self, url: str) -> bool:
        """Remove file from cache"""
        cache_key = self.get_cache_key(url)
        return self._remove_entry(cache_key)
    
    def clear_cache(self) -> Tuple[int, int]:
        """
        Clear all cache entries
        
        Returns:
            (files_removed, total_size_freed_mb)
        """
        files_removed = 0
        total_size = 0
        
        for entry in list(self.entries.values()):
            if os.path.exists(entry.local_path):
                total_size += entry.file_size
                os.remove(entry.local_path)
                files_removed += 1
        
        self.entries.clear()
        self._save_metadata()
        
        total_size_mb = total_size // (1024 * 1024)
        logger.info(f"Cache cleared: {files_removed} files, {total_size_mb} MB freed")
        
        return files_removed, total_size_mb
    
    def get_cache_info(self) -> Dict:
        """Get cache statistics"""
        total_files = len(self.entries)
        total_size = sum(entry.file_size for entry in self.entries.values())
        
        # Check disk usage
        if total_files > 0:
            valid_files = sum(1 for entry in self.entries.values() 
                            if os.path.exists(entry.local_path))
        else:
            valid_files = 0
        
        return {
            'cache_dir': str(self.cache_dir),
            'total_files': total_files,
            'valid_files': valid_files,
            'total_size_mb': total_size // (1024 * 1024),
            'max_size_gb': self.max_size_bytes // (1024 * 1024 * 1024),
            'usage_percent': (total_size / self.max_size_bytes * 100) if self.max_size_bytes > 0 else 0
        }
    
    def list_cached_files(self) -> List[Dict]:
        """List all cached files with metadata"""
        cached_files = []
        
        for cache_key, entry in self.entries.items():
            file_exists = os.path.exists(entry.local_path)
            
            cached_files.append({
                'cache_key': cache_key,
                'url': entry.url[:50] + '...' if len(entry.url) > 50 else entry.url,
                'local_path': entry.local_path,
                'size_mb': entry.file_size // (1024 * 1024),
                'duration_min': entry.duration / 60 if entry.duration > 0 else 0,
                'format': entry.format_name,
                'download_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(entry.download_time)),
                'last_accessed': time.strftime('%Y-%m-%d %H:%M', time.localtime(entry.last_accessed)),
                'exists': file_exists,
                'valid': entry.is_valid and file_exists
            })
        
        # Sort by last accessed (most recent first)
        cached_files.sort(key=lambda x: x['last_accessed'], reverse=True)
        return cached_files
    
    def _load_metadata(self) -> Dict[str, CacheEntry]:
        """Load cache metadata from disk"""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            entries = {}
            for cache_key, entry_data in data.items():
                entries[cache_key] = CacheEntry(**entry_data)
            
            logger.debug(f"Loaded {len(entries)} cache entries")
            return entries
            
        except Exception as e:
            logger.error(f"Failed to load cache metadata: {e}")
            return {}
    
    def _save_metadata(self):
        """Save cache metadata to disk"""
        try:
            data = {}
            for cache_key, entry in self.entries.items():
                data[cache_key] = asdict(entry)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")
    
    def _remove_entry(self, cache_key: str) -> bool:
        """Remove cache entry and associated file"""
        if cache_key not in self.entries:
            return False
        
        entry = self.entries[cache_key]
        
        # Remove file if exists
        if os.path.exists(entry.local_path):
            try:
                os.remove(entry.local_path)
                logger.info(f"Removed cached file: {entry.local_path}")
            except Exception as e:
                logger.error(f"Failed to remove cached file: {e}")
        
        # Remove from metadata
        del self.entries[cache_key]
        self._save_metadata()
        
        return True
    
    def _cleanup_invalid_entries(self):
        """Remove cache entries for missing files"""
        invalid_keys = []
        
        for cache_key, entry in self.entries.items():
            if not os.path.exists(entry.local_path):
                invalid_keys.append(cache_key)
        
        for cache_key in invalid_keys:
            logger.info(f"Removing invalid cache entry: {cache_key}")
            del self.entries[cache_key]
        
        if invalid_keys:
            self._save_metadata()
            logger.info(f"Cleaned up {len(invalid_keys)} invalid cache entries")
    
    def _enforce_cache_limits(self):
        """Enforce cache size limits by removing oldest files"""
        total_size = sum(entry.file_size for entry in self.entries.values())
        
        if total_size <= self.max_size_bytes:
            return
        
        logger.info(f"Cache size ({total_size//1024//1024} MB) exceeds limit, cleaning up...")
        
        # Sort by last accessed time (oldest first)
        sorted_entries = sorted(
            self.entries.items(), 
            key=lambda x: x[1].last_accessed
        )
        
        removed_count = 0
        freed_size = 0
        
        for cache_key, entry in sorted_entries:
            if total_size - freed_size <= self.max_size_bytes:
                break
            
            if self._remove_entry(cache_key):
                freed_size += entry.file_size
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cache cleanup: removed {removed_count} files, freed {freed_size//1024//1024} MB")


# Global cache instance
_global_cache: Optional[DownloadCache] = None


def get_download_cache() -> DownloadCache:
    """Get global download cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = DownloadCache()
    return _global_cache