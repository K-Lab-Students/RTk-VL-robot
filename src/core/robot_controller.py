"""
Robot Controller - Main coordination class for all robot systems.
"""

import time
import threading
from typing import Dict, Any, Optional

from hardware.dynamixel_controller import DynamixelController
from hardware.lidar_controller import LidarController
from hardware.camera_controller import CameraController
from hardware.npu_controller import NPUController
from vision.vision_processor import VisionProcessor
from navigation.navigation_system import NavigationSystem
from utils.logger import setup_logger


class RobotController:
    """Main robot controller coordinating all subsystems."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the robot controller.
        
        Args:
            config: Configuration dictionary
        """
        self.logger = setup_logger(__name__)
        self.config = config
        
        # Hardware controllers
        self.dynamixel_controller: Optional[DynamixelController] = None
        self.lidar_controller: Optional[LidarController] = None
        self.camera_controller: Optional[CameraController] = None
        self.npu_controller: Optional[NPUController] = None
        
        # High-level systems
        self.vision_processor: Optional[VisionProcessor] = None
        self.navigation_system: Optional[NavigationSystem] = None
        
        # Control state
        self.is_initialized = False
        self.is_running = False
        self.control_thread: Optional[threading.Thread] = None
        self.state_lock = threading.Lock()
        
    def initialize_hardware(self):
        """Initialize all hardware components."""
        try:
            self.logger.info("Initializing hardware components...")
            
            # Initialize Dynamixel servos
            if self.config.get('dynamixel', {}).get('enabled', False):
                self.dynamixel_controller = DynamixelController(
                    self.config['dynamixel']
                )
                self.dynamixel_controller.initialize()
                self.logger.info("Dynamixel controller initialized")
            
            # Initialize LiDAR
            if self.config.get('lidar', {}).get('enabled', False):
                self.lidar_controller = LidarController(
                    self.config['lidar']
                )
                self.lidar_controller.initialize()
                self.logger.info("LiDAR controller initialized")
            
            # Initialize cameras
            if self.config.get('camera', {}).get('enabled', False):
                self.camera_controller = CameraController(
                    self.config['camera']
                )
                self.camera_controller.initialize()
                self.logger.info("Camera controller initialized")
            
            # Initialize NPU
            if self.config.get('npu', {}).get('enabled', False):
                self.npu_controller = NPUController(
                    self.config['npu']
                )
                self.npu_controller.initialize()
                self.logger.info("NPU controller initialized")
            
            # Initialize high-level systems
            self._initialize_high_level_systems()
            
            self.is_initialized = True
            self.logger.info("All hardware components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize hardware: {e}")
            raise
    
    def _initialize_high_level_systems(self):
        """Initialize high-level processing systems."""
        # Vision processing system
        self.vision_processor = VisionProcessor(
            camera_controller=self.camera_controller,
            npu_controller=self.npu_controller,
            config=self.config.get('vision', {})
        )
        
        # Navigation system
        self.navigation_system = NavigationSystem(
            lidar_controller=self.lidar_controller,
            vision_processor=self.vision_processor,
            config=self.config.get('navigation', {})
        )
    
    def update(self):
        """Main update loop - called from the main application loop."""
        if not self.is_initialized:
            return
            
        with self.state_lock:
            try:
                # Update sensor data
                self._update_sensors()
                
                # Process vision data
                if self.vision_processor:
                    self.vision_processor.process_frame()
                
                # Update navigation
                if self.navigation_system:
                    navigation_command = self.navigation_system.update()
                    
                    # Execute movement commands
                    if navigation_command and self.dynamixel_controller:
                        self.dynamixel_controller.execute_command(navigation_command)
                
            except Exception as e:
                self.logger.error(f"Error in update loop: {e}")
    
    def _update_sensors(self):
        """Update all sensor readings."""
        # Update LiDAR data
        if self.lidar_controller:
            self.lidar_controller.update()
        
        # Update camera frames
        if self.camera_controller:
            self.camera_controller.update()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status.
        
        Returns:
            Dictionary containing system status information
        """
        status = {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'timestamp': time.time(),
            'hardware': {}
        }
        
        if self.dynamixel_controller:
            status['hardware']['dynamixel'] = self.dynamixel_controller.get_status()
        
        if self.lidar_controller:
            status['hardware']['lidar'] = self.lidar_controller.get_status()
        
        if self.camera_controller:
            status['hardware']['camera'] = self.camera_controller.get_status()
        
        if self.npu_controller:
            status['hardware']['npu'] = self.npu_controller.get_status()
        
        return status
    
    def emergency_stop(self):
        """Emergency stop all robot motion."""
        self.logger.warning("Emergency stop activated!")
        
        with self.state_lock:
            if self.dynamixel_controller:
                self.dynamixel_controller.stop_all_motors()
            
            if self.navigation_system:
                self.navigation_system.emergency_stop()
    
    def shutdown(self):
        """Shutdown all robot systems."""
        self.logger.info("Shutting down robot controller...")
        
        self.is_running = False
        
        # Shutdown hardware controllers
        if self.dynamixel_controller:
            self.dynamixel_controller.shutdown()
        
        if self.lidar_controller:
            self.lidar_controller.shutdown()
        
        if self.camera_controller:
            self.camera_controller.shutdown()
        
        if self.npu_controller:
            self.npu_controller.shutdown()
        
        # Shutdown high-level systems
        if self.vision_processor:
            self.vision_processor.shutdown()
        
        if self.navigation_system:
            self.navigation_system.shutdown()
        
        self.logger.info("Robot controller shutdown complete") 