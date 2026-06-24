"""
Neural Network Models

This module contains the core neural network architectures:
- CNNFeatureExtractor: Pyramid-based feature extraction from images
- LiteFlowNet2: Memory-efficient optical flow network (Architecture A)
- SpyNet: Lightweight optical flow network (Architecture B) 
- PoseEstimator: 6-DOF camera pose and misalignment detection head
"""

# Implemented models
from .cnn_feature_extractor import CNNFeatureExtractor
from .liteflownet2 import LiteFlowNet2, FeatureWarping, FlowEstimator, FlowRefiner
from .spynet import SpyNet, BasicFlowModule
from .pose_estimator import (
    PoseEstimator,
    PoseEstimatorWithUncertainty,
    SeverityLevel,
    classify_severity,
    batch_classify_severity,
    severity_to_string,
    severity_to_int
)

__all__ = [
    "CNNFeatureExtractor",
    "LiteFlowNet2",
    "FeatureWarping",
    "FlowEstimator",
    "FlowRefiner",
    "SpyNet",
    "BasicFlowModule",
    "PoseEstimator",
    "PoseEstimatorWithUncertainty",
    "SeverityLevel",
    "classify_severity",
    "batch_classify_severity",
    "severity_to_string",
    "severity_to_int",
]
