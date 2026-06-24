"""
Data loading and processing modules

Provides loaders for:
- KITTI stereo/flow benchmark data
- Real-world autonomous vehicle datasets
- Mock data for testing
"""

from .kitti_loader import (
    KITTIDataLoader,
    KITTISample,
    KITTIConfig
)

__all__ = [
    'KITTIDataLoader',
    'KITTISample',
    'KITTIConfig'
]
