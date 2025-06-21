#!/usr/bin/env python3
"""
Configuration Loader for Hardware Tests

Utility to load robot configuration from YAML files for testing.
"""

import yaml
import os
from typing import Dict, Any, Optional


def load_robot_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load robot configuration from YAML file.
    
    Args:
        config_path: Path to config file. If None, uses default path.
        
    Returns:
        Configuration dictionary
    """
    if config_path is None:
        current_dir = os.path.dirname(__file__)
        config_path = os.path.join(current_dir, '..', 'config', 'robot_config.yaml')
    
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError:
        print(f"⚠️  Config file not found: {config_path}")
        return {}
    except yaml.YAMLError as e:
        print(f"⚠️  Error parsing YAML config: {e}")
        return {}
    except Exception as e:
        print(f"⚠️  Error loading config: {e}")
        return {}


def get_hardware_config(hardware_name: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Get configuration for specific hardware component.
    
    Args:
        hardware_name: Name of hardware component (e.g., 'dynamixel', 'camera', 'lidar')
        config_path: Path to config file. If None, uses default path.
        
    Returns:
        Hardware-specific configuration dictionary
    """
    full_config = load_robot_config(config_path)
    return full_config.get(hardware_name, {})


def create_test_config(hardware_name: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create test configuration by merging default config with overrides.
    
    Args:
        hardware_name: Name of hardware component
        overrides: Dictionary of values to override in the config
        
    Returns:
        Test configuration dictionary
    """
    base_config = get_hardware_config(hardware_name)
    
    if overrides:
        test_config = base_config.copy()
        test_config.update(overrides)
        return test_config
    
    return base_config


if __name__ == '__main__':
    print("Testing configuration loader...")
    
    config = load_robot_config()
    print(f"Full config loaded: {bool(config)}")
    
    for hardware in ['dynamixel', 'lidar', 'camera', 'npu']:
        hw_config = get_hardware_config(hardware)
        print(f"{hardware} config: {bool(hw_config)}")
        if hw_config:
            print(f"  Keys: {list(hw_config.keys())}") 