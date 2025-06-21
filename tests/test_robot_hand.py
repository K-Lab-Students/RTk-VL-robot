#!/usr/bin/env python3
"""
Servo Control Test Suite

Simple servo motor testing using GPIO Zero library on Raspberry Pi.
Tests basic servo positioning and movement patterns.

Requirements:
    sudo apt update
    sudo apt install python3-gpiozero

Hardware:
    Connect servo to BCM pin 12 (GPIO12) with common wire to GND.
"""

from gpiozero import Servo
from time import sleep


SERVO_PIN = 12
MIN_PULSE_WIDTH = 0.0005
MAX_PULSE_WIDTH = 0.0025


class ServoTester:
    """
    Servo motor testing interface using GPIO Zero.
    
    Provides simple servo control with predefined movement patterns
    for testing servo responsiveness and positioning accuracy.
    
    Attributes:
        servo: GPIO Zero Servo instance
        min_pulse_width: Minimum pulse width for 0° position
        max_pulse_width: Maximum pulse width for 180° position
    """
    
    def __init__(self, pin=SERVO_PIN, min_pw=MIN_PULSE_WIDTH, max_pw=MAX_PULSE_WIDTH):
        """
        Initialize servo controller.
        
        Args:
            pin: GPIO pin number (BCM numbering)
            min_pw: Minimum pulse width in seconds for 0° position
            max_pw: Maximum pulse width in seconds for 180° position
        """
        self.servo = Servo(pin, min_pulse_width=min_pw, max_pulse_width=max_pw)
        self.pin = pin
        
    def test_basic_positions(self):
        """
        Test basic servo positions with delays.
        
        Moves servo through minimum, center, and maximum positions
        with appropriate delays for movement completion.
        """
        try:
            while True:
                print(f"Position: 0° (minimum) on pin {self.pin}")
                self.servo.min()
                sleep(1)

                print(f"Position: 90° (center) on pin {self.pin}")
                self.servo.mid()
                sleep(1)

                print(f"Position: 180° (maximum) on pin {self.pin}")
                self.servo.max()
                sleep(1)
                
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            
    def test_sweep_pattern(self):
        """
        Test continuous sweep pattern.
        
        Performs smooth sweeping motion between minimum and maximum
        positions to test servo responsiveness.
        """
        try:
            print(f"Starting sweep pattern on pin {self.pin}")
            
            while True:
                for position in range(-100, 101, 5):
                    self.servo.value = position / 100.0
                    sleep(0.05)
                    
                for position in range(100, -101, -5):
                    self.servo.value = position / 100.0
                    sleep(0.05)
                    
        except KeyboardInterrupt:
            print("\nSweep test interrupted by user")
            
    def cleanup(self):
        """Safely detach servo and cleanup GPIO resources."""
        self.servo.detach()
        print("Servo detached and GPIO cleaned up")


def main():
    """
    Main servo testing function.
    
    Creates servo tester instance and runs basic position test.
    Handles cleanup on exit or interruption.
    """
    tester = ServoTester()
    
    try:
        print("Starting servo test...")
        print("Press Ctrl+C to exit")
        tester.test_basic_positions()
        
    except KeyboardInterrupt:
        print("\nExiting...")
        
    finally:
        tester.cleanup()
        print("Test complete")


if __name__ == '__main__':
    main()
