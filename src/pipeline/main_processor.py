"""
Main Processing Pipeline - Phase 10

Integrates all components into a complete misalignment detection system.

This is a simplified pipeline focused on component integration and testing.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import time
import numpy as np
from datetime import datetime

from src.acquisition.frame_acquisition import FrameAcquisitionModule, CameraSource
from src.cv.feature_extractor import FeatureExtractor, FeatureExtractorConfig
from src.cv.flow_analyzer import OpticalFlowAnalyzer, FlowConfig
from src.detection.vehicle_motion import VehicleMotionEstimator
from src.detection.misalignment_detector import MisalignmentDetector
from src.alerting.alert_system import AlertSystem, AlertChannel
from src.config.calibration import CalibrationLoader
from src.config.system_config import SystemConfigLoader
from src.models.core import PoseEstimate


@dataclass
class PipelineConfig:
    """Configuration for the main pipeline"""
    calibration_file: str
    system_config_file: str
    max_frames: Optional[int] = None  # None = run indefinitely
    target_fps: float = 10.0
    
    def __post_init__(self):
        """Validate configuration"""
        if self.target_fps <= 0:
            raise ValueError(f"target_fps must be positive, got {self.target_fps}")


@dataclass
class PipelineStatistics:
    """Pipeline performance statistics"""
    frames_processed: int = 0
    events_generated: int = 0
    alerts_sent: int = 0
    total_processing_time: float = 0.0
    
    @property
    def average_fps(self) -> float:
        """Calculate average FPS"""
        if self.total_processing_time > 0:
            return self.frames_processed / self.total_processing_time
        return 0.0
    
    @property
    def average_frame_time(self) -> float:
        """Calculate average time per frame in ms"""
        if self.frames_processed > 0:
            return (self.total_processing_time / self.frames_processed) * 1000
        return 0.0


class MisalignmentDetectionPipeline:
    """
    Main processing pipeline for camera misalignment detection
    
    Integrates components from Phases 1-9:
    - Frame acquisition and synchronization (Phase 5)
    - Feature extraction (Phase 2)
    - Optical flow analysis (Phase 3)
    - Vehicle motion estimation (Phase 6)
    - Misalignment detection (Phase 7)
    - Alert dispatching (Phase 8)
    """
    
    def __init__(self, config: PipelineConfig):
        """
        Initialize pipeline
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.statistics = PipelineStatistics()
        
        # Component instances (initialized in setup)
        self.acquisition: Optional[FrameAcquisitionModule] = None
        self.feature_extractor: Optional[FeatureExtractor] = None
        self.flow_analyzer: Optional[OpticalFlowAnalyzer] = None
        self.motion_estimator: Optional[VehicleMotionEstimator] = None
        self.detector: Optional[MisalignmentDetector] = None
        self.alert_system: Optional[AlertSystem] = None
        
        # State management
        self.is_initialized = False
        self.is_running = False
        
    def setup(self, camera_sources: List[CameraSource], alert_channels: List[AlertChannel]):
        """
        Initialize all pipeline components
        
        Args:
            camera_sources: List of camera sources for acquisition
            alert_channels: List of alert channels for notifications
        
        Raises:
            RuntimeError: If setup fails
        """
        try:
            # Load calibration
            calibration = CalibrationLoader.load_from_file(self.config.calibration_file)
            
            # Load system configuration
            system_config = SystemConfigLoader.load_from_file(self.config.system_config_file)
            
            # Initialize frame acquisition
            self.acquisition = FrameAcquisitionModule(
                sync_tolerance_ms=system_config.frame_sync_tolerance_ms,
                buffer_size_per_camera=system_config.frame_buffer_size
            )
            self.acquisition.initialize_cameras(camera_sources)
            
            # Initialize feature extractor
            fe_config = FeatureExtractorConfig(n_features=system_config.min_feature_count)
            self.feature_extractor = FeatureExtractor(fe_config)
            
            # Initialize flow analyzer
            self.flow_analyzer = OpticalFlowAnalyzer(FlowConfig())
            
            # Initialize vehicle motion estimator
            self.motion_estimator = VehicleMotionEstimator()
            
            # Initialize misalignment detector (use camera 0's thresholds as default)
            self.detector = MisalignmentDetector(
                calibration=calibration,
                thresholds=system_config.cameras[0].thresholds,
                sustained_detection_frames=system_config.sustained_detection_frames
            )
            
            # Initialize alert system
            self.alert_system = AlertSystem(
                channels=alert_channels,
                rate_limit_seconds=60.0,
                max_history_size=1000
            )
            
            self.is_initialized = True
            
        except Exception as e:
            raise RuntimeError(f"Pipeline setup failed: {e}")
    
    def run(self) -> PipelineStatistics:
        """
        Run main processing loop
        
        Returns:
            Pipeline statistics
        
        Raises:
            RuntimeError: If pipeline not initialized
        """
        if not self.is_initialized:
            raise RuntimeError("Pipeline not initialized. Call setup() first.")
        
        self.is_running = True
        frame_count = 0
        pipeline_start = time.time()
        
        try:
            while self.is_running:
                # Check frame limit
                if self.config.max_frames and frame_count >= self.config.max_frames:
                    break
                
                frame_start = time.time()
                
                # Acquire and buffer frames from all cameras
                self.acquisition.acquire_and_buffer_all()
                
                # Get synchronized batch
                sync_batch = self.acquisition.get_synchronized_frames()
                
                if sync_batch is None:
                    # No synchronized frames available yet, continue
                    time.sleep(0.001)  # Brief sleep to avoid busy-waiting
                    continue
                
                # Extract features from all frames
                features = {}
                for camera_id, frame in sync_batch.frames.items():
                    feat = self.feature_extractor.extract(
                        frame, camera_id=camera_id, timestamp=sync_batch.timestamps[camera_id]
                    )
                    features[camera_id] = feat
                
                # Generate mock poses from calibration (simplified - no SLAM yet)
                current_poses = {}
                for camera_id in features.keys():
                    ref_pose = self.detector.reference_poses[camera_id]
                    current_poses[camera_id] = PoseEstimate(
                        camera_id=camera_id,
                        transformation=np.eye(4),
                        position=ref_pose.position.copy(),
                        orientation=ref_pose.orientation.copy(),
                        confidence=0.9,
                        timestamp=0
                    )
                
                # Detect misalignment
                events = self.detector.detect(
                    current_poses=current_poses,
                    vehicle_motion=None,
                    flow_results=None,
                    timestamp=datetime.now()
                )
                
                self.statistics.events_generated += len(events)
                
                # Process alerts
                for event in events:
                    if self.alert_system.process_event(event):
                        self.statistics.alerts_sent += 1
                
                # Update statistics
                frame_count += 1
                self.statistics.frames_processed += 1
                frame_elapsed = time.time() - frame_start
                self.statistics.total_processing_time += frame_elapsed
                
                # Rate limiting
                target_frame_time = 1.0 / self.config.target_fps
                sleep_time = target_frame_time - frame_elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            pass
        except Exception as e:
            raise RuntimeError(f"Pipeline error: {e}")
        finally:
            self.is_running = False
        
        return self.statistics
    
    def stop(self):
        """Stop the pipeline gracefully"""
        self.is_running = False
    
    def shutdown(self):
        """Shutdown pipeline and release resources"""
        self.is_running = False
        if self.acquisition:
            self.acquisition.shutdown()
    
    def get_statistics(self) -> PipelineStatistics:
        """Get current pipeline statistics"""
        return self.statistics
    
    def reset_statistics(self):
        """Reset statistics counters"""
        self.statistics = PipelineStatistics()
