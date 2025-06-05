"""
NPU Controller - Interface for Neural Processing Units.
"""

import time
import numpy as np
from typing import Dict, List, Any, Optional
from pathlib import Path

from utils.logger import setup_logger


class NPUController:
    """Controller for Neural Processing Units (NPU)."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize NPU controller.
        
        Args:
            config: NPU configuration dictionary
        """
        self.logger = setup_logger(__name__)
        self.config = config
        
        self.npu_type = config.get('type', 'cpu')
        self.model_path = config.get('model_path', '')
        
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.is_initialized = False
        
    def initialize(self):
        """Initialize NPU and load models."""
        try:
            if self.npu_type == 'coral':
                self._initialize_coral()
            elif self.npu_type == 'jetson':
                self._initialize_jetson()
            else:
                self._initialize_cpu()
            
            self.is_initialized = True
            self.logger.info(f"NPU controller initialized successfully (type: {self.npu_type})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NPU controller: {e}")
            raise
    
    def _initialize_coral(self):
        """Initialize Google Coral Edge TPU."""
        try:
            from pycoral.utils import edgetpu
            from pycoral.adapters import common
            import tflite_runtime.interpreter as tflite
            
            # Initialize Edge TPU interpreter
            self.interpreter = tflite.Interpreter(
                model_path=self.model_path,
                experimental_delegates=[edgetpu.make_edgetpu_delegate()]
            )
            
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            self.logger.info("Coral Edge TPU initialized")
            
        except ImportError:
            raise Exception("Coral libraries not installed. Install pycoral and tflite-runtime.")
    
    def _initialize_jetson(self):
        """Initialize NVIDIA Jetson NPU."""
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit
            
            # Initialize TensorRT engine
            # This is a simplified example - actual implementation would be more complex
            self.logger.info("Jetson NPU initialization placeholder")
            
        except ImportError:
            raise Exception("TensorRT libraries not installed.")
    
    def _initialize_cpu(self):
        """Initialize CPU-based inference."""
        try:
            import tensorflow as tf
            
            # Load TensorFlow Lite model for CPU inference
            if Path(self.model_path).exists():
                self.interpreter = tf.lite.Interpreter(model_path=self.model_path)
                self.interpreter.allocate_tensors()
                self.input_details = self.interpreter.get_input_details()
                self.output_details = self.interpreter.get_output_details()
            
            self.logger.info("CPU inference initialized")
            
        except ImportError:
            self.logger.warning("TensorFlow not available, NPU disabled")
    
    def run_inference(self, input_data: np.ndarray) -> Optional[np.ndarray]:
        """Run inference on input data.
        
        Args:
            input_data: Input data as numpy array
            
        Returns:
            Inference results or None if error
        """
        if not self.is_initialized or self.interpreter is None:
            return None
        
        try:
            # Prepare input data
            input_shape = self.input_details[0]['shape']
            if input_data.shape != tuple(input_shape):
                # Resize input if necessary
                input_data = self._preprocess_input(input_data, input_shape)
            
            # Set input tensor
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            
            # Run inference
            start_time = time.time()
            self.interpreter.invoke()
            inference_time = time.time() - start_time
            
            # Get output
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            self.logger.debug(f"Inference completed in {inference_time:.3f}s")
            return output_data
            
        except Exception as e:
            self.logger.error(f"Inference failed: {e}")
            return None
    
    def _preprocess_input(self, input_data: np.ndarray, target_shape: tuple) -> np.ndarray:
        """Preprocess input data to match model requirements.
        
        Args:
            input_data: Original input data
            target_shape: Target shape for the model
            
        Returns:
            Preprocessed input data
        """
        # This is a basic preprocessing example
        # Actual preprocessing would depend on the specific model requirements
        
        if len(target_shape) == 4:  # Batch, Height, Width, Channels
            batch_size, height, width, channels = target_shape
            
            # Resize if necessary
            if input_data.shape[:2] != (height, width):
                import cv2
                input_data = cv2.resize(input_data, (width, height))
            
            # Add batch dimension if necessary
            if len(input_data.shape) == 3:
                input_data = np.expand_dims(input_data, axis=0)
            
            # Normalize to [0, 1] if needed
            if input_data.dtype == np.uint8:
                input_data = input_data.astype(np.float32) / 255.0
        
        return input_data
    
    def detect_objects(self, image: np.ndarray, confidence_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Detect objects in an image.
        
        Args:
            image: Input image as numpy array
            confidence_threshold: Minimum confidence for detections
            
        Returns:
            List of detected objects with bounding boxes and confidence scores
        """
        if not self.is_initialized:
            return []
        
        # Run inference
        output = self.run_inference(image)
        if output is None:
            return []
        
        # Parse detection results (this is model-specific)
        detections = []
        
        # Example parsing for a typical object detection model
        # Actual implementation would depend on the specific model format
        try:
            # Assuming output format: [batch, num_detections, 6] where 6 = [x1, y1, x2, y2, confidence, class]
            for detection in output[0]:
                confidence = detection[4]
                if confidence >= confidence_threshold:
                    detections.append({
                        'bbox': detection[:4].tolist(),  # [x1, y1, x2, y2]
                        'confidence': float(confidence),
                        'class_id': int(detection[5])
                    })
        except Exception as e:
            self.logger.error(f"Failed to parse detection results: {e}")
        
        return detections
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model.
        
        Returns:
            Model information dictionary
        """
        if not self.is_initialized or self.interpreter is None:
            return {}
        
        info = {
            'model_path': self.model_path,
            'npu_type': self.npu_type
        }
        
        if self.input_details:
            info['input_shape'] = self.input_details[0]['shape'].tolist()
            info['input_dtype'] = str(self.input_details[0]['dtype'])
        
        if self.output_details:
            info['output_shape'] = self.output_details[0]['shape'].tolist()
            info['output_dtype'] = str(self.output_details[0]['dtype'])
        
        return info
    
    def get_status(self) -> Dict[str, Any]:
        """Get NPU status.
        
        Returns:
            Status dictionary
        """
        return {
            'initialized': self.is_initialized,
            'npu_type': self.npu_type,
            'model_loaded': self.interpreter is not None,
            'model_path': self.model_path
        }
    
    def shutdown(self):
        """Shutdown NPU controller."""
        if self.interpreter:
            # Clean up interpreter resources
            self.interpreter = None
        
        self.input_details = None
        self.output_details = None
        self.is_initialized = False
        
        self.logger.info("NPU controller shutdown complete") 