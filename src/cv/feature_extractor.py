"""
Feature Extraction Engine using ORB detector

This module extracts robust visual features from camera frames for tracking
and matching. Uses ORB (Oriented FAST and Rotated BRIEF) for efficiency.

Properties validated:
- Property 2: Feature-Descriptor Correspondence (keypoint count = descriptor rows)
- Property 12: Timestamp Association (features inherit frame timestamp)
"""

import cv2
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass

from src.models.core import FeatureSet, CameraConfig


@dataclass
class FeatureExtractorConfig:
    """Configuration for ORB feature extraction"""
    n_features: int = 500  # Maximum number of features to extract
    scale_factor: float = 1.2  # Pyramid scale factor
    n_levels: int = 8  # Number of pyramid levels
    edge_threshold: int = 31  # Size of border where features are not detected
    first_level: int = 0  # First pyramid level
    wta_k: int = 2  # Number of points for oriented BRIEF descriptor
    score_type: int = cv2.ORB_HARRIS_SCORE  # Harris or FAST score
    patch_size: int = 31  # Size of patch used for oriented BRIEF
    fast_threshold: int = 20  # FAST detector threshold
    min_features_threshold: int = 50  # Minimum features for valid frame
    
    def __post_init__(self):
        """Validate configuration parameters"""
        if self.n_features <= 0:
            raise ValueError(f"n_features must be positive, got {self.n_features}")
        if self.scale_factor <= 1.0:
            raise ValueError(f"scale_factor must be > 1.0, got {self.scale_factor}")
        if self.n_levels < 1:
            raise ValueError(f"n_levels must be >= 1, got {self.n_levels}")
        if self.min_features_threshold < 0:
            raise ValueError(f"min_features_threshold must be non-negative, got {self.min_features_threshold}")


class FeatureExtractor:
    """
    Extract ORB features from camera frames
    
    This class handles feature extraction with quality filtering and validation.
    All extracted features are validated to ensure Property 2 (feature-descriptor
    correspondence) is maintained.
    """
    
    def __init__(self, config: Optional[FeatureExtractorConfig] = None):
        """
        Initialize the feature extractor
        
        Args:
            config: Feature extraction configuration (uses defaults if None)
        """
        self.config = config or FeatureExtractorConfig()
        
        # Create ORB detector with configuration
        self.orb = cv2.ORB_create(
            nfeatures=self.config.n_features,
            scaleFactor=self.config.scale_factor,
            nlevels=self.config.n_levels,
            edgeThreshold=self.config.edge_threshold,
            firstLevel=self.config.first_level,
            WTA_K=self.config.wta_k,
            scoreType=self.config.score_type,
            patchSize=self.config.patch_size,
            fastThreshold=self.config.fast_threshold
        )
        
        self._frame_count = 0  # Track frames processed
    
    def extract(
        self,
        frame: np.ndarray,
        camera_id: int,
        timestamp: Optional[int] = None
    ) -> FeatureSet:
        """
        Extract ORB features from a single frame
        
        Args:
            frame: Input image (BGR or grayscale)
            camera_id: Camera ID (must be 0-3)
            timestamp: Frame timestamp in microseconds (auto-generated if None)
        
        Returns:
            FeatureSet with extracted keypoints and descriptors
        
        Raises:
            ValueError: If frame is invalid or camera_id out of range
            
        Properties validated:
            - Property 2: Ensures keypoint count equals descriptor rows
            - Property 12: Associates timestamp with features
        """
        # Validate inputs
        if frame is None or frame.size == 0:
            raise ValueError("Frame cannot be None or empty")
        
        if not (0 <= camera_id <= 3):
            raise ValueError(f"Camera ID must be in range [0, 3], got {camera_id}")
        
        # Convert to grayscale if needed
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        # Extract features
        keypoints, descriptors = self.orb.detectAndCompute(gray, None)
        
        # Handle case where no features found
        if descriptors is None:
            descriptors = np.array([], dtype=np.uint8).reshape(0, 32)
            keypoints = []
        
        # Convert keypoints to simple (x, y) tuples for FeatureSet
        keypoint_coords = [(kp.pt[0], kp.pt[1]) for kp in keypoints]
        
        # Generate timestamp if not provided (Property 12)
        if timestamp is None:
            timestamp = self._generate_timestamp()
        
        # Create FeatureSet (automatically validates Property 2)
        feature_set = FeatureSet(
            camera_id=camera_id,
            keypoints=keypoint_coords,
            descriptors=descriptors,
            timestamp=timestamp
        )
        
        self._frame_count += 1
        return feature_set
    
    def extract_batch(
        self,
        frames: Dict[int, np.ndarray],
        timestamps: Optional[Dict[int, int]] = None
    ) -> Dict[int, FeatureSet]:
        """
        Extract features from multiple frames (batch processing)
        
        Args:
            frames: Dictionary mapping camera_id -> frame
            timestamps: Optional dictionary mapping camera_id -> timestamp
        
        Returns:
            Dictionary mapping camera_id -> FeatureSet
        
        Raises:
            ValueError: If any camera_id is invalid
        """
        if not frames:
            raise ValueError("Frames dictionary cannot be empty")
        
        # Validate all camera IDs first
        for camera_id in frames.keys():
            if not (0 <= camera_id <= 3):
                raise ValueError(f"Camera ID must be in range [0, 3], got {camera_id}")
        
        results = {}
        for camera_id, frame in frames.items():
            timestamp = timestamps.get(camera_id) if timestamps else None
            results[camera_id] = self.extract(frame, camera_id, timestamp)
        
        return results
    
    def is_frame_quality_sufficient(self, feature_set: FeatureSet) -> bool:
        """
        Check if frame has sufficient features for tracking
        
        Args:
            feature_set: Extracted features to check
        
        Returns:
            True if feature count >= min_features_threshold
        """
        return len(feature_set.keypoints) >= self.config.min_features_threshold
    
    def get_feature_quality_metrics(self, feature_set: FeatureSet) -> Dict[str, float]:
        """
        Calculate quality metrics for extracted features
        
        Args:
            feature_set: Extracted features
        
        Returns:
            Dictionary with quality metrics:
            - feature_count: Number of features extracted
            - quality_ratio: Ratio of extracted to target features
            - sufficient: Whether count meets minimum threshold
        """
        feature_count = len(feature_set.keypoints)
        quality_ratio = feature_count / self.config.n_features
        sufficient = feature_count >= self.config.min_features_threshold
        
        return {
            "feature_count": feature_count,
            "quality_ratio": quality_ratio,
            "sufficient": sufficient,
            "min_threshold": self.config.min_features_threshold,
            "target_features": self.config.n_features
        }
    
    def _generate_timestamp(self) -> int:
        """
        Generate a timestamp for frames without explicit timestamps
        
        Returns:
            Timestamp in microseconds (based on frame count)
        """
        # Simple timestamp generation for testing
        # In production, this would use actual system time
        return self._frame_count * 33333  # ~30fps (33.333ms per frame)
    
    @property
    def frames_processed(self) -> int:
        """Get count of frames processed"""
        return self._frame_count
    
    def reset(self):
        """Reset the extractor state"""
        self._frame_count = 0
