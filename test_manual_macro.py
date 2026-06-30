"""
Manual test: Open Excel, wait for you to manually click the button,
then try to automate the InputBox that appears.

This tests if the InputBox automation part works, separate from macro calling.
"""

import win32com.client
import win32gui
import pythoncom
import time

EXCEL_FILE = r"C:\KALMAR_SC_ad_TEL_CAMERAS_Frank_Copy.xlsm"

def test_manual_inputbox():
    """Open Excel and wait for manual button click to test InputBox automation"""
    
    try:
        pythoncom.CoInitialize()
        
        excel_app = win32com.client.Dispatch("Excel.Application")
        excel_app.Visible = True  # Make it visible so you can click
        excel_app.DisplayAlerts = False
        
        print("=" * 80)
        print("MANUAL INPUTBOX AUTOMATION TEST")
        print("=" * 80)
        print()
        print("Excel is now open and visible.")
        print()
        print("INSTRUCTIONS:")
        print("1. Locate the 'Spreader Video Encoder' button in the Excel file")
        print("2. Click it manually")
        print("3. When the InputBox appears, DON'T TYPE ANYTHING")
        print("4. Press Enter in this console window")
        print("5. Watch as the script attempts to automate the InputBox")
        print()
        
        workbook = excel_app.Workbooks.Open(EXCEL_FILE)
        
        input("Press Enter AFTER you've clicked the button and the InputBox is visible...")
        
        print("\nSearching for InputBox dialog...")
        
        # Try to find the InputBox
        input_box_found = False
        max_attempts = 10
        
        for attempt in range(max_attempts):
            print(f"  Attempt {attempt + 1}/{max_attempts}...")
            
            # Try different possible window titles
            possible_titles = [
                "Enter SC #",
                "Microsoft Excel",
                "Enter SC#",
                "Enter the strad in the format: SC001"
            ]
            
            for title in possible_titles:
                hwnd = win32gui.FindWindow(None, title)
                if hwnd:
                    print(f"  ✓ Found window with title: '{title}' (HWND: {hwnd})")
                    input_box_found = True
                    
                    # Try to automate it
                    print(f"\n  Attempting to send keystrokes...")
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.3)
                    
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shell.SendKeys("SC001", 0)
                    time.sleep(0.2)
                    shell.SendKeys("{ENTER}", 0)
                    
                    print(f"  ✓ Sent 'SC001' and Enter key")
                    break
            
            if input_box_found:
                break
            
            time.sleep(0.5)
        
        if not input_box_found:
            print("\n  ✗ InputBox not found with any expected title")
            print("\n  Let's enumerate ALL windows to find it:")
            print("  " + "=" * 76)
            
            def enum_windows_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:  # Only show windows with titles
                        results.append((hwnd, title))
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            for hwnd, title in windows:
                print(f"    HWND {hwnd}: {title}")
            
            print("  " + "=" * 76)
            print("\n  Look for your InputBox in the list above!")
        else:
            # Wait a bit and check if VLC opened
            print("\nWaiting for VLC window...")
            time.sleep(3)
            
            vlc_hwnd = win32gui.FindWindow("Qt5QWindowIcon", None)
            if not vlc_hwnd:
                vlc_hwnd = win32gui.FindWindow(None, "VLC media player")
            
            if vlc_hwnd:
                print(f"  ✓ VLC window found! (HWND: {vlc_hwnd})")
                print("\n✓ InputBox automation WORKS!")
            else:
                print(f"  ✗ VLC window not found")
                print("\nInputBox was automated, but VLC didn't open.")
                print("This suggests:")
                print("  - Wrong strad ID (SC001 doesn't exist)")
                print("  - VBA macro has an error")
                print("  - VLC path is wrong in macro")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print("\nClosing Excel in 5 seconds...")
        time.sleep(5)
        
        workbook.Close(SaveChanges=False)
        excel_app.Quit()
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass


if __name__ == "__main__":
    test_manual_inputbox()
