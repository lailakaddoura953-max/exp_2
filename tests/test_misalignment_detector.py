"""
Unit tests for Misalignment Detection Core Module

Tests misalignment detection with:
- Property 5: Event Severity Ordering
- Property 6: Displacement Metric Consistency  
- Property 13: Threshold-Based Event Generation
- Property 15: Complete Event Structure
- Property 16: Diagnostic Data Completeness
- Property 18: Reference Pose Updates
"""

import pytest
import numpy as np
from datetime import datetime

from src.detection.misalignment_detector import (
    DetectionThresholds,
    MisalignmentDetector
)
from src.detection.vehicle_motion import VehicleMotion
from src.models.core import (
    PoseEstimate,
    Severity,
    CalibrationPose,
    FlowResult
)
from src.config.calibration import create_mock_calibration


class TestDetectionThresholds:
    """Test DetectionThresholds dataclass"""
    
    def test_valid_thresholds(self):
        """Test creating valid thresholds"""
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0,
            flow_inconsistency_threshold=0.3,
            confidence_threshold=0.7
        )
        
        assert thresholds.position_threshold_m == 0.05
        assert thresholds.angle_threshold_deg == 2.0
        assert thresholds.flow_inconsistency_threshold == 0.3
        assert thresholds.confidence_threshold == 0.7
    
    def test_invalid_position_threshold(self):
        """Test error when position threshold is non-positive"""
        with pytest.raises(ValueError, match="Position threshold must be positive"):
            DetectionThresholds(
                position_threshold_m=0.0,
                angle_threshold_deg=2.0
            )
    
    def test_invalid_angle_threshold(self):
        """Test error when angle threshold is invalid"""
        with pytest.raises(ValueError, match="Angle threshold must be in"):
            DetectionThresholds(
                position_threshold_m=0.05,
                angle_threshold_deg=0.0
            )
        
        with pytest.raises(ValueError, match="Angle threshold must be in"):
            DetectionThresholds(
                position_threshold_m=0.05,
                angle_threshold_deg=200.0
            )
    
    def test_invalid_flow_threshold(self):
        """Test error when flow inconsistency threshold is invalid"""
        with pytest.raises(ValueError, match="Flow inconsistency threshold must be in"):
            DetectionThresholds(
                position_threshold_m=0.05,
                angle_threshold_deg=2.0,
                flow_inconsistency_threshold=1.5
            )
    
    def test_invalid_confidence_threshold(self):
        """Test error when confidence threshold is invalid"""
        with pytest.raises(ValueError, match="Confidence threshold must be in"):
            DetectionThresholds(
                position_threshold_m=0.05,
                angle_threshold_deg=2.0,
                confidence_threshold=1.5
            )



class TestMisalignmentDetectorInit:
    """Test MisalignmentDetector initialization"""
    
    @pytest.fixture
    def calibration(self):
        """Create mock calibration"""
        return create_mock_calibration()
    
    @pytest.fixture
    def thresholds(self):
        """Create detection thresholds"""
        return DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0
        )
    
    def test_init_valid(self, calibration, thresholds):
        """Test valid initialization"""
        detector = MisalignmentDetector(calibration, thresholds)
        
        assert detector.calibration == calibration
        assert detector.thresholds == thresholds
        assert detector.sustained_detection_frames == 2
        assert len(detector.reference_poses) == 4
    
    def test_init_custom_sustained_frames(self, calibration, thresholds):
        """Test initialization with custom sustained frames"""
        detector = MisalignmentDetector(
            calibration,
            thresholds,
            sustained_detection_frames=3
        )
        
        assert detector.sustained_detection_frames == 3
    
    def test_init_invalid_sustained_frames(self, calibration, thresholds):
        """Test error when sustained_detection_frames is invalid"""
        with pytest.raises(ValueError, match="sustained_detection_frames must be"):
            MisalignmentDetector(
                calibration,
                thresholds,
                sustained_detection_frames=0
            )



class TestDisplacementComputation:
    """Test displacement computation"""
    
    @pytest.fixture
    def detector(self):
        """Create detector"""
        calibration = create_mock_calibration()
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0
        )
        return MisalignmentDetector(calibration, thresholds)
    
    def create_pose(self, camera_id, position, orientation):
        """Helper to create pose estimate"""
        transformation = np.eye(4)
        return PoseEstimate(
            camera_id=camera_id,
            transformation=transformation,
            position=np.array(position),
            orientation=np.array(orientation),
            confidence=1.0,
            timestamp=0
        )
    
    def test_compute_displacement_no_motion(self, detector):
        """Test displacement computation with no motion"""
        # Current pose matches reference
        ref_pose = detector.reference_poses[0]
        current_pose = self.create_pose(0, ref_pose.position, ref_pose.orientation)
        
        displacement = detector._compute_displacement(0, current_pose, None)
        
        # Should be zero displacement
        assert np.allclose(displacement.position_delta, [0, 0, 0], atol=1e-6)
        assert displacement.position_delta_magnitude < 0.001
    
    def test_compute_displacement_with_position_change(self, detector):
        """Test displacement computation with position change"""
        ref_pose = detector.reference_poses[0]
        
        # Move camera 0.1m in X direction
        new_position = ref_pose.position + np.array([0.1, 0, 0])
        current_pose = self.create_pose(0, new_position, ref_pose.orientation)
        
        displacement = detector._compute_displacement(0, current_pose, None)
        
        # Should detect 0.1m displacement in X
        assert np.isclose(displacement.position_delta[0], 0.1, atol=0.001)
        assert np.isclose(displacement.position_delta_magnitude, 0.1, atol=0.001)
    
    def test_compute_displacement_with_vehicle_motion_compensation(self, detector):
        """Test displacement computation with vehicle motion compensation"""
        ref_pose = detector.reference_poses[0]
        
        # Camera and vehicle both moved 0.1m in X
        new_position = ref_pose.position + np.array([0.1, 0, 0])
        current_pose = self.create_pose(0, new_position, ref_pose.orientation)
        
        vehicle_motion = VehicleMotion(
            position_delta=np.array([0.1, 0, 0]),
            rotation_delta=np.array([1, 0, 0, 0]),
            confidence=1.0,
            inlier_count=4,
            total_cameras=4,
            inlier_camera_ids=[0, 1, 2, 3]
        )
        
        displacement = detector._compute_displacement(0, current_pose, vehicle_motion)
        
        # After compensation, should be near zero
        assert np.allclose(displacement.position_delta, [0, 0, 0], atol=0.001)
        assert displacement.position_delta_magnitude < 0.001



class TestThresholdChecking:
    """Test threshold checking and severity classification"""
    
    @pytest.fixture
    def detector(self):
        """Create detector"""
        calibration = create_mock_calibration()
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,  # 5cm
            angle_threshold_deg=2.0  # 2 degrees
        )
        return MisalignmentDetector(calibration, thresholds)
    
    def create_displacement(self, pos_mag, angle_mag):
        """Helper to create displacement metrics"""
        from src.models.core import DisplacementMetrics
        return DisplacementMetrics(
            position_delta=np.array([pos_mag, 0, 0]),
            position_delta_magnitude=pos_mag,
            angle_delta=np.array([angle_mag, 0, 0]),
            angle_delta_magnitude=angle_mag,
            flow_inconsistency=0.0
        )
    
    def test_property_13_below_threshold(self, detector):
        """Test Property 13: Below threshold does not generate event"""
        displacement = self.create_displacement(0.02, 1.0)  # Below thresholds
        
        exceeds, severity = detector._check_thresholds(displacement, 0.8)
        
        assert exceeds is False
    
    def test_property_13_exceeds_position_threshold(self, detector):
        """Test Property 13: Exceeding position threshold generates event"""
        displacement = self.create_displacement(0.1, 0.5)  # 2x position threshold
        
        exceeds, severity = detector._check_thresholds(displacement, 0.8)
        
        assert exceeds is True
        assert severity in [Severity.LOW, Severity.MEDIUM]
    
    def test_property_13_exceeds_angle_threshold(self, detector):
        """Test Property 13: Exceeding angle threshold generates event"""
        displacement = self.create_displacement(0.01, 5.0)  # 2.5x angle threshold
        
        exceeds, severity = detector._check_thresholds(displacement, 0.8)
        
        assert exceeds is True
        assert severity in [Severity.MEDIUM, Severity.HIGH]
    
    def test_severity_classification_low(self, detector):
        """Test LOW severity classification (1-2x threshold)"""
        displacement = self.create_displacement(0.08, 0.0)  # 1.6x threshold
        
        exceeds, severity = detector._check_thresholds(displacement, 0.8)
        
        assert exceeds is True
        assert severity == Severity.LOW
    
    def test_severity_classification_medium(self, detector):
        """Test MEDIUM severity classification (2-3x threshold)"""
        displacement = self.create_displacement(0.12, 0.0)  # 2.4x threshold
        
        exceeds, severity = detector._check_thresholds(displacement, 0.8)
        
        assert exceeds is True
        assert severity == Severity.MEDIUM
    
    def test_severity_classification_high(self, detector):
        """Test HIGH severity classification (3-5x threshold)"""
        displacement = self.create_displacement(0.20, 0.0)  # 4x threshold
        
        exceeds, severity = detector._check_thresholds(displacement, 0.8)
        
        assert exceeds is True
        assert severity == Severity.HIGH
    
    def test_severity_classification_critical(self, detector):
        """Test CRITICAL severity classification (>=5x threshold)"""
        displacement = self.create_displacement(0.30, 0.0)  # 6x threshold
        
        exceeds, severity = detector._check_thresholds(displacement, 0.8)
        
        assert exceeds is True
        assert severity == Severity.CRITICAL



class TestSustainedDetection:
    """Test sustained detection over multiple frames"""
    
    @pytest.fixture
    def detector(self):
        """Create detector with 2 frame sustained detection"""
        calibration = create_mock_calibration()
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0
        )
        return MisalignmentDetector(calibration, thresholds, sustained_detection_frames=2)
    
    def test_single_frame_not_sustained(self, detector):
        """Test that single detection is not sustained"""
        detector.detection_history[0] = [True]
        
        is_sustained = detector._is_sustained_detection(0)
        
        assert is_sustained is False
    
    def test_two_consecutive_frames_sustained(self, detector):
        """Test that two consecutive detections are sustained"""
        detector.detection_history[0] = [True, True]
        
        is_sustained = detector._is_sustained_detection(0)
        
        assert is_sustained is True
    
    def test_intermittent_detection_not_sustained(self, detector):
        """Test that intermittent detection is not sustained"""
        detector.detection_history[0] = [True, False, True]
        
        is_sustained = detector._is_sustained_detection(0)
        
        assert is_sustained is False



class TestEventCreation:
    """Test event creation with complete structure and diagnostic data"""
    
    @pytest.fixture
    def detector(self):
        """Create detector"""
        calibration = create_mock_calibration()
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0
        )
        return MisalignmentDetector(calibration, thresholds)
    
    def create_pose(self, camera_id, position):
        """Helper to create pose"""
        return PoseEstimate(
            camera_id=camera_id,
            transformation=np.eye(4),
            position=np.array(position),
            orientation=np.array([1, 0, 0, 0]),
            confidence=0.9,
            timestamp=0
        )
    
    def create_displacement(self, pos_mag):
        """Helper to create displacement"""
        from src.models.core import DisplacementMetrics
        return DisplacementMetrics(
            position_delta=np.array([pos_mag, 0, 0]),
            position_delta_magnitude=pos_mag,
            angle_delta=np.array([0, 0, 0]),
            angle_delta_magnitude=0.0,
            flow_inconsistency=0.0
        )
    
    def test_property_15_complete_event_structure(self, detector):
        """Test Property 15: Event has complete structure"""
        ref_pose = detector.reference_poses[0]
        current_pose = self.create_pose(0, ref_pose.position + [0.1, 0, 0])
        displacement = self.create_displacement(0.1)
        timestamp = datetime.now()
        
        event = detector._create_event(
            camera_id=0,
            timestamp=timestamp,
            severity=Severity.MEDIUM,
            displacement=displacement,
            confidence=0.85,
            current_pose=current_pose,
            vehicle_motion=None,
            flow_results=None
        )
        
        # Verify complete structure (Property 15)
        assert event.event_id is not None and len(event.event_id) > 0
        assert event.camera_id == 0
        assert event.timestamp == timestamp
        assert event.severity == Severity.MEDIUM
        assert event.displacement == displacement
        assert event.confidence == 0.85
        assert isinstance(event.diagnostic_data, dict)
    
    def test_property_16_diagnostic_data_completeness(self, detector):
        """Test Property 16: Diagnostic data is complete"""
        ref_pose = detector.reference_poses[0]
        current_pose = self.create_pose(0, ref_pose.position + [0.1, 0, 0])
        displacement = self.create_displacement(0.1)
        
        event = detector._create_event(
            camera_id=0,
            timestamp=datetime.now(),
            severity=Severity.MEDIUM,
            displacement=displacement,
            confidence=0.85,
            current_pose=current_pose,
            vehicle_motion=None,
            flow_results=None
        )
        
        # Verify diagnostic data completeness (Property 16)
        assert 'current_position' in event.diagnostic_data
        assert 'current_orientation' in event.diagnostic_data
        assert 'reference_position' in event.diagnostic_data
        assert 'reference_orientation' in event.diagnostic_data
        assert 'pose_confidence' in event.diagnostic_data
        assert 'vehicle_motion_applied' in event.diagnostic_data
        assert 'sustained_frames' in event.diagnostic_data
        assert 'detection_timestamp' in event.diagnostic_data
    
    def test_diagnostic_data_with_vehicle_motion(self, detector):
        """Test diagnostic data includes vehicle motion when available"""
        ref_pose = detector.reference_poses[0]
        current_pose = self.create_pose(0, ref_pose.position)
        displacement = self.create_displacement(0.0)
        
        vehicle_motion = VehicleMotion(
            position_delta=np.array([0.1, 0, 0]),
            rotation_delta=np.array([1, 0, 0, 0]),
            confidence=0.9,
            inlier_count=3,
            total_cameras=4,
            inlier_camera_ids=[0, 1, 2]
        )
        
        event = detector._create_event(
            camera_id=0,
            timestamp=datetime.now(),
            severity=Severity.LOW,
            displacement=displacement,
            confidence=0.85,
            current_pose=current_pose,
            vehicle_motion=vehicle_motion,
            flow_results=None
        )
        
        assert event.diagnostic_data['vehicle_motion_applied'] is True
        assert 'vehicle_motion' in event.diagnostic_data
        assert event.diagnostic_data['vehicle_motion']['inlier_count'] == 3



class TestDetectMethod:
    """Test main detect() method"""
    
    @pytest.fixture
    def detector(self):
        """Create detector"""
        calibration = create_mock_calibration()
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0,
            confidence_threshold=0.7
        )
        return MisalignmentDetector(calibration, thresholds, sustained_detection_frames=2)
    
    def create_pose(self, camera_id, position):
        """Helper to create pose"""
        return PoseEstimate(
            camera_id=camera_id,
            transformation=np.eye(4),
            position=np.array(position),
            orientation=np.array([1, 0, 0, 0]),
            confidence=0.9,
            timestamp=0
        )
    
    def test_detect_no_misalignment(self, detector):
        """Test detection with no misalignment"""
        # All cameras at reference positions
        current_poses = {}
        for i in range(4):
            ref_pos = detector.reference_poses[i].position
            current_poses[i] = self.create_pose(i, ref_pos)
        
        events = detector.detect(current_poses)
        
        assert len(events) == 0
    
    def test_detect_single_camera_misaligned(self, detector):
        """Test detection with single camera misaligned"""
        current_poses = {}
        
        # Cameras 0, 1, 2 at reference
        for i in range(3):
            ref_pos = detector.reference_poses[i].position
            current_poses[i] = self.create_pose(i, ref_pos)
        
        # Camera 3 misaligned by 0.15m (3x threshold)
        ref_pos = detector.reference_poses[3].position
        current_poses[3] = self.create_pose(3, ref_pos + [0.15, 0, 0])
        
        # First detection - not sustained yet
        events1 = detector.detect(current_poses)
        assert len(events1) == 0  # Need sustained detection
        
        # Second detection - now sustained
        events2 = detector.detect(current_poses)
        assert len(events2) == 1
        assert events2[0].camera_id == 3
    
    def test_property_5_event_severity_ordering(self, detector):
        """Test Property 5: Events are sorted by severity (highest first)"""
        current_poses = {}
        
        # Camera 0: LOW severity (1.6x threshold = 0.08m)
        ref_pos = detector.reference_poses[0].position
        current_poses[0] = self.create_pose(0, ref_pos + [0.08, 0, 0])
        
        # Camera 1: CRITICAL severity (6x threshold = 0.30m)
        ref_pos = detector.reference_poses[1].position
        current_poses[1] = self.create_pose(1, ref_pos + [0.30, 0, 0])
        
        # Camera 2: MEDIUM severity (2.4x threshold = 0.12m)
        ref_pos = detector.reference_poses[2].position
        current_poses[2] = self.create_pose(2, ref_pos + [0.12, 0, 0])
        
        # Camera 3: HIGH severity (4x threshold = 0.20m)
        ref_pos = detector.reference_poses[3].position
        current_poses[3] = self.create_pose(3, ref_pos + [0.20, 0, 0])
        
        # Two detections for sustained
        detector.detect(current_poses)
        events = detector.detect(current_poses)
        
        # Should be sorted: CRITICAL, HIGH, MEDIUM, LOW
        assert len(events) == 4
        assert events[0].severity == Severity.CRITICAL  # Camera 1
        assert events[1].severity == Severity.HIGH      # Camera 3
        assert events[2].severity == Severity.MEDIUM    # Camera 2
        assert events[3].severity == Severity.LOW       # Camera 0
    
    def test_detect_with_low_confidence_suppressed(self, detector):
        """Test that low confidence detections are suppressed"""
        # Camera with misalignment but low confidence
        ref_pos = detector.reference_poses[0].position
        
        low_conf_pose = PoseEstimate(
            camera_id=0,
            transformation=np.eye(4),
            position=ref_pos + np.array([0.15, 0, 0]),
            orientation=np.array([1, 0, 0, 0]),
            confidence=0.5,  # Below 0.7 threshold
            timestamp=0
        )
        
        current_poses = {0: low_conf_pose}
        
        # Two detections
        detector.detect(current_poses)
        events = detector.detect(current_poses)
        
        # Should be suppressed due to low confidence
        assert len(events) == 0



class TestReferencePoseUpdate:
    """Test reference pose updates (Property 18)"""
    
    @pytest.fixture
    def detector(self):
        """Create detector"""
        calibration = create_mock_calibration()
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0
        )
        return MisalignmentDetector(calibration, thresholds)
    
    def test_property_18_update_reference_pose(self, detector):
        """Test Property 18: Can update reference pose"""
        # Get original reference
        original_ref = detector.reference_poses[0]
        
        # Create new reference
        new_ref = CalibrationPose(
            position=np.array([1.0, 2.0, 3.0]),
            orientation=np.array([1, 0, 0, 0])
        )
        
        # Update
        detector.update_reference_pose(0, new_ref)
        
        # Verify update
        assert not np.array_equal(detector.reference_poses[0].position, original_ref.position)
        np.testing.assert_allclose(detector.reference_poses[0].position, [1.0, 2.0, 3.0])
    
    def test_update_reference_pose_resets_history(self, detector):
        """Test that updating reference pose resets detection history"""
        # Add some detection history
        detector.detection_history[0] = [True, True, False]
        
        # Update reference
        new_ref = CalibrationPose(
            position=np.array([1.0, 2.0, 3.0]),
            orientation=np.array([1, 0, 0, 0])
        )
        detector.update_reference_pose(0, new_ref)
        
        # History should be reset
        assert len(detector.detection_history[0]) == 0
    
    def test_update_reference_pose_invalid_camera_id(self, detector):
        """Test error when updating invalid camera ID"""
        new_ref = CalibrationPose(
            position=np.array([1.0, 2.0, 3.0]),
            orientation=np.array([1, 0, 0, 0])
        )
        
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            detector.update_reference_pose(5, new_ref)



class TestStatistics:
    """Test statistics tracking"""
    
    @pytest.fixture
    def detector(self):
        """Create detector"""
        calibration = create_mock_calibration()
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0
        )
        return MisalignmentDetector(calibration, thresholds, sustained_detection_frames=1)
    
    def create_pose(self, camera_id, position):
        """Helper"""
        return PoseEstimate(
            camera_id=camera_id,
            transformation=np.eye(4),
            position=np.array(position),
            orientation=np.array([1, 0, 0, 0]),
            confidence=0.9,
            timestamp=0
        )
    
    def test_detections_processed_counter(self, detector):
        """Test that detections processed are counted"""
        current_poses = {
            0: self.create_pose(0, detector.reference_poses[0].position)
        }
        
        detector.detect(current_poses)
        detector.detect(current_poses)
        
        stats = detector.get_statistics()
        assert stats['detections_processed'] == 2
    
    def test_events_generated_counter(self, detector):
        """Test that events generated are counted"""
        # Create misalignment
        ref_pos = detector.reference_poses[0].position
        current_poses = {
            0: self.create_pose(0, ref_pos + [0.15, 0, 0])
        }
        
        detector.detect(current_poses)
        
        stats = detector.get_statistics()
        assert stats['events_generated'] == 1
    
    def test_false_positives_suppressed_counter(self, detector):
        """Test that false positives suppressed are counted"""
        detector.sustained_detection_frames = 2
        
        # Create misalignment
        ref_pos = detector.reference_poses[0].position
        current_poses = {
            0: self.create_pose(0, ref_pos + [0.15, 0, 0])
        }
        
        # First detection - not sustained yet
        detector.detect(current_poses)
        
        stats = detector.get_statistics()
        assert stats['false_positives_suppressed'] == 1
    
    def test_reset_statistics(self, detector):
        """Test resetting statistics"""
        current_poses = {
            0: self.create_pose(0, detector.reference_poses[0].position)
        }
        
        detector.detect(current_poses)
        detector.reset_statistics()
        
        stats = detector.get_statistics()
        assert stats['detections_processed'] == 0
        assert stats['events_generated'] == 0



class TestResetDetectionHistory:
    """Test detection history reset"""
    
    @pytest.fixture
    def detector(self):
        """Create detector"""
        calibration = create_mock_calibration()
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0
        )
        return MisalignmentDetector(calibration, thresholds)
    
    def test_reset_single_camera(self, detector):
        """Test resetting detection history for single camera"""
        detector.detection_history[0] = [True, True, False]
        detector.detection_history[1] = [True, False]
        
        detector.reset_detection_history(0)
        
        assert len(detector.detection_history[0]) == 0
        assert len(detector.detection_history[1]) == 2  # Unchanged
    
    def test_reset_all_cameras(self, detector):
        """Test resetting detection history for all cameras"""
        detector.detection_history[0] = [True, True]
        detector.detection_history[1] = [False, True]
        detector.detection_history[2] = [True]
        detector.detection_history[3] = [False, False, True]
        
        detector.reset_detection_history()
        
        for i in range(4):
            assert len(detector.detection_history[i]) == 0
    
    def test_reset_invalid_camera_id(self, detector):
        """Test error when resetting invalid camera ID"""
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            detector.reset_detection_history(5)


class TestQuaternionUtilities:
    """Test quaternion utility methods"""
    
    @pytest.fixture
    def detector(self):
        """Create detector"""
        calibration = create_mock_calibration()
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0
        )
        return MisalignmentDetector(calibration, thresholds)
    
    def test_quaternion_to_euler_identity(self, detector):
        """Test converting identity quaternion to Euler angles"""
        q_identity = np.array([1, 0, 0, 0])
        
        euler = detector._quaternion_to_euler(q_identity)
        
        # Should be near zero
        assert np.allclose(euler, [0, 0, 0], atol=1e-6)
    
    def test_wrap_angle(self, detector):
        """Test angle wrapping to [-180, 180]"""
        assert detector._wrap_angle(0) == 0
        assert detector._wrap_angle(90) == 90
        assert detector._wrap_angle(180) == 180
        assert np.isclose(detector._wrap_angle(270), -90)
        assert np.isclose(detector._wrap_angle(360), 0)
        assert np.isclose(detector._wrap_angle(-270), 90)


class TestEdgeCases:
    """Test edge cases"""
    
    @pytest.fixture
    def detector(self):
        """Create detector"""
        calibration = create_mock_calibration()
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=2.0
        )
        return MisalignmentDetector(calibration, thresholds)
    
    def test_detect_empty_poses(self, detector):
        """Test detection with no poses"""
        events = detector.detect({})
        
        assert len(events) == 0
    
    def test_detect_missing_camera(self, detector):
        """Test detection with some cameras missing"""
        # Only camera 0 present
        pose = PoseEstimate(
            camera_id=0,
            transformation=np.eye(4),
            position=detector.reference_poses[0].position,
            orientation=np.array([1, 0, 0, 0]),
            confidence=0.9,
            timestamp=0
        )
        
        events = detector.detect({0: pose})
        
        # Should handle gracefully
        assert isinstance(events, list)
