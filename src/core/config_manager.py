"""
Configuration Manager - Handles loading and managing robot configuration.
"""

import os
import yaml
from typing import Dict, Any
from pathlib import Path

from utils.logger import setup_logger


class ConfigManager:
    """Manages robot configuration settings."""
    
    def __init__(self, config_path: str = None):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.logger = setup_logger(__name__)
        
        if config_path is None:
            # Default config path
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "robot_config.yaml"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config = yaml.safe_load(f)
                self.logger.info(f"Configuration loaded from {self.config_path}")
            else:
                self.logger.warning(f"Config file not found at {self.config_path}, using defaults")
                self.config = self._get_default_config()
                self.save_config()
                
            return self.config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.config = self._get_default_config()
            return self.config
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
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
        """Set configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
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
        """Get default configuration.
        
        Returns:
            Default configuration dictionary
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