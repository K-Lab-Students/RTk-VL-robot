#!/usr/bin/env python3
"""
Robot Hand Servo Test Suite

Converts the original servo test to use HardwareTestSuite framework.
Tests servo motor control using GPIO Zero library on Raspberry Pi.

Requirements:
    sudo apt update
    sudo apt install python3-gpiozero

Hardware:
    Connect servo to BCM pin 12 (GPIO12) with common wire to GND.
"""

import sys
import os
import time
from typing import Dict, Any, Optional
from gpiozero import Servo

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'basic_cases'))

from basic_cases.hardwaretestsuite import HardwareTestSuite
from config_loader import load_robot_config


class RobotHandTestSuite(HardwareTestSuite):
    """Robot hand servo testing suite."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("RobotHand", config)
        
        # Load servo configuration with fallbacks
        # Note: robot_config.yaml doesn't have servo config, so we use test-specific defaults
        servo_config = self.config.get('servo', {})
        
        self.SERVO_PIN = servo_config.get('pin', 12)
        self.MIN_PULSE_WIDTH = servo_config.get('min_pulse_width', 0.0005)
        self.MAX_PULSE_WIDTH = servo_config.get('max_pulse_width', 0.0025)
        
        # Test parameters
        self.POSITION_DELAY = 1.0
        self.SWEEP_DELAY = 0.05
        
        # Servo object
        self.servo = None
    
    def setup_hardware(self) -> bool:
        """Setup servo hardware."""
        try:
            self.servo = Servo(
                self.SERVO_PIN, 
                min_pulse_width=self.MIN_PULSE_WIDTH,
                max_pulse_width=self.MAX_PULSE_WIDTH
            )
            
            self.logger.info(f"Servo initialized on pin {self.SERVO_PIN}")
            return True
            
        except Exception as e:
            self.logger.error(f"Servo setup failed: {e}")
            return False
    
    def cleanup_hardware(self) -> None:
        """Cleanup servo resources."""
        try:
            if self.servo:
                self.servo.detach()
                self.logger.info("Servo detached and GPIO cleaned up")
        except Exception as e:
            self.logger.error(f"Servo cleanup failed: {e}")
    
    def test_basic_functionality(self) -> bool:
        """Test basic servo positioning."""
        try:
            if not self.servo:
                return False
            
            # Test minimum position (0°)
            self.logger.info("Testing minimum position (0°)")
            self.servo.min()
            time.sleep(self.POSITION_DELAY)
            
            # Test center position (90°)
            self.logger.info("Testing center position (90°)")
            self.servo.mid()
            time.sleep(self.POSITION_DELAY)
            
            # Test maximum position (180°)
            self.logger.info("Testing maximum position (180°)")
            self.servo.max()
            time.sleep(self.POSITION_DELAY)
            
            # Return to center
            self.servo.mid()
            
            self.logger.info("✅ Basic positioning test completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Basic functionality test failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling with invalid servo operations."""
        try:
            if not self.servo:
                return False
            
            # Test invalid position values
            test_values = [-2.0, 2.0]  # Outside -1.0 to 1.0 range
            
            for value in test_values:
                try:
                    self.servo.value = value
                    # If no exception, servo should clamp the value
                    actual_value = self.servo.value
                    if -1.0 <= actual_value <= 1.0:
                        self.logger.info(f"✅ Value {value} correctly clamped to {actual_value}")
                    else:
                        self.logger.warning(f"Value {value} not properly handled: {actual_value}")
                        return False
                except Exception as e:
                    self.logger.info(f"✅ Exception correctly raised for value {value}: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling test failed: {e}")
            return False
    
    def test_performance(self) -> bool:
        """Test servo performance with sweep pattern."""
        try:
            if not self.servo:
                return False
            
            self.logger.info("Testing servo performance with sweep pattern")
            
            # Forward sweep
            start_time = time.time()
            for position in range(-100, 101, 10):  # Reduced steps for faster test
                self.servo.value = position / 100.0
                time.sleep(self.SWEEP_DELAY)
            
            # Reverse sweep
            for position in range(100, -101, -10):
                self.servo.value = position / 100.0
                time.sleep(self.SWEEP_DELAY)
            
            elapsed_time = time.time() - start_time
            
            # Return to center
            self.servo.mid()
            
            # Calculate performance metrics
            positions_tested = 42  # Total positions in sweep
            avg_time_per_position = elapsed_time / positions_tested
            
            self.logger.info(f"✅ Sweep test completed in {elapsed_time:.2f}s")
            self.logger.info(f"Average time per position: {avg_time_per_position:.3f}s")
            
            # Consider successful if average time per position is reasonable
            return avg_time_per_position < 0.2  # Less than 200ms per position
            
        except Exception as e:
            self.logger.error(f"Performance test failed: {e}")
            return False


def main():
    """Main test function."""
    print("🤖 RTK-VL Robot Hand Servo Test Suite")
    print("Press Ctrl+C to interrupt tests\n")
    
    # Load configuration
    config = load_robot_config()
    test_suite = RobotHandTestSuite(config)
    
    try:
        success = test_suite.run_all_tests()
        exit_code = 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        test_suite.cleanup_hardware()
        exit_code = 2
        
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        test_suite.cleanup_hardware()
        exit_code = 3
    
    print(f"\nExiting with code {exit_code}")
    return exit_code


if __name__ == '__main__':
    exit(main())
