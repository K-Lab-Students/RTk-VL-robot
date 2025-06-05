"""
LiDAR Controller - Interface for LiDAR sensors.
"""

import time
import threading
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from rplidar import RPLidar

from utils.logger import setup_logger


class LidarController:
    """Controller for LiDAR sensors."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize LiDAR controller.
        
        Args:
            config: LiDAR configuration dictionary
        """
        self.logger = setup_logger(__name__)
        self.config = config
        
        self.lidar = None
        self.is_initialized = False
        self.is_scanning = False
        
        # Scan data
        self.scan_data: List[Tuple[float, float, float]] = []  # (quality, angle, distance)
        self.scan_lock = threading.Lock()
        self.scan_thread: Optional[threading.Thread] = None
        
    def initialize(self):
        """Initialize LiDAR communication."""
        try:
            # Initialize RPLiDAR
            self.lidar = RPLidar(self.config['port'])
            
            # Get device info
            info = self.lidar.get_info()
            self.logger.info(f"LiDAR Info: {info}")
            
            # Get health status
            health = self.lidar.get_health()
            self.logger.info(f"LiDAR Health: {health}")
            
            if health[0] != 'Good':
                self.logger.warning(f"LiDAR health status: {health}")
            
            self.is_initialized = True
            self.logger.info("LiDAR controller initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LiDAR controller: {e}")
            raise
    
    def start_scanning(self):
        """Start LiDAR scanning."""
        if not self.is_initialized or self.is_scanning:
            return False
        
        try:
            self.is_scanning = True
            self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
            self.scan_thread.start()
            
            self.logger.info("LiDAR scanning started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start LiDAR scanning: {e}")
            self.is_scanning = False
            return False
    
    def stop_scanning(self):
        """Stop LiDAR scanning."""
        if not self.is_scanning:
            return
        
        self.is_scanning = False
        
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=2.0)
        
        if self.lidar:
            self.lidar.stop()
        
        self.logger.info("LiDAR scanning stopped")
    
    def _scan_loop(self):
        """Main scanning loop running in separate thread."""
        try:
            for scan in self.lidar.iter_scans():
                if not self.is_scanning:
                    break
                
                # Filter and process scan data
                filtered_scan = []
                for quality, angle, distance in scan:
                    # Filter by quality and distance
                    if (quality > 10 and 
                        0.1 < distance < self.config.get('max_distance', 12.0) * 1000):
                        filtered_scan.append((quality, angle, distance / 1000.0))  # Convert to meters
                
                # Update scan data thread-safely
                with self.scan_lock:
                    self.scan_data = filtered_scan
                
        except Exception as e:
            self.logger.error(f"Error in LiDAR scan loop: {e}")
            self.is_scanning = False
    
    def get_scan_data(self) -> List[Tuple[float, float, float]]:
        """Get latest scan data.
        
        Returns:
            List of (quality, angle, distance) tuples
        """
        with self.scan_lock:
            return self.scan_data.copy()
    
    def get_cartesian_points(self) -> np.ndarray:
        """Get scan data as Cartesian coordinates.
        
        Returns:
            Numpy array of (x, y) points
        """
        scan_data = self.get_scan_data()
        
        if not scan_data:
            return np.array([]).reshape(0, 2)
        
        points = []
        for quality, angle, distance in scan_data:
            # Convert polar to Cartesian coordinates
            angle_rad = np.radians(angle)
            x = distance * np.cos(angle_rad)
            y = distance * np.sin(angle_rad)
            points.append([x, y])
        
        return np.array(points)
    
    def get_obstacles_in_direction(self, target_angle: float, angle_tolerance: float = 10.0) -> List[float]:
        """Get obstacles in a specific direction.
        
        Args:
            target_angle: Target angle in degrees
            angle_tolerance: Tolerance in degrees
            
        Returns:
            List of distances to obstacles in the specified direction
        """
        scan_data = self.get_scan_data()
        obstacles = []
        
        for quality, angle, distance in scan_data:
            angle_diff = abs(angle - target_angle)
            # Handle angle wraparound
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            
            if angle_diff <= angle_tolerance:
                obstacles.append(distance)
        
        return sorted(obstacles)
    
    def get_closest_obstacle(self) -> Optional[Tuple[float, float, float]]:
        """Get the closest obstacle.
        
        Returns:
            Tuple of (angle, distance, quality) for closest obstacle or None
        """
        scan_data = self.get_scan_data()
        
        if not scan_data:
            return None
        
        closest = min(scan_data, key=lambda x: x[2])  # Sort by distance
        return (closest[1], closest[2], closest[0])  # (angle, distance, quality)
    
    def is_path_clear(self, start_angle: float, end_angle: float, min_distance: float = 0.5) -> bool:
        """Check if a path is clear of obstacles.
        
        Args:
            start_angle: Start angle in degrees
            end_angle: End angle in degrees
            min_distance: Minimum safe distance in meters
            
        Returns:
            True if path is clear, False otherwise
        """
        scan_data = self.get_scan_data()
        
        # Normalize angles
        if start_angle > end_angle:
            start_angle, end_angle = end_angle, start_angle
        
        for quality, angle, distance in scan_data:
            if start_angle <= angle <= end_angle and distance < min_distance:
                return False
        
        return True
    
    def update(self):
        """Update LiDAR data - called from main loop."""
        if not self.is_scanning:
            self.start_scanning()
    
    def get_status(self) -> Dict[str, Any]:
        """Get LiDAR status.
        
        Returns:
            Status dictionary
        """
        scan_data = self.get_scan_data()
        
        status = {
            'initialized': self.is_initialized,
            'scanning': self.is_scanning,
            'scan_points': len(scan_data),
            'timestamp': time.time()
        }
        
        if scan_data:
            distances = [d for _, _, d in scan_data]
            status.update({
                'min_distance': min(distances),
                'max_distance': max(distances),
                'avg_distance': sum(distances) / len(distances)
            })
        
        return status
    
    def shutdown(self):
        """Shutdown LiDAR controller."""
        self.stop_scanning()
        
        if self.lidar:
            try:
                self.lidar.stop()
                self.lidar.disconnect()
            except:
                pass
        
        self.is_initialized = False
        self.logger.info("LiDAR controller shutdown complete") 