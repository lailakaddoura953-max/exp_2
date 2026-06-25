"""
Test Excel file path and automation

This script verifies that the Excel file path in system_config.json is correct
and that Excel COM automation is working.

Usage:
    python test_excel_connection.py
"""

import sys
import json
import os
from pathlib import Path


def print_header(message):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(message)
    print("=" * 70)


def print_success(message):
    """Print success message"""
    print(f"✓ {message}")


def print_error(message):
    """Print error message"""
    print(f"✗ {message}")


def print_info(message):
    """Print info message"""
    print(f"  {message}")


def test_excel_path():
    """Test if Excel file exists"""
    print_header("TEST 1: EXCEL FILE PATH")
    
    # Load configuration
    config_path = "system_config.json"
    
    if not Path(config_path).exists():
        print_error(f"Configuration file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        return False
    
    if 'excel_file_path' not in config:
        print_error("excel_file_path not found in config")
        return False
    
    excel_path = config['excel_file_path']
    
    print_info(f"Configured path: {excel_path}")
    
    # Check if file exists
    if os.path.exists(excel_path):
        print_success("File exists")
        
        # Get file info
        file_size = os.path.getsize(excel_path)
        print_info(f"File size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
        
        # Check if it's an Excel file
        if excel_path.lower().endswith(('.xlsx', '.xlsm', '.xls')):
            print_info(f"File type: Excel workbook")
        else:
            print_info(f"⚠ Warning: File doesn't have Excel extension")
        
        # Check if readable
        try:
            with open(excel_path, 'rb') as f:
                f.read(10)  # Try to read first 10 bytes
            print_success("File is readable")
            return True
        except Exception as e:
            print_error(f"Cannot read file: {e}")
            return False
    else:
        print_error("File does NOT exist")
        print()
        print_info("Troubleshooting:")
        print_info("  1. Check the path is correct")
        print_info("  2. Check file hasn't been moved/renamed")
        print_info("  3. Check network drive is accessible (if UNC path)")
        print_info("  4. Use double backslashes: C:\\\\path\\\\to\\\\file.xlsx")
        return False


def test_excel_automation():
    """Test Excel COM automation"""
    print_header("TEST 2: EXCEL COM AUTOMATION")
    
    # Check if pywin32 is installed
    try:
        import win32com.client
    except ImportError:
        print_error("pywin32 not installed")
        print_info("Install with: pip install pywin32")
        return False
    
    print_success("pywin32 is installed")
    
    # Load configuration
    try:
        with open('system_config.json', 'r') as f:
            config = json.load(f)
        excel_path = config['excel_file_path']
    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        return False
    
    try:
        print_info("Initializing Excel COM automation...")
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False  # Keep hidden for test
        excel.DisplayAlerts = False
        
        print_success("Excel COM automation initialized")
        
        print_info(f"Opening workbook: {Path(excel_path).name}")
        workbook = excel.Workbooks.Open(excel_path)
        
        print_success("Workbook opened successfully")
        
        # Get active sheet
        sheet = workbook.ActiveSheet
        print_info(f"Active sheet: {sheet.Name}")
        
        # Count sheets
        sheet_count = workbook.Sheets.Count
        print_info(f"Total sheets: {sheet_count}")
        
        # Try to read cell A1
        try:
            value = sheet.Range("A1").Value
            if value:
                print_info(f"Cell A1 value: '{value}'")
            else:
                print_info("Cell A1 is empty")
        except Exception as e:
            print_info(f"Could not read cell A1: {e}")
        
        # Test write to a cell (don't save)
        try:
            test_cell = "Z999"  # Use a cell unlikely to be used
            original_value = sheet.Range(test_cell).Value
            sheet.Range(test_cell).Value = "TEST_AUTOMATION_WORKS"
            new_value = sheet.Range(test_cell).Value
            
            if new_value == "TEST_AUTOMATION_WORKS":
                print_success("Successfully wrote to test cell")
                # Restore original value
                sheet.Range(test_cell).Value = original_value
            else:
                print_info("⚠ Could not verify write operation")
        except Exception as e:
            print_info(f"Could not test write: {e}")
        
        # Clean up
        workbook.Close(SaveChanges=False)
        excel.Quit()
        
        print_success("Excel automation test completed successfully")
        return True
        
    except Exception as e:
        print_error(f"Excel automation failed: {e}")
        print()
        print_info("Troubleshooting:")
        print_info("  1. Ensure Microsoft Excel is installed")
        print_info("  2. Install pywin32: pip install pywin32")
        print_info("  3. Check file isn't password protected")
        print_info("  4. Check file isn't already open")
        print_info("  5. Close any open Excel instances")
        
        # Try to clean up
        try:
            excel.Quit()
        except:
            pass
        
        return False


def main():
    print_header("EXCEL CONNECTION TEST")
    
    # Test 1: File path
    path_test = test_excel_path()
    
    # Test 2: COM automation (only if path test passed)
    if path_test:
        automation_test = test_excel_automation()
    else:
        print()
        print_info("Skipping automation test (file path test failed)")
        automation_test = False
    
    # Summary
    print()
    print_header("TEST SUMMARY")
    
    print_info(f"File path test: {'✓ PASSED' if path_test else '✗ FAILED'}")
    print_info(f"Automation test: {'✓ PASSED' if automation_test else '✗ FAILED (or skipped)'}")
    
    if path_test and automation_test:
        print()
        print_header("✓ ALL TESTS PASSED")
        print()
        print_info("Excel file is configured correctly!")
        print_info("Next steps:")
        print_info("  1. Verify your spreadsheet has required structure")
        print_info("  2. Test VBA macro manually")
        print_info("  3. Run system: python -m src.strad_monitoring.main")
        print()
        print_info("For detailed setup instructions, see:")
        print_info("  EXCEL_CONFIGURATION_GUIDE.md")
        print()
        return 0
    else:
        print()
        print_header("✗ TESTS FAILED")
        print()
        print_info("Please fix the issues above before running the system")
        print_info("For detailed help, see: EXCEL_CONFIGURATION_GUIDE.md")
        print()
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
