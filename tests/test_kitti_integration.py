"""
Integration Tests for KITTI Data with Pipeline

Tests the entire camera misalignment detection pipeline using KITTI data
"""

import pytest
import numpy as np
from datetime import datetime

from src.data.kitti_loader import create_mock_kitti_sample
from src.cv.feature_extractor import FeatureExtractor, FeatureExtractorConfig
from src.cv.flow_analyzer import OpticalFlowAnalyzer
from src.detection.misalignment_detector import (
    MisalignmentDetector,
    DetectionThresholds
)
from src.alerting.alert_system import AlertSystem, MockAlertChannel
from src.config.calibration import create_mock_calibration
from src.models.core import PoseEstimate


class TestKITTIPipelineIntegration:
    """Test full pipeline with KITTI mock data"""
    
    @pytest.fixture
    def mock_calibration(self):
        """Create mock calibration for testing"""
        return create_mock_calibration()
    
    @pytest.fixture
    def feature_extractor(self):
        """Create feature extractor"""
        config = FeatureExtractorConfig(n_features=500)
        return FeatureExtractor(config)
    
    @pytest.fixture
    def flow_analyzer(self):
        """Create flow analyzer"""
        return OpticalFlowAnalyzer()
    
    @pytest.fixture
    def detector(self, mock_calibration):
        """Create misalignment detector"""
        thresholds = DetectionThresholds(
            position_threshold_m=0.1,
            angle_threshold_deg=5.0,
            flow_inconsistency_threshold=0.3,
            confidence_threshold=0.7
        )
        return MisalignmentDetector(
            calibration=mock_calibration,
            thresholds=thresholds
        )
    
    @pytest.fixture
    def alert_system(self):
        """Create alert system"""
        channel = MockAlertChannel("test-channel")
        return AlertSystem([channel], rate_limit_seconds=0)
    
    def test_extract_features_from_kitti(self, feature_extractor):
        """Test feature extraction from KITTI sample"""
        # Create mock KITTI sample
        sample = create_mock_kitti_sample()
        
        # Extract features from left image (first arg is frame, second is camera_id)
        features = feature_extractor.extract(
            sample.image_left,
            camera_id=0,
            timestamp=sample.timestamp.timestamp()
        )
        
        # Verify features extracted
        assert features is not None
        assert len(features.keypoints) > 0
        assert features.camera_id == 0

    
    def test_compute_flow_from_kitti(self, flow_analyzer):
        """Test optical flow from KITTI stereo pair"""
        # Create two mock samples (consecutive frames)
        sample1 = create_mock_kitti_sample(sample_id="frame_000")
        sample2 = create_mock_kitti_sample(sample_id="frame_001")
        
        # Compute flow between frames (use grayscale)
        gray1 = sample1.image_left[:, :, 0]
        gray2 = sample2.image_left[:, :, 0]
        
        flow_result = flow_analyzer.compute_flow(gray1, gray2)
        
        # Verify flow computed (flow_vectors, not flow)
        assert flow_result is not None
        assert flow_result.flow_vectors.shape[:2] == sample1.image_left.shape[:2]
        assert 0.0 <= np.mean(flow_result.confidence) <= 1.0
    
    def test_full_pipeline_no_misalignment(
        self,
        feature_extractor,
        flow_analyzer,
        detector,
        alert_system
    ):
        """Test full pipeline with no misalignment"""
        # Create KITTI samples
        sample1 = create_mock_kitti_sample()
        sample2 = create_mock_kitti_sample()
        
        # Extract features
        features1 = feature_extractor.extract(
            sample1.image_left,
            camera_id=0,
            timestamp=sample1.timestamp.timestamp()
        )
        
        # Compute flow
        flow = flow_analyzer.compute_flow(
            sample1.image_left[:, :, 0],
            sample2.image_left[:, :, 0]
        )
        
        # Create mock poses (aligned with calibration)
        current_poses = {}
        for i in range(4):
            current_poses[i] = PoseEstimate(
                camera_id=i,
                transformation=np.eye(4),
                position=np.array([i * 1.0, 0.0, 1.5]),  # Match calibration
                orientation=np.array([1.0, 0.0, 0.0, 0.0]),
                confidence=0.9,
                timestamp=0
            )
        
        # Detect misalignment (should be none)
        events = detector.detect(current_poses)
        
        # Process alerts
        for event in events:
            alert_system.process_event(event)
        
        # Verify no alerts sent (no misalignment)
        assert len(events) == 0
        assert alert_system.alerts_sent == 0
    
    def test_full_pipeline_with_misalignment(
        self,
        feature_extractor,
        flow_analyzer,
        detector,
        alert_system
    ):
        """Test full pipeline with misalignment detected"""
        # Create KITTI samples
        sample1 = create_mock_kitti_sample()
        sample2 = create_mock_kitti_sample()
        
        # Extract features
        features = feature_extractor.extract(
            sample1.image_left,
            camera_id=0,
            timestamp=sample1.timestamp.timestamp()
        )
        
        # Compute flow
        flow = flow_analyzer.compute_flow(
            sample1.image_left[:, :, 0],
            sample2.image_left[:, :, 0]
        )
        
        # Create poses with misalignment
        current_poses = {}
        for i in range(4):
            # Camera 0 is misaligned (0.2m off)
            offset = np.array([0.2, 0, 0]) if i == 0 else np.array([0, 0, 0])
            
            current_poses[i] = PoseEstimate(
                camera_id=i,
                transformation=np.eye(4),
                position=np.array([i * 1.0, 0.0, 1.5]) + offset,
                orientation=np.array([1.0, 0.0, 0.0, 0.0]),
                confidence=0.9,
                timestamp=0
            )
        
        # Detect misalignment (frame 1 - not sustained yet)
        events1 = detector.detect(current_poses)
        
        # Detect again (frame 2 - now sustained)
        events2 = detector.detect(current_poses)
        
        # Process alerts
        for event in events2:
            alert_system.process_event(event)
        
        # Verify misalignment detected and alerted
        assert len(events2) > 0
        assert events2[0].camera_id == 0
        assert alert_system.alerts_sent > 0
    
    def test_batch_kitti_samples(self, feature_extractor):
        """Test processing multiple KITTI samples"""
        # Create batch of mock samples
        samples = [create_mock_kitti_sample(sample_id=f"sample_{i:03d}") 
                  for i in range(5)]
        
        # Extract features from all samples
        all_features = []
        for i, sample in enumerate(samples):
            features = feature_extractor.extract(
                sample.image_left,
                camera_id=0,
                timestamp=sample.timestamp.timestamp()
            )
            all_features.append(features)
        
        # Verify all processed
        assert len(all_features) == 5
        assert all(f is not None for f in all_features)
        assert all(len(f.keypoints) > 0 for f in all_features)
    
    def test_stereo_processing(self, feature_extractor):
        """Test processing stereo pair from KITTI"""
        # Create sample with stereo images
        sample = create_mock_kitti_sample()
        
        # Extract features from both cameras
        features_left = feature_extractor.extract(
            sample.image_left,
            camera_id=0,
            timestamp=sample.timestamp.timestamp()
        )
        
        features_right = feature_extractor.extract(
            sample.image_right,
            camera_id=1,
            timestamp=sample.timestamp.timestamp()
        )
        
        # Verify both processed
        assert features_left is not None
        assert features_right is not None
        assert features_left.camera_id == 0
        assert features_right.camera_id == 1
    
    def test_disparity_available(self):
        """Test that KITTI sample includes disparity map"""
        sample = create_mock_kitti_sample()
        
        # Verify disparity present
        assert sample.disparity_map is not None
        assert sample.disparity_map.shape == sample.image_left.shape[:2]
        
        # Disparity should have reasonable values
        assert sample.disparity_map.min() >= 0
        assert sample.disparity_map.max() > 0
    
    def test_temporal_consistency(self, flow_analyzer):
        """Test temporal consistency across KITTI frames"""
        # Create sequence of frames
        frames = [create_mock_kitti_sample(sample_id=f"seq_{i:03d}") 
                 for i in range(3)]
        
        # Compute flow between consecutive frames
        flow_01 = flow_analyzer.compute_flow(
            frames[0].image_left[:, :, 0],
            frames[1].image_left[:, :, 0]
        )
        
        flow_12 = flow_analyzer.compute_flow(
            frames[1].image_left[:, :, 0],
            frames[2].image_left[:, :, 0]
        )
        
        # Both flows should be valid
        assert flow_01 is not None
        assert flow_12 is not None


class TestKITTIDataQuality:
    """Test KITTI data quality checks"""
    
    def test_image_dimensions(self):
        """Test that KITTI images have consistent dimensions"""
        sample = create_mock_kitti_sample(width=1242, height=375)
        
        # KITTI stereo 2012 typical dimensions
        assert sample.image_left.shape[0] == 375
        assert sample.image_left.shape[1] == 1242
        assert sample.image_left.shape[2] == 3  # RGB
    
    def test_image_data_type(self):
        """Test that images have correct data type"""
        sample = create_mock_kitti_sample()
        
        assert sample.image_left.dtype == np.uint8
        assert sample.image_right.dtype == np.uint8
    
    def test_metadata_present(self):
        """Test that metadata is included"""
        sample = create_mock_kitti_sample()
        
        assert sample.metadata is not None
        assert isinstance(sample.metadata, dict)
        assert 'mock' in sample.metadata
    
    def test_timestamp_valid(self):
        """Test that timestamp is valid"""
        sample = create_mock_kitti_sample()
        
        assert sample.timestamp is not None
        assert isinstance(sample.timestamp, datetime)


class TestPipelinePerformance:
    """Test pipeline performance with KITTI data"""
    
    def test_feature_extraction_speed(self):
        """Test feature extraction performance"""
        sample = create_mock_kitti_sample()
        config = FeatureExtractorConfig(n_features=500)
        extractor = FeatureExtractor(config)
        
        import time
        start = time.time()
        
        features = extractor.extract(
            sample.image_left,
            camera_id=0,
            timestamp=sample.timestamp.timestamp()
        )
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time (<500ms for mock data)
        assert elapsed < 0.5
        assert features is not None
    
    def test_flow_computation_speed(self):
        """Test optical flow computation performance"""
        sample1 = create_mock_kitti_sample()
        sample2 = create_mock_kitti_sample()
        analyzer = OpticalFlowAnalyzer()
        
        import time
        start = time.time()
        
        flow = analyzer.compute_flow(
            sample1.image_left[:, :, 0],
            sample2.image_left[:, :, 0]
        )
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time (<500ms for mock data)
        assert elapsed < 0.5
        assert flow is not None
