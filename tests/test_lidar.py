#!/usr/bin/env python3
"""
LiDAR Test Suite

Converts the original LiDAR test to use HardwareTestSuite framework.
Tests RPLiDAR A1 communication and scanning functionality.
"""

import serial
import time
import struct
import sys
import os
from typing import Dict, Any, Optional
import numpy as np
import matplotlib.pyplot as plt

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'basic_cases'))

from basic_cases.hardwaretestsuite import HardwareTestSuite
from config_loader import load_robot_config


class LidarTestSuite(HardwareTestSuite):
    """LiDAR testing suite."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("LiDAR", config)
        
        lidar_config = self.config.get('lidar', {})
        
        self.PORT = lidar_config.get('port', '/dev/ttyUSB1')
        self.BAUD = lidar_config.get('baudrate', 115200)
        self.MAX_DISTANCE = lidar_config.get('max_distance', 12.0) * 1000  # Convert to mm
        
        self.INFO_CMD = b'\xA5\x50'
        self.SCAN_CMD = b'\xA5\x20'
        self.TIMEOUT = 1.0
        self.OUTPUT_IMG = 'lidar_test_cloud.png'
        
        self.ser = None

    def _read_descriptor(self, ser) -> tuple:
        """Read descriptor from LiDAR."""
        hdr = ser.read(7)
        if len(hdr) != 7 or hdr[0] != 0xA5 or hdr[1] != 0x5A:
            raise RuntimeError(f"Bad descriptor hdr: {hdr.hex()}")
        size = hdr[2]
        payload = ser.read(size)
        if len(payload) != size:
            raise RuntimeError("Bad descriptor payload")
        return hdr, payload

    def _polar_to_xy(self, nodes) -> tuple:
        """Convert polar coordinates to Cartesian."""
        xs, ys = [], []
        for b0, b1, b2, b3, b4 in nodes:
            new_scan = bool(b0 & 0x1)
            quality = b0 >> 2
            raw_ang = ((b2 << 8) | b1) >> 1
            angle = raw_ang / 64.0  # degrees
            dist = ((b4 << 8) | b3) / 4.0  # mm
            if dist > 0:
                rad = np.deg2rad(angle)
                xs.append(dist * np.cos(rad))
                ys.append(dist * np.sin(rad))
        return np.array(xs), np.array(ys)

    def setup_hardware(self) -> bool:
        """Setup LiDAR serial communication."""
        try:
            self.ser = serial.Serial(self.PORT, self.BAUD, timeout=self.TIMEOUT)
            time.sleep(0.1)
            self.ser.reset_input_buffer()
            
            self.logger.info(f"LiDAR serial port opened: {self.PORT} at {self.BAUD} baud")
            return True
            
        except Exception as e:
            self.logger.error(f"LiDAR setup failed: {e}")
            return False

    def cleanup_hardware(self) -> None:
        """Cleanup LiDAR resources."""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.logger.info("LiDAR serial port closed")
        except Exception as e:
            self.logger.error(f"LiDAR cleanup failed: {e}")

    def test_basic_functionality(self) -> bool:
        """Test basic LiDAR communication."""
        try:
            if not self.ser or not self.ser.is_open:
                return False

            self.ser.write(self.INFO_CMD)
            hdr, payload = self._read_descriptor(self.ser)
            
            self.logger.info(f"✅ LiDAR descriptor OK: {hdr.hex()}, payload: {payload.hex()}")
            return True
            
        except Exception as e:
            self.logger.error(f"Basic functionality test failed: {e}")
            return False

    def test_error_handling(self) -> bool:
        """Test error handling with invalid commands."""
        try:
            if not self.ser or not self.ser.is_open:
                return False

            invalid_cmd = b'\xFF\xFF'
            self.ser.write(invalid_cmd)
            
            try:
                response = self.ser.read(10)
                if len(response) == 0:
                    self.logger.info("✅ Invalid command correctly ignored (no response)")
                    return True
                else:
                    self.logger.warning(f"Unexpected response to invalid command: {response.hex()}")
                    return False
            except Exception as e:
                self.logger.info(f"✅ Invalid command correctly handled: {e}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error handling test failed: {e}")
            return False

    def test_performance(self) -> bool:
        """Test LiDAR scanning performance."""
        try:
            if not self.ser or not self.ser.is_open:
                return False

            # Start scanning
            self.ser.write(self.SCAN_CMD)
            
            # Skip scan header
            self._read_descriptor(self.ser)
            
            # Read scan data for one complete rotation
            nodes = []
            got_first = False
            start_time = time.time()
            
            while True:
                data = self.ser.read(5)
                if len(data) != 5:
                    self.logger.warning("EOF or timeout during scan")
                    break
                    
                b0, b1, b2, b3, b4 = struct.unpack('<BBBBB', data)
                if b0 & 0x1:
                    if got_first:
                        break
                    else:
                        got_first = True
                        
                nodes.append((b0, b1, b2, b3, b4))
                
                if time.time() - start_time > 10.0:
                    self.logger.warning("Scan timeout after 10 seconds")
                    break

            scan_time = time.time() - start_time
            
            xs, ys = self._polar_to_xy(nodes)
            
            plt.figure(figsize=(6, 6))
            plt.scatter(xs, ys, s=2)
            plt.axis('equal')
            plt.title('RPLIDAR A1 — Test Scan Cloud')
            plt.xlabel('X (mm)')
            plt.ylabel('Y (mm)')
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(self.OUTPUT_IMG)
            plt.close()
            
            self.logger.info(f"✅ Scan completed in {scan_time:.2f}s")
            self.logger.info(f"✅ Points collected: {len(xs)}")
            self.logger.info(f"✅ Scan cloud saved to {self.OUTPUT_IMG}")
            return len(xs) > 50
            
        except Exception as e:
            self.logger.error(f"Performance test failed: {e}")
            return False


def main():
    """Main test function."""
    print("🤖 RTK-VL Robot LiDAR Test Suite")
    print("Press Ctrl+C to interrupt tests\n")
    
    # Load configuration
    config = load_robot_config()
    test_suite = LidarTestSuite(config)
    
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
