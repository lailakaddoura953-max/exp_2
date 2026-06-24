"""
Hybrid Ensemble Prediction

This module implements the ensemble predictor that combines neural network
and rule-based predictions using weighted averaging.

Task 12.3: Implement Hybrid Ensemble Prediction
Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

import logging
import time
from typing import Dict, Optional, Union
import numpy as np

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

from .mode_controller import DetectionResult, DetectionMode

logger = logging.getLogger(__name__)


# ==============================================================================
# Task 12.3: Ensemble Predictor
# ==============================================================================

class EnsemblePredictor:
    """
    Combines neural network and rule-based predictions using weighted ensemble.
    
    What does the ensemble predictor do?
    1. Executes both neural network and rule-based pipelines in parallel
    2. Computes weighted average of predictions
    3. Outputs individual AND ensemble predictions
    4. Falls back to rule-based if neural network fails
    
    Why use ensemble prediction?
    - Leverages strengths of both approaches
    - More robust than either system alone
    - Reduces false positives and false negatives
    - Provides fallback redundancy
    
    Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
    """
    
    def __init__(
        self,
        neural_weight: float = 0.7,
        rule_based_weight: float = 0.3
    ):
        """
        Initialize ensemble predictor.
        
        Args:
            neural_weight: Weight for neural network predictions (default 0.7)
            rule_based_weight: Weight for rule-based predictions (default 0.3)
        
        Raises:
            ValueError: If weights don't sum to 1.0
        
        Requirements: 15.2 (weighted average), 15.3 (configurable weights)
        
        Example:
            >>> predictor = EnsemblePredictor(neural_weight=0.7, rule_based_weight=0.3)
            >>> predictor.neural_weight
            0.7
        """
        # Validate weights
        weight_sum = neural_weight + rule_based_weight
        if not np.isclose(weight_sum, 1.0, atol=1e-6):
            raise ValueError(
                f"Weights must sum to 1.0, got {weight_sum} "
                f"(neural={neural_weight}, rule_based={rule_based_weight})"
            )
        
        if neural_weight < 0 or neural_weight > 1:
            raise ValueError(f"Neural weight must be in [0, 1], got {neural_weight}")
        
        if rule_based_weight < 0 or rule_based_weight > 1:
            raise ValueError(f"Rule-based weight must be in [0, 1], got {rule_based_weight}")
        
        self.neural_weight = neural_weight
        self.rule_based_weight = rule_based_weight
        
        # Statistics
        self.predictions_count = 0
        self.neural_failures = 0
        self.rule_based_failures = 0
        self.fallback_count = 0
        
        logger.info(
            f"EnsemblePredictor initialized with weights: "
            f"neural={neural_weight:.2f}, rule_based={rule_based_weight:.2f}"
        )
    
    def predict(
        self,
        camera_frames: Dict[int, Union[np.ndarray, 'Image.Image']],
        neural_backend: 'InferenceEngine',
        rule_based_backend: 'RuleBasedInterface',
        timestamp: float
    ) -> DetectionResult:
        """
        Run hybrid ensemble prediction.
        
        Executes both pipelines and combines predictions using weighted averaging.
        
        Args:
            camera_frames: Dictionary mapping camera_id → image
            neural_backend: Neural network inference engine
            rule_based_backend: Rule-based detection interface
            timestamp: Prediction timestamp
        
        Returns:
            DetectionResult with ensemble predictions
        
        Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
        
        Example:
            >>> frames = {0: front_img, 1: left_img, 2: right_img, 3: rear_img}
            >>> result = predictor.predict(frames, neural, rule_based, time.time())
            >>> result.camera_probabilities[0]  # Ensemble probability
            0.68
            >>> result.neural_probabilities[0]  # Individual neural prediction
            0.80
            >>> result.rule_based_probabilities[0]  # Individual rule-based prediction
            0.40
        """
        self.predictions_count += 1
        
        start_time = time.time()
        
        # ==================================================================
        # Requirement 15.1: Execute both pipelines in parallel
        # ==================================================================
        # Note: True parallel execution would use threading/multiprocessing
        # For simplicity, we run sequentially but could be parallelized
        
        neural_probabilities = None
        rule_based_probabilities = None
        neural_severities = None
        rule_based_severities = None
        neural_poses = None
        
        # Try neural network inference
        try:
            neural_result = self._run_neural_network(
                camera_frames, neural_backend, timestamp
            )
            neural_probabilities = neural_result.camera_probabilities
            neural_severities = neural_result.camera_severities
            neural_poses = neural_result.camera_poses
            
        except Exception as e:
            logger.error(f"Neural network inference failed: {e}")
            self.neural_failures += 1
            neural_probabilities = None
        
        # Run rule-based detection
        try:
            rule_based_result = self._run_rule_based(
                camera_frames, rule_based_backend, timestamp
            )
            rule_based_probabilities = rule_based_result.camera_probabilities
            rule_based_severities = rule_based_result.camera_severities
            
        except Exception as e:
            logger.error(f"Rule-based detection failed: {e}")
            self.rule_based_failures += 1
            rule_based_probabilities = None
        
        # ==================================================================
        # Requirement 15.6: Fallback to rule-based if neural fails
        # ==================================================================
        if neural_probabilities is None and rule_based_probabilities is None:
            # Both failed - critical error
            raise RuntimeError("Both neural network and rule-based detection failed")
        
        elif neural_probabilities is None:
            # Neural failed, use rule-based only
            logger.warning("Neural network failed, using rule-based predictions only")
            self.fallback_count += 1
            
            processing_time = (time.time() - start_time) * 1000
            
            return DetectionResult(
                camera_probabilities=rule_based_probabilities,
                camera_severities=rule_based_severities,
                camera_poses=rule_based_result.camera_poses,
                mode=DetectionMode.HYBRID,
                processing_time_ms=processing_time,
                timestamp=timestamp,
                neural_probabilities=None,  # Failed
                rule_based_probabilities=rule_based_probabilities
            )
        
        elif rule_based_probabilities is None:
            # Rule-based failed, use neural only
            logger.warning("Rule-based detection failed, using neural predictions only")
            
            processing_time = (time.time() - start_time) * 1000
            
            return DetectionResult(
                camera_probabilities=neural_probabilities,
                camera_severities=neural_severities,
                camera_poses=neural_poses,
                mode=DetectionMode.HYBRID,
                processing_time_ms=processing_time,
                timestamp=timestamp,
                neural_probabilities=neural_probabilities,
                rule_based_probabilities=None  # Failed
            )
        
        # ==================================================================
        # Requirement 15.2: Compute weighted average
        # ==================================================================
        ensemble_probabilities = self._compute_ensemble(
            neural_probabilities,
            rule_based_probabilities
        )
        
        # ==================================================================
        # Requirement 15.4: Output individual AND ensemble predictions
        # ==================================================================
        ensemble_severities = self._classify_severities(ensemble_probabilities)
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.debug(
            f"Hybrid prediction complete: {len(ensemble_probabilities)} cameras, "
            f"{processing_time:.1f}ms"
        )
        
        return DetectionResult(
            camera_probabilities=ensemble_probabilities,
            camera_severities=ensemble_severities,
            camera_poses=neural_poses,  # Use neural network poses
            mode=DetectionMode.HYBRID,
            processing_time_ms=processing_time,
            timestamp=timestamp,
            neural_probabilities=neural_probabilities,
            rule_based_probabilities=rule_based_probabilities
        )
    
    def _run_neural_network(
        self,
        camera_frames: Dict[int, Union[np.ndarray, 'Image.Image']],
        neural_backend: 'InferenceEngine',
        timestamp: float
    ) -> DetectionResult:
        """
        Run neural network inference.
        
        Args:
            camera_frames: Camera frames
            neural_backend: Inference engine
            timestamp: Timestamp
        
        Returns:
            DetectionResult from neural network
        """
        # Convert camera_id (int) to camera_name (str) for inference engine
        camera_id_to_name = {0: 'front', 1: 'left', 2: 'right', 3: 'rear'}
        
        frames_by_name = {
            camera_id_to_name[cam_id]: frame
            for cam_id, frame in camera_frames.items()
            if cam_id in camera_id_to_name
        }
        
        # Run inference
        output = neural_backend.infer(frames_by_name)
        
        # Convert to unified format
        camera_probabilities = {}
        camera_severities = {}
        camera_poses = {}
        
        for cam_id, cam_name in camera_id_to_name.items():
            if cam_id in camera_frames:
                # Find matching result
                for result in output.camera_results:
                    if result.camera_id == cam_name:
                        camera_probabilities[cam_id] = result.misalignment_probability
                        camera_severities[cam_id] = result.severity_level
                        camera_poses[cam_id] = {
                            'position': result.position,
                            'orientation': result.orientation
                        }
                        break
        
        return DetectionResult(
            camera_probabilities=camera_probabilities,
            camera_severities=camera_severities,
            camera_poses=camera_poses,
            mode=DetectionMode.NEURAL_NETWORK,
            processing_time_ms=output.processing_time_ms,
            timestamp=timestamp
        )
    
    def _run_rule_based(
        self,
        camera_frames: Dict[int, Union[np.ndarray, 'Image.Image']],
        rule_based_backend: 'RuleBasedInterface',
        timestamp: float
    ) -> DetectionResult:
        """
        Run rule-based detection.
        
        Args:
            camera_frames: Camera frames
            rule_based_backend: Rule-based interface
            timestamp: Timestamp
        
        Returns:
            DetectionResult from rule-based system
        """
        # Convert PIL images to numpy arrays if needed
        frames_np = {}
        for cam_id, frame in camera_frames.items():
            if PIL_AVAILABLE and isinstance(frame, Image.Image):
                frames_np[cam_id] = np.array(frame)
            else:
                frames_np[cam_id] = frame
        
        # Run rule-based detection
        result = rule_based_backend.detect(frames_np)
        
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
            processing_time_ms=0.0,
            timestamp=timestamp
        )
    
    def _compute_ensemble(
        self,
        neural_probs: Dict[int, float],
        rule_based_probs: Dict[int, float]
    ) -> Dict[int, float]:
        """
        Compute weighted ensemble of predictions.
        
        Requirement 15.2: Weighted average (default 0.7 neural + 0.3 rule-based)
        
        Args:
            neural_probs: Neural network probabilities per camera
            rule_based_probs: Rule-based probabilities per camera
        
        Returns:
            Ensemble probabilities per camera
        
        Example:
            >>> neural = {0: 0.8, 1: 0.3}
            >>> rule_based = {0: 0.4, 1: 0.6}
            >>> predictor._compute_ensemble(neural, rule_based)
            {0: 0.68, 1: 0.39}  # 0.7*0.8 + 0.3*0.4 = 0.68, 0.7*0.3 + 0.3*0.6 = 0.39
        """
        ensemble = {}
        
        # Get all camera IDs from both predictions
        all_camera_ids = set(neural_probs.keys()) | set(rule_based_probs.keys())
        
        for cam_id in all_camera_ids:
            neural_prob = neural_probs.get(cam_id, 0.0)
            rule_based_prob = rule_based_probs.get(cam_id, 0.0)
            
            # Weighted average
            ensemble_prob = (
                self.neural_weight * neural_prob +
                self.rule_based_weight * rule_based_prob
            )
            
            # Clamp to [0, 1] range
            ensemble_prob = np.clip(ensemble_prob, 0.0, 1.0)
            
            ensemble[cam_id] = float(ensemble_prob)
        
        return ensemble
    
    def _classify_severities(
        self,
        probabilities: Dict[int, float]
    ) -> Dict[int, str]:
        """
        Classify severity levels from probabilities.
        
        Uses same thresholds as design specification:
        - [0.25, 0.50): LOW
        - [0.50, 0.75): MEDIUM
        - [0.75, 0.90): HIGH
        - [0.90, 1.00]: CRITICAL
        - <0.25: NONE
        
        Args:
            probabilities: Misalignment probabilities per camera
        
        Returns:
            Severity levels per camera
        """
        severities = {}
        
        for cam_id, prob in probabilities.items():
            if prob >= 0.90:
                severity = 'CRITICAL'
            elif prob >= 0.75:
                severity = 'HIGH'
            elif prob >= 0.50:
                severity = 'MEDIUM'
            elif prob >= 0.25:
                severity = 'LOW'
            else:
                severity = 'NONE'
            
            severities[cam_id] = severity
        
        return severities
    
    def get_statistics(self) -> Dict:
        """Get ensemble predictor statistics."""
        return {
            'predictions_count': self.predictions_count,
            'neural_failures': self.neural_failures,
            'rule_based_failures': self.rule_based_failures,
            'fallback_count': self.fallback_count,
            'neural_weight': self.neural_weight,
            'rule_based_weight': self.rule_based_weight
        }
    
    def reset_statistics(self):
        """Reset statistics counters."""
        self.predictions_count = 0
        self.neural_failures = 0
        self.rule_based_failures = 0
        self.fallback_count = 0
    
    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"EnsemblePredictor(neural_weight={self.neural_weight:.2f}, "
            f"rule_based_weight={self.rule_based_weight:.2f}, "
            f"predictions={self.predictions_count})"
        )
