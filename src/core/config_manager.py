"""
Configuration Management System

Handles loading, saving, and accessing robot configuration parameters
with support for YAML files and default fallback values.
"""

import os
import yaml
from typing import Dict, Any
from pathlib import Path

from utils.logger import setup_logger


class ConfigManager:
    """
    Manages robot configuration settings with YAML persistence.
    
    Provides centralized configuration management with automatic defaults,
    file I/O, and dot-notation access to nested configuration values.
    
    Attributes:
        config_path: Path to the configuration YAML file
        config: Current configuration dictionary
        logger: Logger instance for configuration operations
    """
    
    def __init__(self, config_path: str = "config/robot_config.yaml"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file, defaults to standard location
        """
        self.logger = setup_logger(__name__)
        
        if config_path is None:
            # Default config path
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "robot_config.yaml"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file with fallback to defaults.
        
        Attempts to load from the specified file, falling back to default
        configuration if the file doesn't exist or is invalid.
        
        Returns:
            Complete configuration dictionary
            
        Raises:
            RuntimeError: If both file loading and default generation fail
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
                self.logger.info(f"Configuration loaded from {self.config_path}")
            else:
                self.logger.warning(f"Config file not found at {self.config_path}, using defaults")
                self.config = self._get_default_config()
                self.save_config()
                
            return self.config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.logger.info("Falling back to default configuration")
            self.config = self._get_default_config()
            return self.config
    
    def save_config(self):
        """
        Save current configuration to file.
        
        Creates the configuration directory if it doesn't exist and writes
        the current configuration to the YAML file with proper formatting.
        
        Raises:
            IOError: If file cannot be written
        """
        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
    
    def get(self, key: str, default=None):
        """
        Get configuration value using dot notation.
        
        Supports nested key access using dot notation (e.g., 'robot.name').
        Returns the default value if the key path doesn't exist.
        
        Args:
            key: Configuration key path with dot notation support
            default: Default value if key not found
            
        Returns:
            Configuration value or default if not found
            
        Examples:
            >>> config.get('robot.name')
            'RTK-VL Robot'
            >>> config.get('dynamixel.motors.base_rotation.id')
            1
            >>> config.get('nonexistent.key', 'fallback')
            'fallback'
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation.
        
        Creates nested dictionary structure as needed to accommodate
        the key path. Modifies the in-memory configuration only.
        
        Args:
            key: Configuration key path with dot notation support
            value: Value to set at the specified path
            
        Examples:
            >>> config.set('robot.name', 'New Robot Name')
            >>> config.set('new.nested.value', 42)
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Generate default configuration structure.
        
        Provides comprehensive default settings for all robot subsystems
        including hardware interfaces and operational parameters.
        
        Returns:
            Default configuration dictionary with all required sections
        """
        return {
            'robot': {
                'name': 'RTK-VL Robot',
                'version': '1.0.0',
                'control_frequency': 100  # Hz
            },
            'dynamixel': {
                'enabled': True,
                'port': '/dev/ttyUSB0',
                'baudrate': 1000000,
                'protocol_version': 2.0,
                'motors': {
                    'base_rotation': {'id': 1, 'model': 'XM430-W350'},
                    'shoulder': {'id': 2, 'model': 'XM430-W350'},
                    'elbow': {'id': 3, 'model': 'XM430-W350'},
                    'wrist': {'id': 4, 'model': 'XM430-W350'}
                }
            },
            'lidar': {
                'enabled': True,
                'type': 'rplidar',
                'port': '/dev/ttyUSB1',
                'baudrate': 115200,
                'scan_frequency': 10,  # Hz
                'max_distance': 12.0   # meters
            },
            'camera': {
                'enabled': True,
                'devices': [
                    {
                        'id': 0,
                        'name': 'front_camera',
                        'resolution': [640, 480],
                        'fps': 30
                    }
                ]
            },
            'npu': {
                'enabled': False,
                'type': 'coral',  # 'coral', 'jetson', or 'cpu'
                'model_path': 'models/detection_model.tflite'
            },
            'vision': {
                'object_detection': {
                    'enabled': True,
                    'confidence_threshold': 0.5,
                    'nms_threshold': 0.4
                },
                'face_recognition': {
                    'enabled': False,
                    'database_path': 'data/faces'
                }
            },
            'navigation': {
                'slam': {
                    'enabled': True,
                    'map_resolution': 0.05,  # meters per pixel
                    'map_size': [2000, 2000]  # pixels
                },
                'path_planning': {
                    'algorithm': 'a_star',
                    'safety_margin': 0.3  # meters
                }
            },
            'logging': {
                'level': 'INFO',
                'file': 'data/logs/robot.log',
                'max_size': '10MB',
                'backup_count': 5
            }
        } 