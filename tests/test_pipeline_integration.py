"""
Tests for Phase 10: Pipeline Integration

Tests the main processing pipeline that integrates all components from Phases 1-9.
"""

import pytest
import numpy as np
from pathlib import Path

from src.pipeline.main_processor import (
    MisalignmentDetectionPipeline,
    PipelineConfig,
    PipelineStatistics
)
from src.acquisition.frame_acquisition import CameraSource
from src.alerting.alert_system import AlertChannel
from src.config.calibration import CalibrationLoader
from src.config.system_config import SystemConfigLoader
from src.models.core import MisalignmentEvent, Severity


class MockAlertChannel(AlertChannel):
    """Mock alert channel for testing"""
    
    def __init__(self, name: str):
        self.name = name
        self.alerts_sent = []
    
    def send_alert(self, event: MisalignmentEvent) -> bool:
        """Record alert"""
        self.alerts_sent.append(event)
        return True


class TestPipelineConfig:
    """Test pipeline configuration"""
    
    def test_valid_config(self):
        """Test creating valid pipeline config"""
        config = PipelineConfig(
            calibration_file="cal.json",
            system_config_file="sys.json",
            max_frames=10,
            target_fps=10.0
        )
        
        assert config.calibration_file == "cal.json"
        assert config.system_config_file == "sys.json"
        assert config.max_frames == 10
        assert config.target_fps == 10.0
    
    def test_invalid_target_fps(self):
        """Test validation of target_fps"""
        with pytest.raises(ValueError, match="target_fps must be positive"):
            PipelineConfig(
                calibration_file="cal.json",
                system_config_file="sys.json",
                target_fps=0.0
            )


class TestPipelineStatistics:
    """Test pipeline statistics"""
    
    def test_initial_statistics(self):
        """Test initial statistics values"""
        stats = PipelineStatistics()
        
        assert stats.frames_processed == 0
        assert stats.events_generated == 0
        assert stats.alerts_sent == 0
        assert stats.total_processing_time == 0.0
        assert stats.average_fps == 0.0
        assert stats.average_frame_time == 0.0
    
    def test_average_fps_calculation(self):
        """Test FPS calculation"""
        stats = PipelineStatistics(
            frames_processed=100,
            total_processing_time=10.0
        )
        
        assert stats.average_fps == 10.0
    
    def test_average_frame_time_calculation(self):
        """Test frame time calculation"""
        stats = PipelineStatistics(
            frames_processed=10,
            total_processing_time=1.0  # 1 second
        )
        
        assert stats.average_frame_time == 100.0  # 100ms per frame


class TestPipelineInitialization:
    """Test pipeline initialization"""
    
    @pytest.fixture
    def setup_files(self, tmp_path):
        """Create calibration and system config files"""
        # Create calibration file
        cal_file = tmp_path / "calibration.json"
        from src.config.calibration import create_mock_calibration
        calibration = create_mock_calibration()
        CalibrationLoader.save_to_file(calibration, str(cal_file))
        
        # Create system config file
        sys_file = tmp_path / "system.json"
        from src.config.system_config import create_default_config
        sys_config = create_default_config()
        SystemConfigLoader.save_to_file(sys_config, str(sys_file))
        
        return cal_file, sys_file
    
    def test_pipeline_init(self):
        """Test pipeline initialization"""
        config = PipelineConfig(
            calibration_file="dummy.json",
            system_config_file="dummy.json",
            max_frames=5
        )
        
        pipeline = MisalignmentDetectionPipeline(config)
        
        assert pipeline.config == config
        assert pipeline.statistics.frames_processed == 0
        assert pipeline.is_initialized is False
        assert pipeline.is_running is False
    
    def test_pipeline_setup(self, setup_files):
        """Test pipeline setup with valid configuration"""
        cal_file, sys_file = setup_files
        
        config = PipelineConfig(
            calibration_file=str(cal_file),
            system_config_file=str(sys_file),
            max_frames=5
        )
        
        pipeline = MisalignmentDetectionPipeline(config)
        
        # Create mock camera sources
        camera_sources = []
        for i in range(4):
            frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) 
                     for _ in range(10)]
            camera_sources.append(CameraSource(
                camera_id=i,
                source=frames,
                resolution=(640, 480),
                fps=30
            ))
        
        alert_channels = [MockAlertChannel("test")]
        
        # Setup should succeed
        pipeline.setup(camera_sources, alert_channels)
        
        assert pipeline.is_initialized is True
        assert pipeline.acquisition is not None
        assert pipeline.feature_extractor is not None
        assert pipeline.flow_analyzer is not None
        assert pipeline.motion_estimator is not None
        assert pipeline.detector is not None
        assert pipeline.alert_system is not None


class TestPipelineExecution:
    """Test pipeline execution"""
    
    @pytest.fixture
    def setup_pipeline(self, tmp_path):
        """Setup a complete pipeline for testing"""
        # Create config files
        cal_file = tmp_path / "calibration.json"
        from src.config.calibration import create_mock_calibration
        calibration = create_mock_calibration()
        CalibrationLoader.save_to_file(calibration, str(cal_file))
        
        sys_file = tmp_path / "system.json"
        from src.config.system_config import create_default_config
        sys_config = create_default_config()
        SystemConfigLoader.save_to_file(sys_config, str(sys_file))
        
        config = PipelineConfig(
            calibration_file=str(cal_file),
            system_config_file=str(sys_file),
            max_frames=5,  # Process 5 frames
            target_fps=100.0  # Fast for testing
        )
        
        pipeline = MisalignmentDetectionPipeline(config)
        
        # Create mock camera sources with enough frames
        camera_sources = []
        for i in range(4):
            frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) 
                     for _ in range(10)]
            camera_sources.append(CameraSource(
                camera_id=i,
                source=frames,
                resolution=(640, 480),
                fps=30
            ))
        
        alert_channels = [MockAlertChannel("test")]
        pipeline.setup(camera_sources, alert_channels)
        
        return pipeline
    
    def test_pipeline_run(self, setup_pipeline):
        """Test running pipeline"""
        pipeline = setup_pipeline
        
        stats = pipeline.run()
        
        assert stats.frames_processed == 5
        assert stats.total_processing_time > 0
        assert stats.average_fps > 0
    
    def test_pipeline_run_without_setup(self, tmp_path):
        """Test error when running without setup"""
        config = PipelineConfig(
            calibration_file="dummy.json",
            system_config_file="dummy.json",
            max_frames=1
        )
        
        pipeline = MisalignmentDetectionPipeline(config)
        
        with pytest.raises(RuntimeError, match="Pipeline not initialized"):
            pipeline.run()
    
    def test_pipeline_stop(self, setup_pipeline):
        """Test stopping pipeline"""
        pipeline = setup_pipeline
        
        pipeline.stop()
        
        assert pipeline.is_running is False
    
    def test_pipeline_shutdown(self, setup_pipeline):
        """Test pipeline shutdown"""
        pipeline = setup_pipeline
        
        pipeline.shutdown()
        
        assert pipeline.is_running is False
    
    def test_get_statistics(self, setup_pipeline):
        """Test getting statistics"""
        pipeline = setup_pipeline
        
        stats = pipeline.get_statistics()
        
        assert isinstance(stats, PipelineStatistics)
        assert stats.frames_processed == 0  # Haven't run yet
    
    def test_reset_statistics(self, setup_pipeline):
        """Test resetting statistics"""
        pipeline = setup_pipeline
        
        # Manually set some stats
        pipeline.statistics.frames_processed = 10
        pipeline.statistics.events_generated = 5
        
        # Reset
        pipeline.reset_statistics()
        
        assert pipeline.statistics.frames_processed == 0
        assert pipeline.statistics.events_generated == 0


class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    def test_complete_pipeline_workflow(self, tmp_path):
        """Test complete pipeline workflow from start to finish"""
        # Create config files
        cal_file = tmp_path / "calibration.json"
        from src.config.calibration import create_mock_calibration
        calibration = create_mock_calibration()
        CalibrationLoader.save_to_file(calibration, str(cal_file))
        
        sys_file = tmp_path / "system.json"
        from src.config.system_config import create_default_config
        sys_config = create_default_config()
        SystemConfigLoader.save_to_file(sys_config, str(sys_file))
        
        # Create pipeline
        config = PipelineConfig(
            calibration_file=str(cal_file),
            system_config_file=str(sys_file),
            max_frames=3,
            target_fps=100.0
        )
        
        pipeline = MisalignmentDetectionPipeline(config)
        
        # Create camera sources
        camera_sources = []
        for i in range(4):
            frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) 
                     for _ in range(10)]
            camera_sources.append(CameraSource(
                camera_id=i,
                source=frames,
                resolution=(640, 480),
                fps=30
            ))
        
        # Create alert channel
        alert_channel = MockAlertChannel("test")
        
        # Setup pipeline
        pipeline.setup(camera_sources, [alert_channel])
        
        # Run pipeline
        stats = pipeline.run()
        
        # Verify execution
        assert stats.frames_processed == 3
        assert stats.total_processing_time > 0
        assert stats.average_fps > 0
        
        # Shutdown
        pipeline.shutdown()
