"""
Camera Controller - Interface for camera systems.
"""

import cv2
import time
import threading
import numpy as np
from typing import Dict, List, Any, Optional

from utils.logger import setup_logger


class CameraController:
    """Controller for camera systems."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize camera controller.
        
        Args:
            config: Camera configuration dictionary
        """
        self.logger = setup_logger(__name__)
        self.config = config
        
        self.cameras: Dict[str, Dict] = {}
        self.is_initialized = False
        self.frame_lock = threading.Lock()
        
    def initialize(self):
        """Initialize camera devices."""
        try:
            for camera_config in self.config['devices']:
                camera_id = camera_config['id']
                camera_name = camera_config['name']
                
                # Initialize camera
                cap = cv2.VideoCapture(camera_id)
                
                if not cap.isOpened():
                    raise Exception(f"Failed to open camera {camera_name} (ID: {camera_id})")
                
                # Set camera properties
                resolution = camera_config.get('resolution', [640, 480])
                fps = camera_config.get('fps', 30)
                
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
                cap.set(cv2.CAP_PROP_FPS, fps)
                
                # Store camera info
                self.cameras[camera_name] = {
                    'id': camera_id,
                    'capture': cap,
                    'resolution': resolution,
                    'fps': fps,
                    'latest_frame': None,
                    'frame_timestamp': 0
                }
                
                self.logger.info(f"Camera {camera_name} (ID: {camera_id}) initialized")
            
            self.is_initialized = True
            self.logger.info("Camera controller initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize camera controller: {e}")
            raise
    
    def capture_frame(self, camera_name: str) -> Optional[np.ndarray]:
        """Capture a frame from specified camera.
        
        Args:
            camera_name: Name of the camera
            
        Returns:
            Captured frame as numpy array or None if error
        """
        if not self.is_initialized or camera_name not in self.cameras:
            return None
        
        camera = self.cameras[camera_name]
        cap = camera['capture']
        
        ret, frame = cap.read()
        if not ret:
            self.logger.warning(f"Failed to capture frame from camera {camera_name}")
            return None
        
        # Update stored frame
        with self.frame_lock:
            camera['latest_frame'] = frame.copy()
            camera['frame_timestamp'] = time.time()
        
        return frame
    
    def get_latest_frame(self, camera_name: str) -> Optional[np.ndarray]:
        """Get the latest captured frame.
        
        Args:
            camera_name: Name of the camera
            
        Returns:
            Latest frame or None if not available
        """
        if camera_name not in self.cameras:
            return None
        
        with self.frame_lock:
            return self.cameras[camera_name]['latest_frame']
    
    def capture_all_frames(self) -> Dict[str, np.ndarray]:
        """Capture frames from all cameras.
        
        Returns:
            Dictionary mapping camera names to frames
        """
        frames = {}
        
        for camera_name in self.cameras.keys():
            frame = self.capture_frame(camera_name)
            if frame is not None:
                frames[camera_name] = frame
        
        return frames
    
    def save_frame(self, camera_name: str, filename: str) -> bool:
        """Save current frame to file.
        
        Args:
            camera_name: Name of the camera
            filename: Output filename
            
        Returns:
            True if successful, False otherwise
        """
        frame = self.get_latest_frame(camera_name)
        
        if frame is None:
            return False
        
        try:
            cv2.imwrite(filename, frame)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save frame: {e}")
            return False
    
    def get_camera_properties(self, camera_name: str) -> Optional[Dict[str, Any]]:
        """Get camera properties.
        
        Args:
            camera_name: Name of the camera
            
        Returns:
            Dictionary of camera properties or None
        """
        if camera_name not in self.cameras:
            return None
        
        camera = self.cameras[camera_name]
        cap = camera['capture']
        
        return {
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'brightness': cap.get(cv2.CAP_PROP_BRIGHTNESS),
            'contrast': cap.get(cv2.CAP_PROP_CONTRAST),
            'saturation': cap.get(cv2.CAP_PROP_SATURATION),
            'exposure': cap.get(cv2.CAP_PROP_EXPOSURE)
        }
    
    def set_camera_property(self, camera_name: str, property_name: str, value: float) -> bool:
        """Set camera property.
        
        Args:
            camera_name: Name of the camera
            property_name: Property name (e.g., 'brightness', 'contrast')
            value: Property value
            
        Returns:
            True if successful, False otherwise
        """
        if camera_name not in self.cameras:
            return False
        
        cap = self.cameras[camera_name]['capture']
        
        property_map = {
            'brightness': cv2.CAP_PROP_BRIGHTNESS,
            'contrast': cv2.CAP_PROP_CONTRAST,
            'saturation': cv2.CAP_PROP_SATURATION,
            'exposure': cv2.CAP_PROP_EXPOSURE,
            'gain': cv2.CAP_PROP_GAIN
        }
        
        if property_name not in property_map:
            return False
        
        return cap.set(property_map[property_name], value)
    
    def update(self):
        """Update camera frames - called from main loop."""
        self.capture_all_frames()
    
    def get_status(self) -> Dict[str, Any]:
        """Get camera system status.
        
        Returns:
            Status dictionary
        """
        status = {
            'initialized': self.is_initialized,
            'cameras': {}
        }
        
        for camera_name, camera in self.cameras.items():
            with self.frame_lock:
                frame_age = time.time() - camera['frame_timestamp'] if camera['frame_timestamp'] > 0 else None
            
            status['cameras'][camera_name] = {
                'id': camera['id'],
                'resolution': camera['resolution'],
                'fps': camera['fps'],
                'frame_age': frame_age,
                'has_frame': camera['latest_frame'] is not None
            }
        
        return status
    
    def shutdown(self):
        """Shutdown camera controller."""
        for camera_name, camera in self.cameras.items():
            cap = camera['capture']
            if cap.isOpened():
                cap.release()
            self.logger.info(f"Camera {camera_name} released")
        
        self.cameras.clear()
        self.is_initialized = False
        self.logger.info("Camera controller shutdown complete") 