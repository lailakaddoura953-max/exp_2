"""
Data Loading and Preprocessing Module

This module handles all data-related operations:
- KITTI dataset loading
- Data augmentation (synthetic misalignment generation)
- Train/val/test splitting
- Batch preparation

Main components:
- KITTIDataset: PyTorch Dataset for KITTI imagery
- create_dataloaders: Create train/val/test DataLoaders
- AugmentationEngine: Generate synthetic misalignments (implemented separately)
"""

from dl_misalignment.data.kitti_dataset import (
    KITTIDataset,
    create_dataloaders
)
from dl_misalignment.data.augmentation import (
    AugmentationEngine,
    create_augmentation_engine
)

__all__ = [
    'KITTIDataset',
    'create_dataloaders',
    'AugmentationEngine',
    'create_augmentation_engine',
]
