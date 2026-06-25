"""
Unit tests for VLC Capture component

Tests the VLCCapture class functionality including initialization,
snapshot validation, and error handling.
"""

import unittest
from unittest.mock import MagicMock, patch, call, Mock
import numpy as np
import pytest
import sys

# Create mock win32gui and win32con modules before importing VLCCapture
mock_win32gui = MagicMock()
mock_win32con = MagicMock()
mock_win32con.SW_RESTORE = 9
mock_pyautogui = MagicMock()

sys.modules['win32gui'] = mock_win32gui
sys.modules['win32con'] = mock_win32con
sys.modules['pyautogui'] = mock_pyautogui

from src.strad_monitoring.vlc_capture import VLCCapture, CaptureError


class TestVLCCaptureInitialization(unittest.TestCase):
    """Test VLCCapture initialization and parameter validation."""
    
    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        capture = VLCCapture()
        
        assert capture.stabilization_delay == 5.0
        assert capture.min_width == 640
        assert capture.min_height == 480
    
    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        capture = VLCCapture(
            stabilization_delay=3.0,
            min_width=800,
            min_height=600
        )
        
        assert capture.stabilization_delay == 3.0
        assert capture.min_width == 800
        assert capture.min_height == 600
    
    def test_init_negative_stabilization_delay_raises_error(self):
        """Test that negative stabilization delay raises ValueError."""
        with pytest.raises(ValueError, match="stabilization_delay must be positive"):
            VLCCapture(stabilization_delay=-1.0)
    
    def test_init_zero_stabilization_delay_raises_error(self):
        """Test that zero stabilization delay raises ValueError."""
        with pytest.raises(ValueError, match="stabilization_delay must be positive"):
            VLCCapture(stabilization_delay=0.0)
    
    def test_init_negative_min_width_raises_error(self):
        """Test that negative min_width raises ValueError."""
        with pytest.raises(ValueError, match="min_width must be positive"):
            VLCCapture(min_width=-100)
    
    def test_init_negative_min_height_raises_error(self):
        """Test that negative min_height raises ValueError."""
        with pytest.raises(ValueError, match="min_height must be positive"):
            VLCCapture(min_height=-100)


class TestSnapshotValidation(unittest.TestCase):
    """Test snapshot validation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.capture = VLCCapture(min_width=640, min_height=480)
    
    def test_validate_snapshot_valid_dimensions(self):
        """Test validation passes for snapshot meeting minimum dimensions."""
        # Create snapshot with valid dimensions (800x600, RGB)
        snapshot = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
        
        assert self.capture.validate_snapshot(snapshot) is True
    
    def test_validate_snapshot_exact_minimum_dimensions(self):
        """Test validation passes for snapshot with exact minimum dimensions."""
        # Create snapshot with exact minimum dimensions (640x480, RGB)
        snapshot = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        assert self.capture.validate_snapshot(snapshot) is True
    
    def test_validate_snapshot_width_too_small(self):
        """Test validation fails when width is below minimum."""
        # Create snapshot with width below minimum (600x480, RGB)
        snapshot = np.random.randint(0, 255, (480, 600, 3), dtype=np.uint8)
        
        assert self.capture.validate_snapshot(snapshot) is False
    
    def test_validate_snapshot_height_too_small(self):
        """Test validation fails when height is below minimum."""
        # Create snapshot with height below minimum (640x400, RGB)
        snapshot = np.random.randint(0, 255, (400, 640, 3), dtype=np.uint8)
        
        assert self.capture.validate_snapshot(snapshot) is False
    
    def test_validate_snapshot_both_dimensions_too_small(self):
        """Test validation fails when both dimensions are below minimum."""
        # Create snapshot with both dimensions too small (320x240, RGB)
        snapshot = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        
        assert self.capture.validate_snapshot(snapshot) is False
    
    def test_validate_snapshot_none_returns_false(self):
        """Test validation fails for None input."""
        assert self.capture.validate_snapshot(None) is False
    
    def test_validate_snapshot_not_numpy_array_returns_false(self):
        """Test validation fails for non-numpy array input."""
        assert self.capture.validate_snapshot([1, 2, 3]) is False
    
    def test_validate_snapshot_invalid_shape_returns_false(self):
        """Test validation fails for invalid array shape."""
        # 1D array
        invalid_snapshot = np.array([1, 2, 3])
        assert self.capture.validate_snapshot(invalid_snapshot) is False
    
    def test_validate_snapshot_rgba_format(self):
        """Test validation works for RGBA format (4 channels)."""
        # Create snapshot with RGBA format (800x600x4)
        snapshot = np.random.randint(0, 255, (600, 800, 4), dtype=np.uint8)
        
        assert self.capture.validate_snapshot(snapshot) is True


class TestCaptureSnapshot(unittest.TestCase):
    """Test snapshot capture functionality with mocked dependencies."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.capture = VLCCapture(stabilization_delay=0.1, min_width=640, min_height=480)
        # Reset mocks before each test
        mock_win32gui.reset_mock()
        mock_win32con.reset_mock()
        mock_pyautogui.reset_mock()
        # Clear any side effects
        mock_pyautogui.screenshot.side_effect = None
    
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.time.sleep')
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.np.array')
    def test_capture_snapshot_success(self, mock_np_array, mock_sleep):
        """Test successful snapshot capture."""
        # Mock VLC window found
        mock_win32gui.FindWindow.return_value = 12345
        mock_win32gui.IsIconic.return_value = False
        mock_win32gui.GetWindowRect.return_value = (100, 100, 900, 700)  # 800x600 window
        
        # Create mock screenshot
        mock_array = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
        mock_np_array.return_value = mock_array
        
        snapshot = self.capture.capture_snapshot()
        
        # Verify stabilization delay was applied
        assert mock_sleep.call_count >= 1
        
        # Verify VLC window was located
        assert mock_win32gui.FindWindow.called
        
        # Verify window was brought to foreground
        mock_win32gui.SetForegroundWindow.assert_called_with(12345)
        
        # Verify screenshot was captured with correct region
        mock_pyautogui.screenshot.assert_called_once_with(region=(100, 100, 800, 600))
        
        # Verify snapshot has correct shape
        assert snapshot.shape == (600, 800, 3)
    
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.time.sleep')
    def test_capture_snapshot_vlc_not_found_raises_error(self, mock_sleep):
        """Test that CaptureError is raised when VLC window not found."""
        # Mock VLC window not found
        mock_win32gui.FindWindow.return_value = 0
        mock_win32gui.EnumWindows.return_value = None
        
        with pytest.raises(CaptureError, match="VLC media player window not found"):
            self.capture.capture_snapshot()
    
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.time.sleep')
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.np.array')
    def test_capture_snapshot_dimensions_too_small_raises_error(self, mock_np_array, mock_sleep):
        """Test that CaptureError is raised when snapshot dimensions too small."""
        # Mock VLC window found
        mock_win32gui.FindWindow.return_value = 12345
        mock_win32gui.IsIconic.return_value = False
        mock_win32gui.GetWindowRect.return_value = (100, 100, 420, 340)  # 320x240 window (too small)
        
        # Create mock screenshot with small dimensions
        mock_array = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        mock_np_array.return_value = mock_array
        
        with pytest.raises(CaptureError, match="do not meet minimum requirements"):
            self.capture.capture_snapshot()
    
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.time.sleep')
    def test_capture_snapshot_screenshot_failure_raises_error(self, mock_sleep):
        """Test that CaptureError is raised when screenshot capture fails after retries."""
        # Mock VLC window found
        mock_win32gui.FindWindow.return_value = 12345
        mock_win32gui.IsIconic.return_value = False
        mock_win32gui.GetWindowRect.return_value = (100, 100, 900, 700)
        
        # Mock screenshot failure
        mock_pyautogui.screenshot.side_effect = Exception("Screenshot failed")
        
        with pytest.raises(CaptureError, match="Failed to capture snapshot after 3 attempts"):
            self.capture.capture_snapshot()
    
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.time.sleep')
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.np.array')
    def test_capture_snapshot_retry_success_on_second_attempt(self, mock_np_array, mock_sleep):
        """Test retry logic succeeds on second attempt."""
        # Mock VLC window found
        mock_win32gui.FindWindow.return_value = 12345
        mock_win32gui.IsIconic.return_value = False
        mock_win32gui.GetWindowRect.return_value = (100, 100, 900, 700)
        
        # Create mock screenshot
        mock_array = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
        mock_np_array.return_value = mock_array
        
        # First attempt fails, second succeeds
        mock_pyautogui.screenshot.side_effect = [
            Exception("First attempt failed"),
            Mock()  # Second attempt succeeds
        ]
        
        snapshot = self.capture.capture_snapshot()
        
        # Verify we got a valid snapshot
        assert snapshot.shape == (600, 800, 3)
        
        # Verify screenshot was called twice (first failed, second succeeded)
        assert mock_pyautogui.screenshot.call_count == 2
    
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.time.sleep')
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.np.array')
    def test_capture_snapshot_retry_success_on_third_attempt(self, mock_np_array, mock_sleep):
        """Test retry logic succeeds on third (final) attempt."""
        # Mock VLC window found
        mock_win32gui.FindWindow.return_value = 12345
        mock_win32gui.IsIconic.return_value = False
        mock_win32gui.GetWindowRect.return_value = (100, 100, 900, 700)
        
        # Create mock screenshot
        mock_array = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
        mock_np_array.return_value = mock_array
        
        # First two attempts fail, third succeeds
        mock_pyautogui.screenshot.side_effect = [
            Exception("First attempt failed"),
            Exception("Second attempt failed"),
            Mock()  # Third attempt succeeds
        ]
        
        snapshot = self.capture.capture_snapshot()
        
        # Verify we got a valid snapshot
        assert snapshot.shape == (600, 800, 3)
        
        # Verify screenshot was called three times
        assert mock_pyautogui.screenshot.call_count == 3
    
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.time.sleep')
    def test_capture_snapshot_multi_monitor_window_not_visible_raises_error(self, mock_sleep):
        """Test that CaptureError is raised when window is not visible (multi-monitor support)."""
        # Mock VLC window found but minimized (not visible)
        mock_win32gui.FindWindow.return_value = 12345
        mock_win32gui.IsIconic.return_value = True  # Window is minimized
        mock_win32gui.GetWindowRect.return_value = (100, 100, 900, 700)
        
        with pytest.raises(CaptureError, match="Failed to capture snapshot after 3 attempts"):
            self.capture.capture_snapshot()
    
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.time.sleep')
    def test_capture_snapshot_multi_monitor_invalid_dimensions_raises_error(self, mock_sleep):
        """Test that CaptureError is raised when window has invalid dimensions."""
        # Mock VLC window found but with zero dimensions
        mock_win32gui.FindWindow.return_value = 12345
        mock_win32gui.IsIconic.return_value = False
        mock_win32gui.GetWindowRect.return_value = (100, 100, 100, 100)  # Zero dimensions
        
        with pytest.raises(CaptureError, match="Failed to capture snapshot after 3 attempts"):
            self.capture.capture_snapshot()
    
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.time.sleep')
    def test_capture_snapshot_multi_monitor_extreme_coordinates_raises_error(self, mock_sleep):
        """Test that CaptureError is raised when window has extreme off-screen coordinates."""
        # Mock VLC window found but with extreme coordinates (way off screen)
        mock_win32gui.FindWindow.return_value = 12345
        mock_win32gui.IsIconic.return_value = False
        mock_win32gui.GetWindowRect.return_value = (-50000, -50000, -49000, -49000)  # Extreme negative
        
        with pytest.raises(CaptureError, match="Failed to capture snapshot after 3 attempts"):
            self.capture.capture_snapshot()
    
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.time.sleep')
    @patch('src.strad_monitoring.vlc_capture.vlc_capture.np.array')
    def test_capture_snapshot_multi_monitor_valid_negative_coordinates(self, mock_np_array, mock_sleep):
        """Test multi-monitor support with valid negative coordinates (secondary monitor)."""
        # Mock VLC window on secondary monitor (reasonable negative coordinates)
        mock_win32gui.FindWindow.return_value = 12345
        mock_win32gui.IsIconic.return_value = False
        mock_win32gui.GetWindowRect.return_value = (-1920, 0, -920, 600)  # 1000x600 on left monitor
        
        # Create mock screenshot
        mock_array = np.random.randint(0, 255, (600, 1000, 3), dtype=np.uint8)
        mock_np_array.return_value = mock_array
        
        snapshot = self.capture.capture_snapshot()
        
        # Verify we got a valid snapshot
        assert snapshot.shape == (600, 1000, 3)
        
        # Verify screenshot was captured with negative coordinates (multi-monitor support)
        mock_pyautogui.screenshot.assert_called_once_with(region=(-1920, 0, 1000, 600))


if __name__ == '__main__':
    unittest.main()
