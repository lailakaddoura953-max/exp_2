"""
System configuration loading and validation

This module handles loading and validating system configuration parameters
including detection thresholds, alert channels, and processing parameters.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Union, Optional
from dataclasses import dataclass, field


@dataclass
class DetectionThresholds:
    """
    Detection thresholds for misalignment events
    
    Per-camera thresholds allow different sensitivity levels based on
    camera placement and expected stability.
    """
    position_threshold_m: float  # Position displacement threshold in meters
    angle_threshold_deg: float   # Angle displacement threshold in degrees
    flow_inconsistency_threshold: float  # Flow pattern inconsistency [0.0, 1.0]
    confidence_threshold: float  # Minimum confidence for event generation [0.0, 1.0]
    
    def __post_init__(self):
        """Validate threshold values"""
        if self.position_threshold_m <= 0:
            raise ValueError(f"position_threshold_m must be positive, got {self.position_threshold_m}")
        
        if self.angle_threshold_deg <= 0 or self.angle_threshold_deg > 180:
            raise ValueError(f"angle_threshold_deg must be in (0, 180], got {self.angle_threshold_deg}")
        
        if not 0.0 <= self.flow_inconsistency_threshold <= 1.0:
            raise ValueError(
                f"flow_inconsistency_threshold must be in [0.0, 1.0], got {self.flow_inconsistency_threshold}"
            )
        
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be in [0.0, 1.0], got {self.confidence_threshold}"
            )


@dataclass
class CameraSettings:
    """
    Per-camera settings including stream configuration and thresholds
    """
    camera_id: int
    stream_url: str
    resolution: tuple  # (width, height)
    fps: int
    thresholds: DetectionThresholds
    
    def __post_init__(self):
        """Validate camera settings"""
        if not 0 <= self.camera_id <= 3:
            raise ValueError(f"camera_id must be in range [0, 3], got {self.camera_id}")
        
        if not isinstance(self.resolution, (tuple, list)) or len(self.resolution) != 2:
            raise ValueError(f"resolution must be (width, height) tuple, got {self.resolution}")
        
        width, height = self.resolution
        if width <= 0 or height <= 0:
            raise ValueError(f"resolution must have positive dimensions, got {self.resolution}")
        
        if self.fps <= 0 or self.fps > 120:
            raise ValueError(f"fps must be in (0, 120], got {self.fps}")


@dataclass
class AlertChannelConfig:
    """Configuration for an alert channel (email, SMS, dashboard, etc.)"""
    channel_type: str  # "email", "sms", "dashboard", "webhook"
    enabled: bool
    config: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate alert channel configuration"""
        valid_types = {"email", "sms", "dashboard", "webhook"}
        if self.channel_type not in valid_types:
            raise ValueError(
                f"channel_type must be one of {valid_types}, got {self.channel_type}"
            )


@dataclass
class SystemConfig:
    """
    Complete system configuration
    
    Includes all camera settings, detection thresholds, alert channels,
    and processing parameters.
    """
    cameras: Dict[int, CameraSettings]
    alert_channels: List[AlertChannelConfig]
    processing_params: Dict = field(default_factory=dict)
    
    # Processing parameters (with defaults)
    frame_sync_tolerance_ms: float = 50.0
    frame_buffer_size: int = 100
    min_feature_count: int = 100
    target_processing_rate_hz: float = 10.0
    sustained_detection_frames: int = 2
    
    def __post_init__(self):
        """Validate system configuration"""
        # Validate we have all 4 cameras
        camera_ids = set(self.cameras.keys())
        expected_ids = {0, 1, 2, 3}
        if camera_ids != expected_ids:
            raise ValueError(
                f"System must have all 4 cameras configured. Found: {sorted(camera_ids)}"
            )
        
        # Validate processing parameters
        if self.frame_sync_tolerance_ms <= 0:
            raise ValueError(
                f"frame_sync_tolerance_ms must be positive, got {self.frame_sync_tolerance_ms}"
            )
        
        if self.frame_buffer_size <= 0:
            raise ValueError(
                f"frame_buffer_size must be positive, got {self.frame_buffer_size}"
            )
        
        if self.min_feature_count <= 0:
            raise ValueError(
                f"min_feature_count must be positive, got {self.min_feature_count}"
            )
        
        if self.target_processing_rate_hz <= 0 or self.target_processing_rate_hz > 60:
            raise ValueError(
                f"target_processing_rate_hz must be in (0, 60], got {self.target_processing_rate_hz}"
            )
        
        if self.sustained_detection_frames < 1:
            raise ValueError(
                f"sustained_detection_frames must be >= 1, got {self.sustained_detection_frames}"
            )
    
    def get_camera_settings(self, camera_id: int) -> CameraSettings:
        """Get settings for a specific camera"""
        if camera_id not in self.cameras:
            raise ValueError(f"Camera {camera_id} not found in configuration")
        return self.cameras[camera_id]
    
    def get_enabled_alert_channels(self) -> List[AlertChannelConfig]:
        """Get list of enabled alert channels"""
        return [ch for ch in self.alert_channels if ch.enabled]


class SystemConfigLoader:
    """
    Load and validate system configuration from files
    
    Supports YAML and JSON formats with comprehensive validation
    to ensure all required parameters are present and valid.
    """
    
    @staticmethod
    def load_from_file(file_path: Union[str, Path]) -> SystemConfig:
        """
        Load system configuration from YAML or JSON file
        
        Args:
            file_path: Path to configuration file (.yaml or .json)
        
        Returns:
            SystemConfig object with validated configuration
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If configuration is invalid or incomplete
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Load based on file extension
        if file_path.suffix == '.json':
            with open(file_path, 'r') as f:
                data = json.load(f)
        elif file_path.suffix in ['.yaml', '.yml']:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(
                f"Unsupported file format: {file_path.suffix}. Use .json, .yaml, or .yml"
            )
        
        return SystemConfigLoader.load_from_dict(data)
    
    @staticmethod
    def load_from_dict(data: Dict) -> SystemConfig:
        """
        Load system configuration from dictionary
        
        Args:
            data: Dictionary with configuration data
        
        Returns:
            SystemConfig object with validated configuration
        """
        # Validate required top-level keys
        required_keys = ['cameras']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key in configuration: {key}")
        
        # Parse camera settings
        cameras = {}
        cameras_data = data['cameras']
        
        for camera_id_str, camera_data in cameras_data.items():
            camera_id = int(camera_id_str)
            
            # Parse thresholds
            if 'thresholds' not in camera_data:
                raise ValueError(f"Missing thresholds for camera {camera_id}")
            
            thresh_data = camera_data['thresholds']
            thresholds = DetectionThresholds(
                position_threshold_m=float(thresh_data['position_threshold_m']),
                angle_threshold_deg=float(thresh_data['angle_threshold_deg']),
                flow_inconsistency_threshold=float(thresh_data['flow_inconsistency_threshold']),
                confidence_threshold=float(thresh_data['confidence_threshold'])
            )
            
            # Parse camera settings
            cameras[camera_id] = CameraSettings(
                camera_id=camera_id,
                stream_url=camera_data['stream_url'],
                resolution=tuple(camera_data['resolution']),
                fps=int(camera_data['fps']),
                thresholds=thresholds
            )
        
        # Parse alert channels (optional)
        alert_channels = []
        if 'alert_channels' in data:
            for channel_data in data['alert_channels']:
                alert_channels.append(AlertChannelConfig(
                    channel_type=channel_data['type'],
                    enabled=channel_data.get('enabled', True),
                    config=channel_data.get('config', {})
                ))
        
        # Parse processing parameters (optional, use defaults if not specified)
        processing_params = data.get('processing_params', {})
        
        return SystemConfig(
            cameras=cameras,
            alert_channels=alert_channels,
            processing_params=processing_params,
            frame_sync_tolerance_ms=float(processing_params.get(
                'frame_sync_tolerance_ms', 50.0
            )),
            frame_buffer_size=int(processing_params.get('frame_buffer_size', 100)),
            min_feature_count=int(processing_params.get('min_feature_count', 100)),
            target_processing_rate_hz=float(processing_params.get(
                'target_processing_rate_hz', 10.0
            )),
            sustained_detection_frames=int(processing_params.get(
                'sustained_detection_frames', 2
            ))
        )
    
    @staticmethod
    def save_to_file(config: SystemConfig, file_path: Union[str, Path]):
        """
        Save system configuration to YAML or JSON file
        
        Args:
            config: SystemConfig to save
            file_path: Path to output file (.yaml or .json)
        """
        file_path = Path(file_path)
        
        # Convert to dictionary
        data = SystemConfigLoader._config_to_dict(config)
        
        # Save based on file extension
        if file_path.suffix == '.json':
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        elif file_path.suffix in ['.yaml', '.yml']:
            with open(file_path, 'w') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
        else:
            raise ValueError(
                f"Unsupported file format: {file_path.suffix}. Use .json, .yaml, or .yml"
            )
    
    @staticmethod
    def _config_to_dict(config: SystemConfig) -> Dict:
        """Convert SystemConfig object to dictionary for saving"""
        cameras = {}
        for camera_id, camera_settings in config.cameras.items():
            cameras[str(camera_id)] = {
                'stream_url': camera_settings.stream_url,
                'resolution': list(camera_settings.resolution),
                'fps': camera_settings.fps,
                'thresholds': {
                    'position_threshold_m': camera_settings.thresholds.position_threshold_m,
                    'angle_threshold_deg': camera_settings.thresholds.angle_threshold_deg,
                    'flow_inconsistency_threshold': camera_settings.thresholds.flow_inconsistency_threshold,
                    'confidence_threshold': camera_settings.thresholds.confidence_threshold
                }
            }
        
        alert_channels = []
        for channel in config.alert_channels:
            alert_channels.append({
                'type': channel.channel_type,
                'enabled': channel.enabled,
                'config': channel.config
            })
        
        return {
            'cameras': cameras,
            'alert_channels': alert_channels,
            'processing_params': {
                'frame_sync_tolerance_ms': config.frame_sync_tolerance_ms,
                'frame_buffer_size': config.frame_buffer_size,
                'min_feature_count': config.min_feature_count,
                'target_processing_rate_hz': config.target_processing_rate_hz,
                'sustained_detection_frames': config.sustained_detection_frames
            }
        }


def create_default_config() -> SystemConfig:
    """
    Create default system configuration for testing
    
    Returns:
        SystemConfig with default parameters
    """
    # Create default thresholds
    default_thresholds = DetectionThresholds(
        position_threshold_m=0.05,  # 5cm
        angle_threshold_deg=5.0,     # 5 degrees
        flow_inconsistency_threshold=0.3,
        confidence_threshold=0.7
    )
    
    # Create camera settings for all 4 cameras
    cameras = {}
    for camera_id in range(4):
        cameras[camera_id] = CameraSettings(
            camera_id=camera_id,
            stream_url=f"rtsp://camera{camera_id}.local/stream",
            resolution=(640, 480),
            fps=30,
            thresholds=default_thresholds
        )
    
    # Create default alert channels
    alert_channels = [
        AlertChannelConfig(
            channel_type="dashboard",
            enabled=True,
            config={}
        ),
        AlertChannelConfig(
            channel_type="email",
            enabled=False,
            config={"recipients": ["admin@example.com"]}
        )
    ]
    
    return SystemConfig(
        cameras=cameras,
        alert_channels=alert_channels
    )
