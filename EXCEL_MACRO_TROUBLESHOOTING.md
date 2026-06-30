# Excel Macro Troubleshooting Guide

**Problem**: Excel automation fails with "Macro execution error" and "InputBox dialog not found"

**Date**: 2024-12-29

---

## Quick Diagnosis: Run These Tests

### Test 1: Verify Macro Works Manually

```bash
# On deployment machine
cd c:\source\repos\cv_strad
```

1. Open `C:\KALMAR_SC_ad_TEL_CAMERAS_Frank_Copy.xlsm` in Excel
2. Click the "Spreader Video Encoder" button
3. Type "SC001" in the InputBox
4. Observe result:
   - ✅ **VLC opens**: Macro works, automation issue
   - ❌ **Error message**: VBA code has errors
   - ❌ **Nothing happens**: Strad ID invalid or VBA logic issue

### Test 2: Find Actual Macro Name

```bash
python debug_excel_macros.py
```

This script will:
- List all VBA modules in the Excel file
- Show all Sub and Function procedures
- Try different macro calling patterns

**Look for**:
- A procedure named `OPEN_CAMERAS` or similar
- The module it's in (e.g., `Sheet1`, `Module1`, etc.)
- Any parameters it requires

### Test 3: Manual InputBox Automation Test

```bash
python test_manual_macro.py
```

This script will:
1. Open Excel (visible)
2. Wait for you to manually click the button
3. Attempt to automate the InputBox that appears
4. Show what window titles exist

**This isolates whether the issue is:**
- **Macro calling** (can't run the macro)
- **InputBox detection** (can't find the dialog)
- **Keystroke automation** (can't send keys)

---

## Common Issues and Fixes

### Issue 1: Macro Name Doesn't Match

**Symptoms:**
```
ERROR: macro execution error: Excel.Application.Run
```

**Causes:**
- Macro is named differently (e.g., `OpenCameras`, `OPEN_CAMERA`, `open_cameras`)
- Macro requires full path (e.g., `Sheet1.OPEN_CAMERAS`)

**Fix:**
1. Run `debug_excel_macros.py` to find the actual name
2. Update `excel_automation.py` line ~340:
   ```python
   self.excel_app.Run("ACTUAL_MACRO_NAME")
   ```

The updated code now tries 4 different calling patterns automatically:
- `OPEN_CAMERAS` (simple)
- `'workbook.xlsm'!OPEN_CAMERAS` (with workbook)
- `Sheet1.OPEN_CAMERAS` (with module)
- `open_cameras` (lowercase)

### Issue 2: InputBox Window Title Different

**Symptoms:**
```
ERROR: InputBox dialog not found within timeout
```

**Causes:**
- InputBox title isn't "Enter SC #"
- Excel shows different dialog (security warning, etc.)

**Fix:**
1. Run `test_manual_macro.py`
2. Look at the list of all windows it shows
3. Find your InputBox title
4. Update `excel_automation.py` line ~365:
   ```python
   hwnd = win32gui.FindWindow(None, "ACTUAL_TITLE_HERE")
   ```

### Issue 3: Macro Requires Parameters

**Symptoms:**
- Macro runs but immediately exits
- No InputBox appears
- VBA error

**Causes:**
- Macro signature is: `Sub OPEN_CAMERAS(stradId As String)`
- We're calling it without parameters

**Fix:**
Update the macro call to pass the strad ID:
```python
self.excel_app.Run("OPEN_CAMERAS", strad_id)
```

**Note**: This would be the BEST outcome - means we can skip InputBox entirely!

### Issue 4: Excel Security Blocks Macro

**Symptoms:**
- Nothing happens when macro is called
- No errors, no InputBox

**Causes:**
- Macro security set to "Disable all macros"
- File not in trusted location

**Fix:**
1. Excel → File → Options → Trust Center → Trust Center Settings
2. Macro Settings → Select "Enable all macros" (temporary for testing)
3. OR add file location to Trusted Locations

### Issue 5: VBA Project Access Denied

**Symptoms:**
```
ERROR: Cannot access VBA project: ...
```

**Causes:**
- Trust access to VBA project object model is disabled

**Fix:**
1. Excel → File → Options → Trust Center → Trust Center Settings
2. Macro Settings → Check "Trust access to the VBA project object model"
3. Click OK and restart Excel

---

## Advanced Diagnostics

### Check If Excel Opens at All

```python
import win32com.client
import pythoncom

pythoncom.CoInitialize()
excel_app = win32com.client.Dispatch("Excel.Application")
excel_app.Visible = True
print(f"Excel version: {excel_app.Version}")
wb = excel_app.Workbooks.Open(r"C:\KALMAR_SC_ad_TEL_CAMERAS_Frank_Copy.xlsm")
print(f"Workbook name: {wb.Name}")
input("Press Enter to close...")
wb.Close(SaveChanges=False)
excel_app.Quit()
pythoncom.CoUninitialize()
```

### List All Available Macros

```python
import win32com.client
import pythoncom

pythoncom.CoInitialize()
excel_app = win32com.client.Dispatch("Excel.Application")
wb = excel_app.Workbooks.Open(r"C:\KALMAR_SC_ad_TEL_CAMERAS_Frank_Copy.xlsm")

# Try to list macros
try:
    vb_project = wb.VBProject
    for component in vb_project.VBComponents:
        print(f"Module: {component.Name}")
except Exception as e:
    print(f"Can't access VBA project: {e}")

wb.Close(SaveChanges=False)
excel_app.Quit()
pythoncom.CoUninitialize()
```

### Find Window by Partial Title

```python
import win32gui

def find_windows_with_text(search_text):
    """Find all windows containing search_text in title"""
    results = []
    
    def callback(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if search_text.lower() in title.lower():
                results.append((hwnd, title))
        return True
    
    win32gui.EnumWindows(callback, None)
    return results

# Usage
windows = find_windows_with_text("Enter")
for hwnd, title in windows:
    print(f"HWND {hwnd}: {title}")
```

---

## Timing Adjustments

If the macro is slow to execute, increase delays in `excel_automation.py`:

```python
# Line ~355: Wait longer for InputBox
time.sleep(2.0)  # Increase to 3.0 or 5.0 if needed

# Line ~358: More attempts
max_attempts = 20  # Increase to 30 or 40 if needed

# Line ~369: Wait longer after finding window
time.sleep(0.3)  # Increase to 0.5 or 1.0 if needed

# Line ~374: Wait longer before pressing Enter
time.sleep(0.2)  # Increase to 0.5 if needed
```

---

## Alternative: Skip InputBox Entirely

If we can modify the VBA macro to accept parameters (even if we can't edit it permanently):

### Option A: VBA Macro Accepts Parameter

If the macro signature is already:
```vba
Sub OPEN_CAMERAS(Optional stradId As String = "")
```

Then we can call it with:
```python
self.excel_app.Run("OPEN_CAMERAS", "SC001")
```

And the InputBox is skipped!

### Option B: Use Excel Formula to Trigger

Instead of calling macro, set a cell value that triggers the macro:
```python
worksheet = self.workbook.ActiveSheet
worksheet.Range("A1").Value = "SC001"  # Trigger cell
worksheet.Calculate()  # Force recalc
```

### Option C: Click Button Programmatically

If the button is a Shape/Form Control:
```python
worksheet = self.workbook.ActiveSheet
shapes = worksheet.Shapes

for shape in shapes:
    if "spreader video encoder" in shape.Name.lower():
        # Simulate click
        shape.OnAction  # Get macro it runs
        # Then automate InputBox as before
```

---

## Success Criteria

✅ **Macro is called successfully**
✅ **InputBox appears**
✅ **Text is typed into InputBox**
✅ **Enter is pressed**
✅ **VLC window opens**
✅ **Snapshot is captured**

Each step logs to console. Track which step fails to narrow down the issue.

---

## Contact

If none of these diagnostics help, provide:
1. Output from `debug_excel_macros.py`
2. Output from `test_manual_macro.py`
3. Screenshot of Excel VBA editor showing the macro
4. Full error log from `test_orchestrator_single.py`

This will allow pinpointing the exact issue.
