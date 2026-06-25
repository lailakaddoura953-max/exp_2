# Excel Video Encoder Configuration Guide
## Configuring the Excel Spreader Encoder File Path

**Last Updated:** 2024  
**Purpose:** Guide for configuring the Excel video encoder file path in the strad monitoring system

---

## Table of Contents

1. [Overview](#overview)
2. [Finding Your Excel File](#finding-your-excel-file)
3. [Configuring system_config.json](#configuring-systemconfigjson)
4. [Excel File Requirements](#excel-file-requirements)
5. [Testing the Configuration](#testing-the-configuration)
6. [Troubleshooting](#troubleshooting)

---

## Overview

### What is the Excel Video Encoder?

The strad monitoring system uses an Excel spreadsheet to control the video encoder that displays live feeds from strad carriers. The system:

1. Opens the Excel file programmatically
2. Enters a strad ID (e.g., SC042) into a specific cell
3. Clicks a button in Excel to open the video feed
4. Waits for VLC to display the video
5. Captures a snapshot from VLC

### System Requirements

- **Microsoft Excel** (2016 or later recommended)
- **Windows Operating System** (COM automation requires Windows)
- **Excel file** with video encoder macro/button
- **VLC Media Player** for video playback

---

## Finding Your Excel File

### Method 1: Search by Name

```cmd
# Search for Excel files in common locations
dir /s /b C:\*.xlsx | findstr /i "encoder"
dir /s /b C:\*.xlsx | findstr /i "spreader"
dir /s /b C:\*.xlsx | findstr /i "video"
```

### Method 2: Check Recent Files

1. Open File Explorer
2. Type in address bar: `%APPDATA%\Microsoft\Office\Recent`
3. Look for your video encoder Excel file
4. Right-click → "Open file location" to find the full path

### Method 3: Ask Your Team

The Excel file might be stored on:
- **Local drive:** `C:\VideoEncoder\spreader_encoder.xlsx`
- **Network drive:** `\\NetworkShare\VideoEncoder\spreader_encoder.xlsx`
- **Shared folder:** `C:\Users\Shared\VideoEncoder\spreader_encoder.xlsx`
- **Desktop:** `C:\Users\[YourUsername]\Desktop\spreader_encoder.xlsx`

### Common File Names

- `spreader_encoder.xlsx`
- `video_encoder.xlsx`
- `strad_carrier_encoder.xlsx`
- `camera_control.xlsx`
- `rtsp_encoder.xlsx`

---

## Configuring system_config.json

### File Location

```
c:\Users\Miles\Desktop\exp_2\system_config.json
```

### Configuration Field

The Excel file path is specified in the `excel_file_path` field.

### Path Format Requirements

**Important:** Use double backslashes (`\\`) in JSON!

```json
{
  "excel_file_path": "C:\\Path\\To\\Your\\File.xlsx"
}
```

**Why double backslashes?**
- Single backslash (`\`) is an escape character in JSON
- `\n` = newline, `\t` = tab, etc.
- To represent an actual backslash, use `\\`

---

### Configuration Examples

#### Example 1: File on C: Drive

```json
{
  "excel_file_path": "C:\\VideoEncoder\\spreader_encoder.xlsx"
}
```

**Path breakdown:**
- Drive: `C:`
- Folder: `VideoEncoder`
- File: `spreader_encoder.xlsx`

---

#### Example 2: File on Desktop

```json
{
  "excel_file_path": "C:\\Users\\Miles\\Desktop\\spreader_encoder.xlsx"
}
```

**Replace `Miles` with your Windows username!**

---

#### Example 3: File in Documents

```json
{
  "excel_file_path": "C:\\Users\\Miles\\Documents\\VideoEncoder\\spreader_encoder.xlsx"
}
```

---

#### Example 4: Network Drive (UNC Path)

```json
{
  "excel_file_path": "\\\\NetworkServer\\SharedFolder\\VideoEncoder\\spreader_encoder.xlsx"
}
```

**UNC path format:**
- Starts with `\\\\` (four backslashes in JSON)
- Server name
- Share name
- Folder path
- File name

---

#### Example 5: Mapped Network Drive

```json
{
  "excel_file_path": "Z:\\VideoEncoder\\spreader_encoder.xlsx"
}
```

**If you have a mapped network drive (e.g., Z:), you can use it directly.**

---

### Full system_config.json Example

```json
{
  "_comment_header": "===== STRAD CARRIER MONITORING AUTOMATION - SYSTEM CONFIGURATION =====",
  "_comment_instructions": "Update paths and connection strings for your environment before running",
  
  "_comment_database": "===== DATABASE CONFIGURATION =====",
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;Trusted_Connection=yes",
  
  "_comment_paths": "===== FILE PATHS =====",
  "_excel_instructions": "STEP 2: Update this path to your Excel video encoder file",
  "_excel_example_1": "Local file: C:\\\\VideoEncoder\\\\spreader_encoder.xlsx",
  "_excel_example_2": "Desktop: C:\\\\Users\\\\YourUsername\\\\Desktop\\\\spreader_encoder.xlsx",
  "_excel_example_3": "Network: \\\\\\\\Server\\\\Share\\\\VideoEncoder\\\\spreader_encoder.xlsx",
  "excel_file_path": "C:\\VideoEncoder\\spreader_encoder.xlsx",
  
  "_model_instructions": "STEP 3: Update this path to your DL model checkpoint",
  "model_checkpoint_path": "C:\\Models\\misalignment_detector_v2.pth",
  
  "_temp_snapshots_instructions": "STEP 4: Update temporary snapshot storage path",
  "temp_snapshot_path": "C:\\StradMonitoring\\temp_snapshots",
  
  "_permanent_snapshots_instructions": "STEP 5: Update permanent snapshot storage path (critical only)",
  "permanent_snapshot_path": "D:\\StradMonitoring\\critical_snapshots",
  
  "_log_instructions": "STEP 6: Update log file storage path",
  "log_file_path": "C:\\StradMonitoring\\logs",
  
  "_comment_timing": "===== TIMING CONFIGURATION =====",
  "cycle_schedule_cron": "0 * * * *",
  "strad_selection_count": 10,
  "cooldown_hours": 1,
  "classification_timeout_seconds": 10,
  
  "_comment_snapshot": "===== SNAPSHOT CONFIGURATION =====",
  "snapshot_min_width": 640,
  "snapshot_min_height": 480,
  "snapshot_retention_days": 30,
  "log_retention_days": 14,
  
  "_comment_fallback": "===== LOCAL TESTING FALLBACK CONFIGURATION =====",
  "enable_local_testing_mode": true,
  "use_sqlite_fallback": true,
  "sqlite_db_path": "tests/test.db",
  "fallback_data_source": "sqlite",
  "fallback_data_path": "C:\\test_data\\strad_list.csv",
  
  "_comment_dl_model": "===== DEEP LEARNING MODEL CONFIGURATION =====",
  "dl_model_config": {
    "flow_network": "liteflownet2",
    "target_resolution": [640, 640],
    "confidence_threshold": 0.5,
    "enable_uncertainty": false
  }
}
```

---

## Excel File Requirements

### Expected Excel Structure

The system expects an Excel file with:

1. **A cell for strad ID input**
   - Default: Cell `A1` or a named cell
   - The system writes the strad ID here (e.g., "SC042")

2. **A button or macro to trigger video**
   - Usually labeled "Open Video", "Load Feed", "Start Camera"
   - The system clicks this button programmatically

3. **Video encoder integration**
   - Excel macros/VBA code that:
     - Reads the strad ID from the cell
     - Looks up video feed URL
     - Opens VLC or another player
     - Starts streaming the video

### Example Excel Macro (VBA)

If you need to create or modify the Excel file, here's example VBA code:

```vba
Sub OpenVideoFeed()
    Dim stradID As String
    Dim videoURL As String
    Dim vlcPath As String
    
    ' Read strad ID from cell A1
    stradID = Range("A1").Value
    
    ' Validate strad ID format (SCXXX)
    If Not stradID Like "SC[0-9][0-9][0-9]" Then
        MsgBox "Invalid strad ID format. Expected SCXXX.", vbCritical
        Exit Sub
    End If
    
    ' Look up video URL (example - replace with your logic)
    videoURL = LookupVideoURL(stradID)
    
    ' Path to VLC player
    vlcPath = "C:\Program Files\VideoLAN\VLC\vlc.exe"
    
    ' Open VLC with video URL
    Shell vlcPath & " " & videoURL, vbNormalFocus
End Sub

Function LookupVideoURL(stradID As String) As String
    ' Example: Query database or lookup table
    ' Replace with your actual video URL logic
    Select Case stradID
        Case "SC001"
            LookupVideoURL = "rtsp://camera001.example.com/stream"
        Case "SC042"
            LookupVideoURL = "rtsp://camera042.example.com/stream"
        Case Else
            LookupVideoURL = "rtsp://default.example.com/stream"
    End Select
End Function
```

### Adding the Button

1. Open Excel file
2. Developer tab → Insert → Button (Form Control)
3. Draw button on spreadsheet
4. Assign macro: `OpenVideoFeed`
5. Label button: "Open Video Feed"
6. Save as `.xlsm` (macro-enabled) if using macros

---

## Testing the Configuration

### Test 1: Check File Exists

```cmd
# Windows Command Prompt
# Replace path with your excel_file_path value

# Test if file exists
if exist "C:\VideoEncoder\spreader_encoder.xlsx" (
    echo File found!
) else (
    echo File NOT found - check path!
)
```

### Test 2: Open File Manually

```cmd
# Try opening the file
start "" "C:\VideoEncoder\spreader_encoder.xlsx"
```

**Expected Result:**
- Excel opens
- File loads successfully
- You see the video encoder interface

### Test 3: Using Python Test Script

Save as `test_excel_config.py`:

```python
import os
import json
from pathlib import Path

# Load system config
config_path = "system_config.json"

if not os.path.exists(config_path):
    print(f"✗ Config file not found: {config_path}")
    exit(1)

with open(config_path, 'r') as f:
    config = json.load(f)

excel_path = config.get('excel_file_path', '')

print("=" * 60)
print("EXCEL FILE CONFIGURATION TEST")
print("=" * 60)
print()

# Test 1: Path configured
if not excel_path:
    print("✗ excel_file_path not configured in system_config.json")
    exit(1)
else:
    print(f"✓ excel_file_path configured: {excel_path}")

# Test 2: File exists
if not os.path.exists(excel_path):
    print(f"✗ Excel file NOT found at: {excel_path}")
    print()
    print("Troubleshooting:")
    print("1. Check the path is correct")
    print("2. Ensure file exists at that location")
    print("3. Check for typos in filename")
    print("4. Use double backslashes in JSON: C:\\\\Path\\\\To\\\\File.xlsx")
    exit(1)
else:
    print(f"✓ Excel file found")

# Test 3: File is Excel format
if not excel_path.lower().endswith(('.xlsx', '.xlsm', '.xls')):
    print(f"⚠ Warning: File doesn't have Excel extension")
    print(f"  Expected: .xlsx, .xlsm, or .xls")
    print(f"  Got: {Path(excel_path).suffix}")
else:
    print(f"✓ File has Excel extension: {Path(excel_path).suffix}")

# Test 4: File is readable
try:
    with open(excel_path, 'rb') as f:
        # Try reading first few bytes
        header = f.read(8)
    print(f"✓ File is readable")
except PermissionError:
    print(f"✗ Permission denied - cannot read file")
    print(f"  Check file permissions")
    exit(1)
except Exception as e:
    print(f"✗ Error reading file: {e}")
    exit(1)

# Test 5: Check file size
file_size = os.path.getsize(excel_path)
file_size_kb = file_size / 1024

if file_size == 0:
    print(f"✗ File is empty (0 bytes)")
    exit(1)
elif file_size < 1024:
    print(f"⚠ File is very small ({file_size} bytes) - might be corrupted")
else:
    print(f"✓ File size: {file_size_kb:.1f} KB")

print()
print("=" * 60)
print("✓ All tests passed!")
print("Excel file is properly configured and accessible")
print("=" * 60)
```

**Run the test:**
```cmd
python test_excel_config.py
```

**Expected output:**
```
============================================================
EXCEL FILE CONFIGURATION TEST
============================================================

✓ excel_file_path configured: C:\VideoEncoder\spreader_encoder.xlsx
✓ Excel file found
✓ File has Excel extension: .xlsx
✓ File is readable
✓ File size: 45.3 KB

============================================================
✓ All tests passed!
Excel file is properly configured and accessible
============================================================
```

---

### Test 4: Test Excel Automation

Save as `test_excel_automation.py`:

```python
import win32com.client
import os
import json

# Load config
with open('system_config.json', 'r') as f:
    config = json.load(f)

excel_path = config['excel_file_path']

print("Testing Excel COM automation...")
print(f"Excel file: {excel_path}")
print()

try:
    # Initialize Excel application
    print("1. Starting Excel application...")
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False  # Hidden mode
    print("✓ Excel application started")
    
    # Open workbook
    print(f"2. Opening workbook...")
    workbook = excel.Workbooks.Open(excel_path)
    print("✓ Workbook opened")
    
    # Get first sheet
    print("3. Accessing worksheet...")
    sheet = workbook.Sheets(1)
    print(f"✓ Worksheet accessed: {sheet.Name}")
    
    # Test writing to cell
    print("4. Testing cell write...")
    test_value = "SC042"
    sheet.Range("A1").Value = test_value
    read_value = sheet.Range("A1").Value
    
    if read_value == test_value:
        print(f"✓ Cell write successful: A1 = {read_value}")
    else:
        print(f"✗ Cell write failed: Expected {test_value}, got {read_value}")
    
    # Close without saving
    print("5. Closing workbook...")
    workbook.Close(SaveChanges=False)
    excel.Quit()
    print("✓ Workbook closed")
    
    print()
    print("=" * 60)
    print("✓ Excel automation test passed!")
    print("System can successfully open and control the Excel file")
    print("=" * 60)
    
except FileNotFoundError:
    print(f"✗ Excel file not found: {excel_path}")
except Exception as e:
    print(f"✗ Excel automation test failed: {e}")
    print()
    print("Possible causes:")
    print("1. Microsoft Excel not installed")
    print("2. pywin32 package not installed (pip install pywin32)")
    print("3. Excel file is corrupted")
    print("4. File is open in another program")
    print("5. Insufficient permissions")
```

**Run the test:**
```cmd
pip install pywin32
python test_excel_automation.py
```

---

## Troubleshooting

### Error: "FileNotFoundError: [Errno 2] No such file or directory"

**Cause:** File path is incorrect or file doesn't exist

**Solutions:**

1. **Check path spelling:**
   ```cmd
   # List files in directory
   dir "C:\VideoEncoder"
   ```

2. **Verify full path:**
   ```cmd
   # Right-click file in Explorer → Properties → Location
   # Combine Location + Name for full path
   ```

3. **Use absolute path (not relative):**
   ```json
   # ✗ Wrong (relative path)
   "excel_file_path": "..\\VideoEncoder\\file.xlsx"
   
   # ✓ Correct (absolute path)
   "excel_file_path": "C:\\VideoEncoder\\file.xlsx"
   ```

4. **Check for hidden extensions:**
   - File might be named `spreader_encoder.xlsx.xlsx`
   - Enable "File name extensions" in File Explorer
   - View tab → Show → File name extensions

---

### Error: "JSONDecodeError" when loading config

**Cause:** Single backslashes in path (invalid JSON)

**Wrong:**
```json
{
  "excel_file_path": "C:\VideoEncoder\file.xlsx"
}
```

**Correct:**
```json
{
  "excel_file_path": "C:\\VideoEncoder\\file.xlsx"
}
```

**Remember:** Use double backslashes (`\\`) in JSON!

---

### Error: "Permission denied" when accessing file

**Cause:** File is open or locked

**Solutions:**

1. **Close Excel if it's open:**
   ```cmd
   tasklist | findstr EXCEL
   taskkill /IM EXCEL.EXE /F
   ```

2. **Check file permissions:**
   - Right-click file → Properties → Security
   - Ensure your user has "Read" permission

3. **Run as Administrator:**
   - Right-click Python script
   - "Run as administrator"

---

### Error: "Excel.Application" not found (COM error)

**Cause:** Microsoft Excel not installed or not properly registered

**Solutions:**

1. **Verify Excel is installed:**
   ```cmd
   # Try opening Excel
   start excel
   ```

2. **Repair Office installation:**
   - Control Panel → Programs → Microsoft Office
   - Right-click → Change → Repair

3. **Re-register Excel:**
   ```cmd
   # Run as Administrator
   cd "C:\Program Files\Microsoft Office\Office16"
   excel.exe /regserver
   ```

---

### Warning: "Macros are disabled"

**Cause:** Excel security settings block macros

**Solutions:**

1. **Enable macros temporarily:**
   - Open Excel file manually
   - Yellow bar appears → "Enable Content"

2. **Add file to Trusted Locations:**
   - Excel → File → Options → Trust Center
   - Trust Center Settings → Trusted Locations
   - Add your VideoEncoder folder

3. **Change macro security:**
   - Excel → File → Options → Trust Center
   - Trust Center Settings → Macro Settings
   - Select "Enable all macros" (not recommended for general use)

---

## Quick Reference

### Path Format Checklist

✅ **Correct JSON path format:**
```json
"excel_file_path": "C:\\VideoEncoder\\spreader_encoder.xlsx"
```

❌ **Wrong formats:**
```json
"excel_file_path": "C:\VideoEncoder\spreader_encoder.xlsx"      # Single backslash
"excel_file_path": "C:/VideoEncoder/spreader_encoder.xlsx"      # Forward slash
"excel_file_path": "VideoEncoder\\spreader_encoder.xlsx"        # Relative path
"excel_file_path": "C:\\VideoEncoder\\file.xlsx.xlsx"           # Hidden extension
```

### Common File Locations

| Location Type | Example Path |
|--------------|--------------|
| Local drive | `C:\\VideoEncoder\\spreader_encoder.xlsx` |
| Desktop | `C:\\Users\\Username\\Desktop\\spreader_encoder.xlsx` |
| Documents | `C:\\Users\\Username\\Documents\\spreader_encoder.xlsx` |
| Shared folder | `C:\\Users\\Shared\\VideoEncoder\\spreader_encoder.xlsx` |
| Network drive | `\\\\Server\\Share\\VideoEncoder\\spreader_encoder.xlsx` |
| Mapped drive | `Z:\\VideoEncoder\\spreader_encoder.xlsx` |

### Testing Commands

```cmd
# Check file exists
if exist "C:\VideoEncoder\spreader_encoder.xlsx" echo Found

# Open file
start "" "C:\VideoEncoder\spreader_encoder.xlsx"

# List directory
dir "C:\VideoEncoder"

# Search for Excel files
dir /s /b C:\*.xlsx

# Test configuration
python test_excel_config.py

# Test Excel automation
python test_excel_automation.py
```

---

## Summary

**Steps to Configure:**

1. ✅ Locate your Excel video encoder file
2. ✅ Get the full file path (right-click → Properties)
3. ✅ Update `system_config.json` with path (use double backslashes!)
4. ✅ Test file exists (test_excel_config.py)
5. ✅ Test Excel automation (test_excel_automation.py)
6. ✅ Ensure Excel file has video encoder macro/button
7. ✅ Enable macros if needed

**Files to Edit:**
- `c:\Users\Miles\Desktop\exp_2\system_config.json` → `excel_file_path` field

**Test Scripts:**
- `test_excel_config.py` - Verify file path and existence
- `test_excel_automation.py` - Test Excel COM automation

**Common Issues:**
- Single backslashes in JSON (use `\\` not `\`)
- File path typos
- File doesn't exist at specified location
- Excel not installed
- Macros disabled in Excel

**Support:**
- See system_config.json for path examples
- Run test scripts to verify configuration
- Enable local testing mode if Excel unavailable
