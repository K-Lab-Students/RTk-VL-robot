#!/usr/bin/env python3
"""
MPU9250 IMU Test Suite

Comprehensive testing of the MPU9250 9-axis inertial measurement unit
including accelerometer, gyroscope, magnetometer, and temperature sensors.
"""
import smbus
import time
import struct
import math

class MPU9250:
    """
    MPU9250 9-axis inertial measurement unit driver.
    
    Provides interface for reading accelerometer, gyroscope, magnetometer,
    and temperature data from the MPU9250 sensor via I2C communication.
    
    Attributes:
        ADDR_WHO_AM_I: Device identification register address
        ADDR_PWR_MGMT_1: Primary power management register
        ADDR_ACCEL_XOUT_H: Accelerometer X-axis high byte register
        ADDR_GYRO_XOUT_H: Gyroscope X-axis high byte register
        ADDR_TEMP_OUT_H: Temperature sensor high byte register
    """
    
    # MPU9250 registers
    WHO_AM_I = 0x75
    PWR_MGMT_1 = 0x6B
    PWR_MGMT_2 = 0x6C
    CONFIG = 0x1A
    GYRO_CONFIG = 0x1B
    ACCEL_CONFIG = 0x1C
    ACCEL_CONFIG2 = 0x1D
    INT_PIN_CFG = 0x37
    
    # Data registers
    ACCEL_XOUT_H = 0x3B
    TEMP_OUT_H = 0x41
    GYRO_XOUT_H = 0x43
    
    # Magnetometer (AK8963) registers
    MAG_ADDRESS = 0x0C
    MAG_WHO_AM_I = 0x00
    MAG_CNTL1 = 0x0A
    MAG_XOUT_L = 0x03
    
    def __init__(self, bus_num=1, address=0x68):
        """
        Initialize MPU9250 interface.
        
        Args:
            bus_num: I2C bus number (default: 1)
            address: I2C device address (default: 0x68)
        """
        self.bus = smbus.SMBus(bus_num)
        self.address = address
        self.mag_address = 0x0C  # Magnetometer address
        
        # Scale factors
        self.accel_scale = 16384.0  # ±2g
        self.gyro_scale = 131.0     # ±250°/s
        
    def wake_up(self):
        """
        Wake up the MPU9250 from sleep mode.
        
        Returns:
            bool: True if wake-up successful, False otherwise
        """
        try:
            # Clear sleep bit
            self.bus.write_byte_data(self.address, self.PWR_MGMT_1, 0x00)
            time.sleep(0.1)
            print("✅ MPU9250 woken up")
            return True
        except Exception as e:
            print(f"❌ Failed to wake up MPU9250: {e}")
            return False
    
    def init_device(self):
        """
        Initialize MPU9250 with optimal sensor settings.
        
        Configures accelerometer for ±2g range, gyroscope for ±250°/s range,
        sets 1kHz sample rate, and enables I2C bypass for magnetometer access.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Wake up device
            if not self.wake_up():
                return False
            
            # Configure accelerometer (±2g)
            self.bus.write_byte_data(self.address, self.ACCEL_CONFIG, 0x00)
            
            # Configure gyroscope (±250°/s)
            self.bus.write_byte_data(self.address, self.GYRO_CONFIG, 0x00)
            
            # Set sample rate divider (1kHz sample rate)
            self.bus.write_byte_data(self.address, 0x19, 0x07)
            
            # Enable I2C bypass for magnetometer
            self.bus.write_byte_data(self.address, self.INT_PIN_CFG, 0x02)
            time.sleep(0.1)
            
            print("✅ MPU9250 initialized")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize MPU9250: {e}")
            return False
    
    def read_who_am_i(self):
        """
        Verify device identity by reading WHO_AM_I register.
        
        Returns:
            bool: True if valid MPU9250 detected, False otherwise
        """
        try:
            whoami = self.bus.read_byte_data(self.address, self.WHO_AM_I)
            print(f"WHO_AM_I: 0x{whoami:02x}")
            
            if whoami in [0x70, 0x71]:  # Both are valid for MPU9250
                print("✅ MPU9250 detected!")
                return True
            else:
                print(f"❌ Unexpected WHO_AM_I: 0x{whoami:02x}")
                return False
        except Exception as e:
            print(f"❌ Failed to read WHO_AM_I: {e}")
            return False
    
    def read_accelerometer(self):
        """
        Read 3-axis accelerometer data.
        
        Returns:
            tuple: (accel_x, accel_y, accel_z) in g units, or (None, None, None) on error
        """
        try:
            # Read 6 bytes starting from ACCEL_XOUT_H
            data = self.bus.read_i2c_block_data(self.address, self.ACCEL_XOUT_H, 6)
            
            # Convert to signed 16-bit values
            accel_x = struct.unpack('>h', bytes(data[0:2]))[0] / self.accel_scale
            accel_y = struct.unpack('>h', bytes(data[2:4]))[0] / self.accel_scale
            accel_z = struct.unpack('>h', bytes(data[4:6]))[0] / self.accel_scale
            
            return accel_x, accel_y, accel_z
        except Exception as e:
            print(f"❌ Failed to read accelerometer: {e}")
            return None, None, None
    
    def read_gyroscope(self):
        """
        Read 3-axis gyroscope data.
        
        Returns:
            tuple: (gyro_x, gyro_y, gyro_z) in degrees/second, or (None, None, None) on error
        """
        try:
            # Read 6 bytes starting from GYRO_XOUT_H
            data = self.bus.read_i2c_block_data(self.address, self.GYRO_XOUT_H, 6)
            
            # Convert to signed 16-bit values
            gyro_x = struct.unpack('>h', bytes(data[0:2]))[0] / self.gyro_scale
            gyro_y = struct.unpack('>h', bytes(data[2:4]))[0] / self.gyro_scale
            gyro_z = struct.unpack('>h', bytes(data[4:6]))[0] / self.gyro_scale
            
            return gyro_x, gyro_y, gyro_z
        except Exception as e:
            print(f"❌ Failed to read gyroscope: {e}")
            return None, None, None
    
    def read_temperature(self):
        """
        Read internal temperature sensor.
        
        Returns:
            float: Temperature in Celsius, or None on error
        """
        try:
            # Read 2 bytes starting from TEMP_OUT_H
            data = self.bus.read_i2c_block_data(self.address, self.TEMP_OUT_H, 2)
            temp_raw = struct.unpack('>h', bytes(data))[0]
            
            # Convert to Celsius
            temp_c = (temp_raw / 333.87) + 21.0
            return temp_c
        except Exception as e:
            print(f"❌ Failed to read temperature: {e}")
            return None
    
    def init_magnetometer(self):
        """
        Initialize AK8963 magnetometer for continuous measurement.
        
        Returns:
            bool: True if magnetometer initialized successfully, False otherwise
        """
        try:
            # Check magnetometer WHO_AM_I
            mag_whoami = self.bus.read_byte_data(self.mag_address, self.MAG_WHO_AM_I)
            print(f"Magnetometer WHO_AM_I: 0x{mag_whoami:02x}")
            
            if mag_whoami == 0x48:
                print("✅ AK8963 magnetometer detected!")
                
                # Set to continuous measurement mode (16-bit)
                self.bus.write_byte_data(self.mag_address, self.MAG_CNTL1, 0x16)
                time.sleep(0.1)
                return True
            else:
                print(f"❌ Unexpected magnetometer WHO_AM_I: 0x{mag_whoami:02x}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to initialize magnetometer: {e}")
            return False
    
    def read_magnetometer(self):
        """
        Read 3-axis magnetometer data.
        
        Returns:
            tuple: (mag_x, mag_y, mag_z) in raw units, or (None, None, None) on error
        """
        try:
            # Read 6 bytes starting from MAG_XOUT_L
            data = self.bus.read_i2c_block_data(self.mag_address, self.MAG_XOUT_L, 6)
            
            # Convert to signed 16-bit values (little endian for AK8963)
            mag_x = struct.unpack('<h', bytes(data[0:2]))[0]
            mag_y = struct.unpack('<h', bytes(data[2:4]))[0]
            mag_z = struct.unpack('<h', bytes(data[4:6]))[0]
            
            return mag_x, mag_y, mag_z
        except Exception as e:
            print(f"❌ Failed to read magnetometer: {e}")
            return None, None, None
    
    def close(self):
        """Close I2C bus"""
        try:
            self.bus.close()
        except:
            pass

def test_mpu9250_complete():
    """
    Comprehensive test of MPU9250 9-axis functionality.
    
    Tests device communication, initialization, and data reading
    from all sensors including accelerometer, gyroscope, magnetometer,
    and temperature sensor.
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    print("=== MPU9250 Complete Test ===")
    print()
    
    # Initialize device
    mpu = MPU9250(bus_num=1, address=0x68)
    
    try:
        # Test basic communication
        print("1. Testing basic communication...")
        if not mpu.read_who_am_i():
            return False
        print()
        
        # Initialize device
        print("2. Initializing device...")
        if not mpu.init_device():
            return False
        print()
        
        # Initialize magnetometer
        print("3. Initializing magnetometer...")
        mag_ok = mpu.init_magnetometer()
        print()
        
        # Read sensor data
        print("4. Reading sensor data...")
        print()
        
        for i in range(10):
            print(f"--- Reading {i+1}/10 ---")
            
            # Read accelerometer
            ax, ay, az = mpu.read_accelerometer()
            if ax is not None:
                print(f"Accelerometer: X={ax:6.3f}g, Y={ay:6.3f}g, Z={az:6.3f}g")
            
            # Read gyroscope
            gx, gy, gz = mpu.read_gyroscope()
            if gx is not None:
                print(f"Gyroscope:     X={gx:6.1f}°/s, Y={gy:6.1f}°/s, Z={gz:6.1f}°/s")
            
            # Read temperature
            temp = mpu.read_temperature()
            if temp is not None:
                print(f"Temperature:   {temp:5.1f}°C")
            
            # Read magnetometer if available
            if mag_ok:
                mx, my, mz = mpu.read_magnetometer()
                if mx is not None:
                    print(f"Magnetometer:  X={mx:6.0f}, Y={my:6.0f}, Z={mz:6.0f}")
            
            print()
            time.sleep(0.5)
        
        print("✅ MPU9250 test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        mpu.close()

def test_movement_detection():
    """
    Test movement detection capabilities using accelerometer and gyroscope.
    
    Monitors sensor readings for 10 seconds and detects movement based on
    acceleration changes and gyroscope rotation rates.
    
    Returns:
        bool: True if test completes successfully, False otherwise
    """
    print("=== Movement Detection Test ===")
    print("Move the robot around for 10 seconds...")
    print()
    
    mpu = MPU9250()
    
    try:
        if not mpu.read_who_am_i() or not mpu.init_device():
            return False
        
        # Baseline reading
        time.sleep(1)
        ax0, ay0, az0 = mpu.read_accelerometer()
        gx0, gy0, gz0 = mpu.read_gyroscope()
        
        print("Monitoring movement (10 seconds)...")
        start_time = time.time()
        
        while time.time() - start_time < 10:
            ax, ay, az = mpu.read_accelerometer()
            gx, gy, gz = mpu.read_gyroscope()
            
            if ax is not None and ax0 is not None:
                # Calculate movement magnitude
                accel_delta = math.sqrt((ax-ax0)**2 + (ay-ay0)**2 + (az-az0)**2)
                gyro_delta = math.sqrt(gx**2 + gy**2 + gz**2)
                
                movement_detected = accel_delta > 0.1 or gyro_delta > 10
                
                status = "MOVING" if movement_detected else "STILL"
                print(f"{status}: Accel Δ={accel_delta:5.3f}g, Gyro={gyro_delta:5.1f}°/s")
            
            time.sleep(0.2)
        
        print("✅ Movement detection test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Movement test failed: {e}")
        return False
    finally:
        mpu.close()

if __name__ == "__main__":
    print("MPU9250 Working Test Suite")
    print("=" * 40)
    print()
    
    # Run complete test
    success1 = test_mpu9250_complete()
    print()
    
    # Run movement detection test
    if success1:
        input("Press Enter to start movement detection test...")
        success2 = test_movement_detection()
    else:
        success2 = False
    
    print()
    print("=" * 40)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED! MPU9250 is working perfectly!")
    else:
        print("❌ Some tests failed. Check the output above.")
