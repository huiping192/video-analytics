#!/usr/bin/env python3
"""
Configuration Manager - User configuration and parameter templates.
Provides config file support for video analytics CLI tool.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from .logger import get_logger

logger = get_logger(__name__)

@dataclass
class AnalysisConfig:
    """Analysis configuration parameters"""
    # Common settings
    interval: float = 10.0
    output_dir: str = "./output"
    verbose: bool = False
    
    # Chart settings
    chart_config: str = "default"  # default, high_res, compact
    
    # Export settings
    export_json: bool = False
    export_csv: bool = False
    
    # FFmpeg settings
    ffmpeg_timeout: int = 300  # seconds

class ConfigManager:
    """Configuration file manager"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".video-analytics"
        self.config_file = self.config_dir / "config.json"
        self._ensure_config_dir()
        
    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        self.config_dir.mkdir(exist_ok=True)
        
    def save_config(self, config: AnalysisConfig) -> bool:
        """Save configuration to file"""
        try:
            config_dict = asdict(config)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def load_config(self) -> AnalysisConfig:
        """Load configuration from file"""
        if not self.config_file.exists():
            logger.info("No config file found, using defaults")
            return AnalysisConfig()
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # Validate and create config object
            config = AnalysisConfig(**config_dict)
            logger.info(f"Configuration loaded from {self.config_file}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
            return AnalysisConfig()
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update specific configuration values"""
        config = self.load_config()
        
        # Update only valid fields
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
                logger.info(f"Updated config: {key} = {value}")
            else:
                logger.warning(f"Unknown config key: {key}")
        
        return self.save_config(config)
    
    def reset_config(self) -> bool:
        """Reset to default configuration"""
        config = AnalysisConfig()
        return self.save_config(config)
    
    def get_config_path(self) -> str:
        """Get config file path"""
        return str(self.config_file)
    
    def show_config(self) -> Dict[str, Any]:
        """Show current configuration"""
        config = self.load_config()
        return asdict(config)

def get_merged_config(cli_args: Dict[str, Any]) -> AnalysisConfig:
    """Merge CLI arguments with config file settings"""
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # CLI arguments override config file
    for key, value in cli_args.items():
        if value is not None and hasattr(config, key):
            setattr(config, key, value)
    
    return config