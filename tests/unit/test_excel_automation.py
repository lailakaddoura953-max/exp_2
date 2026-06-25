"""
Unit tests for Excel automation component

Tests the ExcelAutomation class and validates:
- Initialization with valid parameters
- COM object handling
- Error handling for missing dependencies
- Cleanup and resource management

Requirements tested:
- 2.1: Excel_Automation SHALL open Excel spreadsheet and locate Video_Encoder_Button
- 13.2: Proper resource cleanup to prevent process leaks
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.strad_monitoring.excel_automation import ExcelAutomation, ExcelAutomationError


class TestExcelAutomationInitialization:
    """Test ExcelAutomation initialization"""
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com.client.Dispatch')
    def test_initialization_success(self, mock_dispatch, mock_pythoncom):
        """Test successful initialization with valid parameters"""
        # Setup mock Excel application
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_dispatch.return_value = mock_excel_app
        
        # Create ExcelAutomation instance
        excel_path = "C:\\test\\spreadsheet.xlsx"
        automation = ExcelAutomation(excel_path, timeout_seconds=30, visible=False)
        
        # Verify COM initialization was called
        mock_pythoncom.CoInitialize.assert_called_once()
        
        # Verify Excel Application was created
        mock_dispatch.assert_called_once_with("Excel.Application")
        
        # Verify Excel visibility set to False (Requirement 2.1 - avoid UI flickering)
        assert mock_excel_app.Visible is False
        
        # Verify DisplayAlerts disabled
        assert mock_excel_app.DisplayAlerts is False
        
        # Verify workbook was opened
        mock_excel_app.Workbooks.Open.assert_called_once_with(excel_path)
        
        # Verify instance attributes
        assert automation.excel_file_path == excel_path
        assert automation.timeout_seconds == 30
        assert automation.visible is False
        assert automation.excel_app is mock_excel_app
        assert automation.workbook is mock_workbook
        
        # Cleanup
        automation.cleanup()
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com.client.Dispatch')
    def test_initialization_with_visible_excel(self, mock_dispatch, mock_pythoncom):
        """Test initialization with visible Excel UI"""
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_dispatch.return_value = mock_excel_app
        
        excel_path = "C:\\test\\spreadsheet.xlsx"
        automation = ExcelAutomation(excel_path, timeout_seconds=45, visible=True)
        
        # Verify Excel visibility set to True
        assert mock_excel_app.Visible is True
        assert automation.visible is True
        assert automation.timeout_seconds == 45
        
        automation.cleanup()
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', False)
    def test_initialization_without_win32com(self):
        """Test initialization fails gracefully when win32com not available"""
        with pytest.raises(ExcelAutomationError, match="win32com not available"):
            ExcelAutomation("C:\\test\\spreadsheet.xlsx")
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com.client.Dispatch')
    def test_initialization_excel_dispatch_error(self, mock_dispatch, mock_pythoncom):
        """Test initialization handles Excel dispatch errors"""
        mock_dispatch.side_effect = Exception("Excel not installed")
        
        with pytest.raises(ExcelAutomationError, match="Excel initialization failed"):
            ExcelAutomation("C:\\test\\spreadsheet.xlsx")
        
        # Verify COM uninitialize was called during cleanup
        mock_pythoncom.CoUninitialize.assert_called()
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com.client.Dispatch')
    def test_initialization_workbook_open_error(self, mock_dispatch, mock_pythoncom):
        """Test initialization handles workbook open errors"""
        mock_excel_app = MagicMock()
        mock_excel_app.Workbooks.Open.side_effect = Exception("File not found")
        mock_dispatch.return_value = mock_excel_app
        
        with pytest.raises(ExcelAutomationError, match="Excel initialization failed"):
            ExcelAutomation("C:\\test\\nonexistent.xlsx")
        
        # Verify cleanup was attempted (Quit should be called)
        mock_excel_app.Quit.assert_called()


class TestExcelAutomationCleanup:
    """Test ExcelAutomation cleanup and resource management"""
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com.client.Dispatch')
    def test_cleanup_releases_resources(self, mock_dispatch, mock_pythoncom):
        """Test cleanup properly releases COM objects (Requirement 13.2)"""
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_dispatch.return_value = mock_excel_app
        
        automation = ExcelAutomation("C:\\test\\spreadsheet.xlsx")
        automation.cleanup()
        
        # Verify workbook was closed without saving
        mock_workbook.Close.assert_called_once_with(SaveChanges=False)
        
        # Verify Excel application was quit
        mock_excel_app.Quit.assert_called_once()
        
        # Verify COM was uninitialized
        mock_pythoncom.CoUninitialize.assert_called()
        
        # Verify references were cleared
        assert automation.workbook is None
        assert automation.excel_app is None
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com.client.Dispatch')
    def test_cleanup_handles_errors_gracefully(self, mock_dispatch, mock_pythoncom):
        """Test cleanup handles errors during resource release"""
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_dispatch.return_value = mock_excel_app
        
        # Simulate error during cleanup
        mock_workbook.Close.side_effect = Exception("Close failed")
        mock_excel_app.Quit.side_effect = Exception("Quit failed")
        
        automation = ExcelAutomation("C:\\test\\spreadsheet.xlsx")
        
        # Cleanup should not raise exception
        automation.cleanup()
        
        # References should still be cleared
        assert automation.workbook is None
        assert automation.excel_app is None
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com.client.Dispatch')
    def test_context_manager_cleanup(self, mock_dispatch, mock_pythoncom):
        """Test context manager automatically cleans up resources"""
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_dispatch.return_value = mock_excel_app
        
        # Use context manager
        with ExcelAutomation("C:\\test\\spreadsheet.xlsx") as automation:
            assert automation.excel_app is not None
            assert automation.workbook is not None
        
        # Verify cleanup was called on exit
        mock_workbook.Close.assert_called_once_with(SaveChanges=False)
        mock_excel_app.Quit.assert_called_once()
        mock_pythoncom.CoUninitialize.assert_called()


class TestExcelAutomationEdgeCases:
    """Test edge cases and error conditions"""
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com.client.Dispatch')
    def test_double_cleanup_is_safe(self, mock_dispatch, mock_pythoncom):
        """Test calling cleanup() multiple times is safe"""
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_dispatch.return_value = mock_excel_app
        
        automation = ExcelAutomation("C:\\test\\spreadsheet.xlsx")
        
        # Call cleanup twice
        automation.cleanup()
        automation.cleanup()
        
        # Should not raise exception
        # First cleanup sets references to None, second cleanup should handle gracefully
    
    @patch('src.strad_monitoring.excel_automation.excel_automation.WIN32_AVAILABLE', True)
    @patch('src.strad_monitoring.excel_automation.excel_automation.pythoncom')
    @patch('src.strad_monitoring.excel_automation.excel_automation.win32com.client.Dispatch')
    def test_custom_timeout_value(self, mock_dispatch, mock_pythoncom):
        """Test custom timeout values are accepted"""
        mock_excel_app = MagicMock()
        mock_workbook = MagicMock()
        mock_excel_app.Workbooks.Open.return_value = mock_workbook
        mock_dispatch.return_value = mock_excel_app
        
        # Test various timeout values
        for timeout in [10, 30, 60, 120]:
            automation = ExcelAutomation(
                "C:\\test\\spreadsheet.xlsx", 
                timeout_seconds=timeout
            )
            assert automation.timeout_seconds == timeout
            automation.cleanup()
