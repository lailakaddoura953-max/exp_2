"""
Inference Output Data Structures

This module defines structured output types for inference results.

Key Components:
1. CameraDetection: Per-camera detection result
2. InferenceOutput: Complete 4-camera batch result
3. JSON serialization support

Task 11.4: Output Data Structures and Serialization
Requirements: 10.1, 10.6, 11.7, 12.4, 13.5, 28.1-28.7
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ==============================================================================
# Severity Level Classification
# ==============================================================================

class SeverityLevel(Enum):
    """
    Misalignment severity classification.
    
    Based on probability thresholds:
    - NONE:     < 0.25 (no action needed)
    - LOW:      0.25-0.50 (monitor)
    - MEDIUM:   0.50-0.75 (investigate)
    - HIGH:     0.75-0.90 (alert)
    - CRITICAL: 0.90-1.00 (immediate action)
    
    Requirements: 11.1-11.6
    """
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def classify_severity(probability: float) -> SeverityLevel:
    """
    Classify severity from probability.
    
    Args:
        probability: Misalignment probability [0, 1]
    
    Returns:
        SeverityLevel enum
    
    Requirements: 11.2-11.6
    """
    if probability < 0.25:
        return SeverityLevel.NONE
    elif probability < 0.50:
        return SeverityLevel.LOW
    elif probability < 0.75:
        return SeverityLevel.MEDIUM
    elif probability < 0.90:
        return SeverityLevel.HIGH
    else:
        return SeverityLevel.CRITICAL


# ==============================================================================
# Task 11.4: Camera Detection Data Structure
# ==============================================================================

@dataclass
class CameraDetection:
    """
    Detection result for a single camera.
    
    Contains all information about misalignment detection for one camera:
    - Probability: continuous score [0, 1]
    - Severity: categorical level (NONE, LOW, MEDIUM, HIGH, CRITICAL)
    - Pose: 6-DOF camera position and orientation
    - Uncertainty: optional confidence estimate
    - Flags: low-confidence warning
    
    Requirements: 10.1, 10.6, 11.7, 12.4, 13.5, 28.2
    """
    
    # Camera identifier
    camera_id: str
    
    # Primary detection outputs
    misalignment_probability: float  # [0, 1]
    severity_level: str  # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    
    # 6-DOF camera pose estimate
    position: Dict[str, float]  # {"X": float, "Y": float, "Z": float} in meters
    orientation: Dict[str, float]  # {"roll": float, "pitch": float, "yaw": float} in degrees
    
    # Optional uncertainty estimates
    probability_uncertainty: Optional[float] = None  # Standard deviation
    pose_uncertainty: Optional[Dict[str, float]] = None  # Std dev per DOF
    
    # Confidence flag
    low_confidence: bool = False  # True if uncertainty > 0.2
    
    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation
        
        Requirements: 28.3
        """
        return asdict(self)
    
    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"CameraDetection(camera_id={self.camera_id}, "
            f"probability={self.misalignment_probability:.3f}, "
            f"severity={self.severity_level})"
        )


# ==============================================================================
# Task 11.4: Inference Output Data Structure
# ==============================================================================

@dataclass
class InferenceOutput:
    """
    Complete inference output for 4-camera batch.
    
    Contains:
    - Per-camera detection results
    - Global metadata (timestamp, model version, timing)
    - JSON serialization support
    
    Requirements: 10.6, 11.7, 28.1-28.7
    """
    
    # Per-camera results
    camera_results: Dict[str, CameraDetection]  # camera_id → CameraDetection
    
    # Global metadata
    timestamp: float  # Unix timestamp
    model_version: str  # Model version identifier
    processing_time_ms: float  # Total inference time in milliseconds
    
    # Optional fields
    architecture: Optional[str] = None  # "architecture_a" or "architecture_b"
    mode: Optional[str] = None  # "neural_network", "rule_based", or "hybrid"
    checkpoint_path: Optional[str] = None  # Path to model checkpoint
    
    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary with all inference results
        
        Requirements: 28.3, 28.4
        """
        return {
            'camera_results': {
                camera_id: detection.to_dict()
                for camera_id, detection in self.camera_results.items()
            },
            'timestamp': self.timestamp,
            'timestamp_iso': datetime.fromtimestamp(self.timestamp).isoformat(),
            'model_version': self.model_version,
            'processing_time_ms': self.processing_time_ms,
            'architecture': self.architecture,
            'mode': self.mode,
            'checkpoint_path': self.checkpoint_path
        }
    
    def to_json(self, indent: int = 2) -> str:
        """
        Serialize to JSON string.
        
        Args:
            indent: JSON indentation level (default: 2)
        
        Returns:
            JSON string representation
        
        Requirements: 28.5, 28.6
        
        Example:
            >>> output = InferenceOutput(
            ...     camera_results={'front': CameraDetection(...)},
            ...     timestamp=1234567890.0,
            ...     model_version='1.0.0',
            ...     processing_time_ms=85.5
            ... )
            >>> json_str = output.to_json()
            >>> 'camera_results' in json_str
            True
        """
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'InferenceOutput':
        """
        Create InferenceOutput from dictionary.
        
        Args:
            data: Dictionary representation
        
        Returns:
            InferenceOutput instance
        """
        # Reconstruct camera results
        camera_results = {}
        for camera_id, detection_dict in data['camera_results'].items():
            camera_results[camera_id] = CameraDetection(**detection_dict)
        
        return cls(
            camera_results=camera_results,
            timestamp=data['timestamp'],
            model_version=data['model_version'],
            processing_time_ms=data['processing_time_ms'],
            architecture=data.get('architecture'),
            mode=data.get('mode'),
            checkpoint_path=data.get('checkpoint_path')
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'InferenceOutput':
        """
        Deserialize from JSON string.
        
        Args:
            json_str: JSON string representation
        
        Returns:
            InferenceOutput instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_camera_detection(self, camera_id: str) -> Optional[CameraDetection]:
        """
        Get detection result for specific camera.
        
        Args:
            camera_id: Camera identifier
        
        Returns:
            CameraDetection or None if not found
        """
        return self.camera_results.get(camera_id)
    
    def get_max_severity(self) -> SeverityLevel:
        """
        Get maximum severity across all cameras.
        
        Returns:
            Highest severity level detected
        
        Example:
            >>> output = InferenceOutput(...)
            >>> max_severity = output.get_max_severity()
            >>> max_severity
            <SeverityLevel.HIGH: 'HIGH'>
        """
        severity_order = {
            SeverityLevel.NONE: 0,
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4
        }
        
        max_severity = SeverityLevel.NONE
        max_level = 0
        
        for detection in self.camera_results.values():
            severity = SeverityLevel(detection.severity_level)
            level = severity_order[severity]
            if level > max_level:
                max_severity = severity
                max_level = level
        
        return max_severity
    
    def has_misalignment(self, threshold: float = 0.5) -> bool:
        """
        Check if any camera detected misalignment above threshold.
        
        Args:
            threshold: Probability threshold (default: 0.5)
        
        Returns:
            True if any camera has probability > threshold
        
        Requirements: 10.5, 10.6
        """
        for detection in self.camera_results.values():
            if detection.misalignment_probability > threshold:
                return True
        return False
    
    def get_misaligned_cameras(self, threshold: float = 0.5) -> List[str]:
        """
        Get list of camera IDs with misalignment above threshold.
        
        Args:
            threshold: Probability threshold (default: 0.5)
        
        Returns:
            List of camera IDs
        """
        misaligned = []
        for camera_id, detection in self.camera_results.items():
            if detection.misalignment_probability > threshold:
                misaligned.append(camera_id)
        return misaligned
    
    def get_low_confidence_cameras(self) -> List[str]:
        """
        Get list of camera IDs with low-confidence predictions.
        
        Returns:
            List of camera IDs flagged as low confidence
        
        Requirements: 13.4, 13.5
        """
        low_conf = []
        for camera_id, detection in self.camera_results.items():
            if detection.low_confidence:
                low_conf.append(camera_id)
        return low_conf
    
    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"InferenceOutput(cameras={len(self.camera_results)}, "
            f"processing_time={self.processing_time_ms:.1f}ms, "
            f"max_severity={self.get_max_severity().value})"
        )


# ==============================================================================
# Helper Functions
# ==============================================================================

def create_camera_detection(
    camera_id: str,
    probability: float,
    pose: List[float],  # [X, Y, Z, roll, pitch, yaw]
    probability_uncertainty: Optional[float] = None,
    pose_uncertainty: Optional[List[float]] = None,
    confidence_threshold: float = 0.2
) -> CameraDetection:
    """
    Create CameraDetection from raw inference outputs.
    
    Args:
        camera_id: Camera identifier
        probability: Misalignment probability [0, 1]
        pose: 6-DOF pose [X, Y, Z, roll, pitch, yaw]
        probability_uncertainty: Optional probability std dev
        pose_uncertainty: Optional pose std dev per dimension
        confidence_threshold: Threshold for low-confidence flag
    
    Returns:
        CameraDetection instance
    
    Requirements: 10.1-10.6, 11.1-11.7, 12.4, 13.5
    
    Example:
        >>> detection = create_camera_detection(
        ...     camera_id='front',
        ...     probability=0.75,
        ...     pose=[0.1, 0.05, 0.0, 2.5, -1.0, 0.5]
        ... )
        >>> detection.severity_level
        'HIGH'
    """
    # Classify severity
    severity = classify_severity(probability)
    
    # Parse pose
    position = {
        'X': float(pose[0]),
        'Y': float(pose[1]),
        'Z': float(pose[2])
    }
    orientation = {
        'roll': float(pose[3]),
        'pitch': float(pose[4]),
        'yaw': float(pose[5])
    }
    
    # Parse pose uncertainty if provided
    pose_unc_dict = None
    if pose_uncertainty is not None:
        pose_unc_dict = {
            'X': float(pose_uncertainty[0]),
            'Y': float(pose_uncertainty[1]),
            'Z': float(pose_uncertainty[2]),
            'roll': float(pose_uncertainty[3]),
            'pitch': float(pose_uncertainty[4]),
            'yaw': float(pose_uncertainty[5])
        }
    
    # Check if low confidence
    low_conf = False
    if probability_uncertainty is not None:
        low_conf = probability_uncertainty > confidence_threshold
    
    return CameraDetection(
        camera_id=camera_id,
        misalignment_probability=float(probability),
        severity_level=severity.value,
        position=position,
        orientation=orientation,
        probability_uncertainty=float(probability_uncertainty) if probability_uncertainty is not None else None,
        pose_uncertainty=pose_unc_dict,
        low_confidence=low_conf
    )


def create_inference_output(
    camera_detections: List[CameraDetection],
    processing_time_ms: float,
    model_version: str = "1.0.0",
    architecture: Optional[str] = None,
    mode: Optional[str] = None,
    checkpoint_path: Optional[str] = None
) -> InferenceOutput:
    """
    Create InferenceOutput from camera detections.
    
    Args:
        camera_detections: List of CameraDetection instances
        processing_time_ms: Total processing time in milliseconds
        model_version: Model version string
        architecture: Architecture identifier (optional)
        mode: Operation mode (optional)
        checkpoint_path: Model checkpoint path (optional)
    
    Returns:
        InferenceOutput instance
    
    Requirements: 28.1-28.7
    """
    # Convert list to dictionary
    camera_results = {
        detection.camera_id: detection
        for detection in camera_detections
    }
    
    return InferenceOutput(
        camera_results=camera_results,
        timestamp=datetime.now().timestamp(),
        model_version=model_version,
        processing_time_ms=processing_time_ms,
        architecture=architecture,
        mode=mode,
        checkpoint_path=checkpoint_path
    )
