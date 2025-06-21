#!/usr/bin/env python3
"""
Dynamixel Motor Test Suite

Converts the original dynamixel test to use HardwareTestSuite framework.
Tests MX-106T/R motors with Protocol 1.0.
"""

import time
import sys
import os
from typing import Dict, Any, Optional
from dynamixel_sdk import PortHandler, PacketHandler

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'basic_cases'))

from basic_cases.hardwaretestsuite import HardwareTestSuite
from config_loader import load_robot_config


class DynamixelTestSuite(HardwareTestSuite):
    """Dynamixel motor testing suite."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("Dynamixel", config)
        
        dynamixel_config = self.config.get('dynamixel', {})
        
        self.DEV = dynamixel_config.get('port', "/dev/ttyUSB0")
        self.BAUD = dynamixel_config.get('baudrate', 57600)
        self.PROTO = dynamixel_config.get('protocol_version', 1.0)
        
        motors_config = dynamixel_config.get('motors', {})
        if motors_config:
            self.DXL_IDS = [motor['id'] for motor in motors_config.values()]
        else:
            self.DXL_IDS = [2, 7, 8, 9] 

        self.ADDR_CW_LIMIT = 6
        self.ADDR_CCW_LIMIT = 8
        self.ADDR_TORQUE = 24
        self.ADDR_SPEED = 32
        
        self.SPD_FWD = 300
        self.SPD_REV = 1024 + 30
        self.PAUSE = 2.0
        
        self.port = None
        self.pkt = None
    
    def setup_hardware(self) -> bool:
        """Setup Dynamixel communication."""
        try:
            self.port = PortHandler(self.DEV)
            self.pkt = PacketHandler(self.PROTO)
            
            if not (self.port.openPort() and self.port.setBaudRate(self.BAUD)):
                self.logger.error("Failed to open port")
                return False
            
            self.logger.info(f"Dynamixel port opened: {self.DEV} at {self.BAUD} baud")
            return True
            
        except Exception as e:
            self.logger.error(f"Dynamixel setup failed: {e}")
            return False
    
    def cleanup_hardware(self) -> None:
        """Cleanup Dynamixel resources."""
        try:
            if self.port and self.pkt:
                for motor_id in self.DXL_IDS:
                    try:
                        self.pkt.write1ByteTxRx(self.port, motor_id, self.ADDR_TORQUE, 0)
                    except:
                        pass
                
                self.port.closePort()
                self.logger.info("Dynamixel cleanup completed - all motors stopped")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    def _write2bytes(self, motor_id: int, addr: int, val: int) -> bool:
        """Write 2 bytes to motor register."""
        try:
            self.pkt.write2ByteTxRx(self.port, motor_id, addr, val)
            return True
        except Exception as e:
            self.logger.error(f"Failed to write 2 bytes to motor {motor_id}: {e}")
            return False
    
    def _write1byte(self, motor_id: int, addr: int, val: int) -> bool:
        """Write 1 byte to motor register."""
        try:
            self.pkt.write1ByteTxRx(self.port, motor_id, addr, val)
            return True
        except Exception as e:
            self.logger.error(f"Failed to write 1 byte to motor {motor_id}: {e}")
            return False
    
    def test_basic_functionality(self) -> bool:
        """Test basic motor communication and wheel mode setup."""
        try:
            success_count = 0
            
            for motor_id in self.DXL_IDS:
                self.logger.info(f"Testing motor {motor_id}")
                
                if not self._write1byte(motor_id, self.ADDR_TORQUE, 0):
                    continue
                
                if not self._write2bytes(motor_id, self.ADDR_CW_LIMIT, 0):
                    continue
                if not self._write2bytes(motor_id, self.ADDR_CCW_LIMIT, 0):
                    continue
                
                if not self._write1byte(motor_id, self.ADDR_TORQUE, 1):
                    continue
                
                success_count += 1
                self.logger.info(f"✅ Motor {motor_id} setup successful")
            
            success = success_count == len(self.DXL_IDS)
            self.logger.info(f"Basic functionality: {success_count}/{len(self.DXL_IDS)} motors ready")
            return success
            
        except Exception as e:
            self.logger.error(f"Basic functionality test failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        try:
            invalid_id = 99
            result = self._write1byte(invalid_id, self.ADDR_TORQUE, 1)
            
            if result:
                self.logger.warning("Expected failure with invalid motor ID, but succeeded")
                return False
            else:
                self.logger.info("✅ Correctly handled invalid motor ID")
                return True
                
        except Exception as e:
            self.logger.info(f"✅ Exception handling works: {e}")
            return True
    
    def test_performance(self) -> bool:
        try:
            self.logger.info("Testing forward rotation...")
            success_count = 0
            
            for motor_id in self.DXL_IDS:
                if self._write2bytes(motor_id, self.ADDR_SPEED, self.SPD_FWD):
                    success_count += 1
            
            if success_count != len(self.DXL_IDS):
                self.logger.error(f"Forward rotation: only {success_count}/{len(self.DXL_IDS)} motors responding")
                return False
            
            time.sleep(self.PAUSE)
            
            self.logger.info("Testing reverse rotation...")
            success_count = 0
            
            for motor_id in self.DXL_IDS:
                if self._write2bytes(motor_id, self.ADDR_SPEED, self.SPD_REV):
                    success_count += 1
            
            if success_count != len(self.DXL_IDS):
                self.logger.error(f"Reverse rotation: only {success_count}/{len(self.DXL_IDS)} motors responding")
                return False
            
            time.sleep(self.PAUSE)
            
            for motor_id in self.DXL_IDS:
                self._write2bytes(motor_id, self.ADDR_SPEED, 0)
            
            self.logger.info("✅ Performance test completed - forward/reverse rotation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Performance test failed: {e}")
            return False


def main():
    print("🤖 RTK-VL Robot Dynamixel Test Suite")
    print("Press Ctrl+C to interrupt tests\n")
    
    config = load_robot_config()
    test_suite = DynamixelTestSuite(config)
    
    try:
        success = test_suite.run_all_tests()
        exit_code = 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n Tests interrupted by user")
        test_suite.cleanup_hardware()
        exit_code = 2
        
    except Exception as e:
        print(f"\n Unexpected error: {e}")
        test_suite.cleanup_hardware()
        exit_code = 3
    
    print(f"\nExiting with code {exit_code}")
    return exit_code


if __name__ == '__main__':
    exit(main())
