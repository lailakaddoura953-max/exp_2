"""
Core data models for the Camera Misalignment Detection System

This module defines all the data structures used throughout the system,
including validation logic to ensure data integrity.

Properties validated:
- Property 7: Camera ID Validity (all camera IDs in range [0, 3])
- Property 4: Universal Confidence Bounds (all confidence scores in [0.0, 1.0])
- Property 6: Displacement Metric Consistency
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime
import numpy as np
import uuid


class Severity(Enum):
    """Severity levels for misalignment events"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class CameraStatus(Enum):
    """Camera connection status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class CameraIntrinsics:
    """
    Camera intrinsic parameters for calibration
    
    Attributes:
        fx, fy: Focal lengths in pixels
        cx, cy: Principal point coordinates
        k1, k2, k3: Radial distortion coefficients
        p1, p2: Tangential distortion coefficients
    """
    fx: float
    fy: float
    cx: float
    cy: float
    k1: float = 0.0
    k2: float = 0.0
    p1: float = 0.0
    p2: float = 0.0
    k3: float = 0.0
    
    def __post_init__(self):
        """Validate intrinsic parameters"""
        if self.fx <= 0 or self.fy <= 0:
            raise ValueError(f"Focal lengths must be positive: fx={self.fx}, fy={self.fy}")
        if self.cx < 0 or self.cy < 0:
            raise ValueError(f"Principal point must be non-negative: cx={self.cx}, cy={self.cy}")


@dataclass
class CalibrationPose:
    """
    Camera pose in vehicle reference frame
    
    Attributes:
        position: 3D position [x, y, z] in meters
        orientation: Quaternion [w, x, y, z] representing rotation
    """
    position: np.ndarray  # 3D vector
    orientation: np.ndarray  # Quaternion [w, x, y, z]
    
    def __post_init__(self):
        """Validate pose data"""
        self.position = np.asarray(self.position, dtype=np.float64)
        self.orientation = np.asarray(self.orientation, dtype=np.float64)
        
        if self.position.shape != (3,):
            raise ValueError(f"Position must be 3D vector, got shape {self.position.shape}")
        
        if self.orientation.shape != (4,):
            raise ValueError(f"Orientation must be quaternion [w,x,y,z], got shape {self.orientation.shape}")
        
        # Normalize quaternion
        norm = np.linalg.norm(self.orientation)
        if norm > 0:
            self.orientation = self.orientation / norm


@dataclass
class CameraConfig:
    """
    Configuration for a single camera
    
    Validates:
        - Property 7: Camera ID must be in range [0, 3]
        - Resolution must have positive dimensions
        - FPS must be positive and <= 120
    """
    camera_id: int
    stream_url: str
    resolution: Tuple[int, int]  # (width, height)
    fps: int
    intrinsics: CameraIntrinsics
    calibration_pose: CalibrationPose
    
    def __post_init__(self):
        """Validate camera configuration"""
        # Property 7: Camera ID Validity
        if not (0 <= self.camera_id <= 3):
            raise ValueError(f"Camera ID must be in range [0, 3], got {self.camera_id}")
        
        # Validate resolution
        width, height = self.resolution
        if width <= 0 or height <= 0:
            raise ValueError(f"Resolution must have positive dimensions, got {self.resolution}")
        
        # Validate FPS
        if self.fps <= 0 or self.fps > 120:
            raise ValueError(f"FPS must be positive and <= 120, got {self.fps}")
        
        # Validate stream URL is not empty
        if not self.stream_url or not self.stream_url.strip():
            raise ValueError("Stream URL cannot be empty")


@dataclass
class FeatureSet:
    """
    Visual features extracted from a camera frame
    
    Validates:
        - Property 2: Number of keypoints equals number of descriptor rows
        - Property 12: Timestamp association
        - Property 7: Camera ID validity
    """
    camera_id: int
    keypoints: List[Tuple[float, float]]  # List of (x, y) coordinates
    descriptors: np.ndarray  # NxM descriptor matrix
    timestamp: int  # microseconds
    
    def __post_init__(self):
        """Validate feature set"""
        # Property 7: Camera ID Validity
        if not (0 <= self.camera_id <= 3):
            raise ValueError(f"Camera ID must be in range [0, 3], got {self.camera_id}")
        
        # Convert descriptors to numpy array if needed
        if not isinstance(self.descriptors, np.ndarray):
            self.descriptors = np.asarray(self.descriptors)
        
        # Property 2: Feature-Descriptor Correspondence
        if len(self.keypoints) != self.descriptors.shape[0]:
            raise ValueError(
                f"Number of keypoints ({len(self.keypoints)}) must equal "
                f"number of descriptor rows ({self.descriptors.shape[0]})"
            )
        
        # Validate timestamp
        if self.timestamp < 0:
            raise ValueError(f"Timestamp must be non-negative, got {self.timestamp}")


@dataclass
class FlowResult:
    """
    Optical flow computation result
    
    Validates:
        - Property 4: Confidence values in [0.0, 1.0]
        - Property 8: Flow spatial dimensions
    """
    flow_vectors: np.ndarray  # 2-channel float array (dx, dy)
    confidence: np.ndarray  # Confidence per pixel [0.0, 1.0]
    mean_magnitude: float
    mean_direction: float
    frame_shape: Tuple[int, int]  # (height, width) for validation
    
    def __post_init__(self):
        """Validate flow result"""
        # Convert to numpy arrays
        self.flow_vectors = np.asarray(self.flow_vectors, dtype=np.float32)
        self.confidence = np.asarray(self.confidence, dtype=np.float32)
        
        # Property 8: Flow Spatial Dimension Preservation
        if self.flow_vectors.shape[:2] != self.frame_shape:
            raise ValueError(
                f"Flow vectors shape {self.flow_vectors.shape[:2]} must match "
                f"frame shape {self.frame_shape}"
            )
        
        if self.confidence.shape != self.frame_shape:
            raise ValueError(
                f"Confidence shape {self.confidence.shape} must match "
                f"frame shape {self.frame_shape}"
            )
        
        # Validate flow is 2-channel
        if len(self.flow_vectors.shape) != 3 or self.flow_vectors.shape[2] != 2:
            raise ValueError(
                f"Flow vectors must be 2-channel (dx, dy), got shape {self.flow_vectors.shape}"
            )
        
        # Property 4: Universal Confidence Bounds
        if not np.all((self.confidence >= 0.0) & (self.confidence <= 1.0)):
            raise ValueError("All confidence values must be in range [0.0, 1.0]")
        
        # Validate statistics
        if self.mean_magnitude < 0:
            raise ValueError(f"Mean magnitude must be non-negative, got {self.mean_magnitude}")


@dataclass
class PoseEstimate:
    """
    Camera pose estimate from SLAM or tracking
    
    Validates:
        - Property 7: Camera ID validity
        - Property 4: Confidence bounds
        - Property 3: Transformation validity (basic checks)
    """
    camera_id: int
    transformation: np.ndarray  # 4x4 homogeneous transformation matrix
    position: np.ndarray  # 3D position [x, y, z]
    orientation: np.ndarray  # Quaternion [w, x, y, z]
    confidence: float  # [0.0, 1.0]
    timestamp: int  # microseconds
    
    def __post_init__(self):
        """Validate pose estimate"""
        # Property 7: Camera ID Validity
        if not (0 <= self.camera_id <= 3):
            raise ValueError(f"Camera ID must be in range [0, 3], got {self.camera_id}")
        
        # Convert to numpy arrays
        self.transformation = np.asarray(self.transformation, dtype=np.float64)
        self.position = np.asarray(self.position, dtype=np.float64)
        self.orientation = np.asarray(self.orientation, dtype=np.float64)
        
        # Validate shapes
        if self.transformation.shape != (4, 4):
            raise ValueError(f"Transformation must be 4x4 matrix, got shape {self.transformation.shape}")
        
        if self.position.shape != (3,):
            raise ValueError(f"Position must be 3D vector, got shape {self.position.shape}")
        
        if self.orientation.shape != (4,):
            raise ValueError(f"Orientation must be quaternion [w,x,y,z], got shape {self.orientation.shape}")
        
        # Property 4: Universal Confidence Bounds
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be in range [0.0, 1.0], got {self.confidence}")
        
        # Validate timestamp
        if self.timestamp < 0:
            raise ValueError(f"Timestamp must be non-negative, got {self.timestamp}")
        
        # Basic transformation validity check (Property 3 - full validation in tests)
        # Check that bottom row is [0, 0, 0, 1]
        if not np.allclose(self.transformation[3, :], [0, 0, 0, 1]):
            raise ValueError("Transformation matrix bottom row must be [0, 0, 0, 1]")


@dataclass
class DisplacementMetrics:
    """
    Displacement metrics for misalignment detection
    
    Validates:
        - Property 6: Displacement metric consistency
    """
    position_delta: np.ndarray  # 3D vector [dx, dy, dz] in meters
    position_delta_magnitude: float  # Euclidean distance in meters
    angle_delta: np.ndarray  # 3D rotation [roll, pitch, yaw] in degrees
    angle_delta_magnitude: float  # Total rotation angle in degrees
    flow_inconsistency: float  # [0.0, 1.0]
    
    def __post_init__(self):
        """Validate displacement metrics"""
        # Convert to numpy arrays
        self.position_delta = np.asarray(self.position_delta, dtype=np.float64)
        self.angle_delta = np.asarray(self.angle_delta, dtype=np.float64)
        
        # Validate shapes
        if self.position_delta.shape != (3,):
            raise ValueError(f"Position delta must be 3D vector, got shape {self.position_delta.shape}")
        
        if self.angle_delta.shape != (3,):
            raise ValueError(f"Angle delta must be 3D vector, got shape {self.angle_delta.shape}")
        
        # Property 6: Displacement Metric Consistency
        computed_magnitude = np.linalg.norm(self.position_delta)
        if not np.isclose(self.position_delta_magnitude, computed_magnitude, atol=1e-6):
            raise ValueError(
                f"Position delta magnitude ({self.position_delta_magnitude}) must equal "
                f"Euclidean norm of position delta ({computed_magnitude})"
            )
        
        # Validate magnitude is non-negative
        if self.position_delta_magnitude < 0:
            raise ValueError(f"Position delta magnitude must be non-negative, got {self.position_delta_magnitude}")
        
        # Validate angle ranges
        if not np.all((self.angle_delta >= -180) & (self.angle_delta <= 180)):
            raise ValueError(f"Angle delta values must be in [-180, 180] degrees, got {self.angle_delta}")
        
        if not (0 <= self.angle_delta_magnitude <= 180):
            raise ValueError(f"Angle delta magnitude must be in [0, 180] degrees, got {self.angle_delta_magnitude}")
        
        # Validate flow inconsistency
        if not (0.0 <= self.flow_inconsistency <= 1.0):
            raise ValueError(f"Flow inconsistency must be in [0.0, 1.0], got {self.flow_inconsistency}")


@dataclass
class MisalignmentEvent:
    """
    Detected misalignment event
    
    Validates:
        - Property 7: Camera ID validity
        - Property 4: Confidence bounds
        - Property 15: Complete event structure
    """
    event_id: str
    camera_id: int
    timestamp: datetime
    severity: Severity
    displacement: DisplacementMetrics
    confidence: float  # [0.0, 1.0]
    diagnostic_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate misalignment event"""
        # Property 7: Camera ID Validity
        if not (0 <= self.camera_id <= 3):
            raise ValueError(f"Camera ID must be in range [0, 3], got {self.camera_id}")
        
        # Property 4: Universal Confidence Bounds
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be in range [0.0, 1.0], got {self.confidence}")
        
        # Validate event ID is not empty
        if not self.event_id or not self.event_id.strip():
            raise ValueError("Event ID cannot be empty")
        
        # Validate severity is a valid enum
        if not isinstance(self.severity, Severity):
            raise ValueError(f"Severity must be a Severity enum, got {type(self.severity)}")
        
        # Validate displacement is correct type
        if not isinstance(self.displacement, DisplacementMetrics):
            raise ValueError(f"Displacement must be DisplacementMetrics, got {type(self.displacement)}")
    
    @staticmethod
    def generate_event_id() -> str:
        """Generate a unique event ID"""
        return str(uuid.uuid4())


@dataclass
class SynchronizedFrameBatch:
    """
    Synchronized frames from multiple cameras
    
    Validates:
        - Property 7: Camera IDs validity
        - Property 1: Frame synchronization tolerance
        - Property 11: Complete batch validation
    """
    frames: Dict[int, np.ndarray]  # camera_id -> frame (BGR image)
    timestamps: Dict[int, int]  # camera_id -> timestamp (microseconds)
    sequence_number: int
    is_complete: bool  # True if all 4 cameras provided frames
    sync_tolerance: int = 50000  # 50ms in microseconds
    
    def __post_init__(self):
        """Validate synchronized frame batch"""
        # Property 7: Camera ID Validity for all frames
        for camera_id in self.frames.keys():
            if not (0 <= camera_id <= 3):
                raise ValueError(f"Camera ID must be in range [0, 3], got {camera_id}")
        
        for camera_id in self.timestamps.keys():
            if not (0 <= camera_id <= 3):
                raise ValueError(f"Camera ID must be in range [0, 3], got {camera_id}")
        
        # Validate frames and timestamps have same keys
        if set(self.frames.keys()) != set(self.timestamps.keys()):
            raise ValueError("Frames and timestamps must have same camera IDs")
        
        # Property 11: Complete Synchronized Batch
        if self.is_complete and len(self.frames) != 4:
            raise ValueError(f"Complete batch must have 4 cameras, got {len(self.frames)}")
        
        # Property 1: Frame Synchronization
        if len(self.timestamps) > 1:
            timestamp_values = list(self.timestamps.values())
            max_diff = max(timestamp_values) - min(timestamp_values)
            if max_diff > self.sync_tolerance:
                raise ValueError(
                    f"Timestamp difference ({max_diff}µs) exceeds synchronization "
                    f"tolerance ({self.sync_tolerance}µs)"
                )
        
        # Validate sequence number is non-negative
        if self.sequence_number < 0:
            raise ValueError(f"Sequence number must be non-negative, got {self.sequence_number}")


@dataclass
class CalibrationData:
    """
    Complete calibration data for all cameras
    
    Validates:
        - Property 7: All camera IDs in valid range
        - Completeness: All 4 cameras must have calibration data
    """
    intrinsics: Dict[int, CameraIntrinsics]  # camera_id -> intrinsics
    reference_poses: Dict[int, CalibrationPose]  # camera_id -> reference pose
    vehicle_to_world: np.ndarray = field(default_factory=lambda: np.eye(4))  # 4x4 transformation
    
    def __post_init__(self):
        """Validate calibration data"""
        # Convert vehicle_to_world to numpy array
        self.vehicle_to_world = np.asarray(self.vehicle_to_world, dtype=np.float64)
        
        # Validate shape
        if self.vehicle_to_world.shape != (4, 4):
            raise ValueError(f"Vehicle to world transform must be 4x4 matrix, got shape {self.vehicle_to_world.shape}")
        
        # Property 7: Camera ID Validity
        for camera_id in self.intrinsics.keys():
            if not (0 <= camera_id <= 3):
                raise ValueError(f"Camera ID must be in range [0, 3], got {camera_id}")
        
        for camera_id in self.reference_poses.keys():
            if not (0 <= camera_id <= 3):
                raise ValueError(f"Camera ID must be in range [0, 3], got {camera_id}")
        
        # Validate completeness: must have data for all 4 cameras
        if len(self.intrinsics) != 4 or len(self.reference_poses) != 4:
            raise ValueError(
                f"Calibration data must contain entries for all 4 cameras. "
                f"Got {len(self.intrinsics)} intrinsics and {len(self.reference_poses)} poses"
            )
        
        # Validate both dicts have same keys
        if set(self.intrinsics.keys()) != set(self.reference_poses.keys()):
            raise ValueError("Intrinsics and reference poses must have same camera IDs")
        
        # Validate all camera IDs 0-3 are present
        expected_ids = {0, 1, 2, 3}
        if set(self.intrinsics.keys()) != expected_ids:
            raise ValueError(f"Calibration data must include cameras 0-3, got {set(self.intrinsics.keys())}")
