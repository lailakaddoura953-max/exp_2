"""
Pytest configuration and shared fixtures for all tests
"""

import pytest
import numpy as np
from datetime import datetime
from src.models.core import (
    CameraIntrinsics,
    CalibrationPose,
    CameraConfig,
    FeatureSet,
    FlowResult,
    PoseEstimate,
    DisplacementMetrics,
    MisalignmentEvent,
    SynchronizedFrameBatch,
    CalibrationData,
    Severity,
)


@pytest.fixture
def valid_intrinsics():
    """Fixture for valid camera intrinsics"""
    return CameraIntrinsics(
        fx=800.0,
        fy=800.0,
        cx=320.0,
        cy=240.0,
        k1=0.1,
        k2=-0.05,
        p1=0.001,
        p2=0.001,
        k3=0.01
    )


@pytest.fixture
def valid_calibration_pose():
    """Fixture for valid calibration pose"""
    return CalibrationPose(
        position=np.array([1.0, 0.5, 1.5]),
        orientation=np.array([1.0, 0.0, 0.0, 0.0])  # Identity quaternion
    )


@pytest.fixture
def valid_camera_config(valid_intrinsics, valid_calibration_pose):
    """Fixture for valid camera configuration"""
    return CameraConfig(
        camera_id=0,
        stream_url="rtsp://camera0/stream",
        resolution=(640, 480),
        fps=30,
        intrinsics=valid_intrinsics,
        calibration_pose=valid_calibration_pose
    )


@pytest.fixture
def valid_feature_set():
    """Fixture for valid feature set"""
    keypoints = [(100.0, 200.0), (150.0, 250.0), (200.0, 300.0)]
    descriptors = np.random.randint(0, 256, (3, 32), dtype=np.uint8)
    return FeatureSet(
        camera_id=0,
        keypoints=keypoints,
        descriptors=descriptors,
        timestamp=1000000
    )


@pytest.fixture
def valid_flow_result():
    """Fixture for valid flow result"""
    flow_vectors = np.random.randn(480, 640, 2).astype(np.float32)
    confidence = np.random.rand(480, 640).astype(np.float32)
    return FlowResult(
        flow_vectors=flow_vectors,
        confidence=confidence,
        mean_magnitude=2.5,
        mean_direction=1.57,
        frame_shape=(480, 640)
    )


@pytest.fixture
def valid_pose_estimate():
    """Fixture for valid pose estimate"""
    transformation = np.eye(4)
    transformation[:3, 3] = [1.0, 0.5, 1.5]
    return PoseEstimate(
        camera_id=0,
        transformation=transformation,
        position=np.array([1.0, 0.5, 1.5]),
        orientation=np.array([1.0, 0.0, 0.0, 0.0]),
        confidence=0.95,
        timestamp=1000000
    )


@pytest.fixture
def valid_displacement_metrics():
    """Fixture for valid displacement metrics"""
    position_delta = np.array([0.1, 0.05, 0.02])
    return DisplacementMetrics(
        position_delta=position_delta,
        position_delta_magnitude=np.linalg.norm(position_delta),
        angle_delta=np.array([2.0, 1.5, 0.5]),
        angle_delta_magnitude=2.5,
        flow_inconsistency=0.3
    )


@pytest.fixture
def valid_misalignment_event(valid_displacement_metrics):
    """Fixture for valid misalignment event"""
    return MisalignmentEvent(
        event_id="test-event-123",
        camera_id=0,
        timestamp=datetime.now(),
        severity=Severity.HIGH,
        displacement=valid_displacement_metrics,
        confidence=0.85,
        diagnostic_data={"test": "data"}
    )


@pytest.fixture
def valid_synchronized_batch():
    """Fixture for valid synchronized frame batch"""
    frames = {
        0: np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8),
        1: np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8),
        2: np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8),
        3: np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8),
    }
    timestamps = {0: 1000000, 1: 1000010, 2: 1000020, 3: 1000030}
    return SynchronizedFrameBatch(
        frames=frames,
        timestamps=timestamps,
        sequence_number=1,
        is_complete=True
    )


@pytest.fixture
def valid_calibration_data(valid_intrinsics, valid_calibration_pose):
    """Fixture for valid calibration data"""
    intrinsics = {i: valid_intrinsics for i in range(4)}
    poses = {i: valid_calibration_pose for i in range(4)}
    return CalibrationData(
        intrinsics=intrinsics,
        reference_poses=poses,
        vehicle_to_world=np.eye(4)
    )
