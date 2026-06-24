"""
Vehicle Motion Estimation Module

Estimates vehicle motion using RANSAC consensus from multiple camera pose estimates.

Properties validated:
- Property 9: Vehicle Motion Consensus (>=50% inlier agreement)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.models.core import PoseEstimate


@dataclass
class VehicleMotion:
    """
    Estimated vehicle motion
    
    Attributes:
        position_delta: 3D position change [dx, dy, dz] in meters
        rotation_delta: Rotation change as quaternion [w, x, y, z]
        confidence: Confidence in estimate [0.0, 1.0]
        inlier_count: Number of cameras agreeing with consensus
        total_cameras: Total number of cameras used
        inlier_camera_ids: List of camera IDs that are inliers
    """
    position_delta: np.ndarray  # 3D vector
    rotation_delta: np.ndarray  # Quaternion [w, x, y, z]
    confidence: float  # [0.0, 1.0]
    inlier_count: int
    total_cameras: int
    inlier_camera_ids: List[int]
    
    def __post_init__(self):
        """Validate vehicle motion"""
        self.position_delta = np.asarray(self.position_delta, dtype=np.float64)
        self.rotation_delta = np.asarray(self.rotation_delta, dtype=np.float64)
        
        if self.position_delta.shape != (3,):
            raise ValueError(f"Position delta must be 3D vector, got shape {self.position_delta.shape}")
        
        if self.rotation_delta.shape != (4,):
            raise ValueError(f"Rotation delta must be quaternion [w,x,y,z], got shape {self.rotation_delta.shape}")
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")
        
        if self.inlier_count < 0 or self.inlier_count > self.total_cameras:
            raise ValueError(f"Inlier count ({self.inlier_count}) must be in [0, {self.total_cameras}]")
        
        # Normalize quaternion
        norm = np.linalg.norm(self.rotation_delta)
        if norm > 0:
            self.rotation_delta = self.rotation_delta / norm


class VehicleMotionEstimator:
    """
    Estimates vehicle motion from multiple camera pose estimates using RANSAC
    
    Uses consensus from multiple cameras to robustly estimate vehicle motion,
    rejecting outliers from misaligned or malfunctioning cameras.
    """
    
    def __init__(
        self,
        position_threshold: float = 0.1,  # meters
        rotation_threshold: float = 5.0,  # degrees
        min_inlier_ratio: float = 0.5,  # Property 9: 50% requirement
        max_iterations: int = 100
    ):
        """
        Initialize vehicle motion estimator
        
        Args:
            position_threshold: Max position difference for inlier (meters)
            rotation_threshold: Max rotation difference for inlier (degrees)
            min_inlier_ratio: Minimum ratio of inliers for valid consensus (Property 9)
            max_iterations: Maximum RANSAC iterations
        """
        if position_threshold <= 0:
            raise ValueError(f"position_threshold must be positive, got {position_threshold}")
        
        if rotation_threshold <= 0 or rotation_threshold > 180:
            raise ValueError(f"rotation_threshold must be in (0, 180], got {rotation_threshold}")
        
        if not (0.0 < min_inlier_ratio <= 1.0):
            raise ValueError(f"min_inlier_ratio must be in (0.0, 1.0], got {min_inlier_ratio}")
        
        if max_iterations <= 0:
            raise ValueError(f"max_iterations must be positive, got {max_iterations}")
        
        self.position_threshold = position_threshold
        self.rotation_threshold = rotation_threshold
        self.min_inlier_ratio = min_inlier_ratio
        self.max_iterations = max_iterations
        
        # Statistics
        self.estimates_computed = 0
        self.consensus_failures = 0
    
    def estimate_motion(
        self,
        current_poses: Dict[int, PoseEstimate],
        previous_poses: Dict[int, PoseEstimate]
    ) -> Optional[VehicleMotion]:
        """
        Estimate vehicle motion from camera pose changes
        
        Uses RANSAC to find consensus motion, rejecting outlier cameras.
        
        Args:
            current_poses: Current pose estimates for each camera
            previous_poses: Previous pose estimates for each camera
        
        Returns:
            VehicleMotion if consensus found, None otherwise
        """
        # Find common cameras between current and previous
        common_camera_ids = set(current_poses.keys()) & set(previous_poses.keys())
        
        if len(common_camera_ids) < 1:
            return None  # Need at least one camera
        
        # Compute motion for each camera
        camera_motions = {}
        for camera_id in common_camera_ids:
            curr = current_poses[camera_id]
            prev = previous_poses[camera_id]
            
            # Compute position delta
            pos_delta = curr.position - prev.position
            
            # Compute rotation delta (quaternion difference)
            rot_delta = self._quaternion_difference(prev.orientation, curr.orientation)
            
            camera_motions[camera_id] = (pos_delta, rot_delta)
        
        # Edge case: single camera (no consensus needed)
        if len(camera_motions) == 1:
            camera_id = list(camera_motions.keys())[0]
            pos_delta, rot_delta = camera_motions[camera_id]
            
            self.estimates_computed += 1
            
            return VehicleMotion(
                position_delta=pos_delta,
                rotation_delta=rot_delta,
                confidence=1.0,  # Single camera, assume correct
                inlier_count=1,
                total_cameras=1,
                inlier_camera_ids=[camera_id]
            )
        
        # Multiple cameras: use RANSAC to find consensus
        best_motion = self._ransac_consensus(camera_motions)
        
        self.estimates_computed += 1
        
        if best_motion is None:
            self.consensus_failures += 1
        
        return best_motion
    
    def _ransac_consensus(
        self,
        camera_motions: Dict[int, Tuple[np.ndarray, np.ndarray]]
    ) -> Optional[VehicleMotion]:
        """
        Find consensus motion using RANSAC
        
        Args:
            camera_motions: Dict mapping camera_id to (position_delta, rotation_delta)
        
        Returns:
            VehicleMotion with consensus, or None if no consensus found
        """
        camera_ids = list(camera_motions.keys())
        n_cameras = len(camera_ids)
        
        # Property 9: Need at least 50% inliers
        min_inliers = int(np.ceil(n_cameras * self.min_inlier_ratio))
        
        best_inliers = []
        best_motion = None
        
        # RANSAC iterations
        for _ in range(self.max_iterations):
            # Sample one camera as hypothesis
            sample_id = np.random.choice(camera_ids)
            hypothesis_pos, hypothesis_rot = camera_motions[sample_id]
            
            # Find inliers (cameras agreeing with hypothesis)
            inliers = []
            for cam_id in camera_ids:
                pos_delta, rot_delta = camera_motions[cam_id]
                
                # Check if this camera agrees with hypothesis
                if self._is_motion_similar(
                    hypothesis_pos, hypothesis_rot,
                    pos_delta, rot_delta
                ):
                    inliers.append(cam_id)
            
            # Update best model if this is better
            if len(inliers) > len(best_inliers):
                best_inliers = inliers
                
                # Compute refined motion from all inliers
                inlier_positions = [camera_motions[cam_id][0] for cam_id in inliers]
                inlier_rotations = [camera_motions[cam_id][1] for cam_id in inliers]
                
                # Average position delta
                avg_pos = np.mean(inlier_positions, axis=0)
                
                # Average quaternion (simplified: mean of quaternions)
                avg_rot = self._average_quaternions(inlier_rotations)
                
                best_motion = (avg_pos, avg_rot)
        
        # Check if we have enough inliers (Property 9)
        if len(best_inliers) >= min_inliers:
            avg_pos, avg_rot = best_motion
            
            # Confidence based on inlier ratio
            confidence = len(best_inliers) / n_cameras
            
            return VehicleMotion(
                position_delta=avg_pos,
                rotation_delta=avg_rot,
                confidence=confidence,
                inlier_count=len(best_inliers),
                total_cameras=n_cameras,
                inlier_camera_ids=best_inliers
            )
        else:
            # Not enough inliers for consensus
            return None
    
    def _is_motion_similar(
        self,
        pos1: np.ndarray,
        rot1: np.ndarray,
        pos2: np.ndarray,
        rot2: np.ndarray
    ) -> bool:
        """
        Check if two motions are similar within thresholds
        
        Args:
            pos1, rot1: First motion (position delta, rotation quaternion)
            pos2, rot2: Second motion (position delta, rotation quaternion)
        
        Returns:
            True if motions are similar
        """
        # Check position difference
        pos_diff = np.linalg.norm(pos1 - pos2)
        if pos_diff > self.position_threshold:
            return False
        
        # Check rotation difference
        rot_diff_deg = self._quaternion_angle_difference(rot1, rot2)
        if rot_diff_deg > self.rotation_threshold:
            return False
        
        return True
    
    def _quaternion_difference(
        self,
        q1: np.ndarray,
        q2: np.ndarray
    ) -> np.ndarray:
        """
        Compute quaternion representing rotation from q1 to q2
        
        Args:
            q1: First quaternion [w, x, y, z]
            q2: Second quaternion [w, x, y, z]
        
        Returns:
            Quaternion difference q_delta = q1^-1 * q2
        """
        # Quaternion conjugate (inverse for unit quaternions)
        q1_inv = self._quaternion_conjugate(q1)
        
        # Quaternion multiplication: q_delta = q1_inv * q2
        q_delta = self._quaternion_multiply(q1_inv, q2)
        
        return q_delta
    
    def _quaternion_conjugate(self, q: np.ndarray) -> np.ndarray:
        """
        Compute quaternion conjugate
        
        Args:
            q: Quaternion [w, x, y, z]
        
        Returns:
            Conjugate [w, -x, -y, -z]
        """
        return np.array([q[0], -q[1], -q[2], -q[3]])
    
    def _quaternion_multiply(
        self,
        q1: np.ndarray,
        q2: np.ndarray
    ) -> np.ndarray:
        """
        Multiply two quaternions
        
        Args:
            q1: First quaternion [w, x, y, z]
            q2: Second quaternion [w, x, y, z]
        
        Returns:
            Product quaternion q1 * q2
        """
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        
        w = w1*w2 - x1*x2 - y1*y2 - z1*z2
        x = w1*x2 + x1*w2 + y1*z2 - z1*y2
        y = w1*y2 - x1*z2 + y1*w2 + z1*x2
        z = w1*z2 + x1*y2 - y1*x2 + z1*w2
        
        return np.array([w, x, y, z])
    
    def _quaternion_angle_difference(
        self,
        q1: np.ndarray,
        q2: np.ndarray
    ) -> float:
        """
        Compute angle difference between two quaternions in degrees
        
        Args:
            q1: First quaternion [w, x, y, z]
            q2: Second quaternion [w, x, y, z]
        
        Returns:
            Angle difference in degrees
        """
        # Compute difference quaternion
        q_diff = self._quaternion_difference(q1, q2)
        
        # Extract angle from quaternion: angle = 2 * arccos(w)
        # Clamp to avoid numerical issues
        w = np.clip(q_diff[0], -1.0, 1.0)
        angle_rad = 2.0 * np.arccos(np.abs(w))  # abs for shortest path
        angle_deg = np.degrees(angle_rad)
        
        return angle_deg
    
    def _average_quaternions(self, quaternions: List[np.ndarray]) -> np.ndarray:
        """
        Average multiple quaternions
        
        Uses simple mean and re-normalization (good enough for small differences)
        
        Args:
            quaternions: List of quaternions [w, x, y, z]
        
        Returns:
            Average quaternion
        """
        if len(quaternions) == 0:
            return np.array([1.0, 0.0, 0.0, 0.0])  # Identity
        
        # Simple average (works well when quaternions are close)
        avg = np.mean(quaternions, axis=0)
        
        # Normalize
        norm = np.linalg.norm(avg)
        if norm > 0:
            avg = avg / norm
        else:
            avg = np.array([1.0, 0.0, 0.0, 0.0])  # Identity if degenerate
        
        return avg
    
    def get_statistics(self) -> Dict:
        """
        Get estimator statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            'estimates_computed': self.estimates_computed,
            'consensus_failures': self.consensus_failures,
            'failure_rate': self.consensus_failures / max(self.estimates_computed, 1)
        }
    
    def reset_statistics(self):
        """Reset statistics counters"""
        self.estimates_computed = 0
        self.consensus_failures = 0


def create_identity_motion() -> VehicleMotion:
    """
    Create identity motion (no movement)
    
    Returns:
        VehicleMotion with zero translation and identity rotation
    """
    return VehicleMotion(
        position_delta=np.zeros(3),
        rotation_delta=np.array([1.0, 0.0, 0.0, 0.0]),  # Identity quaternion
        confidence=1.0,
        inlier_count=0,
        total_cameras=0,
        inlier_camera_ids=[]
    )
