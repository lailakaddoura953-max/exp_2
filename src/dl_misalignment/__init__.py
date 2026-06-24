"""
Deep Learning Misalignment Detection System

This package implements neural network-based camera misalignment detection 
for multi-camera autonomous vehicle systems. It replaces rule-based computer 
vision approaches with learned models trained on the KITTI dataset.

The system supports two architectures for comparative evaluation:
- Architecture A: CNN Feature Extractor + LiteFlowNet2
- Architecture B: CNN Feature Extractor + SpyNet

Key Features:
- Memory-efficient design for consumer GPUs (4-16GB VRAM)
- Real-time inference (<100ms for 4-camera batches)
- Backward compatibility with rule-based systems
- Hybrid mode combining neural and rule-based approaches
"""

__version__ = "0.1.0"
__author__ = "Camera Misalignment Detection Team"

# Expose main components for convenient imports
# Models will be imported once implemented
# from dl_misalignment.models import (
#     CNNFeatureExtractor,
#     LiteFlowNet2,
#     SpyNet,
#     PoseEstimator,
# )

# Data components
from dl_misalignment.data import (
    KITTIDataset,
    create_dataloaders,
)

# Utility components
from dl_misalignment.utils.config import (
    load_config_from_yaml,
    create_default_config,
)

__all__ = [
    # Data
    "KITTIDataset",
    "create_dataloaders",
    # Config
    "load_config_from_yaml",
    "create_default_config",
    # Models (to be added)
    # "CNNFeatureExtractor",
    # "LiteFlowNet2", 
    # "SpyNet",
    # "PoseEstimator",
]
