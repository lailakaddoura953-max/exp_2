"""
Unit tests for system configuration loading and validation

Tests the SystemConfigLoader class and validates:
- Loading from JSON/YAML files
- Validation of configuration parameters
- Detection threshold validation
- Camera settings validation
- Error handling for invalid/incomplete data
"""

import pytest
import json
import yaml
import numpy as np
from pathlib import Path

from src.config.system_config import (
    SystemConfig,
    SystemConfigLoader,
    CameraSettings,
    DetectionThresholds,
    AlertChannelConfig,
    create_default_config
)


class TestDetectionThresholds:
    """Test DetectionThresholds dataclass"""
    
    def test_valid_thresholds(self):
        """Test creating valid thresholds"""
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=5.0,
            flow_inconsistency_threshold=0.3,
            confidence_threshold=0.7
        )
        
        assert thresholds.position_threshold_m == 0.05
        assert thresholds.angle_threshold_deg == 5.0
        assert thresholds.flow_inconsistency_threshold == 0.3
        assert thresholds.confidence_threshold == 0.7
    
    def test_invalid_position_threshold_negative(self):
        """Test error when position threshold is negative"""
        with pytest.raises(ValueError, match="position_threshold_m must be positive"):
            DetectionThresholds(
                position_threshold_m=-0.05,
                angle_threshold_deg=5.0,
                flow_inconsistency_threshold=0.3,
                confidence_threshold=0.7
            )
    
    def test_invalid_position_threshold_zero(self):
        """Test error when position threshold is zero"""
        with pytest.raises(ValueError, match="position_threshold_m must be positive"):
            DetectionThresholds(
                position_threshold_m=0.0,
                angle_threshold_deg=5.0,
                flow_inconsistency_threshold=0.3,
                confidence_threshold=0.7
            )
    
    def test_invalid_angle_threshold_negative(self):
        """Test error when angle threshold is negative"""
        with pytest.raises(ValueError, match="angle_threshold_deg must be in"):
            DetectionThresholds(
                position_threshold_m=0.05,
                angle_threshold_deg=-5.0,
                flow_inconsistency_threshold=0.3,
                confidence_threshold=0.7
            )
    
    def test_invalid_angle_threshold_too_large(self):
        """Test error when angle threshold > 180"""
        with pytest.raises(ValueError, match="angle_threshold_deg must be in"):
            DetectionThresholds(
                position_threshold_m=0.05,
                angle_threshold_deg=181.0,
                flow_inconsistency_threshold=0.3,
                confidence_threshold=0.7
            )
    
    def test_invalid_flow_threshold_negative(self):
        """Test error when flow threshold is negative"""
        with pytest.raises(ValueError, match="flow_inconsistency_threshold must be in"):
            DetectionThresholds(
                position_threshold_m=0.05,
                angle_threshold_deg=5.0,
                flow_inconsistency_threshold=-0.1,
                confidence_threshold=0.7
            )
    
    def test_invalid_flow_threshold_too_large(self):
        """Test error when flow threshold > 1.0"""
        with pytest.raises(ValueError, match="flow_inconsistency_threshold must be in"):
            DetectionThresholds(
                position_threshold_m=0.05,
                angle_threshold_deg=5.0,
                flow_inconsistency_threshold=1.1,
                confidence_threshold=0.7
            )
    
    def test_invalid_confidence_threshold_negative(self):
        """Test error when confidence threshold is negative"""
        with pytest.raises(ValueError, match="confidence_threshold must be in"):
            DetectionThresholds(
                position_threshold_m=0.05,
                angle_threshold_deg=5.0,
                flow_inconsistency_threshold=0.3,
                confidence_threshold=-0.1
            )
    
    def test_invalid_confidence_threshold_too_large(self):
        """Test error when confidence threshold > 1.0"""
        with pytest.raises(ValueError, match="confidence_threshold must be in"):
            DetectionThresholds(
                position_threshold_m=0.05,
                angle_threshold_deg=5.0,
                flow_inconsistency_threshold=0.3,
                confidence_threshold=1.1
            )


class TestCameraSettings:
    """Test CameraSettings dataclass"""
    
    @pytest.fixture
    def valid_thresholds(self):
        return DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=5.0,
            flow_inconsistency_threshold=0.3,
            confidence_threshold=0.7
        )
    
    def test_valid_camera_settings(self, valid_thresholds):
        """Test creating valid camera settings"""
        settings = CameraSettings(
            camera_id=0,
            stream_url="rtsp://camera0.local/stream",
            resolution=(640, 480),
            fps=30,
            thresholds=valid_thresholds
        )
        
        assert settings.camera_id == 0
        assert settings.stream_url == "rtsp://camera0.local/stream"
        assert settings.resolution == (640, 480)
        assert settings.fps == 30
    
    def test_invalid_camera_id_negative(self, valid_thresholds):
        """Test error when camera ID is negative"""
        with pytest.raises(ValueError, match="camera_id must be in range"):
            CameraSettings(
                camera_id=-1,
                stream_url="rtsp://camera.local/stream",
                resolution=(640, 480),
                fps=30,
                thresholds=valid_thresholds
            )
    
    def test_invalid_camera_id_too_large(self, valid_thresholds):
        """Test error when camera ID > 3"""
        with pytest.raises(ValueError, match="camera_id must be in range"):
            CameraSettings(
                camera_id=4,
                stream_url="rtsp://camera.local/stream",
                resolution=(640, 480),
                fps=30,
                thresholds=valid_thresholds
            )
    
    def test_invalid_resolution_not_tuple(self, valid_thresholds):
        """Test error when resolution is not a tuple"""
        with pytest.raises(ValueError, match="resolution must be.*tuple"):
            CameraSettings(
                camera_id=0,
                stream_url="rtsp://camera.local/stream",
                resolution=640,
                fps=30,
                thresholds=valid_thresholds
            )
    
    def test_invalid_resolution_wrong_length(self, valid_thresholds):
        """Test error when resolution tuple has wrong length"""
        with pytest.raises(ValueError, match="resolution must be.*tuple"):
            CameraSettings(
                camera_id=0,
                stream_url="rtsp://camera.local/stream",
                resolution=(640, 480, 3),
                fps=30,
                thresholds=valid_thresholds
            )
    
    def test_invalid_resolution_negative_width(self, valid_thresholds):
        """Test error when resolution has negative dimensions"""
        with pytest.raises(ValueError, match="resolution must have positive dimensions"):
            CameraSettings(
                camera_id=0,
                stream_url="rtsp://camera.local/stream",
                resolution=(-640, 480),
                fps=30,
                thresholds=valid_thresholds
            )
    
    def test_invalid_fps_zero(self, valid_thresholds):
        """Test error when fps is zero"""
        with pytest.raises(ValueError, match="fps must be in"):
            CameraSettings(
                camera_id=0,
                stream_url="rtsp://camera.local/stream",
                resolution=(640, 480),
                fps=0,
                thresholds=valid_thresholds
            )
    
    def test_invalid_fps_too_high(self, valid_thresholds):
        """Test error when fps > 120"""
        with pytest.raises(ValueError, match="fps must be in"):
            CameraSettings(
                camera_id=0,
                stream_url="rtsp://camera.local/stream",
                resolution=(640, 480),
                fps=121,
                thresholds=valid_thresholds
            )


class TestAlertChannelConfig:
    """Test AlertChannelConfig dataclass"""
    
    def test_valid_alert_channel(self):
        """Test creating valid alert channel config"""
        channel = AlertChannelConfig(
            channel_type="email",
            enabled=True,
            config={"recipients": ["admin@example.com"]}
        )
        
        assert channel.channel_type == "email"
        assert channel.enabled is True
        assert "recipients" in channel.config
    
    def test_invalid_channel_type(self):
        """Test error when channel type is invalid"""
        with pytest.raises(ValueError, match="channel_type must be one of"):
            AlertChannelConfig(
                channel_type="invalid_type",
                enabled=True
            )
    
    def test_valid_channel_types(self):
        """Test all valid channel types"""
        valid_types = ["email", "sms", "dashboard", "webhook"]
        
        for channel_type in valid_types:
            channel = AlertChannelConfig(
                channel_type=channel_type,
                enabled=True
            )
            assert channel.channel_type == channel_type


class TestSystemConfig:
    """Test SystemConfig dataclass"""
    
    @pytest.fixture
    def valid_cameras(self):
        """Create valid camera settings for all 4 cameras"""
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=5.0,
            flow_inconsistency_threshold=0.3,
            confidence_threshold=0.7
        )
        
        cameras = {}
        for i in range(4):
            cameras[i] = CameraSettings(
                camera_id=i,
                stream_url=f"rtsp://camera{i}.local/stream",
                resolution=(640, 480),
                fps=30,
                thresholds=thresholds
            )
        return cameras
    
    def test_valid_system_config(self, valid_cameras):
        """Test creating valid system configuration"""
        alert_channels = [
            AlertChannelConfig(channel_type="dashboard", enabled=True)
        ]
        
        config = SystemConfig(
            cameras=valid_cameras,
            alert_channels=alert_channels
        )
        
        assert len(config.cameras) == 4
        assert len(config.alert_channels) == 1
        assert config.frame_sync_tolerance_ms == 50.0  # Default value
    
    def test_invalid_missing_camera(self, valid_cameras):
        """Test error when not all 4 cameras are present"""
        del valid_cameras[3]
        
        with pytest.raises(ValueError, match="must have all 4 cameras"):
            SystemConfig(
                cameras=valid_cameras,
                alert_channels=[]
            )
    
    def test_invalid_extra_camera(self, valid_cameras):
        """Test error when extra camera is present"""
        # Add a 5th camera with a duplicate ID (camera 1)
        # This tests that we detect when camera_ids != {0,1,2,3}
        thresholds = DetectionThresholds(
            position_threshold_m=0.05,
            angle_threshold_deg=5.0,
            flow_inconsistency_threshold=0.3,
            confidence_threshold=0.7
        )
        
        # Add camera with key 4 but camera_id=1 (duplicate)
        # We can't create CameraSettings with camera_id=4 because it validates
        valid_cameras[4] = valid_cameras[1]  # Duplicate camera 1 with key 4
        
        with pytest.raises(ValueError, match="must have all 4 cameras"):
            SystemConfig(
                cameras=valid_cameras,
                alert_channels=[]
            )
    
    def test_get_camera_settings(self, valid_cameras):
        """Test getting camera settings by ID"""
        config = SystemConfig(cameras=valid_cameras, alert_channels=[])
        
        settings = config.get_camera_settings(0)
        assert settings.camera_id == 0
        
        settings = config.get_camera_settings(3)
        assert settings.camera_id == 3
    
    def test_get_camera_settings_invalid_id(self, valid_cameras):
        """Test error when getting settings for invalid camera ID"""
        config = SystemConfig(cameras=valid_cameras, alert_channels=[])
        
        with pytest.raises(ValueError, match="Camera.*not found"):
            config.get_camera_settings(4)
    
    def test_get_enabled_alert_channels(self, valid_cameras):
        """Test getting only enabled alert channels"""
        alert_channels = [
            AlertChannelConfig(channel_type="dashboard", enabled=True),
            AlertChannelConfig(channel_type="email", enabled=False),
            AlertChannelConfig(channel_type="sms", enabled=True)
        ]
        
        config = SystemConfig(cameras=valid_cameras, alert_channels=alert_channels)
        
        enabled = config.get_enabled_alert_channels()
        assert len(enabled) == 2
        assert all(ch.enabled for ch in enabled)
    
    def test_custom_processing_params(self, valid_cameras):
        """Test custom processing parameters"""
        config = SystemConfig(
            cameras=valid_cameras,
            alert_channels=[],
            frame_sync_tolerance_ms=100.0,
            frame_buffer_size=200,
            min_feature_count=150,
            target_processing_rate_hz=15.0,
            sustained_detection_frames=3
        )
        
        assert config.frame_sync_tolerance_ms == 100.0
        assert config.frame_buffer_size == 200
        assert config.min_feature_count == 150
        assert config.target_processing_rate_hz == 15.0
        assert config.sustained_detection_frames == 3
    
    def test_invalid_frame_sync_tolerance(self, valid_cameras):
        """Test error when frame sync tolerance is non-positive"""
        with pytest.raises(ValueError, match="frame_sync_tolerance_ms must be positive"):
            SystemConfig(
                cameras=valid_cameras,
                alert_channels=[],
                frame_sync_tolerance_ms=0.0
            )
    
    def test_invalid_frame_buffer_size(self, valid_cameras):
        """Test error when frame buffer size is non-positive"""
        with pytest.raises(ValueError, match="frame_buffer_size must be positive"):
            SystemConfig(
                cameras=valid_cameras,
                alert_channels=[],
                frame_buffer_size=0
            )
    
    def test_invalid_min_feature_count(self, valid_cameras):
        """Test error when min feature count is non-positive"""
        with pytest.raises(ValueError, match="min_feature_count must be positive"):
            SystemConfig(
                cameras=valid_cameras,
                alert_channels=[],
                min_feature_count=0
            )
    
    def test_invalid_target_processing_rate(self, valid_cameras):
        """Test error when target processing rate is out of range"""
        with pytest.raises(ValueError, match="target_processing_rate_hz must be in"):
            SystemConfig(
                cameras=valid_cameras,
                alert_channels=[],
                target_processing_rate_hz=0.0
            )
        
        with pytest.raises(ValueError, match="target_processing_rate_hz must be in"):
            SystemConfig(
                cameras=valid_cameras,
                alert_channels=[],
                target_processing_rate_hz=61.0
            )
    
    def test_invalid_sustained_detection_frames(self, valid_cameras):
        """Test error when sustained detection frames < 1"""
        with pytest.raises(ValueError, match="sustained_detection_frames must be >= 1"):
            SystemConfig(
                cameras=valid_cameras,
                alert_channels=[],
                sustained_detection_frames=0
            )


class TestSystemConfigLoader:
    """Test SystemConfigLoader class"""
    
    @pytest.fixture
    def valid_config_dict(self):
        """Valid system configuration as dictionary"""
        cameras = {}
        for i in range(4):
            cameras[str(i)] = {
                'stream_url': f"rtsp://camera{i}.local/stream",
                'resolution': [640, 480],
                'fps': 30,
                'thresholds': {
                    'position_threshold_m': 0.05,
                    'angle_threshold_deg': 5.0,
                    'flow_inconsistency_threshold': 0.3,
                    'confidence_threshold': 0.7
                }
            }
        
        return {
            'cameras': cameras,
            'alert_channels': [
                {'type': 'dashboard', 'enabled': True}
            ],
            'processing_params': {
                'frame_sync_tolerance_ms': 50.0,
                'frame_buffer_size': 100
            }
        }
    
    def test_load_from_dict_valid(self, valid_config_dict):
        """Test loading valid configuration from dictionary"""
        config = SystemConfigLoader.load_from_dict(valid_config_dict)
        
        assert isinstance(config, SystemConfig)
        assert len(config.cameras) == 4
        assert config.frame_sync_tolerance_ms == 50.0
    
    def test_load_from_dict_missing_cameras(self):
        """Test error when 'cameras' key is missing"""
        data = {'alert_channels': []}
        
        with pytest.raises(ValueError, match="Missing required key.*cameras"):
            SystemConfigLoader.load_from_dict(data)
    
    def test_load_from_json_file(self, valid_config_dict, tmp_path):
        """Test loading configuration from JSON file"""
        json_file = tmp_path / "config.json"
        with open(json_file, 'w') as f:
            json.dump(valid_config_dict, f)
        
        config = SystemConfigLoader.load_from_file(json_file)
        
        assert isinstance(config, SystemConfig)
        assert len(config.cameras) == 4
    
    def test_load_from_yaml_file(self, valid_config_dict, tmp_path):
        """Test loading configuration from YAML file"""
        yaml_file = tmp_path / "config.yaml"
        with open(yaml_file, 'w') as f:
            yaml.safe_dump(valid_config_dict, f)
        
        config = SystemConfigLoader.load_from_file(yaml_file)
        
        assert isinstance(config, SystemConfig)
        assert len(config.cameras) == 4
    
    def test_load_from_file_not_found(self):
        """Test error when file doesn't exist"""
        with pytest.raises(FileNotFoundError):
            SystemConfigLoader.load_from_file("nonexistent.json")
    
    def test_load_from_file_unsupported_format(self, tmp_path):
        """Test error for unsupported file format"""
        txt_file = tmp_path / "config.txt"
        txt_file.write_text("some data")
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            SystemConfigLoader.load_from_file(txt_file)
    
    def test_save_to_json_file(self, tmp_path):
        """Test saving configuration to JSON file"""
        config = create_default_config()
        json_file = tmp_path / "config_output.json"
        
        SystemConfigLoader.save_to_file(config, json_file)
        
        assert json_file.exists()
        
        # Verify we can load it back
        loaded = SystemConfigLoader.load_from_file(json_file)
        assert len(loaded.cameras) == 4
    
    def test_save_to_yaml_file(self, tmp_path):
        """Test saving configuration to YAML file"""
        config = create_default_config()
        yaml_file = tmp_path / "config_output.yml"
        
        SystemConfigLoader.save_to_file(config, yaml_file)
        
        assert yaml_file.exists()
        
        # Verify we can load it back
        loaded = SystemConfigLoader.load_from_file(yaml_file)
        assert len(loaded.cameras) == 4
    
    def test_round_trip_json(self, tmp_path):
        """Test saving and loading produces equivalent config (JSON)"""
        original = create_default_config()
        json_file = tmp_path / "config_roundtrip.json"
        
        SystemConfigLoader.save_to_file(original, json_file)
        loaded = SystemConfigLoader.load_from_file(json_file)
        
        # Verify cameras match
        for i in range(4):
            orig_cam = original.cameras[i]
            load_cam = loaded.cameras[i]
            assert orig_cam.camera_id == load_cam.camera_id
            assert orig_cam.resolution == load_cam.resolution
            assert orig_cam.fps == load_cam.fps


class TestCreateDefaultConfig:
    """Test create_default_config helper function"""
    
    def test_creates_valid_config(self):
        """Test that default config is valid"""
        config = create_default_config()
        
        assert isinstance(config, SystemConfig)
        assert len(config.cameras) == 4
        assert len(config.alert_channels) > 0
    
    def test_all_cameras_configured(self):
        """Test that all 4 cameras are configured"""
        config = create_default_config()
        
        for i in range(4):
            assert i in config.cameras
            assert config.cameras[i].camera_id == i
    
    def test_has_default_alert_channels(self):
        """Test that default alert channels are present"""
        config = create_default_config()
        
        assert len(config.alert_channels) > 0
        # At least one channel should be enabled
        assert any(ch.enabled for ch in config.alert_channels)
