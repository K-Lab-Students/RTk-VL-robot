#!/usr/bin/env python3
"""
RTK-VL Robot Main Application

Entry point for the robotics system integrating Dynamixel servos, LiDAR sensors,
neural processing units, and camera systems for autonomous operation.
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
    """
    Main robot application orchestrating system lifecycle.
    
    Handles initialization, main control loop execution, and graceful shutdown
    of all robot subsystems. Provides signal handling for clean termination.
    
    Attributes:
        logger: Application logger instance
        config_manager: Configuration management interface
        robot_controller: Main robot control system
        running: Application execution state flag
    """
    
    def __init__(self):
        """Initialize the robot application with default components."""
        self.logger = setup_logger(__name__)
        self.config_manager = ConfigManager()
        self.robot_controller = None
        self.running = False
        
    def initialize(self):
        """
        Initialize all robot systems and hardware.
        
        Loads configuration, creates robot controller, and initializes
        all hardware components. Handles initialization failures gracefully.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
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
        """
        Execute main application lifecycle.
        
        Performs initialization, runs the main control loop, and handles
        cleanup on exit. Returns appropriate exit codes for process management.
        
        Returns:
            int: Exit code (0 for success, 1 for failure)
        """
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
        """
        Gracefully shutdown the robot system.
        
        Stops all robot operations, disables hardware, and cleans up
        resources in the proper order to ensure safe system termination.
        """
        self.logger.info("Shutting down robot system...")
        self.running = False
        
        if self.robot_controller:
            self.robot_controller.shutdown()
            
        self.logger.info("Robot system shutdown complete.")
    
    def signal_handler(self, signum, frame):
        """
        Handle system signals for graceful shutdown.
        
        Processes SIGINT and SIGTERM signals to ensure clean application
        termination when requested by the operating system or user.
        
        Args:
            signum: Signal number received
            frame: Current stack frame (unused)
        """
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False


def main():
    """
    Application entry point.
    
    Creates the robot application instance, configures signal handlers,
    and executes the main application lifecycle.
    
    Returns:
        int: Process exit code
    """
    app = RobotApplication()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)
    
    # Run the application
    return app.run()


if __name__ == "__main__":
    sys.exit(main()) 