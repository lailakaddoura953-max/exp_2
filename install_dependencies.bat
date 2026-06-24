@echo off
REM =============================================================================
REM Dependency Installation Script for Deep Learning Misalignment Detection
REM =============================================================================
REM This batch script installs all required Python dependencies for the system.
REM It handles both production and development dependencies.
REM
REM Usage:
REM   install_dependencies.bat [dev]
REM
REM   Without arguments: Installs production dependencies only
REM   With 'dev' argument: Installs both production and development dependencies
REM =============================================================================

echo ================================================================================
echo  Deep Learning Misalignment Detection System - Dependency Installation
echo ================================================================================
echo.

REM Check if virtual environment exists
if not exist ".venv\" (
    echo ERROR: Virtual environment not found at .venv
    echo Please create one first:
    echo   python -m venv .venv
    echo.
    exit /b 1
)

echo Using virtual environment: .venv
echo.

REM Step 1: Upgrade pip, setuptools, wheel
echo [Step 1/4] Upgrading pip, setuptools, and wheel...
echo.
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip
    exit /b 1
)
echo.

REM Step 2: Install PyTorch with CUDA support
echo [Step 2/4] Installing PyTorch with CUDA 12.1 support...
echo This may take several minutes depending on your internet connection...
echo.
.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 (
    echo.
    echo WARNING: Failed to install PyTorch with CUDA 12.1
    echo Trying with CUDA 11.8...
    echo.
    .venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
    if errorlevel 1 (
        echo.
        echo WARNING: Failed to install PyTorch with CUDA 11.8
        echo Falling back to CPU-only version...
        echo NOTE: Training will be VERY slow without GPU acceleration
        echo.
        .venv\Scripts\python.exe -m pip install torch torchvision
        if errorlevel 1 (
            echo ERROR: Failed to install PyTorch
            exit /b 1
        )
    )
)
echo.

REM Step 3: Install other production dependencies
echo [Step 3/4] Installing other production dependencies...
echo.
.venv\Scripts\python.exe -m pip install PyYAML>=6.0 tensorboard>=2.13.0 numpy>=1.24.0 opencv-python>=4.8.0 Pillow>=10.0.0 psutil>=5.9.0
if errorlevel 1 (
    echo ERROR: Failed to install production dependencies
    exit /b 1
)
echo.

REM Step 4: Install development dependencies if requested
if "%1"=="dev" (
    echo [Step 4/4] Installing development dependencies...
    echo.
    .venv\Scripts\python.exe -m pip install pytest>=7.4.0 pytest-cov>=4.1.0 pytest-xdist>=3.3.0 pytest-timeout>=2.1.0 black>=23.7.0 flake8>=6.1.0 mypy>=1.5.0 isort>=5.12.0
    if errorlevel 1 (
        echo WARNING: Some development dependencies failed to install
        echo This is not critical for production use
    )
    echo.
) else (
    echo [Step 4/4] Skipping development dependencies (use 'install_dependencies.bat dev' to install them)
    echo.
)

echo ================================================================================
echo  Installation Complete!
echo ================================================================================
echo.
echo Next steps:
echo   1. Verify CUDA availability:
echo      .venv\Scripts\python.exe verify_cuda.py
echo.
echo   2. Run tests (if dev dependencies installed):
echo      .venv\Scripts\python.exe -m pytest tests/
echo.
echo   3. Start training:
echo      .venv\Scripts\python.exe scripts/train_architecture_a.py
echo.
echo ================================================================================
