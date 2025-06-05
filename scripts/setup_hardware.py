#!/usr/bin/env python3
"""
Hardware Setup Script
Utility script for setting up and testing robot hardware components.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.config_manager import ConfigManager
from utils.logger import setup_logger


def test_dynamixel(config):
    """Test Dynamixel servo connection."""
    print("Testing Dynamixel servos...")
    
    try:
        from hardware.dynamixel_controller import DynamixelController
        
        controller = DynamixelController(config['dynamixel'])
        controller.initialize()
        
        # Test each motor
        for motor_name in controller.motors.keys():
            print(f"  Testing motor: {motor_name}")
            position = controller.get_position(motor_name)
            print(f"    Current position: {position}")
        
        controller.shutdown()
        print("✓ Dynamixel test passed")
        return True
        
    except Exception as e:
        print(f"✗ Dynamixel test failed: {e}")
        return False


def main():
    """Main setup function."""
    logger = setup_logger(__name__)
    
    print("RTK-VL Robot Hardware Setup")
    print("=" * 40)
    
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    print("Configuration loaded successfully!")
    print(f"Robot name: {config.get('robot', {}).get('name', 'Unknown')}")
    print(f"Version: {config.get('robot', {}).get('version', 'Unknown')}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 