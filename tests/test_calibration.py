"""
Unit tests for calibration loading and validation

Tests the CalibrationLoader class and validates:
- Loading from JSON/YAML files
- Validation of calibration data completeness
- Error handling for invalid/incomplete data
- Property 7: Camera ID validity
"""

import pytest
import json
import yaml
import numpy as np
from pathlib import Path
import tempfile

from src.config.calibration import CalibrationLoader, create_mock_calibration
from src.models.core import CalibrationData, CameraIntrinsics, CalibrationPose


class TestCalibrationLoader:
    """Test CalibrationLoader class"""
    
    @pytest.fixture
    def valid_calibration_dict(self):
        """Valid calibration data as dictionary"""
        cameras = {}
        for i in range(4):
            cameras[str(i)] = {
                'intrinsics': {
                    'fx': 800.0,
                    'fy': 800.0,
                    'cx': 320.0,
                    'cy': 240.0,
                    'k1': 0.1,
                    'k2': -0.05,
                    'p1': 0.001,
                    'p2': 0.001,
                    'k3': 0.01
                },
                'reference_pose': {
                    'position': [float(i), 0.5, 1.5],
                    'orientation': [1.0, 0.0, 0.0, 0.0]  # Identity quaternion
                }
            }
        
        return {
            'cameras': cameras,
            'vehicle_to_world': np.eye(4).tolist()
        }
    
    def test_load_from_dict_valid(self, valid_calibration_dict):
        """Test loading valid calibration from dictionary"""
        calibration = CalibrationLoader.load_from_dict(valid_calibration_dict)
        
        assert isinstance(calibration, CalibrationData)
        assert len(calibration.intrinsics) == 4
        assert len(calibration.reference_poses) == 4
        
        # Verify all cameras 0-3 are present
        for i in range(4):
            assert i in calibration.intrinsics
            assert i in calibration.reference_poses
    
    def test_load_from_dict_missing_cameras_key(self):
        """Test error when 'cameras' key is missing"""
        data = {'vehicle_to_world': np.eye(4).tolist()}
        
        with pytest.raises(ValueError, match="Missing required key.*cameras"):
            CalibrationLoader.load_from_dict(data)
    
    def test_load_from_dict_missing_vehicle_to_world_key(self):
        """Test error when 'vehicle_to_world' key is missing"""
        data = {'cameras': {}}
        
        with pytest.raises(ValueError, match="Missing required key.*vehicle_to_world"):
            CalibrationLoader.load_from_dict(data)
    
    def test_load_from_dict_incomplete_cameras(self, valid_calibration_dict):
        """Test error when not all 4 cameras are present"""
        # Remove camera 3
        del valid_calibration_dict['cameras']['3']
        
        with pytest.raises(ValueError, match="must include all cameras 0-3"):
            CalibrationLoader.load_from_dict(valid_calibration_dict)
    
    def test_load_from_dict_extra_camera(self, valid_calibration_dict):
        """Test error when extra camera ID is present"""
        valid_calibration_dict['cameras']['4'] = valid_calibration_dict['cameras']['0']
        
        with pytest.raises(ValueError, match="must include all cameras 0-3"):
            CalibrationLoader.load_from_dict(valid_calibration_dict)
    
    def test_load_from_dict_missing_intrinsics(self, valid_calibration_dict):
        """Test error when camera intrinsics are missing"""
        del valid_calibration_dict['cameras']['0']['intrinsics']
        
        with pytest.raises(ValueError, match="Missing intrinsics for camera 0"):
            CalibrationLoader.load_from_dict(valid_calibration_dict)
    
    def test_load_from_dict_missing_reference_pose(self, valid_calibration_dict):
        """Test error when reference pose is missing"""
        del valid_calibration_dict['cameras']['1']['reference_pose']
        
        with pytest.raises(ValueError, match="Missing reference_pose for camera 1"):
            CalibrationLoader.load_from_dict(valid_calibration_dict)
    
    def test_load_from_dict_invalid_intrinsics(self, valid_calibration_dict):
        """Test error when intrinsics are invalid (e.g., negative focal length)"""
        valid_calibration_dict['cameras']['0']['intrinsics']['fx'] = -800.0
        
        with pytest.raises(ValueError):
            CalibrationLoader.load_from_dict(valid_calibration_dict)
    
    def test_load_from_json_file_valid(self, valid_calibration_dict, tmp_path):
        """Test loading valid calibration from JSON file"""
        json_file = tmp_path / "calibration.json"
        with open(json_file, 'w') as f:
            json.dump(valid_calibration_dict, f)
        
        calibration = CalibrationLoader.load_from_file(json_file)
        
        assert isinstance(calibration, CalibrationData)
        assert len(calibration.intrinsics) == 4
    
    def test_load_from_yaml_file_valid(self, valid_calibration_dict, tmp_path):
        """Test loading valid calibration from YAML file"""
        yaml_file = tmp_path / "calibration.yaml"
        with open(yaml_file, 'w') as f:
            yaml.safe_dump(valid_calibration_dict, f)
        
        calibration = CalibrationLoader.load_from_file(yaml_file)
        
        assert isinstance(calibration, CalibrationData)
        assert len(calibration.intrinsics) == 4
    
    def test_load_from_file_not_found(self):
        """Test error when file doesn't exist"""
        with pytest.raises(FileNotFoundError):
            CalibrationLoader.load_from_file("nonexistent.json")
    
    def test_load_from_file_unsupported_format(self, valid_calibration_dict, tmp_path):
        """Test error for unsupported file format"""
        txt_file = tmp_path / "calibration.txt"
        txt_file.write_text("some data")
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            CalibrationLoader.load_from_file(txt_file)
    
    def test_save_to_json_file(self, tmp_path):
        """Test saving calibration to JSON file"""
        calibration = create_mock_calibration()
        json_file = tmp_path / "calibration_output.json"
        
        CalibrationLoader.save_to_file(calibration, json_file)
        
        assert json_file.exists()
        
        # Verify we can load it back
        loaded = CalibrationLoader.load_from_file(json_file)
        assert len(loaded.intrinsics) == 4
        assert len(loaded.reference_poses) == 4
    
    def test_save_to_yaml_file(self, tmp_path):
        """Test saving calibration to YAML file"""
        calibration = create_mock_calibration()
        yaml_file = tmp_path / "calibration_output.yml"
        
        CalibrationLoader.save_to_file(calibration, yaml_file)
        
        assert yaml_file.exists()
        
        # Verify we can load it back
        loaded = CalibrationLoader.load_from_file(yaml_file)
        assert len(loaded.intrinsics) == 4
        assert len(loaded.reference_poses) == 4
    
    def test_save_to_file_unsupported_format(self, tmp_path):
        """Test error when saving to unsupported format"""
        calibration = create_mock_calibration()
        txt_file = tmp_path / "calibration.txt"
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            CalibrationLoader.save_to_file(calibration, txt_file)
    
    def test_round_trip_json(self, tmp_path):
        """Test saving and loading produces equivalent calibration (JSON)"""
        original = create_mock_calibration(resolution=(1920, 1080), focal_length=1200.0)
        json_file = tmp_path / "calibration_roundtrip.json"
        
        CalibrationLoader.save_to_file(original, json_file)
        loaded = CalibrationLoader.load_from_file(json_file)
        
        # Verify all cameras have matching parameters
        for i in range(4):
            # Check intrinsics
            orig_intr = original.intrinsics[i]
            load_intr = loaded.intrinsics[i]
            assert orig_intr.fx == pytest.approx(load_intr.fx)
            assert orig_intr.fy == pytest.approx(load_intr.fy)
            assert orig_intr.cx == pytest.approx(load_intr.cx)
            assert orig_intr.cy == pytest.approx(load_intr.cy)
            
            # Check reference poses
            orig_pose = original.reference_poses[i]
            load_pose = loaded.reference_poses[i]
            np.testing.assert_allclose(orig_pose.position, load_pose.position)
            np.testing.assert_allclose(orig_pose.orientation, load_pose.orientation)
    
    def test_round_trip_yaml(self, tmp_path):
        """Test saving and loading produces equivalent calibration (YAML)"""
        original = create_mock_calibration()
        yaml_file = tmp_path / "calibration_roundtrip.yaml"
        
        CalibrationLoader.save_to_file(original, yaml_file)
        loaded = CalibrationLoader.load_from_file(yaml_file)
        
        # Verify vehicle_to_world matrix matches
        np.testing.assert_allclose(original.vehicle_to_world, loaded.vehicle_to_world)


class TestCreateMockCalibration:
    """Test create_mock_calibration helper function"""
    
    def test_creates_valid_calibration(self):
        """Test that mock calibration is valid"""
        calibration = create_mock_calibration()
        
        assert isinstance(calibration, CalibrationData)
        assert len(calibration.intrinsics) == 4
        assert len(calibration.reference_poses) == 4
    
    def test_custom_resolution(self):
        """Test creating mock calibration with custom resolution"""
        calibration = create_mock_calibration(resolution=(1920, 1080))
        
        # Check that principal point is centered
        for i in range(4):
            intr = calibration.intrinsics[i]
            assert intr.cx == pytest.approx(1920 / 2.0)
            assert intr.cy == pytest.approx(1080 / 2.0)
    
    def test_custom_focal_length(self):
        """Test creating mock calibration with custom focal length"""
        focal_length = 1200.0
        calibration = create_mock_calibration(focal_length=focal_length)
        
        for i in range(4):
            intr = calibration.intrinsics[i]
            assert intr.fx == pytest.approx(focal_length)
            assert intr.fy == pytest.approx(focal_length)
    
    def test_all_cameras_have_unique_positions(self):
        """Test that each camera has a unique reference position"""
        calibration = create_mock_calibration()
        
        positions = [calibration.reference_poses[i].position for i in range(4)]
        
        # Check that positions are unique
        for i in range(4):
            for j in range(i + 1, 4):
                assert not np.allclose(positions[i], positions[j])
    
    def test_property_7_camera_id_validity(self):
        """Test Property 7: All camera IDs are in range [0, 3]"""
        calibration = create_mock_calibration()
        
        # Verify all camera IDs are in valid range
        camera_ids = set(calibration.intrinsics.keys())
        assert camera_ids == {0, 1, 2, 3}
        
        camera_ids_poses = set(calibration.reference_poses.keys())
        assert camera_ids_poses == {0, 1, 2, 3}


class TestCalibrationDataValidation:
    """Test CalibrationData validation through loader"""
    
    def test_validates_on_load(self):
        """Test that validation occurs during loading"""
        # Create invalid data (missing camera)
        data = {
            'cameras': {
                '0': {
                    'intrinsics': {'fx': 800, 'fy': 800, 'cx': 320, 'cy': 240},
                    'reference_pose': {'position': [0, 0, 0], 'orientation': [1, 0, 0, 0]}
                }
            },
            'vehicle_to_world': np.eye(4).tolist()
        }
        
        with pytest.raises(ValueError):
            CalibrationLoader.load_from_dict(data)
    
    def test_validates_camera_id_range(self):
        """Test that camera IDs must be in range [0, 3]"""
        data = {
            'cameras': {
                '-1': {  # Invalid camera ID
                    'intrinsics': {'fx': 800, 'fy': 800, 'cx': 320, 'cy': 240},
                    'reference_pose': {'position': [0, 0, 0], 'orientation': [1, 0, 0, 0]}
                },
                '0': {
                    'intrinsics': {'fx': 800, 'fy': 800, 'cx': 320, 'cy': 240},
                    'reference_pose': {'position': [0, 0, 0], 'orientation': [1, 0, 0, 0]}
                },
                '1': {
                    'intrinsics': {'fx': 800, 'fy': 800, 'cx': 320, 'cy': 240},
                    'reference_pose': {'position': [0, 0, 0], 'orientation': [1, 0, 0, 0]}
                },
                '2': {
                    'intrinsics': {'fx': 800, 'fy': 800, 'cx': 320, 'cy': 240},
                    'reference_pose': {'position': [0, 0, 0], 'orientation': [1, 0, 0, 0]}
                }
            },
            'vehicle_to_world': np.eye(4).tolist()
        }
        
        with pytest.raises(ValueError):
            CalibrationLoader.load_from_dict(data)
