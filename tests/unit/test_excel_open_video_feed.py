"""
Unit tests for Excel automation open_video_feed method

Tests the open_video_feed() functionality and validates:
- Video encoder control location
- Strad ID input handling
- Control activation
- VLC window detection with timeout

Requirements tested:
- 2.2: Locate "spreader video encoder" control
- 2.3: Insert CHE_Number (SCXXX format) into control
- 2.4: Activate control to trigger video feed
- 2.5: Verify VLC media player window opens
- 2.6: Return error status if VLC fails to open within 30 seconds
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import time

from src.strad_monitoring.excel_automation import ExcelAutomation, ExcelAutomationError


class TestOpenVideoFeed:
    """Test open_video_feed method"""
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.time')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32gui')
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com')
    def test_open_video_feed_success(
        self, 
        mock_win32com, 
        mock_pythoncom, 
        mock_win32gui,
        mock_time
    ):
        """Test successful video feed opening with VLC window detection"""
        # Setup mock Excel application
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_worksheet = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_workbook.ActiveSheet = mock_worksheet
        mock_win32com.client.Dispatch.return_value = mock_excel_app
        
        # Setup mock OLE objects
        mock_ole_objects = MagicMock()
        mock_ole_objects.Count = 3
        
        mock_control1 = MagicMock()
        mock_control1.Name = "Button1"
        
        mock_control2 = MagicMock()
        mock_control2.Name = "Spreader Video Encoder"
        mock_control_object = MagicMock()
        mock_control2.Object = mock_control_object
        
        mock_control3 = MagicMock()
        mock_control3.Name = "Button3"
        
        # Return controls in sequence
        mock_ole_objects.side_effect = lambda i: [mock_control1, mock_control2, mock_control3][i-1]
        mock_worksheet.OLEObjects.return_value = mock_ole_objects
        
        # Mock time.time() to simulate time progression
        start_time = 1000.0
        mock_time.time.side_effect = [start_time, start_time + 0.1, start_time + 0.2]
        mock_time.sleep.return_value = None
        
        # Mock VLC window found
        mock_win32gui.FindWindow.side_effect = [None, 12345]  # First Qt5 search fails, second finds window
        
        # Create ExcelAutomation instance
        automation = ExcelAutomation("C:\\test\\spreadsheet.xlsx", timeout_seconds=30)
        
        # Call open_video_feed
        result = automation.open_video_feed("SC042")
        
        # Verify result is True
        assert result is True
        
        # Verify control value was set
        assert mock_control_object.Value == "SC042"
        
        # Verify control was clicked
        mock_control_object.Click.assert_called_once()
        
        # Verify VLC window search was attempted
        assert mock_win32gui.FindWindow.call_count >= 1
        
        automation.cleanup()
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.time')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32gui')
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com')
    def test_open_video_feed_vlc_timeout(
        self, 
        mock_win32com, 
        mock_pythoncom, 
        mock_win32gui,
        mock_time
    ):
        """Test video feed opening when VLC window times out"""
        # Setup mock Excel application
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_worksheet = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_workbook.ActiveSheet = mock_worksheet
        mock_win32com.client.Dispatch.return_value = mock_excel_app
        
        # Setup mock OLE objects
        mock_ole_objects = MagicMock()
        mock_ole_objects.Count = 1
        
        mock_control = MagicMock()
        mock_control.Name = "spreader video encoder"
        mock_control_object = MagicMock()
        mock_control.Object = mock_control_object
        
        mock_ole_objects.side_effect = lambda i: mock_control
        mock_worksheet.OLEObjects.return_value = mock_ole_objects
        
        # Mock time.time() to simulate timeout
        start_time = 1000.0
        timeout = 5.0  # Short timeout for testing
        # Simulate time progression beyond timeout
        mock_time.time.side_effect = [
            start_time,
            start_time + 1.0,
            start_time + 2.0,
            start_time + 3.0,
            start_time + 4.0,
            start_time + 5.5  # Beyond timeout
        ]
        mock_time.sleep.return_value = None
        
        # Mock VLC window never found
        mock_win32gui.FindWindow.return_value = None
        
        # Create ExcelAutomation instance with short timeout
        automation = ExcelAutomation("C:\\test\\spreadsheet.xlsx", timeout_seconds=timeout)
        
        # Call open_video_feed
        result = automation.open_video_feed("SC115")
        
        # Verify result is False (timeout)
        assert result is False
        
        # Verify control was still set and clicked
        assert mock_control_object.Value == "SC115"
        mock_control_object.Click.assert_called_once()
        
        automation.cleanup()
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com')
    def test_open_video_feed_control_not_found(
        self, 
        mock_win32com, 
        mock_pythoncom
    ):
        """Test video feed opening when video encoder control is not found"""
        # Setup mock Excel application
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_worksheet = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_workbook.ActiveSheet = mock_worksheet
        mock_win32com.client.Dispatch.return_value = mock_excel_app
        
        # Setup mock OLE objects with no matching control
        mock_ole_objects = MagicMock()
        mock_ole_objects.Count = 2
        
        mock_control1 = MagicMock()
        mock_control1.Name = "Button1"
        
        mock_control2 = MagicMock()
        mock_control2.Name = "Button2"
        
        mock_ole_objects.side_effect = lambda i: [mock_control1, mock_control2][i-1]
        mock_worksheet.OLEObjects.return_value = mock_ole_objects
        
        # Create ExcelAutomation instance
        automation = ExcelAutomation("C:\\test\\spreadsheet.xlsx")
        
        # Call open_video_feed
        result = automation.open_video_feed("SC042")
        
        # Verify result is False (control not found)
        assert result is False
        
        automation.cleanup()
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.time')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32gui')
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com')
    def test_open_video_feed_with_text_property(
        self, 
        mock_win32com, 
        mock_pythoncom, 
        mock_win32gui,
        mock_time
    ):
        """Test video feed opening using Text property fallback"""
        # Setup mock Excel application
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_worksheet = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_workbook.ActiveSheet = mock_worksheet
        mock_win32com.client.Dispatch.return_value = mock_excel_app
        
        # Setup mock OLE objects
        mock_ole_objects = MagicMock()
        mock_ole_objects.Count = 1
        
        mock_control = MagicMock()
        mock_control.Name = "SPREADER VIDEO ENCODER"  # Test case-insensitive matching
        mock_control_object = MagicMock()
        # Simulate Value property not existing, but Text property does
        type(mock_control_object).Value = property(
            lambda self: (_ for _ in ()).throw(AttributeError("Value not available"))
        )
        mock_control_object.Text = ""
        mock_control.Object = mock_control_object
        
        mock_ole_objects.side_effect = lambda i: mock_control
        mock_worksheet.OLEObjects.return_value = mock_ole_objects
        
        # Mock time and VLC window
        start_time = 1000.0
        mock_time.time.side_effect = [start_time, start_time + 0.1]
        mock_time.sleep.return_value = None
        mock_win32gui.FindWindow.return_value = 54321
        
        # Create ExcelAutomation instance
        automation = ExcelAutomation("C:\\test\\spreadsheet.xlsx")
        
        # Call open_video_feed
        result = automation.open_video_feed("SC078")
        
        # Verify result is True
        assert result is True
        
        # Verify Text property was set
        assert mock_control_object.Text == "SC078"
        
        automation.cleanup()
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com')
    def test_open_video_feed_workbook_not_initialized(
        self, 
        mock_win32com, 
        mock_pythoncom
    ):
        """Test open_video_feed fails when workbook is not initialized"""
        # Setup mock Excel application (but will set workbook to None)
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_win32com.client.Dispatch.return_value = mock_excel_app
        
        # Create ExcelAutomation instance
        automation = ExcelAutomation("C:\\test\\spreadsheet.xlsx")
        
        # Manually set workbook to None to simulate uninitialized state
        automation.workbook = None
        
        # Call open_video_feed should raise error
        with pytest.raises(ExcelAutomationError, match="Workbook not initialized"):
            automation.open_video_feed("SC042")
        
        automation.cleanup()
