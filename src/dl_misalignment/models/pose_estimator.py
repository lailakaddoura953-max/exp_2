"""
Pose Estimator: Multi-Task Head for Misalignment Detection

This is the final component of the neural network pipeline. It takes features
and optical flow, then outputs:
1. Misalignment probability [0, 1]
2. 6-DOF camera pose (position X,Y,Z + rotation roll,pitch,yaw)
3. Severity classification (LOW, MEDIUM, HIGH, CRITICAL)
4. Uncertainty estimates (optional, via Monte Carlo Dropout)

What is a multi-task head?
- Single network that learns multiple related tasks simultaneously
- Shares feature representations across tasks
- More efficient than training separate networks
- Tasks help each other learn (multi-task learning benefit)

Why multi-task learning works:
- Misalignment probability and pose are correlated
- Learning pose helps network understand spatial changes
- Learning probability helps network focus on relevant features
- Shared representations prevent overfitting

Architecture Design:
Input: Level 0 features (64 channels) + optical flow (2 channels) = 66 channels
│
├─ Global Average Pooling (spatial → feature vector)
├─ Shared FC layer: 66 → 256 with Dropout(0.3)
│
├─ Branch 1: Misalignment Probability
│  └─ FC: 256 → 128 → 1 with Sigmoid
│
└─ Branch 2: 6-DOF Pose
   └─ FC: 256 → 128 → 6 (no activation)

Task 7 Implementation: Pose Estimator Module
Requirements: 10.1-10.6, 11.1-11.7, 12.1-12.6, 13.1-13.6
"""

import logging
from typing import Tuple, Optional, Dict
from enum import Enum

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None
    F = None

logger = logging.getLogger(__name__)


# ==============================================================================
# Severity Level Classification
# ==============================================================================

class SeverityLevel(Enum):
    """
    Severity levels for misalignment classification.
    
    Based on misalignment probability thresholds:
    - NONE:     probability < 0.25 (no action needed)
    - LOW:      0.25 ≤ probability < 0.50 (monitor)
    - MEDIUM:   0.50 ≤ probability < 0.75 (investigate)
    - HIGH:     0.75 ≤ probability < 0.90 (alert)
    - CRITICAL: 0.90 ≤ probability ≤ 1.00 (immediate action)
    
    Requirements: 11.1-11.7
    """
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def classify_severity(probability: float) -> SeverityLevel:
    """
    Classify misalignment severity based on probability.
    
    Args:
        probability: Misalignment probability in range [0, 1]
    
    Returns:
        SeverityLevel enum
    
    Requirements: 11.2, 11.3, 11.4, 11.5, 11.6
    
    Example:
        >>> classify_severity(0.15)
        <SeverityLevel.NONE: 'NONE'>
        >>> classify_severity(0.35)
        <SeverityLevel.LOW: 'LOW'>
        >>> classify_severity(0.65)
        <SeverityLevel.MEDIUM: 'MEDIUM'>
        >>> classify_severity(0.85)
        <SeverityLevel.HIGH: 'HIGH'>
        >>> classify_severity(0.95)
        <SeverityLevel.CRITICAL: 'CRITICAL'>
    """
    if probability < 0.25:
        return SeverityLevel.NONE
    elif probability < 0.50:
        return SeverityLevel.LOW
    elif probability < 0.75:
        return SeverityLevel.MEDIUM
    elif probability < 0.90:
        return SeverityLevel.HIGH
    else:
        return SeverityLevel.CRITICAL


# ==============================================================================
# Task 7.1: Pose Estimator Module
# ==============================================================================

class PoseEstimator(nn.Module if TORCH_AVAILABLE else object):
    """
    Multi-task head for misalignment probability and 6-DOF pose estimation.
    
    What does this module do?
    1. Takes features + optical flow as input
    2. Compresses spatial information via global average pooling
    3. Processes through shared feature layers
    4. Splits into two branches:
       - Misalignment probability (classification)
       - 6-DOF camera pose (regression)
    
    Architecture Details:
    ┌──────────────────────────────────────────────────────────────┐
    │ Input: feat_level0 [B, 64, H, W] + flow [B, 2, H, W]        │
    │ Concatenate → [B, 66, H, W]                                  │
    ├──────────────────────────────────────────────────────────────┤
    │ Global Average Pooling                                        │
    │ [B, 66, H, W] → [B, 66] (spatial dimensions collapsed)      │
    ├──────────────────────────────────────────────────────────────┤
    │ Shared Feature Processing:                                    │
    │   FC: 66 → 256 with ReLU                                     │
    │   Dropout(p=0.3) for regularization                          │
    ├──────────────────────────────────────────────────────────────┤
    │ Branch 1: Misalignment Probability                           │
    │   FC: 256 → 128 with ReLU + Dropout(0.3)                    │
    │   FC: 128 → 1 with Sigmoid                                   │
    │   Output: [B, 1] in range [0, 1]                            │
    ├──────────────────────────────────────────────────────────────┤
    │ Branch 2: 6-DOF Pose                                         │
    │   FC: 256 → 128 with ReLU + Dropout(0.3)                    │
    │   FC: 128 → 6 (no activation)                                │
    │   Output: [B, 6] = [X, Y, Z, roll, pitch, yaw]              │
    │   - Position (X,Y,Z) in meters                               │
    │   - Orientation (roll,pitch,yaw) in degrees                  │
    └──────────────────────────────────────────────────────────────┘
    
    Why this architecture?
    - Global pooling: Converts spatial features to single vector
    - Shared layers: Common representations help both tasks
    - Separate branches: Task-specific processing
    - Dropout: Prevents overfitting, enables uncertainty estimation
    
    Requirements: 10.1-10.6, 12.1-12.6
    """
    
    def __init__(
        self,
        feature_channels: int = 64,
        flow_channels: int = 2,
        shared_dim: int = 256,
        branch_dim: int = 128,
        dropout_rate: float = 0.3
    ):
        """
        Initialize Pose Estimator.
        
        Args:
            feature_channels: Number of feature channels from Level 0 (default: 64)
            flow_channels: Number of optical flow channels (default: 2 for u,v)
            shared_dim: Dimension of shared feature layer (default: 256)
            branch_dim: Dimension of branch-specific layers (default: 128)
            dropout_rate: Dropout probability for regularization (default: 0.3)
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        super(PoseEstimator, self).__init__()
        
        self.feature_channels = feature_channels
        self.flow_channels = flow_channels
        input_dim = feature_channels + flow_channels  # 64 + 2 = 66
        
        # ======================================================================
        # Shared Feature Processing
        # ======================================================================
        # These layers are shared between both tasks
        # Learning shared representations helps both probability and pose estimation
        self.shared_fc = nn.Linear(input_dim, shared_dim)
        self.shared_dropout = nn.Dropout(p=dropout_rate)
        
        # ======================================================================
        # Branch 1: Misalignment Probability Estimation
        # ======================================================================
        # Binary classification: is the camera misaligned?
        # Output: single value in [0, 1] via sigmoid
        self.prob_fc1 = nn.Linear(shared_dim, branch_dim)
        self.prob_dropout = nn.Dropout(p=dropout_rate)
        self.prob_fc2 = nn.Linear(branch_dim, 1)
        
        # ======================================================================
        # Branch 2: 6-DOF Camera Pose Regression
        # ======================================================================
        # Regression: predict 6 continuous values
        # Output: [X, Y, Z, roll, pitch, yaw]
        self.pose_fc1 = nn.Linear(shared_dim, branch_dim)
        self.pose_dropout = nn.Dropout(p=dropout_rate)
        self.pose_fc2 = nn.Linear(branch_dim, 6)
        
        logger.info(f"PoseEstimator initialized with {input_dim}→{shared_dim}→{branch_dim} architecture")
    
    def forward(
        self,
        features: torch.Tensor,
        flow: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through pose estimator.
        
        Args:
            features: Features from Level 0 [B, 64, H, W]
            flow: Optical flow field [B, 2, H, W]
        
        Returns:
            Tuple of (misalignment_probability, pose):
            - misalignment_probability: [B, 1] in range [0, 1]
            - pose: [B, 6] = [X, Y, Z, roll, pitch, yaw]
                   Position in meters, orientation in degrees
        
        Requirements: 10.1-10.6, 12.1-12.6
        
        Example:
            >>> estimator = PoseEstimator()
            >>> features = torch.randn(2, 64, 640, 640)
            >>> flow = torch.randn(2, 2, 640, 640)
            >>> prob, pose = estimator(features, flow)
            >>> prob.shape, pose.shape
            (torch.Size([2, 1]), torch.Size([2, 6]))
            >>> (prob >= 0).all() and (prob <= 1).all()
            True
        """
        # ======================================================================
        # Step 1: Concatenate features and flow
        # ======================================================================
        # Combine features (what the camera sees) with flow (how it moved)
        # Shape: [B, 64, H, W] + [B, 2, H, W] → [B, 66, H, W]
        x = torch.cat([features, flow], dim=1)
        
        # ======================================================================
        # Step 2: Global Average Pooling
        # ======================================================================
        # Collapse spatial dimensions (H, W) by averaging
        # This aggregates information from entire image into single feature vector
        # Why? We need a fixed-size representation regardless of input resolution
        # Shape: [B, 66, H, W] → [B, 66]
        x = F.adaptive_avg_pool2d(x, (1, 1))  # Pool to 1×1 spatial size
        x = x.view(x.size(0), -1)  # Flatten: [B, 66, 1, 1] → [B, 66]
        
        # ======================================================================
        # Step 3: Shared Feature Processing
        # ======================================================================
        # Process through shared layers that benefit both tasks
        x = F.relu(self.shared_fc(x))  # 66 → 256 with ReLU
        x = self.shared_dropout(x)  # Apply dropout for regularization
        
        # ======================================================================
        # Step 4: Branch 1 - Misalignment Probability
        # ======================================================================
        # Classify: is the camera misaligned?
        prob = F.relu(self.prob_fc1(x))  # 256 → 128
        prob = self.prob_dropout(prob)
        prob = torch.sigmoid(self.prob_fc2(prob))  # 128 → 1, sigmoid for [0,1]
        # Shape: [B, 1]
        
        # ======================================================================
        # Step 5: Branch 2 - 6-DOF Pose
        # ======================================================================
        # Regress: where is the camera (position + orientation)?
        pose = F.relu(self.pose_fc1(x))  # 256 → 128
        pose = self.pose_dropout(pose)
        pose = self.pose_fc2(pose)  # 128 → 6, no activation (regression)
        # Shape: [B, 6]
        # pose[:, 0:3] = position (X, Y, Z) in meters
        # pose[:, 3:6] = orientation (roll, pitch, yaw) in degrees
        
        return prob, pose
    
    def predict_with_severity(
        self,
        features: torch.Tensor,
        flow: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, list]:
        """
        Forward pass with severity classification.
        
        Args:
            features: Features from Level 0 [B, 64, H, W]
            flow: Optical flow field [B, 2, H, W]
        
        Returns:
            Tuple of (probability, pose, severity_levels):
            - probability: [B, 1] misalignment probability
            - pose: [B, 6] camera pose
            - severity_levels: List of SeverityLevel enums (length B)
        
        Requirements: 11.1, 11.7
        
        Example:
            >>> estimator = PoseEstimator()
            >>> features = torch.randn(2, 64, 640, 640)
            >>> flow = torch.randn(2, 2, 640, 640)
            >>> prob, pose, severities = estimator.predict_with_severity(features, flow)
            >>> len(severities)
            2
            >>> isinstance(severities[0], SeverityLevel)
            True
        """
        # Get predictions
        prob, pose = self.forward(features, flow)
        
        # Classify severity for each sample in batch
        severity_levels = []
        for p in prob:
            severity = classify_severity(p.item())
            severity_levels.append(severity)
        
        return prob, pose, severity_levels


# ==============================================================================
# Task 7.2: Monte Carlo Dropout for Uncertainty Estimation
# ==============================================================================

class PoseEstimatorWithUncertainty(PoseEstimator):
    """
    Pose Estimator with Monte Carlo Dropout for uncertainty quantification.
    
    What is Monte Carlo Dropout?
    - Standard dropout: randomly drops neurons during training
    - MC Dropout: keep dropout active during inference
    - Run forward pass multiple times with different dropout masks
    - Variation in outputs indicates model uncertainty
    
    Why uncertainty matters?
    - Know when the model is confident vs guessing
    - Flag edge cases that need human review
    - Improve system reliability and trust
    
    How it works:
    1. Run forward pass N times (e.g., 10) with dropout enabled
    2. Get N different predictions for same input
    3. Mean = final prediction
    4. Std dev = uncertainty estimate
    5. High std dev = low confidence, flag for review
    
    Computational cost:
    - Standard inference: ~10ms
    - With uncertainty (10 samples): ~100ms
    - Trade-off: accuracy vs speed
    
    Requirements: 13.1-13.6
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with same parameters as base PoseEstimator."""
        super().__init__(*args, **kwargs)
        logger.info("PoseEstimatorWithUncertainty initialized (MC Dropout enabled)")
    
    def forward_with_uncertainty(
        self,
        features: torch.Tensor,
        flow: torch.Tensor,
        num_samples: int = 10,
        confidence_threshold: float = 0.2
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass with uncertainty estimation using Monte Carlo Dropout.
        
        Args:
            features: Features from Level 0 [B, 64, H, W]
            flow: Optical flow field [B, 2, H, W]
            num_samples: Number of MC Dropout samples (default: 10)
            confidence_threshold: Threshold for low-confidence flag (default: 0.2)
        
        Returns:
            Dictionary containing:
            - 'probability_mean': [B, 1] mean misalignment probability
            - 'probability_std': [B, 1] std dev (uncertainty)
            - 'pose_mean': [B, 6] mean pose estimate
            - 'pose_std': [B, 6] std dev per dimension
            - 'low_confidence': [B] boolean flags (True if uncertain)
        
        Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
        
        Example:
            >>> estimator = PoseEstimatorWithUncertainty()
            >>> features = torch.randn(1, 64, 640, 640)
            >>> flow = torch.randn(1, 2, 640, 640)
            >>> results = estimator.forward_with_uncertainty(features, flow)
            >>> results.keys()
            dict_keys(['probability_mean', 'probability_std', 'pose_mean', 
                      'pose_std', 'low_confidence'])
        """
        # ======================================================================
        # Enable dropout for inference (Monte Carlo Dropout)
        # ======================================================================
        # Normally dropout is disabled during eval()
        # For MC Dropout, we keep it active to get stochastic predictions
        self.train()  # Enable dropout
        
        # ======================================================================
        # Run multiple forward passes with different dropout masks
        # ======================================================================
        prob_samples = []
        pose_samples = []
        
        with torch.no_grad():  # No gradients needed for inference
            for _ in range(num_samples):
                prob, pose = self.forward(features, flow)
                prob_samples.append(prob)
                pose_samples.append(pose)
        
        # Stack samples: List of [B, ...] → [num_samples, B, ...]
        prob_samples = torch.stack(prob_samples, dim=0)  # [N, B, 1]
        pose_samples = torch.stack(pose_samples, dim=0)  # [N, B, 6]
        
        # ======================================================================
        # Compute statistics across samples
        # ======================================================================
        # Mean = final prediction
        prob_mean = prob_samples.mean(dim=0)  # [B, 1]
        pose_mean = pose_samples.mean(dim=0)  # [B, 6]
        
        # Standard deviation = uncertainty
        prob_std = prob_samples.std(dim=0)  # [B, 1]
        pose_std = pose_samples.std(dim=0)  # [B, 6]
        
        # ======================================================================
        # Flag low-confidence predictions
        # ======================================================================
        # If std dev > threshold, prediction is uncertain
        low_confidence = (prob_std > confidence_threshold).squeeze()  # [B]
        
        # Return to eval mode
        self.eval()
        
        return {
            'probability_mean': prob_mean,
            'probability_std': prob_std,
            'pose_mean': pose_mean,
            'pose_std': pose_std,
            'low_confidence': low_confidence
        }


# ==============================================================================
# Task 7.3: Severity Classification Helper
# ==============================================================================

def batch_classify_severity(probabilities: torch.Tensor) -> list:
    """
    Classify severity for a batch of probabilities.
    
    Args:
        probabilities: Tensor of shape [B, 1] or [B]
    
    Returns:
        List of SeverityLevel enums (length B)
    
    Requirements: 11.1, 11.7
    
    Example:
        >>> probs = torch.tensor([[0.15], [0.35], [0.65], [0.85], [0.95]])
        >>> severities = batch_classify_severity(probs)
        >>> [s.value for s in severities]
        ['NONE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    """
    if probabilities.dim() == 2:
        probabilities = probabilities.squeeze(1)  # [B, 1] → [B]
    
    severities = []
    for prob in probabilities:
        severity = classify_severity(prob.item())
        severities.append(severity)
    
    return severities


def severity_to_string(severity: SeverityLevel) -> str:
    """Convert SeverityLevel enum to string."""
    return severity.value


def severity_to_int(severity: SeverityLevel) -> int:
    """
    Convert SeverityLevel to integer code.
    
    Useful for:
    - Logging to databases
    - Numerical analysis
    - Sorting by severity
    """
    severity_map = {
        SeverityLevel.NONE: 0,
        SeverityLevel.LOW: 1,
        SeverityLevel.MEDIUM: 2,
        SeverityLevel.HIGH: 3,
        SeverityLevel.CRITICAL: 4
    }
    return severity_map[severity]
