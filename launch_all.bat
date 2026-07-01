@echo off
REM ============================================================================
REM Strad Carrier Monitoring - Full System Launcher
REM ============================================================================
REM Starts the Monitoring Orchestrator + Web App together.
REM Double-click this file (or the desktop shortcut) to launch everything.
REM ============================================================================

echo.
echo ================================================================================
echo STRAD CARRIER MONITORING - FULL SYSTEM LAUNCHER
echo ================================================================================
echo.

REM Get the directory this script lives in (project root)
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found at .venv\
    echo Please create it first with: python -m venv .venv
    echo Then install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

REM ============================================================================
REM Step 1: Start Monitoring Orchestrator
REM ============================================================================
echo [1/2] Starting Monitoring Orchestrator...
echo       (Runs hourly cycles, captures screenshots, classifies strads)
echo.
start "Strad Monitoring Orchestrator" cmd /k "cd /d "%PROJECT_DIR%" && call .venv\Scripts\activate.bat && python -m src.strad_monitoring.main"

REM Give the orchestrator a moment to initialize
timeout /t 3 /nobreak >nul

REM ============================================================================
REM Step 2: Start Web App (Backend + Frontend + Browser)
REM ============================================================================
echo [2/2] Starting Web App...
echo       (Flask backend on port 5000, frontend on port 8000)
echo.
call start_web_app.bat

echo.
echo ================================================================================
echo ALL SYSTEMS LAUNCHED
echo ================================================================================
echo.
echo Running:
echo   1. Monitoring Orchestrator (separate window)
echo      - Selects strads from database
echo      - Captures screenshots via headless browser
echo      - Classifies images with DL model
echo      - Stores results in local state
echo.
echo   2. Web App Backend (port 5000, separate window)
echo      - Serves API for live monitoring data
echo      - Reads from monitoring_state.json + SCFootage
echo.
echo   3. Web App Frontend (port 8000, separate window)
echo      - Dashboard with live image feed
echo      - Open in browser: http://localhost:8000
echo.
echo TO STOP EVERYTHING:
echo   Close all terminal windows, or press Ctrl+C in each.
echo.
echo ================================================================================
pause
