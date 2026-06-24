"""
Misalignment Detection Core Module

Detects camera misalignment by comparing current poses to reference calibration,
with vehicle motion compensation.

Properties validated:
- Property 5: Event Severity Ordering
- Property 6: Displacement Metric Consistency
- Property 13: Threshold-Based Event Generation
- Property 15: Complete Event Structure
- Property 16: Diagnostic Data Completeness
- Property 18: Reference Pose Updates
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from src.models.core import (
    PoseEstimate,
    DisplacementMetrics,
    MisalignmentEvent,
    Severity,
    CalibrationData,
    FlowResult
)
from src.detection.vehicle_motion import VehicleMotion


@dataclass
class DetectionThresholds:
    """
    Thresholds for misalignment detection
    
    Attributes:
        position_threshold_m: Position displacement threshold in meters
        angle_threshold_deg: Angle displacement threshold in degrees
        flow_inconsistency_threshold: Flow inconsistency threshold [0.0, 1.0]
        confidence_threshold: Minimum confidence for event generation [0.0, 1.0]
    """
    position_threshold_m: float
    angle_threshold_deg: float
    flow_inconsistency_threshold: float = 0.3
    confidence_threshold: float = 0.7
    
    def __post_init__(self):
        """Validate thresholds"""
        if self.position_threshold_m <= 0:
            raise ValueError(f"Position threshold must be positive, got {self.position_threshold_m}")
        
        if self.angle_threshold_deg <= 0 or self.angle_threshold_deg > 180:
            raise ValueError(f"Angle threshold must be in (0, 180], got {self.angle_threshold_deg}")
        
        if not (0.0 <= self.flow_inconsistency_threshold <= 1.0):
            raise ValueError(f"Flow inconsistency threshold must be in [0.0, 1.0], got {self.flow_inconsistency_threshold}")
        
        if not (0.0 <= self.confidence_threshold <= 1.0):
            raise ValueError(f"Confidence threshold must be in [0.0, 1.0], got {self.confidence_threshold}")


class MisalignmentDetector:
    """
    Detects camera misalignment by comparing current poses to reference calibration
    
    Applies vehicle motion compensation and generates events when displacement
    exceeds thresholds.
    """
    
    def __init__(
        self,
        calibration: CalibrationData,
        thresholds: DetectionThresholds,
        sustained_detection_frames: int = 2
    ):
        """
        Initialize misalignment detector
        
        Args:
            calibration: Reference calibration data
            thresholds: Detection thresholds
            sustained_detection_frames: Frames to confirm sustained misalignment
        """
        if sustained_detection_frames < 1:
            raise ValueError(f"sustained_detection_frames must be >= 1, got {sustained_detection_frames}")
        
        self.calibration = calibration
        self.thresholds = thresholds
        self.sustained_detection_frames = sustained_detection_frames
        
        # Reference poses (can be updated - Property 18)
        self.reference_poses = {
            cam_id: calibration.reference_poses[cam_id]
            for cam_id in range(4)
        }
        
        # Detection state for sustained detection
        self.detection_history: Dict[int, List[bool]] = {i: [] for i in range(4)}
        
        # Statistics
        self.detections_processed = 0
        self.events_generated = 0
        self.false_positives_suppressed = 0
    
    def detect(
        self,
        current_poses: Dict[int, PoseEstimate],
        vehicle_motion: Optional[VehicleMotion] = None,
        flow_results: Optional[Dict[int, FlowResult]] = None,
        timestamp: Optional[datetime] = None
    ) -> List[MisalignmentEvent]:
        """
        Detect misalignment for all cameras
        
        Args:
            current_poses: Current pose estimates for cameras
            vehicle_motion: Vehicle motion for compensation (optional)
            flow_results: Optical flow results for confidence (optional)
            timestamp: Event timestamp (defaults to now)
        
        Returns:
            List of misalignment events, sorted by severity (Property 5)
        """
        self.detections_processed += 1
        
        if timestamp is None:
            timestamp = datetime.now()
        
        events = []
        
        for camera_id in range(4):
            if camera_id not in current_poses:
                continue  # Camera not available
            
            # Compute displacement
            displacement = self._compute_displacement(
                camera_id,
                current_poses[camera_id],
                vehicle_motion
            )
            
            # Calculate confidence
            pose_confidence = current_poses[camera_id].confidence
            flow_confidence = self._get_flow_confidence(camera_id, flow_results)
            overall_confidence = self._combine_confidence(pose_confidence, flow_confidence)
            
            # Check if exceeds thresholds (Property 13)
            exceeds_threshold, severity = self._check_thresholds(displacement, overall_confidence)
            
            # Update detection history for sustained detection
            self.detection_history[camera_id].append(exceeds_threshold)
            if len(self.detection_history[camera_id]) > self.sustained_detection_frames:
                self.detection_history[camera_id].pop(0)
            
            # Check sustained detection
            is_sustained = self._is_sustained_detection(camera_id)
            
            if exceeds_threshold and is_sustained and overall_confidence >= self.thresholds.confidence_threshold:
                # Generate event
                event = self._create_event(
                    camera_id,
                    timestamp,
                    severity,
                    displacement,
                    overall_confidence,
                    current_poses[camera_id],
                    vehicle_motion,
                    flow_results
                )
                events.append(event)
                self.events_generated += 1
            elif exceeds_threshold and not is_sustained:
                # Suppress potential false positive
                self.false_positives_suppressed += 1
        
        # Sort by severity (Property 5)
        events.sort(key=lambda e: e.severity.value, reverse=True)
        
        return events
    
    def _compute_displacement(
        self,
        camera_id: int,
        current_pose: PoseEstimate,
        vehicle_motion: Optional[VehicleMotion]
    ) -> DisplacementMetrics:
        """
        Compute displacement from reference pose with vehicle motion compensation
        
        Args:
            camera_id: Camera ID
            current_pose: Current pose estimate
            vehicle_motion: Vehicle motion for compensation
        
        Returns:
            DisplacementMetrics
        """
        reference_pose = self.reference_poses[camera_id]
        
        # Compute position delta
        position_delta = current_pose.position - reference_pose.position
        
        # Apply vehicle motion compensation if available
        if vehicle_motion is not None:
            position_delta = position_delta - vehicle_motion.position_delta
        
        # Compute position magnitude (Property 6)
        position_magnitude = np.linalg.norm(position_delta)
        
        # Compute rotation delta
        angle_delta = self._quaternion_to_euler(
            self._quaternion_difference(reference_pose.orientation, current_pose.orientation)
        )
        
        # Apply vehicle motion compensation for rotation
        if vehicle_motion is not None:
            vehicle_euler = self._quaternion_to_euler(vehicle_motion.rotation_delta)
            angle_delta = angle_delta - vehicle_euler
            
            # Wrap angles to [-180, 180]
            angle_delta = np.array([self._wrap_angle(a) for a in angle_delta])
        
        # Compute angle magnitude
        angle_magnitude = np.linalg.norm(angle_delta)
        
        # Compute flow inconsistency (0.0 if not available)
        flow_inconsistency = 0.0
        
        return DisplacementMetrics(
            position_delta=position_delta,
            position_delta_magnitude=position_magnitude,
            angle_delta=angle_delta,
            angle_delta_magnitude=angle_magnitude,
            flow_inconsistency=flow_inconsistency
        )
    
    def _check_thresholds(
        self,
        displacement: DisplacementMetrics,
        confidence: float
    ) -> Tuple[bool, Severity]:
        """
        Check if displacement exceeds thresholds and classify severity
        
        Property 13: Threshold-Based Event Generation
        
        Args:
            displacement: Displacement metrics
            confidence: Overall confidence
        
        Returns:
            Tuple of (exceeds_threshold, severity)
        """
        pos_exceeds = displacement.position_delta_magnitude > self.thresholds.position_threshold_m
        angle_exceeds = displacement.angle_delta_magnitude > self.thresholds.angle_threshold_deg
        
        if not (pos_exceeds or angle_exceeds):
            return (False, Severity.LOW)
        
        # Classify severity based on how much thresholds are exceeded
        pos_ratio = displacement.position_delta_magnitude / self.thresholds.position_threshold_m
        angle_ratio = displacement.angle_delta_magnitude / self.thresholds.angle_threshold_deg
        max_ratio = max(pos_ratio, angle_ratio)
        
        # Severity classification
        if max_ratio >= 5.0:
            severity = Severity.CRITICAL
        elif max_ratio >= 3.0:
            severity = Severity.HIGH
        elif max_ratio >= 2.0:
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW
        
        return (True, severity)
    
    def _is_sustained_detection(self, camera_id: int) -> bool:
        """
        Check if detection is sustained over multiple frames
        
        Args:
            camera_id: Camera ID
        
        Returns:
            True if sustained detection
        """
        history = self.detection_history[camera_id]
        
        if len(history) < self.sustained_detection_frames:
            return False
        
        # All recent frames must have detection
        return all(history[-self.sustained_detection_frames:])
    
    def _create_event(
        self,
        camera_id: int,
        timestamp: datetime,
        severity: Severity,
        displacement: DisplacementMetrics,
        confidence: float,
        current_pose: PoseEstimate,
        vehicle_motion: Optional[VehicleMotion],
        flow_results: Optional[Dict[int, FlowResult]]
    ) -> MisalignmentEvent:
        """
        Create misalignment event with complete diagnostic data
        
        Property 15: Complete Event Structure
        Property 16: Diagnostic Data Completeness
        
        Args:
            camera_id: Camera ID
            timestamp: Event timestamp
            severity: Event severity
            displacement: Displacement metrics
            confidence: Overall confidence
            current_pose: Current pose estimate
            vehicle_motion: Vehicle motion (for diagnostics)
            flow_results: Flow results (for diagnostics)
        
        Returns:
            MisalignmentEvent
        """
        # Generate event ID
        event_id = MisalignmentEvent.generate_event_id()
        
        # Collect diagnostic data (Property 16)
        diagnostic_data = {
            'current_position': current_pose.position.tolist(),
            'current_orientation': current_pose.orientation.tolist(),
            'reference_position': self.reference_poses[camera_id].position.tolist(),
            'reference_orientation': self.reference_poses[camera_id].orientation.tolist(),
            'pose_confidence': current_pose.confidence,
            'vehicle_motion_applied': vehicle_motion is not None,
            'sustained_frames': len(self.detection_history[camera_id]),
            'detection_timestamp': timestamp.isoformat()
        }
        
        if vehicle_motion is not None:
            diagnostic_data['vehicle_motion'] = {
                'position_delta': vehicle_motion.position_delta.tolist(),
                'rotation_delta': vehicle_motion.rotation_delta.tolist(),
                'confidence': vehicle_motion.confidence,
                'inlier_count': vehicle_motion.inlier_count
            }
        
        if flow_results and camera_id in flow_results:
            flow = flow_results[camera_id]
            diagnostic_data['flow'] = {
                'mean_magnitude': flow.mean_magnitude,
                'mean_direction': flow.mean_direction
            }
        
        return MisalignmentEvent(
            event_id=event_id,
            camera_id=camera_id,
            timestamp=timestamp,
            severity=severity,
            displacement=displacement,
            confidence=confidence,
            diagnostic_data=diagnostic_data
        )
    
    def _get_flow_confidence(
        self,
        camera_id: int,
        flow_results: Optional[Dict[int, FlowResult]]
    ) -> float:
        """Get flow-based confidence if available"""
        if flow_results and camera_id in flow_results:
            # Use mean confidence from flow
            return float(np.mean(flow_results[camera_id].confidence))
        return 1.0  # Default if not available
    
    def _combine_confidence(
        self,
        pose_confidence: float,
        flow_confidence: float
    ) -> float:
        """Combine pose and flow confidence scores"""
        # Weighted average (pose weighted higher)
        return 0.7 * pose_confidence + 0.3 * flow_confidence
    
    def _quaternion_difference(self, q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
        """Compute quaternion difference q_delta = q1^-1 * q2"""
        q1_inv = self._quaternion_conjugate(q1)
        return self._quaternion_multiply(q1_inv, q2)
    
    def _quaternion_conjugate(self, q: np.ndarray) -> np.ndarray:
        """Compute quaternion conjugate"""
        return np.array([q[0], -q[1], -q[2], -q[3]])
    
    def _quaternion_multiply(self, q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
        """Multiply two quaternions"""
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        
        w = w1*w2 - x1*x2 - y1*y2 - z1*z2
        x = w1*x2 + x1*w2 + y1*z2 - z1*y2
        y = w1*y2 - x1*z2 + y1*w2 + z1*x2
        z = w1*z2 + x1*y2 - y1*x2 + z1*w2
        
        return np.array([w, x, y, z])
    
    def _quaternion_to_euler(self, q: np.ndarray) -> np.ndarray:
        """
        Convert quaternion to Euler angles (roll, pitch, yaw) in degrees
        
        Args:
            q: Quaternion [w, x, y, z]
        
        Returns:
            Euler angles [roll, pitch, yaw] in degrees
        """
        w, x, y, z = q
        
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = np.copysign(np.pi / 2, sinp)  # Use 90 degrees if out of range
        else:
            pitch = np.arcsin(sinp)
        
        # Yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)
        
        # Convert to degrees
        return np.degrees(np.array([roll, pitch, yaw]))
    
    def _wrap_angle(self, angle_deg: float) -> float:
        """Wrap angle to [-180, 180] degrees"""
        while angle_deg > 180:
            angle_deg -= 360
        while angle_deg < -180:
            angle_deg += 360
        return angle_deg
    
    def update_reference_pose(self, camera_id: int, new_reference: 'CalibrationPose'):
        """
        Update reference pose for a camera (Property 18)
        
        Args:
            camera_id: Camera ID
            new_reference: New reference pose
        """
        if not (0 <= camera_id <= 3):
            raise ValueError(f"Camera ID must be in range [0, 3], got {camera_id}")
        
        self.reference_poses[camera_id] = new_reference
        
        # Reset detection history for this camera
        self.detection_history[camera_id] = []
    
    def reset_detection_history(self, camera_id: Optional[int] = None):
        """
        Reset detection history
        
        Args:
            camera_id: Camera ID to reset (None = reset all)
        """
        if camera_id is None:
            self.detection_history = {i: [] for i in range(4)}
        else:
            if not (0 <= camera_id <= 3):
                raise ValueError(f"Camera ID must be in range [0, 3], got {camera_id}")
            self.detection_history[camera_id] = []
    
    def get_statistics(self) -> Dict:
        """Get detector statistics"""
        return {
            'detections_processed': self.detections_processed,
            'events_generated': self.events_generated,
            'false_positives_suppressed': self.false_positives_suppressed,
            'event_rate': self.events_generated / max(self.detections_processed, 1)
        }
    
    def reset_statistics(self):
        """Reset statistics counters"""
        self.detections_processed = 0
        self.events_generated = 0
        self.false_positives_suppressed = 0
