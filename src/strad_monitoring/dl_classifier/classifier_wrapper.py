"""
DL Classifier Wrapper for Strad Carrier Monitoring

This module provides a simplified interface to the existing deep learning
misalignment detection system for integration with the Strad Carrier
monitoring automation system.

Key Features:
1. Wraps InferenceEngine for snapshot classification
2. Maps model outputs to severity levels (none, moderate, critical)
3. Handles preprocessing of snapshots from VLC capture
4. Provides confidence scoring and classification results
5. Tracks processing time and performance metrics

Task 6.1: DL Classifier Wrapper Integration
Requirements: 4.1, 4.2
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Union
import numpy as np

try:
    import torch
    from PIL import Image
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    Image = None

# Import existing inference components
# Use relative imports to avoid module path issues
import sys
from pathlib import Path

# Add src directory to path if not already there
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from dl_misalignment.inference.inference_engine import InferenceEngine
from dl_misalignment.inference.preprocessing import ImagePreprocessor

logger = logging.getLogger(__name__)


# ==============================================================================
# Data Types
# ==============================================================================

@dataclass
class ClassificationResult:
    """
    Result of camera misalignment classification.
    
    Attributes:
        severity: Classification level ('none', 'moderate', 'critical')
        confidence: Confidence score from 0.0 to 1.0
        processing_time_ms: Time taken for classification in milliseconds
        raw_output: Model-specific diagnostic data
    
    Requirements: 4.3, 4.4, 4.5
    """
    severity: str  # 'none', 'moderate', 'critical'
    confidence: float  # 0.0 to 1.0
    processing_time_ms: float
    raw_output: Dict  # Model-specific diagnostic data


# ==============================================================================
# Task 6.1: DL Classifier Wrapper
# ==============================================================================

class DLClassifierWrapper:
    """
    Wrapper for deep learning misalignment classifier.
    
    What does this wrapper do?
    1. Simplifies the InferenceEngine interface for single-snapshot classification
    2. Handles preprocessing of RGB numpy arrays from VLC capture
    3. Maps model probability outputs to severity levels (none/moderate/critical)
    4. Provides confidence scores and performance tracking
    
    Why wrap the InferenceEngine?
    - InferenceEngine is designed for 4-camera batch processing
    - Monitoring system processes one strad at a time
    - Need simpler interface: snapshot in → classification out
    - Abstract away model complexity from orchestration layer
    
    Severity Mapping:
    - probability < 0.3: "none" (properly aligned)
    - 0.3 ≤ probability < 0.7: "moderate" (minor misalignment)
    - probability ≥ 0.7: "critical" (severe misalignment)
    
    Requirements: 4.1, 4.2
    """
    
    def __init__(
        self,
        model_checkpoint_path: str,
        config: Dict,
        device: str = 'cuda'
    ):
        """
        Initialize DL classifier wrapper.
        
        Args:
            model_checkpoint_path: Path to PyTorch model checkpoint (.pth file)
            config: Configuration dictionary with model settings
            device: 'cuda' for GPU or 'cpu' for CPU
        
        Raises:
            ImportError: If PyTorch is not available
            FileNotFoundError: If checkpoint doesn't exist
            RuntimeError: If checkpoint loading fails
        
        Requirements: 4.1
        """
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch required for DL classification. "
                "Install with: pip install torch torchvision"
            )
        
        self.config = config
        self.device = device
        self.model_checkpoint_path = model_checkpoint_path
        
        logger.info("Initializing DLClassifierWrapper...")
        logger.info(f"  Checkpoint: {model_checkpoint_path}")
        logger.info(f"  Device: {device}")
        
        # ======================================================================
        # Load existing InferenceEngine with model checkpoint
        # ======================================================================
        try:
            self.inference_engine = InferenceEngine(
                checkpoint_path=model_checkpoint_path,
                config=config,
                device=device
            )
            logger.info("✓ InferenceEngine loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load InferenceEngine: {e}")
            raise RuntimeError(f"InferenceEngine loading failed: {e}")
        
        # ======================================================================
        # Initialize standalone preprocessor for snapshot preprocessing
        # ======================================================================
        target_res = tuple(config.get('target_resolution', [640, 640]))
        self.preprocessor = ImagePreprocessor(
            target_resolution=target_res,
            normalization_mean=config.get('normalization_mean'),
            normalization_std=config.get('normalization_std'),
            device=device
        )
        
        # ======================================================================
        # Severity mapping thresholds
        # ======================================================================
        # These map model probability output to human-readable severity levels
        self.none_threshold = config.get('none_threshold', 0.3)
        self.moderate_threshold = config.get('moderate_threshold', 0.7)
        
        # Performance tracking
        self.classification_count = 0
        self.total_classification_time = 0.0
        
        logger.info("✓ DLClassifierWrapper initialized")
        logger.info(f"  Target resolution: {target_res}")
        logger.info(f"  Severity thresholds: none<{self.none_threshold}, "
                   f"moderate<{self.moderate_threshold}, critical≥{self.moderate_threshold}")
    
    def classify_snapshot(
        self,
        snapshot: np.ndarray
    ) -> ClassificationResult:
        """
        Classify snapshot for camera misalignment.
        
        This is the primary interface for the monitoring system.
        Takes a raw snapshot from VLC capture and returns a classification result.
        
        Processing Pipeline:
        1. Validate input: Check snapshot is RGB numpy array
        2. Preprocess: Convert to PIL Image → Resize to 640x640 → Normalize → Tensor
        3. Inference: Run through neural network model
        4. Map output: Convert probability to severity level
        5. Return result: Classification with confidence and timing
        
        Args:
            snapshot: RGB numpy array (H, W, 3) from VLC capture
                     Values should be in range [0, 255] as uint8
        
        Returns:
            ClassificationResult with severity, confidence, timing, and raw output
        
        Raises:
            ValueError: If snapshot format is invalid
            RuntimeError: If classification fails
            TimeoutError: If classification exceeds 10 seconds (future enhancement)
        
        Requirements: 4.1, 4.2, 4.3, 4.5
        
        Example:
            >>> wrapper = DLClassifierWrapper('model.pth', config)
            >>> snapshot = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            >>> result = wrapper.classify_snapshot(snapshot)
            >>> result.severity in ['none', 'moderate', 'critical']
            True
            >>> 0.0 <= result.confidence <= 1.0
            True
        """
        start_time = time.time()
        
        # ======================================================================
        # Step 1: Validate input snapshot
        # ======================================================================
        try:
            self._validate_snapshot(snapshot)
        except Exception as e:
            logger.error(f"Snapshot validation failed: {e}")
            raise ValueError(f"Invalid snapshot format: {e}")
        
        # ======================================================================
        # Step 2: Run inference using existing InferenceEngine
        # ======================================================================
        try:
            # Use single-camera inference mode with dummy camera ID
            detection = self.inference_engine.infer_single_camera(
                camera_id='strad_camera',
                image=snapshot
            )
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise RuntimeError(f"Classification inference failed: {e}")
        
        # ======================================================================
        # Step 3: Map probability to severity level
        # ======================================================================
        probability = detection.probability
        severity = self._map_severity(probability)
        
        # ======================================================================
        # Step 4: Calculate processing time and prepare result
        # ======================================================================
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Build raw output dictionary for diagnostic purposes
        raw_output = {
            'camera_id': detection.camera_id,
            'probability': detection.probability,
            'pose': detection.pose,
            'severity_level': detection.severity.value,
            'has_uncertainty': detection.has_uncertainty,
            'model_version': self.inference_engine.model_version,
            'architecture': self.inference_engine.architecture
        }
        
        # Include uncertainty if available
        if detection.has_uncertainty:
            raw_output['probability_uncertainty'] = detection.probability_uncertainty
            raw_output['pose_uncertainty'] = detection.pose_uncertainty
        
        result = ClassificationResult(
            severity=severity,
            confidence=probability,
            processing_time_ms=processing_time_ms,
            raw_output=raw_output
        )
        
        # Update statistics
        self.classification_count += 1
        self.total_classification_time += processing_time_ms
        
        # Log classification result
        logger.info(
            f"Classification complete: severity={severity}, "
            f"confidence={probability:.3f}, time={processing_time_ms:.1f}ms"
        )
        
        # Check if processing time exceeded target (10 seconds = 10000ms)
        if processing_time_ms > 10000:
            logger.warning(
                f"Classification took {processing_time_ms:.1f}ms, "
                f"exceeding 10-second target"
            )
        
        return result
    
    def _validate_snapshot(self, snapshot: np.ndarray) -> None:
        """
        Validate snapshot format.
        
        Args:
            snapshot: Input snapshot array
        
        Raises:
            ValueError: If snapshot format is invalid
        
        Requirements: 3.5 (snapshot dimension validation)
        """
        if not isinstance(snapshot, np.ndarray):
            raise ValueError(
                f"Expected numpy array, got {type(snapshot)}"
            )
        
        if snapshot.ndim != 3:
            raise ValueError(
                f"Expected 3D array (H, W, C), got shape {snapshot.shape}"
            )
        
        height, width, channels = snapshot.shape
        
        if channels != 3:
            raise ValueError(
                f"Expected 3 channels (RGB), got {channels}"
            )
        
        # Validate minimum dimensions (640x480 per requirement 3.5)
        if height < 480 or width < 640:
            logger.warning(
                f"Snapshot dimensions {width}x{height} below minimum 640x480"
            )
        
        # Validate data type
        if snapshot.dtype != np.uint8:
            logger.warning(
                f"Snapshot dtype is {snapshot.dtype}, expected uint8. "
                f"Values will be clipped to [0, 255]"
            )
    
    def _map_severity(self, probability: float) -> str:
        """
        Map model probability to severity level.
        
        Mapping rules:
        - probability < 0.3: "none" (properly aligned)
        - 0.3 ≤ probability < 0.7: "moderate" (minor misalignment)
        - probability ≥ 0.7: "critical" (severe misalignment)
        
        Args:
            probability: Model output probability (0.0 to 1.0)
        
        Returns:
            Severity level string: 'none', 'moderate', or 'critical'
        
        Requirements: 4.3 (severity classification)
        """
        if probability < self.none_threshold:
            return 'none'
        elif probability < self.moderate_threshold:
            return 'moderate'
        else:
            return 'critical'
    
    def get_statistics(self) -> Dict:
        """
        Get classification statistics.
        
        Returns:
            Dictionary with performance metrics
        
        Example:
            >>> wrapper = DLClassifierWrapper('model.pth', config)
            >>> stats = wrapper.get_statistics()
            >>> 'classification_count' in stats
            True
        """
        avg_time_ms = 0.0
        if self.classification_count > 0:
            avg_time_ms = self.total_classification_time / self.classification_count
        
        stats = {
            'classification_count': self.classification_count,
            'average_processing_time_ms': avg_time_ms,
            'total_processing_time_ms': self.total_classification_time,
            'none_threshold': self.none_threshold,
            'moderate_threshold': self.moderate_threshold
        }
        
        # Include InferenceEngine statistics
        engine_stats = self.inference_engine.get_statistics()
        stats['inference_engine'] = engine_stats
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset performance statistics."""
        self.classification_count = 0
        self.total_classification_time = 0.0
        self.inference_engine.reset_statistics()
    
    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"DLClassifierWrapper(checkpoint={self.model_checkpoint_path}, "
            f"device={self.device}, classifications={self.classification_count})"
        )


# ==============================================================================
# Utility Functions
# ==============================================================================

def create_default_config() -> Dict:
    """
    Create default configuration for DL classifier.
    
    Returns:
        Default configuration dictionary
    
    Example:
        >>> config = create_default_config()
        >>> config['target_resolution']
        [640, 640]
    """
    return {
        'target_resolution': [640, 640],
        'flow_network': 'liteflownet2',
        'confidence_threshold': 0.5,
        'enable_uncertainty': False,
        'none_threshold': 0.3,
        'moderate_threshold': 0.7,
        'latency_target_ms': 10000.0  # 10 seconds
    }


def load_classifier_from_config(
    checkpoint_path: str,
    config_dict: Dict = None,
    device: str = 'cuda'
) -> DLClassifierWrapper:
    """
    Load classifier wrapper from configuration.
    
    Args:
        checkpoint_path: Path to model checkpoint
        config_dict: Configuration dictionary (uses defaults if None)
        device: 'cuda' or 'cpu'
    
    Returns:
        DLClassifierWrapper instance
    
    Example:
        >>> wrapper = load_classifier_from_config('model.pth')
        >>> isinstance(wrapper, DLClassifierWrapper)
        True
    """
    if config_dict is None:
        config_dict = create_default_config()
    
    return DLClassifierWrapper(
        model_checkpoint_path=checkpoint_path,
        config=config_dict,
        device=device
    )
