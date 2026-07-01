@echo off
REM Creates a desktop shortcut for launch_all.bat
REM Run this once to create the clickable icon on your desktop.

set "PROJECT_DIR=%~dp0"
set "SHORTCUT=%USERPROFILE%\Desktop\Strad Monitoring.lnk"
set "TARGET=%PROJECT_DIR%launch_all.bat"
set "ICON=%SystemRoot%\System32\shell32.dll,23"

echo Creating desktop shortcut...

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%SHORTCUT%'); $sc.TargetPath = '%TARGET%'; $sc.WorkingDirectory = '%PROJECT_DIR%'; $sc.IconLocation = '%ICON%'; $sc.Description = 'Launch Strad Carrier Monitoring System + Web App'; $sc.Save()"

if exist "%SHORTCUT%" (
    echo.
    echo SUCCESS: Shortcut created on Desktop
    echo   Name: "Strad Monitoring"
    echo   Target: %TARGET%
    echo.
    echo Double-click it to launch the full system.
) else (
    echo.
    echo FAILED: Could not create shortcut.
    echo You can manually create one pointing to: %TARGET%
)

pause
