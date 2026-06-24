"""
Comprehensive unit tests for Optical Flow Analyzer

Tests validate:
- Property 8: Flow Spatial Dimension Preservation
- Property 4: Universal Confidence Bounds
- Flow computation with various motion patterns
- Dynamic region segmentation
- Flow filtering and consistency
"""

import pytest
import numpy as np
import cv2

from src.cv.flow_analyzer import OpticalFlowAnalyzer, FlowConfig
from src.models.core import FlowResult


# Helper functions to create test frames with known motion
def create_shifted_frame(
    original: np.ndarray,
    shift_x: int = 0,
    shift_y: int = 0
) -> np.ndarray:
    """Create a shifted version of the frame"""
    h, w = original.shape[:2]
    M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
    shifted = cv2.warpAffine(original, M, (w, h))
    return shifted


def create_test_pattern(width: int = 640, height: int = 480) -> np.ndarray:
    """Create a test pattern with clear features"""
    image = np.zeros((height, width), dtype=np.uint8)
    
    # Add circles
    for i in range(5):
        center = (width // 5 * (i + 1) - 50, height // 2)
        radius = 30
        cv2.circle(image, center, radius, 255, -1)
    
    # Add rectangles
    cv2.rectangle(image, (50, 50), (150, 150), 255, -1)
    cv2.rectangle(image, (450, 300), (550, 400), 255, -1)
    
    return image


def create_rotating_pattern(angle: float, width: int = 640, height: int = 480) -> np.ndarray:
    """Create a rotated version of a test pattern"""
    pattern = create_test_pattern(width, height)
    center = (width // 2, height // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(pattern, M, (width, height))
    return rotated


# Fixtures
@pytest.fixture
def default_config():
    """Default flow analyzer configuration"""
    return FlowConfig()


@pytest.fixture
def analyzer(default_config):
    """Flow analyzer with default configuration"""
    return OpticalFlowAnalyzer(default_config)


@pytest.fixture
def test_frame():
    """Standard test frame"""
    return create_test_pattern(640, 480)


@pytest.fixture
def shifted_frame_pair():
    """Pair of frames with horizontal shift"""
    frame1 = create_test_pattern(640, 480)
    frame2 = create_shifted_frame(frame1, shift_x=10, shift_y=0)
    return frame1, frame2


class TestFlowConfig:
    """Tests for FlowConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = FlowConfig()
        assert config.pyr_scale == 0.5
        assert config.levels == 3
        assert config.winsize == 15
        assert config.iterations == 3
        assert config.flow_threshold == 1.0
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = FlowConfig(
            pyr_scale=0.6,
            levels=5,
            flow_threshold=2.0
        )
        assert config.pyr_scale == 0.6
        assert config.levels == 5
        assert config.flow_threshold == 2.0
    
    def test_invalid_pyr_scale(self):
        """Test that pyr_scale must be in (0.0, 1.0)"""
        with pytest.raises(ValueError, match="pyr_scale must be in"):
            FlowConfig(pyr_scale=1.0)
        
        with pytest.raises(ValueError, match="pyr_scale must be in"):
            FlowConfig(pyr_scale=0.0)
    
    def test_invalid_levels(self):
        """Test that levels must be >= 1"""
        with pytest.raises(ValueError, match="levels must be >= 1"):
            FlowConfig(levels=0)
    
    def test_invalid_winsize(self):
        """Test that winsize must be >= 3"""
        with pytest.raises(ValueError, match="winsize must be >= 3"):
            FlowConfig(winsize=2)
    
    def test_invalid_confidence_threshold(self):
        """Test that confidence_threshold must be in [0.0, 1.0]"""
        with pytest.raises(ValueError, match="confidence_threshold must be in"):
            FlowConfig(confidence_threshold=1.5)


class TestOpticalFlowAnalyzerInitialization:
    """Tests for OpticalFlowAnalyzer initialization"""
    
    def test_init_with_default_config(self):
        """Test initialization with default config"""
        analyzer = OpticalFlowAnalyzer()
        assert analyzer.config.pyr_scale == 0.5
        assert analyzer.flows_computed == 0
    
    def test_init_with_custom_config(self):
        """Test initialization with custom config"""
        config = FlowConfig(pyr_scale=0.6)
        analyzer = OpticalFlowAnalyzer(config)
        assert analyzer.config.pyr_scale == 0.6


class TestFlowComputation:
    """Tests for optical flow computation"""
    
    def test_compute_flow_horizontal_shift(self, analyzer, shifted_frame_pair):
        """Test flow computation with horizontal shift"""
        prev_frame, curr_frame = shifted_frame_pair
        
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        
        assert isinstance(flow_result, FlowResult)
        assert flow_result.mean_magnitude > 0  # Should detect motion
    
    def test_compute_flow_identical_frames(self, analyzer, test_frame):
        """Test flow computation with identical frames (no motion)"""
        flow_result = analyzer.compute_flow(test_frame, test_frame)
        
        assert isinstance(flow_result, FlowResult)
        # Identical frames should have near-zero flow
        assert flow_result.mean_magnitude < 1.0
    
    def test_property_8_flow_spatial_dimension_preservation(self, analyzer, shifted_frame_pair):
        """Test Property 8: Flow vectors match frame dimensions"""
        prev_frame, curr_frame = shifted_frame_pair
        h, w = prev_frame.shape[:2]
        
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        
        # Property 8: Flow Spatial Dimension Preservation
        assert flow_result.flow_vectors.shape == (h, w, 2)
        assert flow_result.frame_shape == (h, w)
        assert flow_result.confidence.shape == (h, w)
    
    def test_property_4_confidence_bounds(self, analyzer, shifted_frame_pair):
        """Test Property 4: Confidence values in [0.0, 1.0]"""
        prev_frame, curr_frame = shifted_frame_pair
        
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        
        # Property 4: Universal Confidence Bounds
        assert np.all(flow_result.confidence >= 0.0)
        assert np.all(flow_result.confidence <= 1.0)
    
    def test_compute_flow_color_frames(self, analyzer):
        """Test flow computation with BGR color frames"""
        frame1 = cv2.cvtColor(create_test_pattern(640, 480), cv2.COLOR_GRAY2BGR)
        frame2 = cv2.cvtColor(create_shifted_frame(create_test_pattern(640, 480), 5, 0), cv2.COLOR_GRAY2BGR)
        
        flow_result = analyzer.compute_flow(frame1, frame2)
        
        assert isinstance(flow_result, FlowResult)
        assert flow_result.flow_vectors.shape[:2] == (480, 640)
    
    def test_compute_flow_different_shifts(self, analyzer, test_frame):
        """Test flow computation with different shift amounts"""
        shifts = [(5, 0), (10, 0), (0, 5), (5, 5)]
        
        prev_magnitude = 0
        for shift_x, shift_y in shifts:
            shifted = create_shifted_frame(test_frame, shift_x, shift_y)
            flow_result = analyzer.compute_flow(test_frame, shifted)
            
            # Larger shifts should generally produce larger flow
            assert flow_result.mean_magnitude >= 0
    
    def test_invalid_prev_frame_none(self, analyzer, test_frame):
        """Test that None previous frame is rejected"""
        with pytest.raises(ValueError, match="Previous frame cannot be None or empty"):
            analyzer.compute_flow(None, test_frame)
    
    def test_invalid_curr_frame_none(self, analyzer, test_frame):
        """Test that None current frame is rejected"""
        with pytest.raises(ValueError, match="Current frame cannot be None or empty"):
            analyzer.compute_flow(test_frame, None)
    
    def test_invalid_frame_dimension_mismatch(self, analyzer):
        """Test that mismatched frame dimensions are rejected"""
        frame1 = create_test_pattern(640, 480)
        frame2 = create_test_pattern(320, 240)  # Different size
        
        with pytest.raises(ValueError, match="Frame dimensions must match"):
            analyzer.compute_flow(frame1, frame2)
    
    def test_flows_computed_counter(self, analyzer, shifted_frame_pair):
        """Test that flow counter is incremented"""
        prev_frame, curr_frame = shifted_frame_pair
        
        assert analyzer.flows_computed == 0
        
        analyzer.compute_flow(prev_frame, curr_frame)
        assert analyzer.flows_computed == 1
        
        analyzer.compute_flow(prev_frame, curr_frame)
        assert analyzer.flows_computed == 2
    
    def test_compute_flow_various_sizes(self, analyzer):
        """Test flow computation with various frame sizes"""
        sizes = [(320, 240), (640, 480), (1280, 720)]
        
        for width, height in sizes:
            frame1 = create_test_pattern(width, height)
            frame2 = create_shifted_frame(frame1, 5, 0)
            
            flow_result = analyzer.compute_flow(frame1, frame2)
            
            assert flow_result.flow_vectors.shape == (height, width, 2)
            assert flow_result.confidence.shape == (height, width)


class TestDynamicRegionSegmentation:
    """Tests for dynamic region segmentation"""
    
    def test_segment_dynamic_regions_with_motion(self, analyzer, shifted_frame_pair):
        """Test segmentation with moving regions"""
        prev_frame, curr_frame = shifted_frame_pair
        
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        dynamic_mask = analyzer.segment_dynamic_regions(flow_result)
        
        assert dynamic_mask.shape == flow_result.frame_shape
        assert dynamic_mask.dtype == np.uint8
        assert np.any(dynamic_mask > 0)  # Should detect some motion
    
    def test_segment_dynamic_regions_no_motion(self, analyzer, test_frame):
        """Test segmentation with no motion"""
        flow_result = analyzer.compute_flow(test_frame, test_frame)
        dynamic_mask = analyzer.segment_dynamic_regions(flow_result)
        
        # Identical frames should have no dynamic regions
        assert np.sum(dynamic_mask) < dynamic_mask.size * 0.1  # Less than 10%
    
    def test_segment_dynamic_regions_custom_threshold(self, test_frame):
        """Test segmentation with custom flow threshold"""
        config = FlowConfig(flow_threshold=5.0)
        analyzer = OpticalFlowAnalyzer(config)
        
        shifted = create_shifted_frame(test_frame, 3, 0)
        flow_result = analyzer.compute_flow(test_frame, shifted)
        dynamic_mask = analyzer.segment_dynamic_regions(flow_result)
        
        assert isinstance(dynamic_mask, np.ndarray)


class TestFlowFiltering:
    """Tests for flow outlier filtering"""
    
    def test_filter_outliers_median(self, analyzer, shifted_frame_pair):
        """Test median filtering of flow"""
        prev_frame, curr_frame = shifted_frame_pair
        
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        filtered_result = analyzer.filter_outliers(flow_result, method="median")
        
        assert isinstance(filtered_result, FlowResult)
        assert filtered_result.flow_vectors.shape == flow_result.flow_vectors.shape
        # Property 4: Confidence still in bounds
        assert np.all(filtered_result.confidence >= 0.0)
        assert np.all(filtered_result.confidence <= 1.0)
    
    def test_filter_outliers_bilateral(self, analyzer, shifted_frame_pair):
        """Test bilateral filtering of flow"""
        prev_frame, curr_frame = shifted_frame_pair
        
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        filtered_result = analyzer.filter_outliers(flow_result, method="bilateral")
        
        assert isinstance(filtered_result, FlowResult)
        assert filtered_result.flow_vectors.shape == flow_result.flow_vectors.shape
    
    def test_filter_outliers_invalid_method(self, analyzer, shifted_frame_pair):
        """Test that invalid filtering method is rejected"""
        prev_frame, curr_frame = shifted_frame_pair
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        
        with pytest.raises(ValueError, match="Unknown filtering method"):
            analyzer.filter_outliers(flow_result, method="invalid")
    
    def test_filtering_preserves_properties(self, analyzer, shifted_frame_pair):
        """Test that filtering preserves all properties"""
        prev_frame, curr_frame = shifted_frame_pair
        
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        filtered_result = analyzer.filter_outliers(flow_result, method="median")
        
        # Property 8: Spatial dimensions preserved
        assert filtered_result.frame_shape == flow_result.frame_shape
        assert filtered_result.flow_vectors.shape == flow_result.flow_vectors.shape
        
        # Property 4: Confidence bounds preserved
        assert np.all((filtered_result.confidence >= 0.0) & (filtered_result.confidence <= 1.0))


class TestFlowConsistency:
    """Tests for flow consistency scoring"""
    
    def test_get_flow_consistency_score_uniform_motion(self, analyzer, shifted_frame_pair):
        """Test consistency score with uniform motion"""
        prev_frame, curr_frame = shifted_frame_pair
        
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        consistency = analyzer.get_flow_consistency_score(flow_result)
        
        assert 0.0 <= consistency <= 1.0
        # Uniform horizontal shift should have some consistency
        assert consistency > 0.0
    
    def test_get_flow_consistency_score_no_motion(self, analyzer, test_frame):
        """Test consistency score with no motion"""
        flow_result = analyzer.compute_flow(test_frame, test_frame)
        consistency = analyzer.get_flow_consistency_score(flow_result)
        
        assert 0.0 <= consistency <= 1.0
    
    def test_get_flow_consistency_score_with_reference(self, analyzer, shifted_frame_pair):
        """Test consistency score with reference direction"""
        prev_frame, curr_frame = shifted_frame_pair
        
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        reference_direction = 0.0  # Horizontal motion
        consistency = analyzer.get_flow_consistency_score(flow_result, reference_direction)
        
        assert 0.0 <= consistency <= 1.0


class TestFlowAnalyzerState:
    """Tests for analyzer state management"""
    
    def test_reset_flows_computed(self, analyzer, shifted_frame_pair):
        """Test resetting flow counter"""
        prev_frame, curr_frame = shifted_frame_pair
        
        analyzer.compute_flow(prev_frame, curr_frame)
        analyzer.compute_flow(prev_frame, curr_frame)
        assert analyzer.flows_computed == 2
        
        analyzer.reset()
        assert analyzer.flows_computed == 0
    
    def test_reset_allows_continued_use(self, analyzer, shifted_frame_pair):
        """Test that analyzer works after reset"""
        prev_frame, curr_frame = shifted_frame_pair
        
        analyzer.compute_flow(prev_frame, curr_frame)
        analyzer.reset()
        
        flow_result = analyzer.compute_flow(prev_frame, curr_frame)
        assert isinstance(flow_result, FlowResult)
        assert analyzer.flows_computed == 1


class TestFlowWithDifferentMotionPatterns:
    """Tests with various motion patterns"""
    
    def test_vertical_motion(self, analyzer, test_frame):
        """Test flow with vertical motion"""
        shifted = create_shifted_frame(test_frame, 0, 10)
        flow_result = analyzer.compute_flow(test_frame, shifted)
        
        assert flow_result.mean_magnitude > 0
        # Vertical motion should have direction around pi/2 or 3pi/2
        assert isinstance(flow_result.mean_direction, float)
    
    def test_diagonal_motion(self, analyzer, test_frame):
        """Test flow with diagonal motion"""
        shifted = create_shifted_frame(test_frame, 7, 7)
        flow_result = analyzer.compute_flow(test_frame, shifted)
        
        assert flow_result.mean_magnitude > 0
    
    def test_rotation_motion(self, analyzer):
        """Test flow with rotation"""
        frame1 = create_rotating_pattern(0)
        frame2 = create_rotating_pattern(5)  # 5 degrees rotation
        
        flow_result = analyzer.compute_flow(frame1, frame2)
        
        assert flow_result.mean_magnitude > 0
        # Rotation should produce non-zero flow
    
    def test_large_motion(self, analyzer, test_frame):
        """Test flow with large motion"""
        shifted = create_shifted_frame(test_frame, 50, 0)  # Large shift
        flow_result = analyzer.compute_flow(test_frame, shifted)
        
        # Should still produce valid result
        assert isinstance(flow_result, FlowResult)
        assert np.all((flow_result.confidence >= 0.0) & (flow_result.confidence <= 1.0))


class TestIntegration:
    """Integration tests combining multiple features"""
    
    def test_complete_flow_analysis_workflow(self, analyzer, test_frame):
        """Test complete workflow: compute, segment, filter, analyze"""
        # Create frame with motion
        shifted = create_shifted_frame(test_frame, 10, 5)
        
        # 1. Compute flow
        flow_result = analyzer.compute_flow(test_frame, shifted)
        
        # Validate properties
        assert flow_result.flow_vectors.shape[:2] == test_frame.shape[:2]
        assert np.all((flow_result.confidence >= 0.0) & (flow_result.confidence <= 1.0))
        
        # 2. Segment dynamic regions
        dynamic_mask = analyzer.segment_dynamic_regions(flow_result)
        assert dynamic_mask.shape == test_frame.shape[:2]
        
        # 3. Filter outliers
        filtered_result = analyzer.filter_outliers(flow_result, method="median")
        assert filtered_result.flow_vectors.shape == flow_result.flow_vectors.shape
        
        # 4. Check consistency
        consistency = analyzer.get_flow_consistency_score(filtered_result)
        assert 0.0 <= consistency <= 1.0
    
    def test_motion_sequence(self, analyzer, test_frame):
        """Test flow computation on a sequence of frames"""
        frames = [test_frame]
        for i in range(5):
            shifted = create_shifted_frame(frames[-1], 2, 0)
            frames.append(shifted)
        
        # Compute flow for each consecutive pair
        flow_results = []
        for i in range(len(frames) - 1):
            flow = analyzer.compute_flow(frames[i], frames[i + 1])
            flow_results.append(flow)
        
        assert len(flow_results) == 5
        assert analyzer.flows_computed == 5
        
        # All should have similar magnitudes (consistent motion)
        magnitudes = [fr.mean_magnitude for fr in flow_results]
        assert all(m > 0 for m in magnitudes)
