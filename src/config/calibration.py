"""
Calibration data loading and validation

This module handles loading and validating camera calibration data from
JSON/YAML files, including camera intrinsics and reference poses.

Properties validated:
- Property 7: Camera ID Validity (all camera IDs in range [0, 3])
- Calibration data completeness (all 4 cameras must have data)
"""

import json
import yaml
import numpy as np
from pathlib import Path
from typing import Dict, Union, Optional

from src.models.core import CalibrationData, CameraIntrinsics, CalibrationPose


class CalibrationLoader:
    """
    Load and validate camera calibration data from files
    
    Supports JSON and YAML formats with validation to ensure
    all required calibration parameters are present and valid.
    """
    
    @staticmethod
    def load_from_file(file_path: Union[str, Path]) -> CalibrationData:
        """
        Load calibration data from JSON or YAML file
        
        Args:
            file_path: Path to calibration file (.json or .yaml/.yml)
        
        Returns:
            CalibrationData object with validated calibration
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid or data is incomplete
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Calibration file not found: {file_path}")
        
        # Load based on file extension
        if file_path.suffix == '.json':
            with open(file_path, 'r') as f:
                data = json.load(f)
        elif file_path.suffix in ['.yaml', '.yml']:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}. Use .json, .yaml, or .yml")
        
        return CalibrationLoader._parse_calibration_data(data)
    
    @staticmethod
    def load_from_dict(data: Dict) -> CalibrationData:
        """
        Load calibration data from dictionary
        
        Args:
            data: Dictionary with calibration data
        
        Returns:
            CalibrationData object with validated calibration
        """
        return CalibrationLoader._parse_calibration_data(data)
    
    @staticmethod
    def save_to_file(calibration: CalibrationData, file_path: Union[str, Path]):
        """
        Save calibration data to JSON or YAML file
        
        Args:
            calibration: CalibrationData to save
            file_path: Path to output file (.json or .yaml/.yml)
        """
        file_path = Path(file_path)
        
        # Convert to dictionary
        data = CalibrationLoader._calibration_to_dict(calibration)
        
        # Save based on file extension
        if file_path.suffix == '.json':
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        elif file_path.suffix in ['.yaml', '.yml']:
            with open(file_path, 'w') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}. Use .json, .yaml, or .yml")
    
    @staticmethod
    def _parse_calibration_data(data: Dict) -> CalibrationData:
        """Parse calibration dictionary into CalibrationData object"""
        
        # Validate required top-level keys
        required_keys = ['cameras', 'vehicle_to_world']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key in calibration data: {key}")
        
        cameras_data = data['cameras']
        
        # Validate that we have all 4 cameras
        camera_ids = set(int(k) for k in cameras_data.keys())
        expected_ids = {0, 1, 2, 3}
        if camera_ids != expected_ids:
            raise ValueError(
                f"Calibration must include all cameras 0-3. Found: {sorted(camera_ids)}"
            )
        
        # Parse intrinsics and reference poses for each camera
        intrinsics = {}
        reference_poses = {}
        
        for camera_id_str, camera_data in cameras_data.items():
            camera_id = int(camera_id_str)
            
            # Parse intrinsics
            if 'intrinsics' not in camera_data:
                raise ValueError(f"Missing intrinsics for camera {camera_id}")
            
            intr_data = camera_data['intrinsics']
            intrinsics[camera_id] = CameraIntrinsics(
                fx=float(intr_data['fx']),
                fy=float(intr_data['fy']),
                cx=float(intr_data['cx']),
                cy=float(intr_data['cy']),
                k1=float(intr_data.get('k1', 0.0)),
                k2=float(intr_data.get('k2', 0.0)),
                p1=float(intr_data.get('p1', 0.0)),
                p2=float(intr_data.get('p2', 0.0)),
                k3=float(intr_data.get('k3', 0.0))
            )
            
            # Parse reference pose
            if 'reference_pose' not in camera_data:
                raise ValueError(f"Missing reference_pose for camera {camera_id}")
            
            pose_data = camera_data['reference_pose']
            reference_poses[camera_id] = CalibrationPose(
                position=np.array(pose_data['position'], dtype=np.float64),
                orientation=np.array(pose_data['orientation'], dtype=np.float64)
            )
        
        # Parse vehicle to world transformation
        v2w_data = data['vehicle_to_world']
        if isinstance(v2w_data, list):
            vehicle_to_world = np.array(v2w_data, dtype=np.float64)
        else:
            vehicle_to_world = np.eye(4, dtype=np.float64)
        
        # Create and return CalibrationData (validates everything)
        return CalibrationData(
            intrinsics=intrinsics,
            reference_poses=reference_poses,
            vehicle_to_world=vehicle_to_world
        )
    
    @staticmethod
    def _calibration_to_dict(calibration: CalibrationData) -> Dict:
        """Convert CalibrationData object to dictionary for saving"""
        cameras = {}
        
        for camera_id in range(4):
            intrinsics = calibration.intrinsics[camera_id]
            pose = calibration.reference_poses[camera_id]
            
            cameras[str(camera_id)] = {
                'intrinsics': {
                    'fx': float(intrinsics.fx),
                    'fy': float(intrinsics.fy),
                    'cx': float(intrinsics.cx),
                    'cy': float(intrinsics.cy),
                    'k1': float(intrinsics.k1),
                    'k2': float(intrinsics.k2),
                    'p1': float(intrinsics.p1),
                    'p2': float(intrinsics.p2),
                    'k3': float(intrinsics.k3)
                },
                'reference_pose': {
                    'position': pose.position.tolist(),
                    'orientation': pose.orientation.tolist()
                }
            }
        
        return {
            'cameras': cameras,
            'vehicle_to_world': calibration.vehicle_to_world.tolist()
        }


def create_mock_calibration(
    resolution: tuple = (640, 480),
    focal_length: float = 800.0
) -> CalibrationData:
    """
    Create mock calibration data for testing
    
    Args:
        resolution: Camera resolution (width, height)
        focal_length: Focal length in pixels
    
    Returns:
        CalibrationData with mock but valid calibration
    """
    width, height = resolution
    cx = width / 2.0
    cy = height / 2.0
    
    # Create intrinsics for all 4 cameras
    intrinsics = {}
    for camera_id in range(4):
        intrinsics[camera_id] = CameraIntrinsics(
            fx=focal_length,
            fy=focal_length,
            cx=cx,
            cy=cy,
            k1=0.1,
            k2=-0.05,
            p1=0.001,
            p2=0.001,
            k3=0.01
        )
    
    # Create reference poses for all 4 cameras
    # Place cameras at corners of a square around vehicle
    camera_positions = [
        [1.0, 0.5, 1.5],    # Camera 0: Front-right
        [1.0, -0.5, 1.5],   # Camera 1: Front-left
        [-1.0, 0.5, 1.5],   # Camera 2: Rear-right
        [-1.0, -0.5, 1.5],  # Camera 3: Rear-left
    ]
    
    reference_poses = {}
    for camera_id in range(4):
        reference_poses[camera_id] = CalibrationPose(
            position=np.array(camera_positions[camera_id], dtype=np.float64),
            orientation=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)  # Identity quaternion
        )
    
    return CalibrationData(
        intrinsics=intrinsics,
        reference_poses=reference_poses,
        vehicle_to_world=np.eye(4, dtype=np.float64)
    )
