"""
Vision Processor - Computer vision processing and analysis.
"""

import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

from utils.logger import setup_logger


class VisionProcessor:
    """Computer vision processor for image analysis and object detection."""
    
    def __init__(self, camera_controller=None, npu_controller=None, config: Dict[str, Any] = None):
        """Initialize vision processor.
        
        Args:
            camera_controller: Camera controller instance
            npu_controller: NPU controller instance
            config: Vision configuration dictionary
        """
        self.logger = setup_logger(__name__)
        self.camera_controller = camera_controller
        self.npu_controller = npu_controller
        self.config = config or {}
        
        # Detection settings
        self.confidence_threshold = self.config.get('object_detection', {}).get('confidence_threshold', 0.5)
        self.nms_threshold = self.config.get('object_detection', {}).get('nms_threshold', 0.4)
        
        # Processing state
        self.latest_detections: List[Dict[str, Any]] = []
        self.latest_frame: Optional[np.ndarray] = None
        
    def process_frame(self, camera_name: str = 'front_camera') -> bool:
        """Process the latest frame from specified camera.
        
        Args:
            camera_name: Name of the camera to process
            
        Returns:
            True if processing successful, False otherwise
        """
        if not self.camera_controller:
            return False
        
        # Get latest frame
        frame = self.camera_controller.get_latest_frame(camera_name)
        if frame is None:
            return False
        
        self.latest_frame = frame.copy()
        
        # Perform object detection if enabled
        if self.config.get('object_detection', {}).get('enabled', False):
            self.latest_detections = self.detect_objects(frame)
        
        return True
    
    def detect_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect objects in the given frame.
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            List of detected objects
        """
        detections = []
        
        if self.npu_controller and self.npu_controller.is_initialized:
            # Use NPU for object detection
            detections = self.npu_controller.detect_objects(frame, self.confidence_threshold)
        else:
            # Fallback to OpenCV-based detection
            detections = self._detect_objects_opencv(frame)
        
        return detections
    
    def _detect_objects_opencv(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Fallback object detection using OpenCV.
        
        Args:
            frame: Input frame
            
        Returns:
            List of detected objects
        """
        detections = []
        
        # Simple color-based detection example (detect red objects)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Define range for red color
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 50, 50])
        upper_red2 = np.array([180, 255, 255])
        
        # Create masks
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = mask1 + mask2
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:  # Minimum area threshold
                x, y, w, h = cv2.boundingRect(contour)
                detections.append({
                    'bbox': [x, y, x + w, y + h],
                    'confidence': 0.8,  # Fixed confidence for color detection
                    'class_id': 0,  # Generic object class
                    'class_name': 'red_object'
                })
        
        return detections
    
    def detect_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect faces in the given frame.
        
        Args:
            frame: Input frame
            
        Returns:
            List of detected faces
        """
        faces = []
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Load Haar cascade for face detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces
        detected_faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        for (x, y, w, h) in detected_faces:
            faces.append({
                'bbox': [x, y, x + w, y + h],
                'confidence': 0.9,  # Fixed confidence for Haar cascade
                'type': 'face'
            })
        
        return faces
    
    def track_objects(self, frame: np.ndarray, previous_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Track objects between frames.
        
        Args:
            frame: Current frame
            previous_detections: Detections from previous frame
            
        Returns:
            Updated detections with tracking IDs
        """
        # Simple tracking based on bounding box overlap
        # In a real implementation, you might use more sophisticated tracking algorithms
        
        current_detections = self.detect_objects(frame)
        
        for current_det in current_detections:
            best_match = None
            best_overlap = 0
            
            for prev_det in previous_detections:
                overlap = self._calculate_bbox_overlap(current_det['bbox'], prev_det['bbox'])
                if overlap > best_overlap and overlap > 0.3:  # Minimum overlap threshold
                    best_overlap = overlap
                    best_match = prev_det
            
            if best_match:
                current_det['track_id'] = best_match.get('track_id', 0)
            else:
                # Assign new track ID
                current_det['track_id'] = len(previous_detections) + len(current_detections)
        
        return current_detections
    
    def _calculate_bbox_overlap(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Calculate overlap between two bounding boxes.
        
        Args:
            bbox1: First bounding box [x1, y1, x2, y2]
            bbox2: Second bounding box [x1, y1, x2, y2]
            
        Returns:
            Overlap ratio (0-1)
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def draw_detections(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """Draw detection results on frame.
        
        Args:
            frame: Input frame
            detections: List of detections to draw
            
        Returns:
            Frame with drawn detections
        """
        result_frame = frame.copy()
        
        for detection in detections:
            bbox = detection['bbox']
            confidence = detection['confidence']
            class_name = detection.get('class_name', f"Class {detection.get('class_id', 'Unknown')}")
            
            x1, y1, x2, y2 = map(int, bbox)
            
            # Draw bounding box
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(result_frame, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), (0, 255, 0), -1)
            cv2.putText(result_frame, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return result_frame
    
    def get_latest_detections(self) -> List[Dict[str, Any]]:
        """Get the latest detection results.
        
        Returns:
            List of latest detections
        """
        return self.latest_detections.copy()
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest processed frame.
        
        Returns:
            Latest frame or None
        """
        return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def shutdown(self):
        """Shutdown vision processor."""
        self.latest_detections.clear()
        self.latest_frame = None
        self.logger.info("Vision processor shutdown complete") 