"""
RTK-VL Robot Controller

Main controller coordinating all robot subsystems including Dynamixel servos,
LiDAR sensors, cameras, and neural processing units.
"""

import time
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass

from hardware.dynamixel_controller import DynamixelController
from hardware.lidar_controller import LidarController
from hardware.camera_controller import CameraController
from hardware.npu_controller import NPUController
from vision.vision_processor import VisionProcessor
from navigation.navigation_system import NavigationSystem
from utils.logger import setup_logger


@dataclass
class RobotState:
    """Robot operational state container."""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    battery_level: float = 100.0
    temperature: float = 25.0
    is_moving: bool = False
    last_update: float = 0.0


class RobotController:
    """
    Main robot controller coordinating all subsystems.
    
    Manages hardware initialization, system coordination, and provides
    a unified interface for robot control and monitoring.
    
    Attributes:
        config: Robot configuration dictionary
        is_initialized: Whether the controller is initialized
        is_running: Whether the main control loop is running
        state: Current robot operational state
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize robot controller with configuration.
        
        Args:
            config: Complete robot configuration dictionary containing
                   settings for all subsystems
        """
        self.logger = setup_logger(__name__)
        self.config = config
        self.is_initialized = False
        self.is_running = False
        
        self.state = RobotState()
        self.state_lock = threading.Lock()
        
        self.dynamixel_controller: Optional[DynamixelController] = None
        self.lidar_controller: Optional[LidarController] = None
        self.camera_controller: Optional[CameraController] = None
        self.npu_controller: Optional[NPUController] = None
        self.vision_processor: Optional[VisionProcessor] = None
        self.navigation_system: Optional[NavigationSystem] = None
        
    def initialize_hardware(self):
        """
        Initialize all hardware subsystems based on configuration.
        
        Raises:
            RuntimeError: If critical hardware initialization fails
        """
        try:
            self.logger.info("Initializing robot hardware subsystems...")
            
            if self.config.get('dynamixel', {}).get('enabled', False):
                self._initialize_dynamixel()
            
            if self.config.get('lidar', {}).get('enabled', False):
                self._initialize_lidar()
            
            if self.config.get('camera', {}).get('enabled', False):
                self._initialize_camera()
            
            if self.config.get('npu', {}).get('enabled', False):
                self._initialize_npu()
            
            self._initialize_vision_processor()
            self._initialize_navigation_system()
            
            self.is_initialized = True
            self.logger.info("All hardware subsystems initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Hardware initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize robot hardware: {e}")
    
    def _initialize_dynamixel(self):
        """Initialize Dynamixel servo controller."""
        self.logger.info("Initializing Dynamixel controller...")
        self.dynamixel_controller = DynamixelController(self.config['dynamixel'])
        self.dynamixel_controller.initialize()
    
    def _initialize_lidar(self):
        """Initialize LiDAR sensor controller."""
        self.logger.info("Initializing LiDAR controller...")
        self.lidar_controller = LidarController(self.config['lidar'])
        self.lidar_controller.initialize()
    
    def _initialize_camera(self):
        """Initialize camera system controller."""
        self.logger.info("Initializing camera controller...")
        self.camera_controller = CameraController(self.config['camera'])
        self.camera_controller.initialize()
    
    def _initialize_npu(self):
        """Initialize neural processing unit controller."""
        self.logger.info("Initializing NPU controller...")
        self.npu_controller = NPUController(self.config['npu'])
        self.npu_controller.initialize()
    
    def _initialize_vision_processor(self):
        """Initialize computer vision processing system."""
        self.logger.info("Initializing vision processor...")
        self.vision_processor = VisionProcessor(
            self.config['vision'],
            self.camera_controller,
            self.npu_controller
        )
    
    def _initialize_navigation_system(self):
        """Initialize autonomous navigation system."""
        self.logger.info("Initializing navigation system...")
        self.navigation_system = NavigationSystem(
            self.config['navigation'],
            self.lidar_controller
        )
    
    def start(self):
        """
        Start the main robot control loop.
        
        Begins continuous operation with hardware monitoring and control
        at the configured frequency.
        """
        if not self.is_initialized:
            raise RuntimeError("Robot not initialized. Call initialize_hardware() first.")
        
        self.is_running = True
        self.logger.info("Starting robot control loop...")
        
        control_frequency = self.config.get('robot', {}).get('control_frequency', 100)
        update_interval = 1.0 / control_frequency
        
        while self.is_running:
            start_time = time.time()
            
            self.update()
            
            elapsed = time.time() - start_time
            sleep_time = max(0, update_interval - elapsed)
            time.sleep(sleep_time)
    
    def update(self):
        """
        Execute single control loop iteration.
        
        Updates all subsystems, processes sensor data, and executes
        navigation and control commands.
        """
        if not self.is_initialized:
            return
        
        current_time = time.time()
        
        with self.state_lock:
            self._update_sensor_data()
            self._update_navigation()
            self._update_vision_processing()
            self._execute_control_commands()
            
            self.state.last_update = current_time
    
    def _update_sensor_data(self):
        """Update sensor readings from all hardware subsystems."""
        if self.dynamixel_controller:
            self.dynamixel_controller.update_all_sensors()
        
        if self.lidar_controller:
            self.lidar_controller.update()
    
    def _update_navigation(self):
        """Update navigation system and path planning."""
        if self.navigation_system:
            self.navigation_system.update()
    
    def _update_vision_processing(self):
        """Update computer vision processing and object detection."""
        if self.vision_processor:
            self.vision_processor.process_frame()
    
    def _execute_control_commands(self):
        """Execute motor control commands based on navigation decisions."""
        if self.navigation_system and self.dynamixel_controller:
            command = self.navigation_system.get_movement_command()
            if command:
                self.dynamixel_controller.execute_command(command)
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status information.
        
        Returns:
            Dictionary containing current status of all subsystems including
            initialization state, hardware health, and operational metrics
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
        """
        Execute immediate emergency stop of all robot motion.
        
        Stops all motors and navigation immediately for safety.
        This is a blocking operation that takes priority over all other commands.
        """
        self.logger.warning("Emergency stop activated!")
        
        with self.state_lock:
            if self.dynamixel_controller:
                self.dynamixel_controller.stop_all_motors()
            
            if self.navigation_system:
                self.navigation_system.emergency_stop()
    
    def navigate_to(self, target_position: tuple[float, float, float]) -> bool:
        """
        Navigate to specified target position.
        
        Args:
            target_position: Target coordinates as (x, y, theta) tuple
            
        Returns:
            True if navigation command accepted, False if unable to navigate
        """
        if not self.navigation_system:
            self.logger.error("Navigation system not available")
            return False
        
        return self.navigation_system.navigate_to(target_position)
    
    def shutdown(self):
        """
        Gracefully shutdown all robot subsystems.
        
        Stops the control loop, disables all motors, and cleans up
        hardware resources in the proper order.
        """
        self.logger.info("Initiating robot controller shutdown...")
        self.is_running = False
        
        if self.dynamixel_controller:
            self.dynamixel_controller.shutdown()
        
        if self.lidar_controller:
            self.lidar_controller.shutdown()
        
        if self.camera_controller:
            self.camera_controller.shutdown()
        
        if self.npu_controller:
            self.npu_controller.shutdown()
        
        self.is_initialized = False
        self.logger.info("Robot controller shutdown complete") 