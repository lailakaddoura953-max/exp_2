"""
Comprehensive unit tests for Feature Extraction module

Tests validate:
- Property 2: Feature-Descriptor Correspondence
- Property 12: Timestamp Association
- Property 7: Camera ID Validity
- Feature extraction with various image types
- Batch processing
- Quality metrics and thresholds
"""

import pytest
import numpy as np
import cv2

from src.cv.feature_extractor import FeatureExtractor, FeatureExtractorConfig
from src.models.core import FeatureSet


# Helper functions to create test images
def create_test_image(width: int = 640, height: int = 480, pattern: str = "checkerboard") -> np.ndarray:
    """Create a test image with visual features"""
    if pattern == "checkerboard":
        # Create checkerboard pattern with good features
        block_size = 40
        image = np.zeros((height, width), dtype=np.uint8)
        for i in range(0, height, block_size):
            for j in range(0, width, block_size):
                if (i // block_size + j // block_size) % 2 == 0:
                    image[i:i+block_size, j:j+block_size] = 255
        return image
    
    elif pattern == "gradient":
        # Create gradient image
        x = np.linspace(0, 255, width, dtype=np.uint8)
        image = np.tile(x, (height, 1))
        return image
    
    elif pattern == "random":
        # Random noise image
        return np.random.randint(0, 256, (height, width), dtype=np.uint8)
    
    elif pattern == "blank":
        # Blank image (no features)
        return np.zeros((height, width), dtype=np.uint8)
    
    elif pattern == "corners":
        # Image with distinct corners
        image = np.zeros((height, width), dtype=np.uint8)
        # Add some rectangles
        cv2.rectangle(image, (100, 100), (200, 200), 255, -1)
        cv2.rectangle(image, (300, 200), (400, 350), 255, -1)
        cv2.rectangle(image, (450, 300), (550, 400), 255, -1)
        return image
    
    else:
        raise ValueError(f"Unknown pattern: {pattern}")


def create_color_test_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Create a BGR color test image"""
    image = create_test_image(width, height, "checkerboard")
    # Convert to BGR
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)


# Fixtures
@pytest.fixture
def default_config():
    """Default feature extractor configuration"""
    return FeatureExtractorConfig()


@pytest.fixture
def extractor(default_config):
    """Feature extractor with default configuration"""
    return FeatureExtractor(default_config)


@pytest.fixture
def test_frame():
    """Standard test frame with good features"""
    return create_test_image(640, 480, "checkerboard")


@pytest.fixture
def color_test_frame():
    """Standard test frame in BGR color"""
    return create_color_test_image(640, 480)


class TestFeatureExtractorConfig:
    """Tests for FeatureExtractorConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = FeatureExtractorConfig()
        assert config.n_features == 500
        assert config.scale_factor == 1.2
        assert config.n_levels == 8
        assert config.min_features_threshold == 50
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = FeatureExtractorConfig(
            n_features=1000,
            scale_factor=1.5,
            min_features_threshold=100
        )
        assert config.n_features == 1000
        assert config.scale_factor == 1.5
        assert config.min_features_threshold == 100
    
    def test_invalid_n_features(self):
        """Test that n_features must be positive"""
        with pytest.raises(ValueError, match="n_features must be positive"):
            FeatureExtractorConfig(n_features=0)
    
    def test_invalid_scale_factor(self):
        """Test that scale_factor must be > 1.0"""
        with pytest.raises(ValueError, match="scale_factor must be > 1.0"):
            FeatureExtractorConfig(scale_factor=1.0)
    
    def test_invalid_n_levels(self):
        """Test that n_levels must be >= 1"""
        with pytest.raises(ValueError, match="n_levels must be >= 1"):
            FeatureExtractorConfig(n_levels=0)
    
    def test_invalid_min_threshold(self):
        """Test that min_features_threshold must be non-negative"""
        with pytest.raises(ValueError, match="min_features_threshold must be non-negative"):
            FeatureExtractorConfig(min_features_threshold=-10)


class TestFeatureExtractorInitialization:
    """Tests for FeatureExtractor initialization"""
    
    def test_init_with_default_config(self):
        """Test initialization with default config"""
        extractor = FeatureExtractor()
        assert extractor.config.n_features == 500
        assert extractor.frames_processed == 0
    
    def test_init_with_custom_config(self):
        """Test initialization with custom config"""
        config = FeatureExtractorConfig(n_features=1000)
        extractor = FeatureExtractor(config)
        assert extractor.config.n_features == 1000
    
    def test_orb_detector_created(self, extractor):
        """Test that ORB detector is created"""
        assert extractor.orb is not None
        assert hasattr(extractor.orb, 'detectAndCompute')


class TestFeatureExtraction:
    """Tests for single frame feature extraction"""
    
    def test_extract_from_grayscale_image(self, extractor, test_frame):
        """Test extracting features from grayscale image"""
        features = extractor.extract(test_frame, camera_id=0, timestamp=1000000)
        
        assert isinstance(features, FeatureSet)
        assert features.camera_id == 0
        assert features.timestamp == 1000000
        assert len(features.keypoints) > 0
        assert features.descriptors.shape[0] > 0
    
    def test_extract_from_color_image(self, extractor, color_test_frame):
        """Test extracting features from BGR color image"""
        features = extractor.extract(color_test_frame, camera_id=1, timestamp=2000000)
        
        assert isinstance(features, FeatureSet)
        assert features.camera_id == 1
        assert len(features.keypoints) > 0
    
    def test_property_2_feature_descriptor_correspondence(self, extractor, test_frame):
        """Test Property 2: Number of keypoints must equal descriptor rows"""
        features = extractor.extract(test_frame, camera_id=0)
        
        # Property 2: Feature-Descriptor Correspondence
        assert len(features.keypoints) == features.descriptors.shape[0]
    
    def test_property_12_timestamp_association(self, extractor, test_frame):
        """Test Property 12: Timestamp is correctly associated with features"""
        timestamp = 5000000
        features = extractor.extract(test_frame, camera_id=0, timestamp=timestamp)
        
        # Property 12: Timestamp Association
        assert features.timestamp == timestamp
    
    def test_auto_timestamp_generation(self, extractor, test_frame):
        """Test automatic timestamp generation when not provided"""
        features1 = extractor.extract(test_frame, camera_id=0)
        features2 = extractor.extract(test_frame, camera_id=0)
        
        # Timestamps should be different and increasing
        assert features1.timestamp != features2.timestamp
        assert features2.timestamp > features1.timestamp
    
    def test_property_7_camera_id_validity(self, extractor, test_frame):
        """Test Property 7: Camera ID must be in valid range [0, 3]"""
        # Valid camera IDs
        for camera_id in range(4):
            features = extractor.extract(test_frame, camera_id=camera_id)
            assert features.camera_id == camera_id
        
        # Invalid camera IDs
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            extractor.extract(test_frame, camera_id=-1)
        
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            extractor.extract(test_frame, camera_id=4)
    
    def test_extract_from_blank_image(self, extractor):
        """Test extracting features from blank image (no features)"""
        blank_frame = create_test_image(640, 480, "blank")
        features = extractor.extract(blank_frame, camera_id=0)
        
        # Should return empty feature set
        assert len(features.keypoints) == 0
        assert features.descriptors.shape[0] == 0
        # Property 2 still holds (0 == 0)
        assert len(features.keypoints) == features.descriptors.shape[0]
    
    def test_extract_with_different_image_sizes(self, extractor):
        """Test extraction with various image sizes"""
        sizes = [(320, 240), (640, 480), (1280, 720), (1920, 1080)]
        
        for width, height in sizes:
            frame = create_test_image(width, height, "checkerboard")
            features = extractor.extract(frame, camera_id=0)
            
            assert isinstance(features, FeatureSet)
            assert len(features.keypoints) == features.descriptors.shape[0]
    
    def test_invalid_frame_none(self, extractor):
        """Test that None frame is rejected"""
        with pytest.raises(ValueError, match="Frame cannot be None or empty"):
            extractor.extract(None, camera_id=0)
    
    def test_invalid_frame_empty(self, extractor):
        """Test that empty frame is rejected"""
        empty_frame = np.array([])
        with pytest.raises(ValueError, match="Frame cannot be None or empty"):
            extractor.extract(empty_frame, camera_id=0)
    
    def test_frames_processed_counter(self, extractor, test_frame):
        """Test that frame counter is incremented"""
        assert extractor.frames_processed == 0
        
        extractor.extract(test_frame, camera_id=0)
        assert extractor.frames_processed == 1
        
        extractor.extract(test_frame, camera_id=0)
        assert extractor.frames_processed == 2


class TestBatchExtraction:
    """Tests for batch feature extraction"""
    
    def test_extract_batch_single_camera(self, extractor, test_frame):
        """Test batch extraction with single camera"""
        frames = {0: test_frame}
        timestamps = {0: 1000000}
        
        results = extractor.extract_batch(frames, timestamps)
        
        assert len(results) == 1
        assert 0 in results
        assert isinstance(results[0], FeatureSet)
        assert results[0].camera_id == 0
        assert results[0].timestamp == 1000000
    
    def test_extract_batch_multiple_cameras(self, extractor):
        """Test batch extraction with all 4 cameras"""
        frames = {
            0: create_test_image(640, 480, "checkerboard"),
            1: create_test_image(640, 480, "corners"),
            2: create_test_image(640, 480, "gradient"),
            3: create_test_image(640, 480, "random")
        }
        timestamps = {0: 1000000, 1: 1000010, 2: 1000020, 3: 1000030}
        
        results = extractor.extract_batch(frames, timestamps)
        
        assert len(results) == 4
        for camera_id in range(4):
            assert camera_id in results
            assert results[camera_id].camera_id == camera_id
            assert results[camera_id].timestamp == timestamps[camera_id]
            # Property 2
            assert len(results[camera_id].keypoints) == results[camera_id].descriptors.shape[0]
    
    def test_extract_batch_without_timestamps(self, extractor, test_frame):
        """Test batch extraction with auto-generated timestamps"""
        frames = {0: test_frame, 1: test_frame}
        
        results = extractor.extract_batch(frames)
        
        assert len(results) == 2
        assert results[0].timestamp != results[1].timestamp
    
    def test_extract_batch_empty_frames(self, extractor):
        """Test that empty frames dict is rejected"""
        with pytest.raises(ValueError, match="Frames dictionary cannot be empty"):
            extractor.extract_batch({})
    
    def test_extract_batch_invalid_camera_id(self, extractor, test_frame):
        """Test that invalid camera ID in batch is rejected"""
        frames = {0: test_frame, 10: test_frame}  # 10 is invalid
        
        with pytest.raises(ValueError, match="Camera ID must be in range"):
            extractor.extract_batch(frames)
    
    def test_extract_batch_partial_timestamps(self, extractor, test_frame):
        """Test batch extraction with partial timestamp dict"""
        frames = {0: test_frame, 1: test_frame, 2: test_frame}
        timestamps = {0: 1000000, 2: 2000000}  # Missing camera 1
        
        results = extractor.extract_batch(frames, timestamps)
        
        assert results[0].timestamp == 1000000
        assert results[1].timestamp != 1000000  # Auto-generated
        assert results[2].timestamp == 2000000


class TestQualityMetrics:
    """Tests for feature quality assessment"""
    
    def test_is_frame_quality_sufficient_good_features(self, extractor, test_frame):
        """Test quality check with sufficient features"""
        features = extractor.extract(test_frame, camera_id=0)
        
        # Checkerboard pattern should produce many features
        assert extractor.is_frame_quality_sufficient(features)
    
    def test_is_frame_quality_sufficient_poor_features(self, extractor):
        """Test quality check with insufficient features"""
        # Blank image produces no features
        blank_frame = create_test_image(640, 480, "blank")
        features = extractor.extract(blank_frame, camera_id=0)
        
        assert not extractor.is_frame_quality_sufficient(features)
    
    def test_get_feature_quality_metrics(self, extractor, test_frame):
        """Test quality metrics calculation"""
        features = extractor.extract(test_frame, camera_id=0)
        metrics = extractor.get_feature_quality_metrics(features)
        
        assert "feature_count" in metrics
        assert "quality_ratio" in metrics
        assert "sufficient" in metrics
        assert "min_threshold" in metrics
        assert "target_features" in metrics
        
        assert isinstance(metrics["feature_count"], int)
        assert 0.0 <= metrics["quality_ratio"] <= 1.0
        assert isinstance(metrics["sufficient"], bool)
    
    def test_quality_metrics_with_custom_threshold(self):
        """Test quality metrics with custom threshold"""
        config = FeatureExtractorConfig(n_features=500, min_features_threshold=200)
        extractor = FeatureExtractor(config)
        
        frame = create_test_image(640, 480, "gradient")
        features = extractor.extract(frame, camera_id=0)
        metrics = extractor.get_feature_quality_metrics(features)
        
        assert metrics["min_threshold"] == 200
        assert metrics["target_features"] == 500


class TestFeatureExtractorState:
    """Tests for extractor state management"""
    
    def test_reset_frames_processed(self, extractor, test_frame):
        """Test resetting frame counter"""
        extractor.extract(test_frame, camera_id=0)
        extractor.extract(test_frame, camera_id=0)
        assert extractor.frames_processed == 2
        
        extractor.reset()
        assert extractor.frames_processed == 0
    
    def test_reset_allows_continued_use(self, extractor, test_frame):
        """Test that extractor works after reset"""
        extractor.extract(test_frame, camera_id=0)
        extractor.reset()
        
        features = extractor.extract(test_frame, camera_id=0)
        assert isinstance(features, FeatureSet)
        assert extractor.frames_processed == 1


class TestFeatureConsistency:
    """Tests for feature extraction consistency and repeatability"""
    
    def test_same_image_produces_same_features(self, extractor, test_frame):
        """Test that same image produces consistent features"""
        features1 = extractor.extract(test_frame.copy(), camera_id=0, timestamp=1000000)
        features2 = extractor.extract(test_frame.copy(), camera_id=0, timestamp=1000000)
        
        # Should extract same number of features
        assert len(features1.keypoints) == len(features2.keypoints)
        
        # Descriptor matrices should have same shape
        assert features1.descriptors.shape == features2.descriptors.shape
    
    def test_different_images_produce_different_features(self, extractor):
        """Test that different images produce different features"""
        frame1 = create_test_image(640, 480, "checkerboard")
        frame2 = create_test_image(640, 480, "corners")
        
        features1 = extractor.extract(frame1, camera_id=0, timestamp=1000000)
        features2 = extractor.extract(frame2, camera_id=0, timestamp=1000000)
        
        # Features should be different (at least keypoint locations)
        assert features1.keypoints != features2.keypoints


class TestIntegration:
    """Integration tests combining multiple features"""
    
    def test_complete_extraction_workflow(self, extractor):
        """Test complete workflow: batch extraction with quality checks"""
        # Create frames for all 4 cameras
        frames = {
            0: create_test_image(640, 480, "checkerboard"),
            1: create_test_image(640, 480, "corners"),
            2: create_test_image(640, 480, "gradient"),
            3: create_test_image(640, 480, "random")
        }
        timestamps = {0: 1000000, 1: 1000010, 2: 1000020, 3: 1000030}
        
        # Extract features
        results = extractor.extract_batch(frames, timestamps)
        
        # Validate all results
        for camera_id, features in results.items():
            # Check basic structure
            assert features.camera_id == camera_id
            assert features.timestamp == timestamps[camera_id]
            
            # Property 2: Feature-Descriptor Correspondence
            assert len(features.keypoints) == features.descriptors.shape[0]
            
            # Get quality metrics
            metrics = extractor.get_feature_quality_metrics(features)
            assert "feature_count" in metrics
            
            # Quality assessment
            is_good = extractor.is_frame_quality_sufficient(features)
            assert isinstance(is_good, bool)
    
    def test_mixed_quality_frames(self, extractor):
        """Test handling frames with varying feature quality"""
        frames = {
            0: create_test_image(640, 480, "checkerboard"),  # Many features
            1: create_test_image(640, 480, "blank"),         # No features
            2: create_test_image(640, 480, "gradient"),      # Some features
        }
        
        results = extractor.extract_batch(frames)
        
        # All should succeed even with varying quality
        assert len(results) == 3
        
        # Check quality varies
        quality_0 = extractor.is_frame_quality_sufficient(results[0])
        quality_1 = extractor.is_frame_quality_sufficient(results[1])
        
        # Checkerboard should have sufficient features
        assert quality_0
        # Blank should not
        assert not quality_1
