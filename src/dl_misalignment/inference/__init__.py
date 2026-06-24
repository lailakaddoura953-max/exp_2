"""
Inference Module for Deep Learning Misalignment Detection

This module provides real-time inference capabilities for camera
misalignment detection using trained neural network models.

Key Components:
- InferenceEngine: Main inference pipeline
- ImagePreprocessor: Image preprocessing and normalization
- FourCameraBatchBuilder: 4-camera batch formation
- InferenceOutput: Structured output data
- CameraDetection: Per-camera detection result

Task 11: Inference Engine Implementation
Requirements: 9.1-9.6, 10.1-10.6, 13.1-13.6, 20.7, 22.1-22.6, 28.1-28.7
"""

from .inference_engine import InferenceEngine, load_inference_engine
from .preprocessing import (
    ImagePreprocessor,
    FourCameraBatchBuilder,
    denormalize_image,
    validate_batch_size
)
from .output_types import (
    CameraDetection,
    InferenceOutput,
    SeverityLevel,
    classify_severity,
    create_camera_detection,
    create_inference_output
)

__all__ = [
    # Main inference engine
    'InferenceEngine',
    'load_inference_engine',
    
    # Preprocessing
    'ImagePreprocessor',
    'FourCameraBatchBuilder',
    'denormalize_image',
    'validate_batch_size',
    
    # Output types
    'CameraDetection',
    'InferenceOutput',
    'SeverityLevel',
    'classify_severity',
    'create_camera_detection',
    'create_inference_output',
]
