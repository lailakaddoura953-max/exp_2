"""
Configuration module for camera misalignment detection system

Handles loading and validating calibration data and system configuration.
"""

from src.config.calibration import CalibrationLoader, create_mock_calibration
from src.config.system_config import (
    SystemConfig,
    SystemConfigLoader,
    CameraSettings,
    DetectionThresholds,
    AlertChannelConfig,
    create_default_config
)

__all__ = [
    'CalibrationLoader',
    'create_mock_calibration',
    'SystemConfig',
    'SystemConfigLoader',
    'CameraSettings',
    'DetectionThresholds',
    'AlertChannelConfig',
    'create_default_config'
]
