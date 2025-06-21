#!/usr/bin/env python3
"""
WASD Movement Controller - COMMAND MODE WITH LOGGING
Controls: W/S/A/D/Q/E + ENTER to execute
COMMAND MODE: Type command + Enter -> Move at max speed for 5 seconds -> Stop -> Wait
LOGS ALL MOVEMENTS FOR REPLAY
"""

import sys
import time
import threading
import logging
from collections import deque
import json
from datetime import datetime

# Import Dynamixel SDK for motor control
try:
    from dynamixel_sdk import PortHandler, PacketHandler
    DYNAMIXEL_AVAILABLE = True
except ImportError:
    print("Warning: dynamixel_sdk not available - using simulation mode")
    DYNAMIXEL_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Wheel Configuration (from your existing tests)
WHEEL_CONFIG = {
    "device": "/dev/ttyUSB0",  # Make sure this is correct
    "baud": 57600,
    "protocol": 1.0,
    "wheels": {
        2: {"name": "Wheel 02", "direction": -1},    # Left front
        9: {"name": "Wheel 09", "direction": -1},    # Left rear  
        8: {"name": "Wheel 08", "direction": 1},     # Right rear
        7: {"name": "Wheel 07", "direction": 1}      # Right front
    }
}

# Dynamixel addresses for MX-106
ADDR_CW_LIMIT = 6
ADDR_CCW_LIMIT = 8
ADDR_TORQUE_ENABLE = 24
ADDR_MOVING_SPEED = 32

class WASDController:
    def __init__(self):
        self.running = False
        self.max_speed = 800  # Maximum motor speed
        self.movement_duration = 1.0  # 5 seconds per movement
        self.currently_moving = False
        
        # Movement logging
        self.movement_log = []
        self.log_file = f"movement_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Motor control
        self.motor_port_handler = None
        self.motor_packet_handler = None
        self.motors_initialized = False
        
        # Initialize motors
        self.initialize_motors()
        
        # Log session start
        self.log_event("SESSION_START", {"timestamp": datetime.now().isoformat()})
        
    def log_event(self, event_type, data):
        """Log movement events for replay."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        self.movement_log.append(log_entry)
        
        # Save to file immediately
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.movement_log, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save log: {e}")
        
    def initialize_motors(self):
        """Initialize Dynamixel motors for wheel control."""
        if not DYNAMIXEL_AVAILABLE:
            logger.warning("Dynamixel SDK not available - using simulation mode")
            self.log_event("MOTOR_INIT", {"status": "simulation_mode"})
            return False
            
        try:
            logger.info(f"Attempting to connect to {WHEEL_CONFIG['device']} at {WHEEL_CONFIG['baud']} baud")
            self.motor_port_handler = PortHandler(WHEEL_CONFIG["device"])
            self.motor_packet_handler = PacketHandler(WHEEL_CONFIG["protocol"])
            
            if not self.motor_port_handler.openPort():
                logger.error(f"Failed to open {WHEEL_CONFIG['device']}")
                self.log_event("MOTOR_INIT", {"status": "failed", "error": "port_open_failed"})
                return False
                
            if not self.motor_port_handler.setBaudRate(WHEEL_CONFIG["baud"]):
                logger.error(f"Failed to set baudrate {WHEEL_CONFIG['baud']}")
                self.motor_port_handler.closePort()
                self.log_event("MOTOR_INIT", {"status": "failed", "error": "baudrate_failed"})
                return False
            
            # Configure each wheel for continuous rotation (wheel mode)
            for wheel_id in WHEEL_CONFIG["wheels"].keys():
                logger.info(f"Configuring wheel {wheel_id}...")
                
                # Disable torque first
                result, error = self.motor_packet_handler.write1ByteTxRx(
                    self.motor_port_handler, wheel_id, ADDR_TORQUE_ENABLE, 0)
                if result != 0:
                    logger.warning(f"Failed to disable torque for wheel {wheel_id}")
                
                # Set wheel mode (both limits to 0)
                self.motor_packet_handler.write2ByteTxRx(
                    self.motor_port_handler, wheel_id, ADDR_CW_LIMIT, 0)
                self.motor_packet_handler.write2ByteTxRx(
                    self.motor_port_handler, wheel_id, ADDR_CCW_LIMIT, 0)
                
                # Enable torque
                result, error = self.motor_packet_handler.write1ByteTxRx(
                    self.motor_port_handler, wheel_id, ADDR_TORQUE_ENABLE, 1)
                
                if result != 0:
                    logger.warning(f"Failed to enable torque for wheel {wheel_id}")
                else:
                    logger.info(f"✅ Wheel {wheel_id} configured successfully")
            
            self.motors_initialized = True
            logger.info("✅ Motors initialized successfully")
            self.log_event("MOTOR_INIT", {"status": "success", "device": WHEEL_CONFIG["device"], "baud": WHEEL_CONFIG["baud"]})
            return True
            
        except Exception as e:
            logger.error(f"Motor initialization failed: {e}")
            self.log_event("MOTOR_INIT", {"status": "failed", "error": str(e)})
            return False
    
    def set_wheel_speeds(self, left_speed, right_speed):
        """Set speeds for left and right wheels."""
        if not self.motors_initialized:
            logger.info(f"🔄 SIMULATION: Left={left_speed}, Right={right_speed}")
            return
        
        try:
            # Set speeds for each wheel
            for wheel_id, config in WHEEL_CONFIG["wheels"].items():
                if wheel_id in [2, 9]:  # Left wheels
                    speed = int(left_speed * config["direction"])
                else:  # Right wheels (7, 8)
                    speed = int(right_speed * config["direction"])
                
                # Convert to Dynamixel format
                if speed >= 0:
                    speed_value = speed & 0x3FF  # Positive direction
                else:
                    speed_value = 0x400 | ((-speed) & 0x3FF)  # Negative direction
                
                # Send speed command
                result, error = self.motor_packet_handler.write2ByteTxRx(
                    self.motor_port_handler, wheel_id, ADDR_MOVING_SPEED, speed_value)
                
                if result != 0:
                    logger.warning(f"Failed to set speed for wheel {wheel_id}")
                    
        except Exception as e:
            logger.error(f"Failed to set wheel speeds: {e}")
    
    def stop_wheels(self):
        """Stop all wheels immediately."""
        self.set_wheel_speeds(0, 0)
        self.currently_moving = False
        
    def execute_burst_movement(self, command):
        """Execute movement at max speed for 5 seconds."""
        if not command or self.currently_moving:
            return
        
        self.currently_moving = True
        start_time = datetime.now()
        
        # Log movement start
        movement_data = {
            "command": command.upper(),
            "max_speed": self.max_speed,
            "duration": self.movement_duration,
            "start_time": start_time.isoformat()
        }
        
        # Execute movement with max speed for 5 seconds
        if command.lower() == 'w':  # Forward
            logger.info(f"🚀 BURST FORWARD at max speed for {self.movement_duration} seconds")
            self.set_wheel_speeds(self.max_speed, self.max_speed)
            movement_data["direction"] = "forward"
            movement_data["left_speed"] = self.max_speed
            movement_data["right_speed"] = self.max_speed
            
        elif command.lower() == 's':  # Backward
            logger.info(f"🚀 BURST BACKWARD at max speed for {self.movement_duration} seconds")
            self.set_wheel_speeds(-self.max_speed, -self.max_speed)
            movement_data["direction"] = "backward"
            movement_data["left_speed"] = -self.max_speed
            movement_data["right_speed"] = -self.max_speed
            
        elif command.lower() == 'a':  # Left (strafe)
            logger.info(f"🚀 BURST LEFT at max speed for {self.movement_duration} seconds")
            self.set_wheel_speeds(-self.max_speed, self.max_speed)
            movement_data["direction"] = "left"
            movement_data["left_speed"] = -self.max_speed
            movement_data["right_speed"] = self.max_speed
            
        elif command.lower() == 'd':  # Right (strafe)
            logger.info(f"🚀 BURST RIGHT at max speed for {self.movement_duration} seconds")
            self.set_wheel_speeds(self.max_speed, -self.max_speed)
            movement_data["direction"] = "right"
            movement_data["left_speed"] = self.max_speed
            movement_data["right_speed"] = -self.max_speed
            
        elif command.lower() == 'q':  # Rotate left
            logger.info(f"🚀 BURST ROTATE LEFT at max speed for {self.movement_duration} seconds")
            self.set_wheel_speeds(-self.max_speed, self.max_speed)
            movement_data["direction"] = "rotate_left"
            movement_data["left_speed"] = -self.max_speed
            movement_data["right_speed"] = self.max_speed
            
        elif command.lower() == 'e':  # Rotate right
            logger.info(f"🚀 BURST ROTATE RIGHT at max speed for {self.movement_duration} seconds")
            self.set_wheel_speeds(self.max_speed, -self.max_speed)
            movement_data["direction"] = "rotate_right"
            movement_data["left_speed"] = self.max_speed
            movement_data["right_speed"] = -self.max_speed
        
        else:
            self.currently_moving = False
            return
        
        # Log movement start
        self.log_event("MOVEMENT_START", movement_data)
        
        # Wait for movement duration
        time.sleep(self.movement_duration)
        
        # Stop and log completion
        self.stop_wheels()
        end_time = datetime.now()
        
        movement_data["end_time"] = end_time.isoformat()
        movement_data["actual_duration"] = (end_time - start_time).total_seconds()
        
        self.log_event("MOVEMENT_END", movement_data)
        logger.info("🛑 Movement complete - Waiting for next command...")
    
    def replay_movements(self, log_file_path):
        """Replay movements from a log file."""
        try:
            with open(log_file_path, 'r') as f:
                replay_log = json.load(f)
            
            logger.info(f"🔄 Starting replay from {log_file_path}")
            self.log_event("REPLAY_START", {"source_file": log_file_path})
            
            for entry in replay_log:
                if entry["event_type"] == "MOVEMENT_START":
                    command = entry["data"]["command"].lower()
                    logger.info(f"🔄 Replaying: {command}")
                    self.execute_burst_movement(command)
                    
        except Exception as e:
            logger.error(f"Replay failed: {e}")
    
    def print_status(self):
        """Print current status and controls."""
        print("\n" + "="*60)
        print("🤖 HOSPITAL BOT - COMMAND MODE WITH LOGGING")
        print("📝 ALL MOVEMENTS LOGGED FOR REPLAY")
        print("="*60)
        print("Commands (type command + ENTER):")
        print("  W + ENTER - BURST Forward for 5 seconds")
        print("  S + ENTER - BURST Backward for 5 seconds") 
        print("  A + ENTER - BURST Left for 5 seconds")
        print("  D + ENTER - BURST Right for 5 seconds")
        print("  Q + ENTER - BURST Rotate Left for 5 seconds")
        print("  E + ENTER - BURST Rotate Right for 5 seconds")
        print("  SPEED + ENTER - Change max speed")
        print("  TIME + ENTER - Change duration")
        print("  REPLAY + ENTER - Replay from log file")
        print("  STATUS + ENTER - Show this status")
        print("  EXIT + ENTER - Exit")
        print("-"*60)
        print(f"Motors: {'🟢 Connected' if self.motors_initialized else '🔴 Simulation'}")
        print(f"Max Speed: {self.max_speed}")
        print(f"Movement Duration: {self.movement_duration} seconds")
        print(f"Status: {'🔄 MOVING' if self.currently_moving else '⏸️ WAITING FOR COMMAND'}")
        print(f"Log File: {self.log_file}")
        print(f"Logged Movements: {len([e for e in self.movement_log if e['event_type'] == 'MOVEMENT_START'])}")
        print("="*60)
    
    def run(self):
        """Main control loop."""
        logger.info("🚀 Starting COMMAND MODE WITH LOGGING")
        logger.info(f"📝 Logging to: {self.log_file}")
        
        self.running = True
        self.print_status()
        
        while self.running:
            try:
                if self.currently_moving:
                    print("⏳ Movement in progress - please wait...")
                    time.sleep(1)
                    continue
                
                command = input("\n🤖 Enter command: ").strip().lower()
                
                if command == 'exit':
                    logger.info("🛑 Exiting controller")
                    self.log_event("SESSION_END", {"timestamp": datetime.now().isoformat()})
                    break
                    
                elif command in ['w', 's', 'a', 'd', 'q', 'e']:
                    self.execute_burst_movement(command)
                    
                elif command == 'speed':
                    try:
                        new_speed = int(input("Enter new max speed (100-1023): "))
                        self.max_speed = max(100, min(1023, new_speed))
                        logger.info(f"🔄 Max speed changed to {self.max_speed}")
                        self.log_event("SETTING_CHANGE", {"setting": "max_speed", "value": self.max_speed})
                    except ValueError:
                        print("Invalid speed value")
                        
                elif command == 'time':
                    try:
                        new_duration = float(input("Enter new duration (0.5-10.0 seconds): "))
                        self.movement_duration = max(0.5, min(10.0, new_duration))
                        logger.info(f"🔄 Duration changed to {self.movement_duration} seconds")
                        self.log_event("SETTING_CHANGE", {"setting": "duration", "value": self.movement_duration})
                    except ValueError:
                        print("Invalid duration value")
                        
                elif command == 'replay':
                    log_file = input("Enter log file path: ").strip()
                    if log_file:
                        self.replay_movements(log_file)
                        
                elif command == 'status':
                    self.print_status()
                    
                else:
                    print("❌ Unknown command. Type 'status' for help.")
                    
            except KeyboardInterrupt:
                logger.info("🛑 Controller interrupted")
                self.log_event("SESSION_END", {"timestamp": datetime.now().isoformat(), "reason": "interrupted"})
                break
            except Exception as e:
                logger.error(f"Error: {e}")
        
        # Clean up motors
        if self.motors_initialized:
            self.stop_wheels()
            # Disable torque on all wheels
            for wheel_id in WHEEL_CONFIG["wheels"].keys():
                self.motor_packet_handler.write1ByteTxRx(
                    self.motor_port_handler, wheel_id, ADDR_TORQUE_ENABLE, 0)
            self.motor_port_handler.closePort()
            logger.info("🔌 Motors disconnected")
            
        logger.info(f"📝 Movement log saved to: {self.log_file}")

if __name__ == "__main__":
    controller = WASDController()
    controller.run() 
