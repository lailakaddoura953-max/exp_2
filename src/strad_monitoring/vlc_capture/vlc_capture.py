"""
VLC Capture Component for Strad Carrier Monitoring Automation

This module provides snapshot capture functionality from VLC media player windows
displaying live camera feeds. It includes stabilization delays and dimension validation
to ensure high-quality snapshots for misalignment detection.

Requirements Coverage:
- Requirement 3.1: Feed stabilization wait (5 seconds default)
- Requirement 3.2: Snapshot capture from VLC active window
"""

import time
import logging
from typing import Optional, Tuple

import numpy as np

# Windows-specific imports (required for VLC window capture on Windows)
try:
    import win32gui
    import win32con
    WINDOWS_AVAILABLE = True
except ImportError:
    # These modules are only available on Windows with pywin32 installed
    # Tests can run without them using mocks
    WINDOWS_AVAILABLE = False
    win32gui = None
    win32con = None

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None

from PIL import Image


logger = logging.getLogger(__name__)


class CaptureError(Exception):
    """Exception raised when snapshot capture fails."""
    pass


class VLCCapture:
    """
    Captures snapshots from VLC media player windows displaying live camera feeds.
    
    This class manages the interaction with VLC media player windows, including
    window location, foreground activation, stabilization delays, and screenshot
    capture with dimension validation.
    
    Attributes:
        stabilization_delay (float): Time in seconds to wait for feed stabilization
                                     before capturing. Default: 5.0 seconds
        min_width (int): Minimum required snapshot width in pixels. Default: 640
        min_height (int): Minimum required snapshot height in pixels. Default: 480
    """
    
    def __init__(
        self,
        stabilization_delay: float = 5.0,
        min_width: int = 640,
        min_height: int = 480,
        rtsp_username: Optional[str] = None,
        rtsp_password: Optional[str] = None
    ):
        """
        Initialize VLC capture settings.
        
        Args:
            stabilization_delay: Time in seconds to wait for feed stabilization
                                before capturing. Must be positive.
            min_width: Minimum required snapshot width in pixels.
            min_height: Minimum required snapshot height in pixels.
            rtsp_username: Optional RTSP authentication username for VLC dialog
            rtsp_password: Optional RTSP authentication password for VLC dialog
            
        Raises:
            ValueError: If any parameter is negative or zero.
        """
        if stabilization_delay <= 0:
            raise ValueError("stabilization_delay must be positive")
        if min_width <= 0:
            raise ValueError("min_width must be positive")
        if min_height <= 0:
            raise ValueError("min_height must be positive")
            
        self.stabilization_delay = stabilization_delay
        self.min_width = min_width
        self.min_height = min_height
        self.rtsp_username = rtsp_username
        self.rtsp_password = rtsp_password
        
        # Warn if Windows dependencies are not available
        if not WINDOWS_AVAILABLE:
            logger.warning(
                "Windows dependencies (pywin32) not available. "
                "VLC capture will not work in production. "
                "Install pywin32 for full functionality."
            )
        if not PYAUTOGUI_AVAILABLE:
            logger.warning(
                "pyautogui not available. VLC capture will not work in production. "
                "Install pyautogui for full functionality."
            )
        
        logger.info(
            f"VLCCapture initialized: stabilization_delay={stabilization_delay}s, "
            f"min_dimensions={min_width}x{min_height}"
        )
    
    def _find_vlc_window(self) -> Optional[int]:
        """
        Locate the VLC media player window.
        
        Returns:
            Window handle (hwnd) if found, None otherwise.
            
        Raises:
            CaptureError: If Windows dependencies are not available.
        """
        if not WINDOWS_AVAILABLE or win32gui is None:
            raise CaptureError(
                "Windows dependencies (pywin32) not available. "
                "Install pywin32 to use VLC capture functionality."
            )
        
        # Try to find VLC window by class name
        hwnd = win32gui.FindWindow("Qt5152QWindowIcon", None)
        
        if hwnd == 0:
            # Fallback: Try alternative VLC window class names
            hwnd = win32gui.FindWindow("Qt5QWindowIcon", None)
        
        if hwnd == 0:
            # Fallback: Try to find by window title containing "VLC"
            def enum_callback(current_hwnd, results):
                if win32gui.IsWindowVisible(current_hwnd):
                    window_text = win32gui.GetWindowText(current_hwnd)
                    if "VLC" in window_text:
                        results.append(current_hwnd)
            
            vlc_windows = []
            win32gui.EnumWindows(enum_callback, vlc_windows)
            
            if vlc_windows:
                hwnd = vlc_windows[0]
            else:
                return None
        
        return hwnd if hwnd != 0 else None
    
    def _handle_vlc_authentication(self) -> None:
        """
        Automatically fill VLC RTSP authentication dialog if it appears.
        
        This method detects if a VLC authentication dialog is present and
        automatically fills in the username and password from configuration.
        Uses PyAutoGUI to type credentials and press Enter.
        
        Note: Only works if rtsp_username and rtsp_password were provided.
        """
        if not self.rtsp_username or not self.rtsp_password:
            logger.debug("No RTSP credentials configured, skipping auth handling")
            return
        
        if not PYAUTOGUI_AVAILABLE or pyautogui is None:
            logger.warning("pyautogui not available, cannot handle VLC authentication")
            return
        
        try:
            # Wait briefly for auth dialog to appear
            time.sleep(1.0)
            
            # Look for VLC authentication dialog window
            def find_auth_dialog(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd).lower()
                    if any(keyword in window_text for keyword in ['authentication', 'login', 'password', 'user']):
                        results.append(hwnd)
            
            auth_dialogs = []
            if WINDOWS_AVAILABLE and win32gui:
                win32gui.EnumWindows(find_auth_dialog, auth_dialogs)
            
            if auth_dialogs:
                logger.info("VLC authentication dialog detected, auto-filling credentials")
                
                # Bring auth dialog to foreground
                auth_hwnd = auth_dialogs[0]
                win32gui.SetForegroundWindow(auth_hwnd)
                time.sleep(0.3)
                
                # Type username, press Tab, type password, press Enter
                pyautogui.write(self.rtsp_username, interval=0.05)
                time.sleep(0.2)
                pyautogui.press('tab')
                time.sleep(0.2)
                pyautogui.write(self.rtsp_password, interval=0.05)
                time.sleep(0.2)
                pyautogui.press('enter')
                
                logger.info("✓ VLC authentication credentials submitted")
                time.sleep(1.0)  # Wait for dialog to close
            else:
                logger.debug("No VLC authentication dialog detected")
                
        except Exception as e:
            logger.warning(f"Failed to handle VLC authentication: {e}")
            # Don't raise - authentication might not be needed or user can do it manually
    
    def _bring_to_foreground(self, hwnd: int) -> None:
        """
        Bring the VLC window to the foreground.
        
        Args:
            hwnd: Window handle of the VLC window.
            
        Raises:
            CaptureError: If unable to bring window to foreground.
        """
        try:
            # Restore window if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # Bring window to foreground
            win32gui.SetForegroundWindow(hwnd)
            
            # Small delay to ensure window is ready
            time.sleep(0.2)
            
            logger.debug(f"VLC window {hwnd} brought to foreground")
            
        except Exception as e:
            raise CaptureError(f"Failed to bring VLC window to foreground: {e}")
    
    def _get_window_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        """
        Get the window rectangle coordinates.
        
        Args:
            hwnd: Window handle of the VLC window.
            
        Returns:
            Tuple of (left, top, right, bottom) coordinates in pixels.
            
        Raises:
            CaptureError: If unable to get window rectangle.
        """
        try:
            rect = win32gui.GetWindowRect(hwnd)
            logger.debug(f"VLC window rectangle: {rect}")
            return rect
            
        except Exception as e:
            raise CaptureError(f"Failed to get VLC window rectangle: {e}")
    
    def _check_window_on_screen(self, hwnd: int) -> bool:
        """
        Check if window is visible on any monitor (multi-monitor support).
        
        Args:
            hwnd: Window handle of the VLC window.
            
        Returns:
            True if window is visible on a monitor, False otherwise.
            
        Requirements:
            - Requirement 3.6: Handle multi-monitor scenarios by ensuring window is visible
        """
        try:
            left, top, right, bottom = self._get_window_rect(hwnd)
            
            # Check if window has valid dimensions (not minimized or off-screen)
            width = right - left
            height = bottom - top
            
            if width <= 0 or height <= 0:
                logger.warning(f"Window has invalid dimensions: {width}x{height}")
                return False
            
            # Check if window coordinates are reasonable (not way off screen)
            # Allow some negative coordinates for multi-monitor setups
            # but reject extreme values that indicate the window is not visible
            MAX_NEGATIVE_OFFSET = 10000
            if (left < -MAX_NEGATIVE_OFFSET or top < -MAX_NEGATIVE_OFFSET or
                right > MAX_NEGATIVE_OFFSET or bottom > MAX_NEGATIVE_OFFSET):
                logger.warning(f"Window coordinates out of range: ({left}, {top}, {right}, {bottom})")
                return False
            
            # Check if window is not minimized
            if win32gui.IsIconic(hwnd):
                logger.warning("Window is minimized")
                return False
            
            logger.debug(f"Window is visible on screen at ({left}, {top}, {right}, {bottom})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to check window visibility: {e}")
            return False
    
    def _capture_single_attempt(self) -> np.ndarray:
        """
        Perform a single snapshot capture attempt.
        
        Returns:
            Numpy array with shape (H, W, 3) in RGB format containing the snapshot.
            
        Raises:
            CaptureError: If capture fails for any reason.
        """
        # ===== Requirement 3.2: Locate VLC window =====
        hwnd = self._find_vlc_window()
        if hwnd is None:
            raise CaptureError("VLC media player window not found")
        
        logger.debug(f"VLC window found: hwnd={hwnd}")
        
        # ===== Requirement 3.6: Multi-monitor support - Check window visibility =====
        if not self._check_window_on_screen(hwnd):
            raise CaptureError("VLC window is not visible on screen")
        
        # Bring window to foreground
        self._bring_to_foreground(hwnd)
        
        # Get window rectangle
        left, top, right, bottom = self._get_window_rect(hwnd)
        
        # Calculate dimensions
        width = right - left
        height = bottom - top
        
        logger.debug(f"Window dimensions: {width}x{height}")
        
        # ===== Capture screenshot =====
        if not PYAUTOGUI_AVAILABLE or pyautogui is None:
            raise CaptureError(
                "pyautogui not available. "
                "Install pyautogui to use VLC capture functionality."
            )
        
        # Capture the window region using pyautogui
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        
        # Convert PIL Image to numpy array (RGB format)
        snapshot = np.array(screenshot)
        
        logger.debug(f"Snapshot captured: shape={snapshot.shape}, dtype={snapshot.dtype}")
        
        # ===== Requirement 3.5: Validate dimensions =====
        if not self.validate_snapshot(snapshot):
            raise CaptureError(
                f"Snapshot dimensions {snapshot.shape[1]}x{snapshot.shape[0]} "
                f"do not meet minimum requirements {self.min_width}x{self.min_height}"
            )
        
        return snapshot
    
    def capture_snapshot(self) -> np.ndarray:
        """
        Capture snapshot from VLC window with retry logic.
        
        This method performs the following steps:
        1. Waits for stabilization delay to allow feed to stabilize
        2. Attempts to capture snapshot (up to 3 times with 2-second intervals)
        3. For each attempt:
           a. Locates the VLC media player window
           b. Checks window is visible (multi-monitor support)
           c. Brings the window to foreground
           d. Captures screenshot of the window region
           e. Converts to numpy array in RGB format
           f. Validates dimensions meet minimum requirements
        
        Returns:
            Numpy array with shape (H, W, 3) in RGB format containing the snapshot.
            
        Raises:
            CaptureError: If all retry attempts fail or VLC window not found.
                         
        Requirements:
            - Requirement 3.1: Waits for stabilization delay before capturing
            - Requirement 3.2: Captures from VLC media player active window
            - Requirement 3.5: Validates snapshot dimensions are at least 640x480
            - Requirement 3.6: Implements 3 retry attempts with 2-second intervals on capture failure
            - Requirement 3.6: Handles multi-monitor scenarios by ensuring window is visible
        """
        logger.info(
            f"Starting snapshot capture with {self.stabilization_delay}s stabilization delay"
        )
        
        # ===== Requirement 3.1: Wait for feed stabilization =====
        logger.debug(f"Waiting {self.stabilization_delay}s for feed stabilization...")
        
        # ===== Handle VLC RTSP authentication if needed =====
        self._handle_vlc_authentication()
        
        # Continue waiting for stabilization after auth
        time.sleep(self.stabilization_delay)
        
        # ===== Requirement 3.6: Implement retry logic (3 attempts with 2-second intervals) =====
        max_attempts = 3
        retry_interval = 2.0
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Capture attempt {attempt}/{max_attempts}")
                
                # Perform single capture attempt
                snapshot = self._capture_single_attempt()
                
                logger.info(
                    f"Snapshot captured successfully on attempt {attempt}: "
                    f"{snapshot.shape[1]}x{snapshot.shape[0]} pixels"
                )
                
                return snapshot
                
            except CaptureError as e:
                last_error = e
                logger.warning(f"Capture attempt {attempt}/{max_attempts} failed: {e}")
                
                # If not the last attempt, wait before retrying
                if attempt < max_attempts:
                    logger.info(f"Retrying in {retry_interval} seconds...")
                    time.sleep(retry_interval)
                else:
                    logger.error(f"All {max_attempts} capture attempts failed")
            
            except Exception as e:
                # Unexpected errors - convert to CaptureError
                last_error = CaptureError(f"Unexpected error during capture: {e}")
                logger.error(f"Capture attempt {attempt}/{max_attempts} failed with unexpected error: {e}")
                
                # If not the last attempt, wait before retrying
                if attempt < max_attempts:
                    logger.info(f"Retrying in {retry_interval} seconds...")
                    time.sleep(retry_interval)
                else:
                    logger.error(f"All {max_attempts} capture attempts failed")
        
        # All attempts failed - raise the last error
        raise CaptureError(
            f"Failed to capture snapshot after {max_attempts} attempts. "
            f"Last error: {last_error}"
        )
    
    def validate_snapshot(self, snapshot: np.ndarray) -> bool:
        """
        Verify snapshot meets minimum dimension requirements.
        
        Args:
            snapshot: Numpy array with shape (H, W, 3) or (H, W, 4).
            
        Returns:
            True if snapshot meets minimum width and height requirements,
            False otherwise.
            
        Requirements:
            - Requirement 3.5: Validates minimum dimensions of 640x480 pixels
        """
        if snapshot is None or not isinstance(snapshot, np.ndarray):
            logger.warning("Invalid snapshot: not a numpy array")
            return False
        
        if len(snapshot.shape) < 2:
            logger.warning(f"Invalid snapshot shape: {snapshot.shape}")
            return False
        
        height, width = snapshot.shape[:2]
        
        is_valid = height >= self.min_height and width >= self.min_width
        
        if not is_valid:
            logger.warning(
                f"Snapshot validation failed: {width}x{height} < "
                f"{self.min_width}x{self.min_height}"
            )
        else:
            logger.debug(f"Snapshot validation passed: {width}x{height}")
        
        return is_valid
