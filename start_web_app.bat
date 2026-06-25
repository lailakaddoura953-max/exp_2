@echo off
REM ============================================================================
REM Strad Carrier Monitoring - Web App Launcher
REM ============================================================================
REM This script starts the Flask backend server and opens the web app
REM ============================================================================

echo.
echo ================================================================================
echo STRAD CARRIER MONITORING - WEB APP LAUNCHER
echo ================================================================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please create it first with: python -m venv .venv
    echo Then install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if backend dependencies are installed
python -c "import flask" 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Flask not installed
    echo Installing backend dependencies...
    pip install flask flask-cors numpy pillow
)

REM Start backend server in a new window
echo.
echo Starting Flask backend server (port 5000)...
echo Backend will run in a separate window
echo.
start "Strad Monitoring Backend (Port 5000)" cmd /k "call .venv\Scripts\activate.bat && python docs\backend\app.py"

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start frontend server in a new window
echo.
echo Starting frontend server (port 8000)...
echo Frontend will run in a separate window
echo.
start "Strad Monitoring Frontend (Port 8000)" cmd /k "call .venv\Scripts\activate.bat && python start_frontend_server.py"

REM Wait for both servers to start
echo.
echo Waiting for servers to start...
timeout /t 5 /nobreak >nul

REM Open web app in default browser
echo.
echo Opening web app in browser...
start http://localhost:8000

echo.
echo ================================================================================
echo WEB APP STARTED
echo ================================================================================
echo.
echo Backend server (port 5000): Running in separate window
echo Frontend server (port 8000): Running in separate window
echo Web app URL: http://localhost:8000
echo.
echo WINDOWS OPEN:
echo   1. This window (launcher)
echo   2. Backend server window (port 5000)
echo   3. Frontend server window (port 8000)
echo   4. Browser with web app
echo.
echo TO STOP:
echo   1. Close the browser
echo   2. Close backend server window (or press Ctrl+C)
echo   3. Close frontend server window (or press Ctrl+C)
echo.
echo TO TEST:
echo   - Check connection status in top right corner
echo   - Green dot (●) = Backend connected, real data mode
echo   - Red dot (○) = Disconnected, demo mode
echo   - Click "View Demo" buttons to play videos
echo   - Scroll down to test live inference with image upload
echo.
echo ================================================================================
echo.
pause
