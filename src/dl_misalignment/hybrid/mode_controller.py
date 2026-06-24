"""
Mode Selection and Switching System

This module implements the mode controller for selecting between neural network,
rule-based, and hybrid operational modes.

Task 12.2: Implement Mode Selection System
Requirements: 14.2, 14.3, 14.4, 14.5, 14.6
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import numpy as np

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

logger = logging.getLogger(__name__)


# ==============================================================================
# Task 12.2: Detection Mode Enumeration
# ==============================================================================

class DetectionMode(Enum):
    """
    Operational modes for misalignment detection system.
    
    Requirements: 14.2
    """
    NEURAL_NETWORK = "neural_network"  # Use only deep learning models
    RULE_BASED = "rule_based"          # Use only traditional CV
    HYBRID = "hybrid"                  # Combine both approaches
    
    @classmethod
    def from_string(cls, mode_str: str) -> 'DetectionMode':
        """
        Parse mode from string (case-insensitive).
        
        Args:
            mode_str: Mode string from configuration
        
        Returns:
            DetectionMode enum value
        
        Raises:
            ValueError: If mode string is invalid
        
        Example:
            >>> DetectionMode.from_string("neural_network")
            <DetectionMode.NEURAL_NETWORK: 'neural_network'>
        """
        mode_str_lower = mode_str.lower()
        
        for mode in cls:
            if mode.value == mode_str_lower:
                return mode
        
        valid_modes = [m.value for m in cls]
        raise ValueError(
            f"Invalid mode '{mode_str}'. "
            f"Valid modes: {valid_modes}"
        )


# ==============================================================================
# Task 12.2: Detection Result Data Structure
# ==============================================================================

@dataclass
class DetectionResult:
    """
    Unified detection result from any operational mode.
    
    This provides a consistent interface across neural network,
    rule-based, and hybrid modes.
    
    Requirements: 14.5 (identical input/output interface)
    """
    # Per-camera results
    camera_probabilities: Dict[int, float]  # camera_id → misalignment probability [0, 1]
    camera_severities: Dict[int, str]        # camera_id → severity level
    camera_poses: Dict[int, Dict]            # camera_id → 6-DOF pose
    
    # Metadata
    mode: DetectionMode
    processing_time_ms: float
    timestamp: float
    
    # Optional: individual predictions in hybrid mode
    neural_probabilities: Optional[Dict[int, float]] = None
    rule_based_probabilities: Optional[Dict[int, float]] = None
    
    # Optional: confidence/uncertainty
    camera_confidences: Optional[Dict[int, float]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            'camera_probabilities': self.camera_probabilities,
            'camera_severities': self.camera_severities,
            'camera_poses': self.camera_poses,
            'mode': self.mode.value,
            'processing_time_ms': self.processing_time_ms,
            'timestamp': self.timestamp
        }
        
        if self.neural_probabilities is not None:
            result['neural_probabilities'] = self.neural_probabilities
        
        if self.rule_based_probabilities is not None:
            result['rule_based_probabilities'] = self.rule_based_probabilities
        
        if self.camera_confidences is not None:
            result['camera_confidences'] = self.camera_confidences
        
        return result


# ==============================================================================
# Task 12.2: Mode Controller
# ==============================================================================

class ModeController:
    """
    Controls operational mode selection and switching for detection system.
    
    What does the mode controller do?
    1. Manages mode selection (neural_network, rule_based, hybrid)
    2. Routes inference requests to appropriate backend(s)
    3. Provides unified interface for all modes
    4. Supports dynamic mode switching via config update
    
    Why is this important?
    - Backward compatibility with existing rule-based system
    - Flexibility to choose optimal approach per deployment
    - Seamless integration between neural and traditional CV
    - Enables hybrid ensemble for maximum robustness
    
    Requirements: 14.2, 14.3, 14.4, 14.5, 14.6
    """
    
    def __init__(
        self,
        config: Dict,
        neural_network_backend: Optional['InferenceEngine'] = None,
        rule_based_backend: Optional['RuleBasedInterface'] = None
    ):
        """
        Initialize mode controller.
        
        Args:
            config: Configuration dictionary with 'mode' key
            neural_network_backend: Neural network inference engine (optional)
            rule_based_backend: Rule-based detection interface (optional)
        
        Raises:
            ValueError: If mode is invalid or required backend is missing
        
        Requirements: 14.2, 14.4
        """
        # Parse mode from config (Requirement 14.2)
        mode_str = config.get('mode', 'neural_network')
        self.current_mode = DetectionMode.from_string(mode_str)
        
        # Store backends
        self.neural_network_backend = neural_network_backend
        self.rule_based_backend = rule_based_backend
        
        # Validate backend availability
        self._validate_backends()
        
        # Store config
        self.config = config
        
        # Statistics
        self.inference_count = 0
        self.mode_switches = 0
        
        logger.info(f"ModeController initialized with mode: {self.current_mode.value}")
        logger.info(f"  Neural network backend: {'available' if neural_network_backend else 'not available'}")
        logger.info(f"  Rule-based backend: {'available' if rule_based_backend else 'not available'}")
    
    def _validate_backends(self):
        """
        Validate that required backends are available for current mode.
        
        Raises:
            ValueError: If required backend is missing
        
        Requirements: 14.3
        """
        if self.current_mode == DetectionMode.NEURAL_NETWORK:
            if self.neural_network_backend is None:
                raise ValueError(
                    "Neural network mode selected but neural_network_backend not provided"
                )
        
        elif self.current_mode == DetectionMode.RULE_BASED:
            if self.rule_based_backend is None:
                raise ValueError(
                    "Rule-based mode selected but rule_based_backend not provided"
                )
        
        elif self.current_mode == DetectionMode.HYBRID:
            if self.neural_network_backend is None or self.rule_based_backend is None:
                raise ValueError(
                    "Hybrid mode requires both neural_network_backend and rule_based_backend"
                )
    
    def switch_mode(self, new_mode: Union[str, DetectionMode]):
        """
        Switch to a different operational mode.
        
        Supports mode switching without system restart as required.
        
        Args:
            new_mode: New mode (string or DetectionMode enum)
        
        Raises:
            ValueError: If new mode is invalid or backend unavailable
        
        Requirements: 14.6 (mode switching without restart)
        
        Example:
            >>> controller.switch_mode("hybrid")
            >>> controller.current_mode
            <DetectionMode.HYBRID: 'hybrid'>
        """
        # Parse mode if string
        if isinstance(new_mode, str):
            new_mode = DetectionMode.from_string(new_mode)
        
        if new_mode == self.current_mode:
            logger.info(f"Already in {new_mode.value} mode, no switch needed")
            return
        
        logger.info(f"Switching mode from {self.current_mode.value} to {new_mode.value}")
        
        # Store old mode for logging
        old_mode = self.current_mode
        
        # Update mode
        self.current_mode = new_mode
        
        # Validate backends for new mode
        try:
            self._validate_backends()
        except ValueError as e:
            # Rollback on failure
            self.current_mode = old_mode
            logger.error(f"Mode switch failed: {e}")
            raise
        
        # Update statistics
        self.mode_switches += 1
        
        logger.info(f"✓ Mode switched successfully to {new_mode.value}")
    
    def infer(
        self,
        camera_frames: Dict[int, Union[np.ndarray, 'Image.Image']],
        timestamp: Optional[float] = None
    ) -> DetectionResult:
        """
        Run inference using current operational mode.
        
        This is the unified interface that works for all modes.
        
        Args:
            camera_frames: Dictionary mapping camera_id → image
                          Example: {0: img_front, 1: img_left, 2: img_right, 3: img_rear}
            timestamp: Optional timestamp (defaults to current time)
        
        Returns:
            DetectionResult with predictions
        
        Requirements: 14.5 (identical input/output)
        
        Example:
            >>> frames = {0: front_img, 1: left_img, 2: right_img, 3: rear_img}
            >>> result = controller.infer(frames)
            >>> result.camera_probabilities[0]  # Front camera probability
            0.73
        """
        import time
        
        if timestamp is None:
            timestamp = time.time()
        
        start_time = time.time()
        
        self.inference_count += 1
        
        # Route to appropriate backend(s) based on mode
        if self.current_mode == DetectionMode.NEURAL_NETWORK:
            result = self._infer_neural_network(camera_frames, timestamp)
        
        elif self.current_mode == DetectionMode.RULE_BASED:
            result = self._infer_rule_based(camera_frames, timestamp)
        
        elif self.current_mode == DetectionMode.HYBRID:
            result = self._infer_hybrid(camera_frames, timestamp)
        
        else:
            raise RuntimeError(f"Unknown mode: {self.current_mode}")
        
        processing_time = (time.time() - start_time) * 1000
        result.processing_time_ms = processing_time
        
        return result
    
    def _infer_neural_network(
        self,
        camera_frames: Dict[int, Union[np.ndarray, 'Image.Image']],
        timestamp: float
    ) -> DetectionResult:
        """
        Run inference using neural network only.
        
        Requirements: 14.3
        """
        # Convert camera_id (int) to camera_name (str) for inference engine
        # Assuming mapping: 0=front, 1=left, 2=right, 3=rear
        camera_id_to_name = {0: 'front', 1: 'left', 2: 'right', 3: 'rear'}
        
        frames_by_name = {
            camera_id_to_name[cam_id]: frame
            for cam_id, frame in camera_frames.items()
        }
        
        # Run neural network inference
        output = self.neural_network_backend.infer(frames_by_name)
        
        # Convert to unified format
        camera_probabilities = {}
        camera_severities = {}
        camera_poses = {}
        camera_confidences = {}
        
        for cam_id, cam_name in camera_id_to_name.items():
            if cam_id in camera_frames:
                # Find matching result
                cam_result = None
                for result in output.camera_results:
                    if result.camera_id == cam_name:
                        cam_result = result
                        break
                
                if cam_result:
                    camera_probabilities[cam_id] = cam_result.misalignment_probability
                    camera_severities[cam_id] = cam_result.severity_level
                    camera_poses[cam_id] = {
                        'position': cam_result.position,
                        'orientation': cam_result.orientation
                    }
                    if cam_result.probability_uncertainty is not None:
                        camera_confidences[cam_id] = 1.0 - cam_result.probability_uncertainty
        
        return DetectionResult(
            camera_probabilities=camera_probabilities,
            camera_severities=camera_severities,
            camera_poses=camera_poses,
            mode=DetectionMode.NEURAL_NETWORK,
            processing_time_ms=0.0,  # Will be set by caller
            timestamp=timestamp,
            camera_confidences=camera_confidences if camera_confidences else None
        )
    
    def _infer_rule_based(
        self,
        camera_frames: Dict[int, Union[np.ndarray, 'Image.Image']],
        timestamp: float
    ) -> DetectionResult:
        """
        Run inference using rule-based system only.
        
        Requirements: 14.3
        """
        # Run rule-based detection
        result = self.rule_based_backend.detect(camera_frames)
        
        # Convert to unified format
        camera_probabilities = {}
        camera_severities = {}
        camera_poses = {}
        
        for cam_id in camera_frames.keys():
            if cam_id in result:
                camera_probabilities[cam_id] = result[cam_id]['probability']
                camera_severities[cam_id] = result[cam_id]['severity']
                camera_poses[cam_id] = result[cam_id]['pose']
        
        return DetectionResult(
            camera_probabilities=camera_probabilities,
            camera_severities=camera_severities,
            camera_poses=camera_poses,
            mode=DetectionMode.RULE_BASED,
            processing_time_ms=0.0,  # Will be set by caller
            timestamp=timestamp
        )
    
    def _infer_hybrid(
        self,
        camera_frames: Dict[int, Union[np.ndarray, 'Image.Image']],
        timestamp: float
    ) -> DetectionResult:
        """
        Run inference using hybrid ensemble (neural + rule-based).
        
        This will be completed in Task 12.3.
        
        Requirements: 15.1-15.6
        """
        # Import ensemble predictor
        from .ensemble_predictor import EnsemblePredictor
        
        # Get hybrid weights from config
        hybrid_weights = self.config.get('hybrid_weights', {'neural': 0.7, 'rule_based': 0.3})
        
        # Create ensemble predictor
        predictor = EnsemblePredictor(
            neural_weight=hybrid_weights['neural'],
            rule_based_weight=hybrid_weights['rule_based']
        )
        
        # Run both pipelines and ensemble
        result = predictor.predict(
            camera_frames=camera_frames,
            neural_backend=self.neural_network_backend,
            rule_based_backend=self.rule_based_backend,
            timestamp=timestamp
        )
        
        return result
    
    def get_mode(self) -> DetectionMode:
        """Get current operational mode."""
        return self.current_mode
    
    def get_statistics(self) -> Dict:
        """Get mode controller statistics."""
        return {
            'current_mode': self.current_mode.value,
            'inference_count': self.inference_count,
            'mode_switches': self.mode_switches,
            'neural_available': self.neural_network_backend is not None,
            'rule_based_available': self.rule_based_backend is not None
        }
    
    def reset_statistics(self):
        """Reset statistics counters."""
        self.inference_count = 0
        self.mode_switches = 0
    
    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"ModeController(mode={self.current_mode.value}, "
            f"inferences={self.inference_count})"
        )


# ==============================================================================
# Rule-Based System Interface (Stub)
# ==============================================================================

class RuleBasedInterface:
    """
    Interface to existing rule-based detection system.
    
    This is a wrapper that interfaces with the existing rule-based components
    without modifying them.
    
    Requirements: 14.1 (no modifications to existing code)
    """
    
    def __init__(self, calibration, thresholds):
        """
        Initialize rule-based interface.
        
        Args:
            calibration: CalibrationData for reference poses
            thresholds: DetectionThresholds for misalignment detection
        """
        from src.cv.feature_extractor import ORBFeatureExtractor
        from src.cv.flow_analyzer import FlowAnalyzer
        from src.detection.misalignment_detector import MisalignmentDetector
        
        # Initialize existing components (no modifications)
        self.feature_extractor = ORBFeatureExtractor(n_features=2000)
        self.flow_analyzer = FlowAnalyzer()
        self.detector = MisalignmentDetector(calibration, thresholds)
        
        logger.info("RuleBasedInterface initialized (wraps existing system)")
    
    def detect(self, camera_frames: Dict[int, np.ndarray]) -> Dict:
        """
        Run rule-based detection on camera frames.
        
        Args:
            camera_frames: Dictionary mapping camera_id → image array
        
        Returns:
            Dictionary with detection results per camera
        """
        # This is a simplified stub that would interface with the actual
        # rule-based pipeline. For full implementation, would:
        # 1. Extract ORB features from frames
        # 2. Compute dense optical flow
        # 3. Estimate poses using visual SLAM
        # 4. Run misalignment detection
        # 5. Return results in unified format
        
        results = {}
        
        for cam_id in camera_frames.keys():
            # Placeholder: In real implementation, would run full pipeline
            results[cam_id] = {
                'probability': 0.0,  # Would come from actual detection
                'severity': 'NONE',
                'pose': {
                    'position': {'X': 0.0, 'Y': 0.0, 'Z': 0.0},
                    'orientation': {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
                }
            }
        
        return results
