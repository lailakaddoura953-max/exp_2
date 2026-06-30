"""
Debug script to list all available macros in the Excel workbook
This will help us find the correct macro name and signature
"""

import win32com.client
import pythoncom

# Path to your Excel file
EXCEL_FILE = r"C:\KALMAR_SC_ad_TEL_CAMERAS_Frank_Copy.xlsm"

def list_excel_macros():
    """List all macros in the Excel workbook"""
    try:
        # Initialize COM
        pythoncom.CoInitialize()
        
        # Create Excel application
        excel_app = win32com.client.Dispatch("Excel.Application")
        excel_app.Visible = False
        excel_app.DisplayAlerts = False
        
        print("=" * 80)
        print("EXCEL MACRO INSPECTOR")
        print("=" * 80)
        print(f"Opening: {EXCEL_FILE}")
        print()
        
        # Open workbook
        workbook = excel_app.Workbooks.Open(EXCEL_FILE)
        
        # Get VBA project
        try:
            vb_project = workbook.VBProject
            print(f"VBA Project Name: {vb_project.Name}")
            print()
            
            # List all modules and their procedures
            print("=" * 80)
            print("VBA MODULES AND PROCEDURES")
            print("=" * 80)
            
            for component in vb_project.VBComponents:
                print(f"\n[MODULE: {component.Name}] (Type: {component.Type})")
                print("-" * 80)
                
                try:
                    code_module = component.CodeModule
                    line_count = code_module.CountOfLines
                    
                    if line_count > 0:
                        # Get all code
                        code = code_module.Lines(1, line_count)
                        
                        # Look for Sub and Function declarations
                        lines = code.split('\n')
                        for i, line in enumerate(lines, 1):
                            line_stripped = line.strip()
                            if (line_stripped.startswith('Sub ') or 
                                line_stripped.startswith('Public Sub ') or
                                line_stripped.startswith('Private Sub ') or
                                line_stripped.startswith('Function ') or
                                line_stripped.startswith('Public Function ') or
                                line_stripped.startswith('Private Function ')):
                                print(f"  Line {i}: {line_stripped[:100]}")
                    else:
                        print("  (Empty module)")
                        
                except Exception as e:
                    print(f"  Error reading module: {e}")
            
        except Exception as e:
            print(f"ERROR: Cannot access VBA project: {e}")
            print("\nThis usually means:")
            print("1. Trust access to VBA project is disabled")
            print("2. Excel security settings block VBA inspection")
            print("\nTo fix:")
            print("- Excel → File → Options → Trust Center → Trust Center Settings")
            print("- Macro Settings → Enable 'Trust access to the VBA project object model'")
        
        print("\n" + "=" * 80)
        print("TESTING MACRO EXECUTION")
        print("=" * 80)
        
        # Try to call the macro with different approaches
        test_names = [
            "OPEN_CAMERAS",
            "open_cameras", 
            "OpenCameras",
            "Sheet1.OPEN_CAMERAS",
            f"'{workbook.Name}'!OPEN_CAMERAS"
        ]
        
        for macro_name in test_names:
            try:
                print(f"\nTrying: excel_app.Run('{macro_name}')")
                # Don't actually run it, just see if it exists
                # (We can't run it without the InputBox automation)
                print(f"  → Would need to handle InputBox for actual execution")
            except Exception as e:
                print(f"  → Error: {e}")
        
        # Close workbook
        workbook.Close(SaveChanges=False)
        excel_app.Quit()
        
        print("\n" + "=" * 80)
        print("INSPECTION COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass


if __name__ == "__main__":
    list_excel_macros()
