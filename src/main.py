#!/usr/bin/env python3
"""
RTK-VL Robot Main Application
Entry point for the robotics system integrating Dynamixels, LiDAR, NPU, and cameras.
"""

import sys
import time
import signal
import logging
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

from core.robot_controller import RobotController
from core.config_manager import ConfigManager
from utils.logger import setup_logger


class RobotApplication:
    """Main robot application class."""
    
    def __init__(self):
        """Initialize the robot application."""
        self.logger = setup_logger(__name__)
        self.config_manager = ConfigManager()
        self.robot_controller = None
        self.running = False
        
    def initialize(self):
        """Initialize all robot systems."""
        try:
            self.logger.info("Initializing RTK-VL Robot System...")
            
            # Load configuration
            config = self.config_manager.load_config()
            
            # Initialize robot controller
            self.robot_controller = RobotController(config)
            
            # Initialize hardware components
            self.robot_controller.initialize_hardware()
            
            self.logger.info("Robot system initialized successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize robot system: {e}")
            return False
    
    def run(self):
        """Main application loop."""
        if not self.initialize():
            return 1
            
        self.running = True
        self.logger.info("Starting robot main loop...")
        
        try:
            while self.running:
                # Main control loop
                self.robot_controller.update()
                time.sleep(0.01)  # 100Hz control loop
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            
        finally:
            self.shutdown()
            
        return 0
    
    def shutdown(self):
        """Gracefully shutdown the robot system."""
        self.logger.info("Shutting down robot system...")
        self.running = False
        
        if self.robot_controller:
            self.robot_controller.shutdown()
            
        self.logger.info("Robot system shutdown complete.")
    
    def signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False


def main():
    """Main function."""
    app = RobotApplication()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)
    
    # Run the application
    return app.run()


if __name__ == "__main__":
    sys.exit(main()) 