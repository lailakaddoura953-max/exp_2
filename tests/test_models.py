"""
Comprehensive unit tests for core data models

Tests validate:
- Property 7: Camera ID Validity (all camera IDs in range [0, 3])
- Property 4: Universal Confidence Bounds (all confidence scores in [0.0, 1.0])
- Property 2: Feature-Descriptor Correspondence
- Property 6: Displacement Metric Consistency
- Property 1: Frame Synchronization
- Property 8: Flow Spatial Dimension Preservation
- Property 11: Complete Synchronized Batch
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
    CameraStatus,
)


class TestCameraIntrinsics:
    """Tests for CameraIntrinsics dataclass"""
    
    def test_valid_intrinsics(self, valid_intrinsics):
        """Test creation of valid camera intrinsics"""
        assert valid_intrinsics.fx == 800.0
        assert valid_intrinsics.fy == 800.0
        assert valid_intrinsics.cx == 320.0
        assert valid_intrinsics.cy == 240.0
    
    def test_negative_focal_length(self):
        """Test that negative focal lengths are rejected"""
        with pytest.raises(ValueError, match="Focal lengths must be positive"):
            CameraIntrinsics(fx=-800.0, fy=800.0, cx=320.0, cy=240.0)
    
    def test_zero_focal_length(self):
        """Test that zero focal lengths are rejected"""
        with pytest.raises(ValueError, match="Focal lengths must be positive"):
            CameraIntrinsics(fx=0.0, fy=800.0, cx=320.0, cy=240.0)
    
    def test_negative_principal_point(self):
        """Test that negative principal point is rejected"""
        with pytest.raises(ValueError, match="Principal point must be non-negative"):
            CameraIntrinsics(fx=800.0, fy=800.0, cx=-320.0, cy=240.0)


class TestCalibrationPose:
    """Tests for CalibrationPose dataclass"""
    
    def test_valid_pose(self, valid_calibration_pose):
        """Test creation of valid calibration pose"""
        assert valid_calibration_pose.position.shape == (3,)
        assert valid_calibration_pose.orientation.shape == (4,)
    
    def test_invalid_position_shape(self):
        """Test that invalid position shape is rejected"""
        with pytest.raises(ValueError, match="Position must be 3D vector"):
            CalibrationPose(
                position=np.array([1.0, 0.5]),  # Only 2D
                orientation=np.array([1.0, 0.0, 0.0, 0.0])
            )
    
    def test_invalid_orientation_shape(self):
        """Test that invalid orientation shape is rejected"""
        with pytest.raises(ValueError, match="Orientation must be quaternion"):
            CalibrationPose(
                position=np.array([1.0, 0.5, 1.5]),
                orientation=np.array([1.0, 0.0, 0.0])  # Only 3 elements
            )
    
    def test_quaternion_normalization(self):
        """Test that quaternions are normalized"""
        pose = CalibrationPose(
            position=np.array([0.0, 0.0, 0.0]),
            orientation=np.array([2.0, 0.0, 0.0, 0.0])  # Not normalized
        )
        assert np.isclose(np.linalg.norm(pose.orientation), 1.0)


class TestCameraConfig:
    """Tests for CameraConfig dataclass"""
    
    def test_valid_config(self, valid_camera_config):
        """Test creation of valid camera config"""
        assert valid_camera_config.camera_id == 0
        assert valid_camera_config.resolution == (640, 480)
        assert valid_camera_config.fps == 30
    
    def test_camera_id_too_low(self, valid_intrinsics, valid_calibration_pose):
        """Test Property 7: Camera ID must be >= 0"""
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            CameraConfig(
                camera_id=-1,
                stream_url="rtsp://camera/stream",
                resolution=(640, 480),
                fps=30,
                intrinsics=valid_intrinsics,
                calibration_pose=valid_calibration_pose
            )
    
    def test_camera_id_too_high(self, valid_intrinsics, valid_calibration_pose):
        """Test Property 7: Camera ID must be <= 3"""
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            CameraConfig(
                camera_id=4,
                stream_url="rtsp://camera/stream",
                resolution=(640, 480),
                fps=30,
                intrinsics=valid_intrinsics,
                calibration_pose=valid_calibration_pose
            )
    
    def test_invalid_resolution(self, valid_intrinsics, valid_calibration_pose):
        """Test that invalid resolution is rejected"""
        with pytest.raises(ValueError, match="Resolution must have positive dimensions"):
            CameraConfig(
                camera_id=0,
                stream_url="rtsp://camera/stream",
                resolution=(640, -480),
                fps=30,
                intrinsics=valid_intrinsics,
                calibration_pose=valid_calibration_pose
            )
    
    def test_invalid_fps_too_high(self, valid_intrinsics, valid_calibration_pose):
        """Test that FPS > 120 is rejected"""
        with pytest.raises(ValueError, match="FPS must be positive and <= 120"):
            CameraConfig(
                camera_id=0,
                stream_url="rtsp://camera/stream",
                resolution=(640, 480),
                fps=150,
                intrinsics=valid_intrinsics,
                calibration_pose=valid_calibration_pose
            )
    
    def test_empty_stream_url(self, valid_intrinsics, valid_calibration_pose):
        """Test that empty stream URL is rejected"""
        with pytest.raises(ValueError, match="Stream URL cannot be empty"):
            CameraConfig(
                camera_id=0,
                stream_url="",
                resolution=(640, 480),
                fps=30,
                intrinsics=valid_intrinsics,
                calibration_pose=valid_calibration_pose
            )


class TestFeatureSet:
    """Tests for FeatureSet dataclass"""
    
    def test_valid_feature_set(self, valid_feature_set):
        """Test creation of valid feature set"""
        assert valid_feature_set.camera_id == 0
        assert len(valid_feature_set.keypoints) == 3
        assert valid_feature_set.descriptors.shape[0] == 3
    
    def test_property_2_feature_descriptor_correspondence(self):
        """Test Property 2: Number of keypoints must equal descriptor rows"""
        keypoints = [(100.0, 200.0), (150.0, 250.0)]
        descriptors = np.random.randint(0, 256, (3, 32), dtype=np.uint8)  # 3 rows != 2 keypoints
        
        with pytest.raises(ValueError, match="Number of keypoints .* must equal"):
            FeatureSet(
                camera_id=0,
                keypoints=keypoints,
                descriptors=descriptors,
                timestamp=1000000
            )
    
    def test_property_7_camera_id_validity(self):
        """Test Property 7: Camera ID must be in valid range"""
        keypoints = [(100.0, 200.0)]
        descriptors = np.random.randint(0, 256, (1, 32), dtype=np.uint8)
        
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            FeatureSet(
                camera_id=5,
                keypoints=keypoints,
                descriptors=descriptors,
                timestamp=1000000
            )
    
    def test_negative_timestamp(self):
        """Test that negative timestamp is rejected"""
        keypoints = [(100.0, 200.0)]
        descriptors = np.random.randint(0, 256, (1, 32), dtype=np.uint8)
        
        with pytest.raises(ValueError, match="Timestamp must be non-negative"):
            FeatureSet(
                camera_id=0,
                keypoints=keypoints,
                descriptors=descriptors,
                timestamp=-1000
            )


class TestFlowResult:
    """Tests for FlowResult dataclass"""
    
    def test_valid_flow_result(self, valid_flow_result):
        """Test creation of valid flow result"""
        assert valid_flow_result.flow_vectors.shape == (480, 640, 2)
        assert valid_flow_result.confidence.shape == (480, 640)
        assert valid_flow_result.mean_magnitude == 2.5
    
    def test_property_8_flow_spatial_dimension_preservation(self):
        """Test Property 8: Flow vectors must match frame dimensions"""
        flow_vectors = np.random.randn(480, 640, 2).astype(np.float32)
        confidence = np.random.rand(480, 640).astype(np.float32)
        
        with pytest.raises(ValueError, match="Flow vectors shape .* must match frame shape"):
            FlowResult(
                flow_vectors=flow_vectors,
                confidence=confidence,
                mean_magnitude=2.5,
                mean_direction=1.57,
                frame_shape=(360, 640)  # Wrong height
            )
    
    def test_property_4_confidence_bounds(self):
        """Test Property 4: Confidence values must be in [0.0, 1.0]"""
        flow_vectors = np.random.randn(480, 640, 2).astype(np.float32)
        confidence = np.random.rand(480, 640).astype(np.float32)
        confidence[0, 0] = 1.5  # Invalid confidence > 1.0
        
        with pytest.raises(ValueError, match="confidence values must be in range"):
            FlowResult(
                flow_vectors=flow_vectors,
                confidence=confidence,
                mean_magnitude=2.5,
                mean_direction=1.57,
                frame_shape=(480, 640)
            )
    
    def test_invalid_flow_channels(self):
        """Test that flow must be 2-channel (dx, dy)"""
        flow_vectors = np.random.randn(480, 640).astype(np.float32)  # Missing channel dimension
        confidence = np.random.rand(480, 640).astype(np.float32)
        
        with pytest.raises(ValueError, match="Flow vectors must be 2-channel"):
            FlowResult(
                flow_vectors=flow_vectors,
                confidence=confidence,
                mean_magnitude=2.5,
                mean_direction=1.57,
                frame_shape=(480, 640)
            )
    
    def test_negative_mean_magnitude(self):
        """Test that negative mean magnitude is rejected"""
        flow_vectors = np.random.randn(480, 640, 2).astype(np.float32)
        confidence = np.random.rand(480, 640).astype(np.float32)
        
        with pytest.raises(ValueError, match="Mean magnitude must be non-negative"):
            FlowResult(
                flow_vectors=flow_vectors,
                confidence=confidence,
                mean_magnitude=-2.5,
                mean_direction=1.57,
                frame_shape=(480, 640)
            )


class TestPoseEstimate:
    """Tests for PoseEstimate dataclass"""
    
    def test_valid_pose_estimate(self, valid_pose_estimate):
        """Test creation of valid pose estimate"""
        assert valid_pose_estimate.camera_id == 0
        assert valid_pose_estimate.transformation.shape == (4, 4)
        assert valid_pose_estimate.confidence == 0.95
    
    def test_property_7_camera_id_validity(self):
        """Test Property 7: Camera ID must be in valid range"""
        transformation = np.eye(4)
        
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            PoseEstimate(
                camera_id=10,
                transformation=transformation,
                position=np.array([0.0, 0.0, 0.0]),
                orientation=np.array([1.0, 0.0, 0.0, 0.0]),
                confidence=0.95,
                timestamp=1000000
            )
    
    def test_property_4_confidence_bounds(self):
        """Test Property 4: Confidence must be in [0.0, 1.0]"""
        transformation = np.eye(4)
        
        with pytest.raises(ValueError, match="Confidence must be in range"):
            PoseEstimate(
                camera_id=0,
                transformation=transformation,
                position=np.array([0.0, 0.0, 0.0]),
                orientation=np.array([1.0, 0.0, 0.0, 0.0]),
                confidence=1.5,
                timestamp=1000000
            )
    
    def test_invalid_transformation_shape(self):
        """Test that transformation must be 4x4"""
        transformation = np.eye(3)  # Wrong size
        
        with pytest.raises(ValueError, match="Transformation must be 4x4 matrix"):
            PoseEstimate(
                camera_id=0,
                transformation=transformation,
                position=np.array([0.0, 0.0, 0.0]),
                orientation=np.array([1.0, 0.0, 0.0, 0.0]),
                confidence=0.95,
                timestamp=1000000
            )
    
    def test_invalid_transformation_bottom_row(self):
        """Test that transformation bottom row must be [0, 0, 0, 1]"""
        transformation = np.eye(4)
        transformation[3, :] = [1, 0, 0, 1]  # Invalid bottom row
        
        with pytest.raises(ValueError, match="bottom row must be"):
            PoseEstimate(
                camera_id=0,
                transformation=transformation,
                position=np.array([0.0, 0.0, 0.0]),
                orientation=np.array([1.0, 0.0, 0.0, 0.0]),
                confidence=0.95,
                timestamp=1000000
            )


class TestDisplacementMetrics:
    """Tests for DisplacementMetrics dataclass"""
    
    def test_valid_displacement_metrics(self, valid_displacement_metrics):
        """Test creation of valid displacement metrics"""
        assert valid_displacement_metrics.position_delta.shape == (3,)
        assert valid_displacement_metrics.position_delta_magnitude > 0
    
    def test_property_6_displacement_consistency(self):
        """Test Property 6: Position magnitude must equal Euclidean norm"""
        position_delta = np.array([0.3, 0.4, 0.0])  # Magnitude should be 0.5
        
        with pytest.raises(ValueError, match="Position delta magnitude .* must equal"):
            DisplacementMetrics(
                position_delta=position_delta,
                position_delta_magnitude=0.6,  # Wrong magnitude
                angle_delta=np.array([0.0, 0.0, 0.0]),
                angle_delta_magnitude=0.0,
                flow_inconsistency=0.0
            )
    
    def test_valid_displacement_consistency(self):
        """Test that correct magnitude passes validation"""
        position_delta = np.array([0.3, 0.4, 0.0])
        correct_magnitude = np.linalg.norm(position_delta)  # Should be 0.5
        
        metrics = DisplacementMetrics(
            position_delta=position_delta,
            position_delta_magnitude=correct_magnitude,
            angle_delta=np.array([0.0, 0.0, 0.0]),
            angle_delta_magnitude=0.0,
            flow_inconsistency=0.0
        )
        
        assert np.isclose(metrics.position_delta_magnitude, 0.5)
    
    def test_invalid_angle_range(self):
        """Test that angles must be in [-180, 180] range"""
        position_delta = np.array([0.0, 0.0, 0.0])
        
        with pytest.raises(ValueError, match="Angle delta values must be in"):
            DisplacementMetrics(
                position_delta=position_delta,
                position_delta_magnitude=0.0,
                angle_delta=np.array([200.0, 0.0, 0.0]),  # Out of range
                angle_delta_magnitude=200.0,
                flow_inconsistency=0.0
            )
    
    def test_invalid_flow_inconsistency(self):
        """Test that flow inconsistency must be in [0.0, 1.0]"""
        position_delta = np.array([0.0, 0.0, 0.0])
        
        with pytest.raises(ValueError, match="Flow inconsistency must be in"):
            DisplacementMetrics(
                position_delta=position_delta,
                position_delta_magnitude=0.0,
                angle_delta=np.array([0.0, 0.0, 0.0]),
                angle_delta_magnitude=0.0,
                flow_inconsistency=1.5  # Out of range
            )


class TestMisalignmentEvent:
    """Tests for MisalignmentEvent dataclass"""
    
    def test_valid_event(self, valid_misalignment_event):
        """Test creation of valid misalignment event"""
        assert valid_misalignment_event.camera_id == 0
        assert valid_misalignment_event.severity == Severity.HIGH
        assert 0.0 <= valid_misalignment_event.confidence <= 1.0
    
    def test_property_7_camera_id_validity(self, valid_displacement_metrics):
        """Test Property 7: Camera ID must be in valid range"""
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            MisalignmentEvent(
                event_id="test-event",
                camera_id=7,
                timestamp=datetime.now(),
                severity=Severity.HIGH,
                displacement=valid_displacement_metrics,
                confidence=0.85
            )
    
    def test_property_4_confidence_bounds(self, valid_displacement_metrics):
        """Test Property 4: Confidence must be in [0.0, 1.0]"""
        with pytest.raises(ValueError, match="Confidence must be in range"):
            MisalignmentEvent(
                event_id="test-event",
                camera_id=0,
                timestamp=datetime.now(),
                severity=Severity.HIGH,
                displacement=valid_displacement_metrics,
                confidence=2.0
            )
    
    def test_generate_event_id(self):
        """Test event ID generation"""
        event_id = MisalignmentEvent.generate_event_id()
        assert isinstance(event_id, str)
        assert len(event_id) > 0
        
        # Generate another and ensure uniqueness
        event_id2 = MisalignmentEvent.generate_event_id()
        assert event_id != event_id2
    
    def test_empty_event_id(self, valid_displacement_metrics):
        """Test that empty event ID is rejected"""
        with pytest.raises(ValueError, match="Event ID cannot be empty"):
            MisalignmentEvent(
                event_id="",
                camera_id=0,
                timestamp=datetime.now(),
                severity=Severity.HIGH,
                displacement=valid_displacement_metrics,
                confidence=0.85
            )


class TestSynchronizedFrameBatch:
    """Tests for SynchronizedFrameBatch dataclass"""
    
    def test_valid_batch(self, valid_synchronized_batch):
        """Test creation of valid synchronized batch"""
        assert len(valid_synchronized_batch.frames) == 4
        assert len(valid_synchronized_batch.timestamps) == 4
        assert valid_synchronized_batch.is_complete
    
    def test_property_1_frame_synchronization(self):
        """Test Property 1: Timestamps must be within tolerance"""
        frames = {
            0: np.zeros((480, 640, 3), dtype=np.uint8),
            1: np.zeros((480, 640, 3), dtype=np.uint8),
        }
        timestamps = {0: 1000000, 1: 1100000}  # 100ms apart, exceeds 50ms tolerance
        
        with pytest.raises(ValueError, match="Timestamp difference .* exceeds"):
            SynchronizedFrameBatch(
                frames=frames,
                timestamps=timestamps,
                sequence_number=1,
                is_complete=False
            )
    
    def test_property_11_complete_batch_validation(self):
        """Test Property 11: Complete batch must have 4 cameras"""
        frames = {
            0: np.zeros((480, 640, 3), dtype=np.uint8),
            1: np.zeros((480, 640, 3), dtype=np.uint8),
        }
        timestamps = {0: 1000000, 1: 1000010}
        
        with pytest.raises(ValueError, match="Complete batch must have 4 cameras"):
            SynchronizedFrameBatch(
                frames=frames,
                timestamps=timestamps,
                sequence_number=1,
                is_complete=True  # Claiming complete but only 2 cameras
            )
    
    def test_property_7_camera_id_validity(self):
        """Test Property 7: Camera IDs must be in valid range"""
        frames = {10: np.zeros((480, 640, 3), dtype=np.uint8)}  # Invalid camera ID
        timestamps = {10: 1000000}
        
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            SynchronizedFrameBatch(
                frames=frames,
                timestamps=timestamps,
                sequence_number=1,
                is_complete=False
            )
    
    def test_frames_timestamps_mismatch(self):
        """Test that frames and timestamps must have same keys"""
        frames = {0: np.zeros((480, 640, 3), dtype=np.uint8)}
        timestamps = {1: 1000000}  # Different camera ID
        
        with pytest.raises(ValueError, match="same camera IDs"):
            SynchronizedFrameBatch(
                frames=frames,
                timestamps=timestamps,
                sequence_number=1,
                is_complete=False
            )


class TestCalibrationData:
    """Tests for CalibrationData dataclass"""
    
    def test_valid_calibration_data(self, valid_calibration_data):
        """Test creation of valid calibration data"""
        assert len(valid_calibration_data.intrinsics) == 4
        assert len(valid_calibration_data.reference_poses) == 4
        assert valid_calibration_data.vehicle_to_world.shape == (4, 4)
    
    def test_incomplete_calibration_data(self, valid_intrinsics, valid_calibration_pose):
        """Test that calibration data must include all 4 cameras"""
        intrinsics = {0: valid_intrinsics, 1: valid_intrinsics}  # Only 2 cameras
        poses = {0: valid_calibration_pose, 1: valid_calibration_pose}
        
        with pytest.raises(ValueError, match="must contain entries for all 4 cameras"):
            CalibrationData(
                intrinsics=intrinsics,
                reference_poses=poses
            )
    
    def test_property_7_camera_id_validity(self, valid_intrinsics, valid_calibration_pose):
        """Test Property 7: Camera IDs must be in valid range"""
        intrinsics = {0: valid_intrinsics, 1: valid_intrinsics, 2: valid_intrinsics, 10: valid_intrinsics}
        poses = {0: valid_calibration_pose, 1: valid_calibration_pose, 2: valid_calibration_pose, 10: valid_calibration_pose}
        
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            CalibrationData(
                intrinsics=intrinsics,
                reference_poses=poses
            )
    
    def test_missing_camera_ids(self, valid_intrinsics, valid_calibration_pose):
        """Test that all cameras 0-3 must be present"""
        intrinsics = {0: valid_intrinsics, 1: valid_intrinsics, 2: valid_intrinsics, 10: valid_intrinsics}
        poses = {0: valid_calibration_pose, 1: valid_calibration_pose, 2: valid_calibration_pose, 10: valid_calibration_pose}
        
        # This will fail on the camera ID validation first (camera_id=10 is invalid)
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            CalibrationData(
                intrinsics=intrinsics,
                reference_poses=poses
            )


class TestEnums:
    """Tests for enum types"""
    
    def test_severity_enum(self):
        """Test Severity enum values"""
        assert Severity.LOW.value == 1
        assert Severity.MEDIUM.value == 2
        assert Severity.HIGH.value == 3
        assert Severity.CRITICAL.value == 4
    
    def test_camera_status_enum(self):
        """Test CameraStatus enum values"""
        assert CameraStatus.ACTIVE.value == "active"
        assert CameraStatus.INACTIVE.value == "inactive"
        assert CameraStatus.DISCONNECTED.value == "disconnected"
        assert CameraStatus.ERROR.value == "error"


# Integration test: Create a complete data flow
class TestDataModelIntegration:
    """Integration tests using multiple data models together"""
    
    def test_complete_detection_data_flow(
        self, 
        valid_camera_config,
        valid_feature_set,
        valid_flow_result,
        valid_pose_estimate,
        valid_displacement_metrics,
        valid_misalignment_event
    ):
        """Test that all models work together in a typical detection scenario"""
        # This test validates that all the data structures can be created
        # and work together as they would in the real system
        
        assert valid_camera_config.camera_id == valid_feature_set.camera_id
        assert valid_feature_set.camera_id == valid_pose_estimate.camera_id
        assert valid_pose_estimate.camera_id == valid_misalignment_event.camera_id
        
        # Verify properties hold across the chain
        assert 0 <= valid_camera_config.camera_id <= 3  # Property 7
        assert len(valid_feature_set.keypoints) == valid_feature_set.descriptors.shape[0]  # Property 2
        assert 0.0 <= valid_pose_estimate.confidence <= 1.0  # Property 4
        assert 0.0 <= valid_misalignment_event.confidence <= 1.0  # Property 4
