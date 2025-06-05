"""
Dynamixel Controller - Interface for Dynamixel servo motors.
"""

import time
from typing import Dict, List, Any, Optional
from dynamixel_sdk import *

from utils.logger import setup_logger


class DynamixelController:
    """Controller for Dynamixel servo motors."""
    
    # Control table addresses for XM430-W350
    ADDR_TORQUE_ENABLE = 64
    ADDR_GOAL_POSITION = 116
    ADDR_PRESENT_POSITION = 132
    ADDR_GOAL_VELOCITY = 104
    ADDR_PRESENT_VELOCITY = 128
    ADDR_PRESENT_TEMPERATURE = 146
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Dynamixel controller.
        
        Args:
            config: Dynamixel configuration dictionary
        """
        self.logger = setup_logger(__name__)
        self.config = config
        
        self.port_handler = None
        self.packet_handler = None
        self.motors: Dict[str, Dict] = {}
        self.is_initialized = False
        
    def initialize(self):
        """Initialize Dynamixel communication."""
        try:
            # Initialize port handler
            self.port_handler = PortHandler(self.config['port'])
            self.packet_handler = PacketHandler(self.config['protocol_version'])
            
            # Open port
            if not self.port_handler.openPort():
                raise Exception(f"Failed to open port {self.config['port']}")
            
            # Set baudrate
            if not self.port_handler.setBaudRate(self.config['baudrate']):
                raise Exception(f"Failed to set baudrate {self.config['baudrate']}")
            
            # Initialize motors
            self._initialize_motors()
            
            self.is_initialized = True
            self.logger.info("Dynamixel controller initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Dynamixel controller: {e}")
            raise
    
    def _initialize_motors(self):
        """Initialize individual motors."""
        for motor_name, motor_config in self.config['motors'].items():
            motor_id = motor_config['id']
            
            # Enable torque
            dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.ADDR_TORQUE_ENABLE, 1
            )
            
            if dxl_comm_result != COMM_SUCCESS:
                raise Exception(f"Failed to enable torque for motor {motor_name}")
            
            # Store motor info
            self.motors[motor_name] = {
                'id': motor_id,
                'model': motor_config['model'],
                'position': 0,
                'velocity': 0,
                'temperature': 0
            }
            
            self.logger.info(f"Motor {motor_name} (ID: {motor_id}) initialized")
    
    def set_position(self, motor_name: str, position: int):
        """Set target position for a motor.
        
        Args:
            motor_name: Name of the motor
            position: Target position (0-4095)
        """
        if not self.is_initialized or motor_name not in self.motors:
            return False
        
        motor_id = self.motors[motor_name]['id']
        
        # Write goal position
        dxl_comm_result, dxl_error = self.packet_handler.write4ByteTxRx(
            self.port_handler, motor_id, self.ADDR_GOAL_POSITION, position
        )
        
        if dxl_comm_result != COMM_SUCCESS:
            self.logger.error(f"Failed to set position for motor {motor_name}")
            return False
        
        return True
    
    def set_velocity(self, motor_name: str, velocity: int):
        """Set target velocity for a motor.
        
        Args:
            motor_name: Name of the motor
            velocity: Target velocity
        """
        if not self.is_initialized or motor_name not in self.motors:
            return False
        
        motor_id = self.motors[motor_name]['id']
        
        # Write goal velocity
        dxl_comm_result, dxl_error = self.packet_handler.write4ByteTxRx(
            self.port_handler, motor_id, self.ADDR_GOAL_VELOCITY, velocity
        )
        
        if dxl_comm_result != COMM_SUCCESS:
            self.logger.error(f"Failed to set velocity for motor {motor_name}")
            return False
        
        return True
    
    def get_position(self, motor_name: str) -> Optional[int]:
        """Get current position of a motor.
        
        Args:
            motor_name: Name of the motor
            
        Returns:
            Current position or None if error
        """
        if not self.is_initialized or motor_name not in self.motors:
            return None
        
        motor_id = self.motors[motor_name]['id']
        
        # Read present position
        position, dxl_comm_result, dxl_error = self.packet_handler.read4ByteTxRx(
            self.port_handler, motor_id, self.ADDR_PRESENT_POSITION
        )
        
        if dxl_comm_result != COMM_SUCCESS:
            return None
        
        self.motors[motor_name]['position'] = position
        return position
    
    def get_velocity(self, motor_name: str) -> Optional[int]:
        """Get current velocity of a motor.
        
        Args:
            motor_name: Name of the motor
            
        Returns:
            Current velocity or None if error
        """
        if not self.is_initialized or motor_name not in self.motors:
            return None
        
        motor_id = self.motors[motor_name]['id']
        
        # Read present velocity
        velocity, dxl_comm_result, dxl_error = self.packet_handler.read4ByteTxRx(
            self.port_handler, motor_id, self.ADDR_PRESENT_VELOCITY
        )
        
        if dxl_comm_result != COMM_SUCCESS:
            return None
        
        self.motors[motor_name]['velocity'] = velocity
        return velocity
    
    def update_all_sensors(self):
        """Update sensor readings for all motors."""
        for motor_name in self.motors.keys():
            self.get_position(motor_name)
            self.get_velocity(motor_name)
    
    def execute_command(self, command: Dict[str, Any]):
        """Execute a movement command.
        
        Args:
            command: Movement command dictionary
        """
        if 'positions' in command:
            for motor_name, position in command['positions'].items():
                self.set_position(motor_name, position)
        
        if 'velocities' in command:
            for motor_name, velocity in command['velocities'].items():
                self.set_velocity(motor_name, velocity)
    
    def stop_all_motors(self):
        """Stop all motors immediately."""
        for motor_name in self.motors.keys():
            self.set_velocity(motor_name, 0)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all motors.
        
        Returns:
            Status dictionary
        """
        status = {
            'initialized': self.is_initialized,
            'motors': {}
        }
        
        for motor_name, motor_info in self.motors.items():
            status['motors'][motor_name] = {
                'id': motor_info['id'],
                'position': self.get_position(motor_name),
                'velocity': self.get_velocity(motor_name)
            }
        
        return status
    
    def shutdown(self):
        """Shutdown Dynamixel controller."""
        if self.is_initialized:
            # Disable torque for all motors
            for motor_name, motor_info in self.motors.items():
                motor_id = motor_info['id']
                self.packet_handler.write1ByteTxRx(
                    self.port_handler, motor_id, self.ADDR_TORQUE_ENABLE, 0
                )
            
            # Close port
            if self.port_handler:
                self.port_handler.closePort()
            
            self.is_initialized = False
            self.logger.info("Dynamixel controller shutdown complete") 