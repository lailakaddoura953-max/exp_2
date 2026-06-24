"""
Unit tests for Frame Acquisition Module

Tests frame synchronization, buffering, and acquisition with:
- Property 1: Frame Synchronization (50ms tolerance)
- Property 10: Frame Buffer Bounds (max size enforced)
- Property 11: Complete Synchronized Batch (all 4 cameras present)
- Property 17: Buffer FIFO Eviction (oldest frames removed first)
"""

import pytest
import numpy as np
from collections import deque

from src.acquisition.frame_acquisition import (
    FrameAcquisitionModule,
    CameraSource,
    create_mock_frame
)
from src.models.core import SynchronizedFrameBatch


class TestCameraSource:
    """Test CameraSource configuration and validation"""
    
    def test_valid_camera_source_mock(self):
        """Test creating valid mock camera source"""
        mock_frames = [create_mock_frame() for _ in range(5)]
        source = CameraSource(
            camera_id=0,
            source=mock_frames,
            resolution=(640, 480),
            fps=30
        )
        
        assert source.camera_id == 0
        assert source.is_mock is True
        assert len(source.mock_frames) == 5
        assert source.is_connected is True
    
    def test_valid_camera_source_file(self):
        """Test creating camera source from file path"""
        source = CameraSource(
            camera_id=1,
            source="/path/to/video.mp4",
            resolution=(1280, 720),
            fps=30
        )
        
        assert source.camera_id == 1
        assert source.is_mock is False
        assert source.source == "/path/to/video.mp4"
    
    def test_valid_camera_source_device_id(self):
        """Test creating camera source from USB device ID"""
        source = CameraSource(
            camera_id=2,
            source=0,  # Device ID
            resolution=(640, 480),
            fps=30
        )
        
        assert source.camera_id == 2
        assert source.is_mock is False
        assert isinstance(source.source, int)
    
    def test_invalid_camera_id_negative(self):
        """Test error when camera_id is negative"""
        with pytest.raises(ValueError, match="camera_id must be in range"):
            CameraSource(
                camera_id=-1,
                source=[],
                resolution=(640, 480),
                fps=30
            )
    
    def test_invalid_camera_id_too_large(self):
        """Test error when camera_id exceeds 3"""
        with pytest.raises(ValueError, match="camera_id must be in range"):
            CameraSource(
                camera_id=4,
                source=[],
                resolution=(640, 480),
                fps=30
            )


class TestFrameAcquisitionModuleInit:
    """Test FrameAcquisitionModule initialization"""
    
    def test_init_default_params(self):
        """Test initialization with default parameters"""
        module = FrameAcquisitionModule()
        
        assert module.sync_tolerance_ms == 50.0
        assert module.buffer_size_per_camera == 100
        assert module.auto_reconnect is True
        assert len(module.cameras) == 0
        assert len(module.frame_buffers) == 0
        assert module.sequence_number == 0
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        module = FrameAcquisitionModule(
            sync_tolerance_ms=100.0,
            buffer_size_per_camera=50,
            auto_reconnect=False
        )
        
        assert module.sync_tolerance_ms == 100.0
        assert module.buffer_size_per_camera == 50
        assert module.auto_reconnect is False
    
    def test_init_invalid_sync_tolerance(self):
        """Test error when sync_tolerance_ms is non-positive"""
        with pytest.raises(ValueError, match="sync_tolerance_ms must be positive"):
            FrameAcquisitionModule(sync_tolerance_ms=0.0)
        
        with pytest.raises(ValueError, match="sync_tolerance_ms must be positive"):
            FrameAcquisitionModule(sync_tolerance_ms=-10.0)
    
    def test_init_invalid_buffer_size(self):
        """Test error when buffer_size_per_camera is non-positive"""
        with pytest.raises(ValueError, match="buffer_size_per_camera must be positive"):
            FrameAcquisitionModule(buffer_size_per_camera=0)
        
        with pytest.raises(ValueError, match="buffer_size_per_camera must be positive"):
            FrameAcquisitionModule(buffer_size_per_camera=-5)


class TestCameraInitialization:
    """Test camera initialization and connection"""
    
    @pytest.fixture
    def mock_camera_sources(self):
        """Create 4 mock camera sources"""
        sources = []
        for i in range(4):
            mock_frames = [create_mock_frame(text=f"Cam{i}") for _ in range(10)]
            sources.append(CameraSource(
                camera_id=i,
                source=mock_frames,
                resolution=(640, 480),
                fps=30
            ))
        return sources
    
    def test_initialize_cameras_valid(self, mock_camera_sources):
        """Test initializing 4 valid cameras"""
        module = FrameAcquisitionModule()
        module.initialize_cameras(mock_camera_sources)
        
        assert len(module.cameras) == 4
        assert len(module.frame_buffers) == 4
        
        # Verify all camera IDs are present
        for i in range(4):
            assert i in module.cameras
            assert i in module.frame_buffers
    
    def test_initialize_cameras_wrong_count(self):
        """Test error when not exactly 4 cameras provided"""
        module = FrameAcquisitionModule()
        sources = [CameraSource(
            camera_id=0,
            source=[],
            resolution=(640, 480),
            fps=30
        )]
        
        with pytest.raises(ValueError, match="Must provide exactly 4 cameras"):
            module.initialize_cameras(sources)
    
    def test_initialize_cameras_invalid_ids(self, mock_camera_sources):
        """Test error when camera IDs are not [0, 1, 2, 3]"""
        module = FrameAcquisitionModule()
        
        # Change camera ID to duplicate
        mock_camera_sources[3].camera_id = 0
        
        with pytest.raises(ValueError, match="Camera IDs must be"):
            module.initialize_cameras(mock_camera_sources)
    
    def test_buffers_initialized_with_correct_capacity(self, mock_camera_sources):
        """Test that buffers are initialized with correct maxlen"""
        module = FrameAcquisitionModule(buffer_size_per_camera=50)
        module.initialize_cameras(mock_camera_sources)
        
        for i in range(4):
            assert module.frame_buffers[i].maxlen == 50


class TestFrameAcquisition:
    """Test frame acquisition from cameras"""
    
    @pytest.fixture
    def module_with_mock_cameras(self):
        """Module with 4 initialized mock cameras"""
        module = FrameAcquisitionModule()
        sources = []
        for i in range(4):
            mock_frames = [create_mock_frame(color=(i*50, i*50, i*50)) for _ in range(10)]
            sources.append(CameraSource(
                camera_id=i,
                source=mock_frames,
                resolution=(640, 480),
                fps=30
            ))
        module.initialize_cameras(sources)
        return module
    
    def test_acquire_frame_from_mock_camera(self, module_with_mock_cameras):
        """Test acquiring single frame from mock camera"""
        result = module_with_mock_cameras.acquire_frame(0)
        
        assert result is not None
        frame, timestamp = result
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (480, 640, 3)
        assert isinstance(timestamp, int)
        assert timestamp > 0
    
    def test_acquire_frame_increments_mock_index(self, module_with_mock_cameras):
        """Test that acquiring frames increments mock frame index"""
        camera = module_with_mock_cameras.cameras[0]
        assert camera.mock_frame_index == 0
        
        module_with_mock_cameras.acquire_frame(0)
        assert camera.mock_frame_index == 1
        
        module_with_mock_cameras.acquire_frame(0)
        assert camera.mock_frame_index == 2
    
    def test_acquire_frame_from_all_cameras(self, module_with_mock_cameras):
        """Test acquiring frames from all 4 cameras"""
        results = []
        for i in range(4):
            result = module_with_mock_cameras.acquire_frame(i)
            results.append(result)
        
        assert all(r is not None for r in results)
        assert len(results) == 4
    
    def test_acquire_frame_from_invalid_camera(self, module_with_mock_cameras):
        """Test acquiring from non-existent camera returns None"""
        result = module_with_mock_cameras.acquire_frame(99)
        assert result is None
    
    def test_acquire_frame_exhausted_mock_source(self, module_with_mock_cameras):
        """Test acquiring when mock frames are exhausted"""
        # Exhaust all frames (10 available)
        for _ in range(10):
            module_with_mock_cameras.acquire_frame(0)
        
        # Next acquisition should return None
        result = module_with_mock_cameras.acquire_frame(0)
        assert result is None


class TestFrameBuffering:
    """Test frame buffering with bounded FIFO queues"""
    
    @pytest.fixture
    def module(self):
        """Module with initialized cameras"""
        module = FrameAcquisitionModule(buffer_size_per_camera=5)
        sources = []
        for i in range(4):
            mock_frames = [create_mock_frame() for _ in range(20)]
            sources.append(CameraSource(
                camera_id=i,
                source=mock_frames,
                resolution=(640, 480),
                fps=30
            ))
        module.initialize_cameras(sources)
        return module
    
    def test_buffer_frame_adds_to_buffer(self, module):
        """Test that buffer_frame adds frame to buffer"""
        frame = create_mock_frame()
        timestamp = 1000000
        
        module.buffer_frame(0, frame, timestamp)
        
        assert len(module.frame_buffers[0]) == 1
        buffered_frame, buffered_ts = module.frame_buffers[0][0]
        assert np.array_equal(buffered_frame, frame)
        assert buffered_ts == timestamp
    
    def test_buffer_frame_multiple_frames(self, module):
        """Test buffering multiple frames"""
        for i in range(3):
            frame = create_mock_frame(text=f"Frame{i}")
            module.buffer_frame(0, frame, i * 1000)
        
        assert len(module.frame_buffers[0]) == 3
    
    def test_property_10_buffer_bounds_enforcement(self, module):
        """Test Property 10: Buffer size is bounded"""
        # Module has buffer_size_per_camera = 5
        # Add 10 frames
        for i in range(10):
            frame = create_mock_frame()
            module.buffer_frame(0, frame, i * 1000)
        
        # Buffer should only have 5 frames (most recent)
        assert len(module.frame_buffers[0]) == 5
    
    def test_property_17_fifo_eviction(self, module):
        """Test Property 17: Oldest frames are evicted first (FIFO)"""
        # Add frames with identifiable timestamps
        timestamps = [1000, 2000, 3000, 4000, 5000, 6000, 7000]
        for ts in timestamps:
            frame = create_mock_frame()
            module.buffer_frame(0, frame, ts)
        
        # Buffer size is 5, so should have timestamps [3000, 4000, 5000, 6000, 7000]
        buffer = module.frame_buffers[0]
        assert len(buffer) == 5
        
        buffered_timestamps = [ts for _, ts in buffer]
        assert buffered_timestamps == [3000, 4000, 5000, 6000, 7000]
    
    def test_buffer_overflow_counter(self, module):
        """Test that buffer overflows are counted"""
        # Add more frames than buffer size
        for i in range(10):
            frame = create_mock_frame()
            module.buffer_frame(0, frame, i * 1000)
        
        # 5 overflows should have occurred (10 frames - 5 capacity)
        assert module.buffer_overflows[0] == 5
    
    def test_frames_acquired_counter(self, module):
        """Test that frames acquired are counted"""
        for i in range(7):
            frame = create_mock_frame()
            module.buffer_frame(0, frame, i * 1000)
        
        assert module.frames_acquired[0] == 7
    
    def test_acquire_and_buffer_all(self, module):
        """Test acquiring and buffering from all cameras at once"""
        module.acquire_and_buffer_all()
        
        # All 4 cameras should have 1 frame buffered
        for i in range(4):
            assert len(module.frame_buffers[i]) == 1


class TestFrameSynchronization:
    """Test frame synchronization logic"""
    
    @pytest.fixture
    def module(self):
        """Module with empty buffers for manual frame injection"""
        module = FrameAcquisitionModule(sync_tolerance_ms=50.0)
        sources = []
        for i in range(4):
            sources.append(CameraSource(
                camera_id=i,
                source=[],  # Empty mock source
                resolution=(640, 480),
                fps=30
            ))
        module.initialize_cameras(sources)
        return module
    
    def test_property_1_synchronized_frames_within_tolerance(self, module):
        """Test Property 1: Frames within 50ms are synchronized"""
        # Add frames with timestamps within 50ms (50000 microseconds)
        base_ts = 1000000
        timestamps = {
            0: base_ts,
            1: base_ts + 10000,  # +10ms
            2: base_ts + 30000,  # +30ms
            3: base_ts + 45000,  # +45ms (within 50ms tolerance)
        }
        
        for cam_id, ts in timestamps.items():
            frame = create_mock_frame(text=f"Cam{cam_id}")
            module.buffer_frame(cam_id, frame, ts)
        
        batch = module.get_synchronized_frames()
        
        assert batch is not None
        assert isinstance(batch, SynchronizedFrameBatch)
        assert len(batch.frames) == 4
        assert len(batch.timestamps) == 4
    
    def test_property_1_frames_outside_tolerance_not_synchronized(self, module):
        """Test Property 1: Frames outside 50ms are not synchronized"""
        # Add frames with timestamps outside 50ms tolerance
        base_ts = 1000000
        timestamps = {
            0: base_ts,
            1: base_ts + 10000,
            2: base_ts + 30000,
            3: base_ts + 60000,  # +60ms (exceeds 50ms tolerance)
        }
        
        for cam_id, ts in timestamps.items():
            frame = create_mock_frame()
            module.buffer_frame(cam_id, frame, ts)
        
        batch = module.get_synchronized_frames()
        
        # Should not synchronize
        assert batch is None
        
        # Oldest frame should have been removed
        assert module.sync_failures > 0
    
    def test_property_11_complete_batch_all_cameras(self, module):
        """Test Property 11: Synchronized batch has all 4 cameras"""
        base_ts = 1000000
        for i in range(4):
            frame = create_mock_frame()
            module.buffer_frame(i, frame, base_ts + i * 1000)
        
        batch = module.get_synchronized_frames()
        
        assert batch is not None
        assert batch.is_complete is True
        assert len(batch.frames) == 4
        assert set(batch.frames.keys()) == {0, 1, 2, 3}
    
    def test_sync_removes_frames_from_buffers(self, module):
        """Test that synchronized frames are removed from buffers"""
        base_ts = 1000000
        for i in range(4):
            frame = create_mock_frame()
            module.buffer_frame(i, frame, base_ts)
        
        # Verify buffers have frames
        for i in range(4):
            assert len(module.frame_buffers[i]) == 1
        
        batch = module.get_synchronized_frames()
        assert batch is not None
        
        # Buffers should now be empty
        for i in range(4):
            assert len(module.frame_buffers[i]) == 0
    
    def test_sync_increments_sequence_number(self, module):
        """Test that successful sync increments sequence number"""
        assert module.sequence_number == 0
        
        base_ts = 1000000
        for i in range(4):
            module.buffer_frame(i, create_mock_frame(), base_ts)
        
        batch = module.get_synchronized_frames()
        assert batch is not None
        assert batch.sequence_number == 0
        assert module.sequence_number == 1
    
    def test_sync_with_missing_camera_returns_none(self, module):
        """Test that sync fails if any camera missing"""
        base_ts = 1000000
        # Only add frames for 3 cameras
        for i in range(3):
            module.buffer_frame(i, create_mock_frame(), base_ts)
        
        batch = module.get_synchronized_frames()
        assert batch is None
    
    def test_sync_removes_oldest_frame_on_failure(self, module):
        """Test that oldest frame is removed when sync fails"""
        # Camera 0 has oldest timestamp
        module.buffer_frame(0, create_mock_frame(), 1000000)
        module.buffer_frame(1, create_mock_frame(), 1100000)
        module.buffer_frame(2, create_mock_frame(), 1100000)
        module.buffer_frame(3, create_mock_frame(), 1100000)
        
        batch = module.get_synchronized_frames()
        assert batch is None
        
        # Camera 0's buffer should be empty (oldest frame removed)
        assert len(module.frame_buffers[0]) == 0
    
    def test_multiple_sync_attempts(self, module):
        """Test multiple synchronization attempts"""
        # Add multiple frames to each camera
        base_ts = 1000000
        for frame_num in range(3):
            for cam_id in range(4):
                ts = base_ts + frame_num * 20000  # 20ms apart
                module.buffer_frame(cam_id, create_mock_frame(), ts)
        
        # Should be able to get 3 synchronized batches
        batches = []
        for _ in range(3):
            batch = module.get_synchronized_frames()
            if batch:
                batches.append(batch)
        
        assert len(batches) == 3
        assert batches[0].sequence_number == 0
        assert batches[1].sequence_number == 1
        assert batches[2].sequence_number == 2


class TestCameraStatus:
    """Test camera and system status reporting"""
    
    @pytest.fixture
    def module(self):
        """Module with mock cameras"""
        module = FrameAcquisitionModule()
        sources = []
        for i in range(4):
            mock_frames = [create_mock_frame() for _ in range(10)]
            sources.append(CameraSource(
                camera_id=i,
                source=mock_frames,
                resolution=(640, 480),
                fps=30
            ))
        module.initialize_cameras(sources)
        return module
    
    def test_get_camera_status(self, module):
        """Test getting status for single camera"""
        status = module.get_camera_status(0)
        
        assert status['camera_id'] == 0
        assert status['connected'] is True
        assert status['buffer_size'] == 0
        assert status['buffer_capacity'] == 100
        assert status['frames_acquired'] == 0
        assert status['buffer_overflows'] == 0
    
    def test_get_camera_status_after_acquisition(self, module):
        """Test camera status after acquiring frames"""
        # Acquire some frames
        for _ in range(5):
            result = module.acquire_frame(0)
            if result:
                frame, ts = result
                module.buffer_frame(0, frame, ts)
        
        status = module.get_camera_status(0)
        assert status['buffer_size'] == 5
        assert status['frames_acquired'] == 5
    
    def test_get_camera_status_invalid_camera(self, module):
        """Test getting status for non-existent camera"""
        status = module.get_camera_status(99)
        assert status['connected'] is False
        assert status['buffer_size'] == 0
    
    def test_get_system_status(self, module):
        """Test getting system-wide status"""
        status = module.get_system_status()
        
        assert status['cameras_connected'] == 4
        assert status['total_cameras'] == 4
        assert status['sync_failures'] == 0
        assert status['sequence_number'] == 0
        assert 'camera_statuses' in status
        assert len(status['camera_statuses']) == 4
    
    def test_system_status_after_sync_failures(self, module):
        """Test system status tracks sync failures"""
        # Create unsynchronized frames
        module.buffer_frame(0, create_mock_frame(), 1000000)
        module.buffer_frame(1, create_mock_frame(), 2000000)  # Way out of sync
        module.buffer_frame(2, create_mock_frame(), 1000000)
        module.buffer_frame(3, create_mock_frame(), 1000000)
        
        module.get_synchronized_frames()
        
        status = module.get_system_status()
        assert status['sync_failures'] > 0


class TestCameraDisconnection:
    """Test handling of disconnected cameras"""
    
    def test_disconnect_camera(self):
        """Test disconnecting a camera"""
        module = FrameAcquisitionModule()
        sources = []
        for i in range(4):
            sources.append(CameraSource(
                camera_id=i,
                source=[create_mock_frame()],
                resolution=(640, 480),
                fps=30
            ))
        module.initialize_cameras(sources)
        
        # Manually disconnect camera
        module._disconnect_camera(0)
        
        status = module.get_camera_status(0)
        assert status['connected'] is False
    
    def test_acquire_from_disconnected_camera(self):
        """Test acquiring from disconnected camera returns None"""
        module = FrameAcquisitionModule()
        sources = []
        for i in range(4):
            sources.append(CameraSource(
                camera_id=i,
                source=[create_mock_frame()],
                resolution=(640, 480),
                fps=30
            ))
        module.initialize_cameras(sources)
        
        # Disconnect and try to acquire
        module._disconnect_camera(0)
        result = module.acquire_frame(0)
        
        # For mock sources, this should still work, but for real sources it would be None
        # Since we're using mock, it will reconnect automatically
        # Let's test with camera.is_connected = False directly
        module.cameras[0].is_connected = False
        module.cameras[0].is_mock = False  # Pretend it's not mock
        
        result = module.acquire_frame(0)
        assert result is None


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_buffers_no_sync(self):
        """Test that empty buffers return None for sync"""
        module = FrameAcquisitionModule()
        sources = []
        for i in range(4):
            sources.append(CameraSource(
                camera_id=i,
                source=[],
                resolution=(640, 480),
                fps=30
            ))
        module.initialize_cameras(sources)
        
        batch = module.get_synchronized_frames()
        assert batch is None
    
    def test_single_camera_with_frames(self):
        """Test sync fails with only one camera having frames"""
        module = FrameAcquisitionModule()
        sources = []
        for i in range(4):
            sources.append(CameraSource(
                camera_id=i,
                source=[],
                resolution=(640, 480),
                fps=30
            ))
        module.initialize_cameras(sources)
        
        # Only camera 0 has frames
        module.buffer_frame(0, create_mock_frame(), 1000000)
        
        batch = module.get_synchronized_frames()
        assert batch is None
    
    def test_sync_with_identical_timestamps(self):
        """Test synchronization with identical timestamps"""
        module = FrameAcquisitionModule()
        sources = []
        for i in range(4):
            sources.append(CameraSource(
                camera_id=i,
                source=[],
                resolution=(640, 480),
                fps=30
            ))
        module.initialize_cameras(sources)
        
        # All cameras have same timestamp
        ts = 1000000
        for i in range(4):
            module.buffer_frame(i, create_mock_frame(), ts)
        
        batch = module.get_synchronized_frames()
        assert batch is not None
        assert batch.is_complete is True
    
    def test_shutdown_releases_resources(self):
        """Test that shutdown properly releases resources"""
        module = FrameAcquisitionModule()
        sources = []
        for i in range(4):
            mock_frames = [create_mock_frame() for _ in range(5)]
            sources.append(CameraSource(
                camera_id=i,
                source=mock_frames,
                resolution=(640, 480),
                fps=30
            ))
        module.initialize_cameras(sources)
        
        # Add some frames
        module.acquire_and_buffer_all()
        
        # Shutdown
        module.shutdown()
        
        # Verify buffers are cleared
        for i in range(4):
            assert len(module.frame_buffers[i]) == 0
        
        # Verify cameras are disconnected
        for i in range(4):
            assert module.cameras[i].is_connected is False


class TestCreateMockFrame:
    """Test create_mock_frame helper function"""
    
    def test_creates_valid_frame_default(self):
        """Test creating frame with default parameters"""
        frame = create_mock_frame()
        
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (480, 640, 3)
        assert frame.dtype == np.uint8
    
    def test_creates_frame_custom_size(self):
        """Test creating frame with custom size"""
        frame = create_mock_frame(width=1280, height=720)
        
        assert frame.shape == (720, 1280, 3)
    
    def test_creates_frame_custom_color(self):
        """Test creating frame with custom color"""
        color = (50, 100, 150)
        frame = create_mock_frame(color=color)
        
        # Check that all pixels have the specified color
        assert np.all(frame[0, 0] == color)
    
    def test_creates_frame_with_text(self):
        """Test creating frame with text overlay"""
        frame = create_mock_frame(text="Test")
        
        # Just verify it doesn't crash and returns valid frame
        assert frame.shape == (480, 640, 3)
