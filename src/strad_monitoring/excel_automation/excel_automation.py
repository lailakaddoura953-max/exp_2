"""
Excel Automation Component for Strad Carrier Monitoring

This module provides Excel COM automation to control the "spreader video encoder"
ActiveX control for opening video feeds for selected Strad Carriers.

Requirements:
- 2.1: Excel_Automation SHALL open Excel spreadsheet and locate Video_Encoder_Button
"""

import logging
import time
from typing import Optional

try:
    import win32com.client
    import win32gui
    import pythoncom
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    win32com = None
    win32gui = None
    pythoncom = None
    logging.warning("win32com/win32gui/pythoncom not available. Excel automation will not work.")


logger = logging.getLogger(__name__)


class ExcelAutomationError(Exception):
    """Exception raised for Excel automation errors."""
    pass


class ExcelAutomation:
    """
    Excel COM automation interface for controlling video encoder.
    
    This class manages the Excel application lifecycle, opens the workbook
    containing the "spreader video encoder" control, and provides methods
    to open video feeds for Strad Carriers.
    
    Attributes:
        excel_file_path (str): Path to the Excel workbook
        timeout_seconds (int): Timeout for VLC window detection
        excel_app: Excel Application COM object
        workbook: Excel Workbook COM object
        visible (bool): Whether Excel UI is visible
    """
    
    def __init__(
        self, 
        excel_file_path: str, 
        timeout_seconds: int = 30,
        visible: bool = False
    ):
        """
        Initialize Excel COM automation.
        
        Args:
            excel_file_path: Path to the Excel workbook containing video encoder control
            timeout_seconds: Timeout in seconds for VLC window detection (default: 30)
            visible: Whether to make Excel visible (default: False to avoid UI flickering)
            
        Raises:
            ExcelAutomationError: If Excel automation is not available or initialization fails
            
        Requirements:
            - 2.1: Open Excel spreadsheet containing Video_Encoder_Button
        """
        if not WIN32_AVAILABLE:
            raise ExcelAutomationError(
                "win32com not available. Please install pywin32: pip install pywin32"
            )
        
        self.excel_file_path = excel_file_path
        self.timeout_seconds = timeout_seconds
        self.visible = visible
        self.excel_app: Optional[win32com.client.CDispatch] = None
        self.workbook: Optional[win32com.client.CDispatch] = None
        
        logger.info(
            f"Initializing Excel automation with file: {excel_file_path}, "
            f"timeout: {timeout_seconds}s, visible: {visible}"
        )
        
        try:
            # Initialize COM for thread safety
            pythoncom.CoInitialize()
            
            # Create Excel Application instance via COM
            self.excel_app = win32com.client.Dispatch("Excel.Application")
            
            # Set visibility to avoid UI flickering (Requirement 2.1)
            self.excel_app.Visible = visible
            
            # Disable alerts to prevent blocking dialogs
            self.excel_app.DisplayAlerts = False
            
            # Open the workbook containing the video encoder control
            logger.info(f"Opening workbook: {excel_file_path}")
            self.workbook = self.excel_app.Workbooks.Open(excel_file_path)
            
            logger.info("Excel automation initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Excel automation: {e}")
            self._cleanup_com_objects()
            raise ExcelAutomationError(f"Excel initialization failed: {e}") from e
    
    def _cleanup_com_objects(self) -> None:
        """
        Clean up COM objects to prevent Excel process leaks.
        
        This method releases COM references and ensures Excel process terminates.
        """
        try:
            if self.workbook is not None:
                try:
                    self.workbook.Close(SaveChanges=False)
                except Exception as e:
                    logger.warning(f"Error closing workbook: {e}")
                finally:
                    self.workbook = None
            
            if self.excel_app is not None:
                try:
                    self.excel_app.Quit()
                except Exception as e:
                    logger.warning(f"Error quitting Excel application: {e}")
                finally:
                    self.excel_app = None
            
            # Uninitialize COM
            try:
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.warning(f"Error uninitializing COM: {e}")
                
        except Exception as e:
            logger.error(f"Error during COM cleanup: {e}")
    
    def cleanup(self) -> None:
        """
        Cleanup Excel COM objects and release resources.
        
        This method should be called when the ExcelAutomation instance is no longer needed
        to ensure proper cleanup and prevent Excel process leaks.
        
        Requirements:
            - 13.2: Ensure proper resource cleanup to prevent process leaks
        """
        logger.info("Cleaning up Excel automation resources")
        self._cleanup_com_objects()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.cleanup()
        return False
    
    def __del__(self):
        """Destructor to ensure cleanup even if cleanup() not called explicitly."""
        try:
            self._cleanup_com_objects()
        except Exception:
            pass  # Suppress errors in destructor
    
    def open_video_feed(self, strad_id: str) -> bool:
        """
        Open video feed for given strad ID using the video encoder control.
        
        This method:
        1. Locates the "spreader video encoder" ActiveX/OLE control in the worksheet
        2. Inserts the strad ID (CHE_Number in SCXXX format) into the control
        3. Activates the control to trigger VLC media player opening
        4. Polls for VLC window appearance with timeout
        
        Args:
            strad_id: Strad Carrier ID in format SCXXX (e.g., "SC042")
            
        Returns:
            True if VLC window opened successfully, False if timeout or error
            
        Raises:
            ExcelAutomationError: If critical errors occur during automation
            
        Requirements:
            - 2.2: Locate "spreader video encoder" control
            - 2.3: Insert CHE_Number (SCXXX format) into control
            - 2.4: Activate control to trigger video feed
            - 2.5: Verify VLC media player window opens
            - 2.6: Return error status if VLC fails to open within 30 seconds
        """
        logger.info(f"Opening video feed for strad: {strad_id}")
        
        if not self.workbook:
            raise ExcelAutomationError("Workbook not initialized")
        
        try:
            # Get the active worksheet (assuming video encoder is on the active sheet)
            worksheet = self.workbook.ActiveSheet
            logger.debug(f"Using worksheet: {worksheet.Name}")
            
            # Requirement 2.2: Locate "spreader video encoder" control using OLEObjects()
            video_encoder_control = None
            ole_objects = worksheet.OLEObjects()
            
            logger.debug(f"Searching through {ole_objects.Count} OLE objects for video encoder control")
            
            for i in range(1, ole_objects.Count + 1):
                ole_obj = ole_objects(i)
                control_name = ole_obj.Name
                logger.debug(f"Found OLE object: {control_name}")
                
                # Look for control with "spreader video encoder" in its name (case-insensitive)
                if "spreader video encoder" in control_name.lower():
                    video_encoder_control = ole_obj
                    logger.info(f"Found video encoder control: {control_name}")
                    break
            
            if not video_encoder_control:
                error_msg = "Could not locate 'spreader video encoder' control in worksheet"
                logger.error(error_msg)
                return False
            
            # Requirement 2.3: Insert CHE_Number (SCXXX format) into control
            # Try multiple properties to set the value (different ActiveX controls use different properties)
            control_object = video_encoder_control.Object
            
            try:
                # Try setting Value property first
                control_object.Value = strad_id
                logger.debug(f"Set control.Value to: {strad_id}")
            except AttributeError:
                try:
                    # Fallback to Text property
                    control_object.Text = strad_id
                    logger.debug(f"Set control.Text to: {strad_id}")
                except AttributeError:
                    logger.error("Control does not have Value or Text property")
                    return False
            
            # Requirement 2.4: Activate control to trigger video feed opening
            try:
                # Try clicking the control
                control_object.Click()
                logger.info("Activated video encoder control via Click()")
            except AttributeError:
                # Some controls may not have Click method, try alternative activation
                try:
                    video_encoder_control.Activate()
                    logger.info("Activated video encoder control via Activate()")
                except Exception as e:
                    logger.warning(f"Could not activate control: {e}")
            
            # Requirement 2.5 & 2.6: Poll for VLC window with 30-second timeout
            logger.info(f"Polling for VLC window (timeout: {self.timeout_seconds}s)")
            start_time = time.time()
            vlc_window_found = False
            
            while time.time() - start_time < self.timeout_seconds:
                # Try to find VLC media player window
                vlc_hwnd = win32gui.FindWindow("Qt5QWindowIcon", None)  # VLC uses Qt5
                if not vlc_hwnd:
                    vlc_hwnd = win32gui.FindWindow(None, "VLC media player")  # Alternative class
                
                if vlc_hwnd:
                    logger.info(f"VLC window found (HWND: {vlc_hwnd})")
                    vlc_window_found = True
                    break
                
                # Check every 0.5 seconds
                time.sleep(0.5)
            
            if not vlc_window_found:
                elapsed = time.time() - start_time
                logger.warning(f"VLC window not found after {elapsed:.1f}s timeout")
                return False
            
            logger.info(f"Video feed opened successfully for strad: {strad_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error opening video feed for {strad_id}: {e}")
            return False
