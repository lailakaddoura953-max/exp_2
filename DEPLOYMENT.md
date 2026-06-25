# Strad Carrier Monitoring Automation - Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [Database Setup](#database-setup)
6. [Windows Service Installation](#windows-service-installation)
7. [Running the System](#running-the-system)
8. [Troubleshooting](#troubleshooting)
9. [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## Overview

The Strad Carrier Monitoring Automation system integrates deep learning camera misalignment detection with SQL Server database operations, Excel-based video feed automation, and VLC media player snapshot capture. The system automatically executes monitoring cycles every hour, processing 10 randomly selected Strad Carriers from a pool of 135 units.

### Key Features

- **Automated Monitoring**: Hourly cycles of 10 Strad Carrier units
- **Deep Learning Classification**: Camera misalignment detection using PyTorch models
- **Database Integration**: SQL Server connectivity with fallback support
- **Excel Automation**: COM-based video encoder control
- **Graceful Shutdown**: Signal handling with completion wait
- **Comprehensive Logging**: Daily log rotation with 14-day retention

---

## System Requirements

### Hardware Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **CPU** | Intel i5/AMD Ryzen 5 or better | Multi-core for parallel processing |
| **RAM** | 16GB minimum | 8GB for DL models, 8GB for system |
| **GPU** | NVIDIA GPU with 4GB+ VRAM | CUDA 11.7+ required for inference |
| **Storage** | 100GB+ free space | For snapshots, logs, and models |
| **Network** | 1Gbps Ethernet | SQL Server and video encoder access |

### Software Requirements

| Software | Version | Required |
|----------|---------|----------|
| **OS** | Windows 10/11 | ✓ (COM automation requires Windows) |
| **Python** | 3.10 or 3.11 | ✓ |
| **CUDA** | 11.7 or higher | ✓ (for GPU inference) |
| **SQL Server** | 2016+ | ✓ (or SQLite fallback) |
| **Microsoft Excel** | 2016+ | ✓ (for video encoder control) |
| **VLC Media Player** | 3.0+ | ✓ (for video capture) |
| **ODBC Driver 17** | Latest | ✓ (for SQL Server connectivity) |

---

## Installation Steps

### Step 1: Install Python 3.10 or 3.11

1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer with these options:
   - ✓ Add Python to PATH
   - ✓ Install pip
   - ✓ Install for all users (optional)
3. Verify installation:
   ```cmd
   python --version
   pip --version
   ```

### Step 2: Install NVIDIA GPU Drivers and CUDA

1. **Check GPU Compatibility**:
   ```cmd
   nvidia-smi
   ```
   This command should display your GPU information.

2. **Install CUDA Toolkit 11.7+**:
   - Download from [NVIDIA CUDA Downloads](https://developer.nvidia.com/cuda-downloads)
   - Run the installer and follow the wizard
   - Select "Express Installation" for default options

3. **Verify CUDA Installation**:
   ```cmd
   nvcc --version
   ```

4. **Test PyTorch CUDA Support** (after installing requirements):
   ```cmd
   python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'CUDA Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
   ```

### Step 3: Install ODBC Driver 17 for SQL Server

1. Download from [Microsoft ODBC Driver Download](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
2. Run `msodbcsql.msi` installer
3. Accept license agreement and install
4. Verify installation:
   ```cmd
   python -c "import pyodbc; print(pyodbc.drivers())"
   ```
   You should see `ODBC Driver 17 for SQL Server` in the output.

### Step 4: Install Microsoft Excel

If not already installed:
1. Install Microsoft Office with Excel
2. Ensure Excel is activated and working
3. Test COM automation:
   ```cmd
   python -c "import win32com.client; excel = win32com.client.Dispatch('Excel.Application'); print(f'Excel Version: {excel.Version}'); excel.Quit()"
   ```

### Step 5: Install VLC Media Player

1. Download VLC from [videolan.org](https://www.videolan.org/vlc/)
2. Run the installer (use default installation path)
3. Verify VLC is installed:
   ```cmd
   "C:\Program Files\VideoLAN\VLC\vlc.exe" --version
   ```

### Step 6: Clone Repository and Install Python Dependencies

1. **Clone or extract the project**:
   ```cmd
   cd C:\
   git clone <repository-url> StradMonitoring
   cd StradMonitoring
   ```
   Or extract the project ZIP file to `C:\StradMonitoring`

2. **Create a virtual environment** (recommended):
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```cmd
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Verify installation**:
   ```cmd
   python -c "import torch, pyodbc, win32com.client, pyautogui; print('All packages imported successfully')"
   ```

---

## Configuration

### Step 1: Create Configuration File

Create a file named `system_config.json` in the project root directory with the following structure:

```json
{
  "_comment_database": "===== DATABASE CONFIGURATION =====",
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=your-server.company.local;DATABASE=StradMonitoring;Trusted_Connection=yes",
  
  "_comment_paths": "===== FILE PATHS =====",
  "excel_file_path": "C:\\VideoEncoder\\spreader_encoder.xlsx",
  "model_checkpoint_path": "C:\\StradMonitoring\\models\\misalignment_detector_v2.pth",
  "temp_snapshot_path": "C:\\StradMonitoring\\temp_snapshots",
  "permanent_snapshot_path": "D:\\StradMonitoring\\critical_snapshots",
  "log_file_path": "C:\\StradMonitoring\\logs",
  
  "_comment_scheduling": "===== SCHEDULING CONFIGURATION =====",
  "cycle_schedule_cron": "0 * * * *",
  "strad_selection_count": 10,
  "cooldown_hours": 1,
  
  "_comment_thresholds": "===== DETECTION THRESHOLDS =====",
  "snapshot_min_width": 640,
  "snapshot_min_height": 480,
  "classification_timeout_seconds": 10,
  
  "_comment_retention": "===== RETENTION POLICIES =====",
  "snapshot_retention_days": 30,
  "log_retention_days": 14,
  
  "_comment_fallback": "===== LOCAL TESTING FALLBACK CONFIGURATION =====",
  "enable_local_testing_mode": true,
  "fallback_data_path": "C:\\test_data\\strad_list.csv",
  "fallback_data_source": "local_folder",
  "_fallback_options": "Valid fallback_data_source values: 'kitti', 'local_folder', 'random'",
  "_fallback_note": "When SQL Server is unavailable, system uses this configuration for local testing",
  
  "_comment_model": "===== DEEP LEARNING MODEL CONFIGURATION =====",
  "dl_model_config": {
    "flow_network": "liteflownet2",
    "target_resolution": [640, 640],
    "confidence_threshold": 0.5,
    "enable_uncertainty": false
  }
}
```

### Step 2: Update Configuration Values

Update the following values in `system_config.json`:

1. **Database Connection String**:
   ```json
   "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=your-server;DATABASE=StradMonitoring;Trusted_Connection=yes"
   ```
   - Replace `your-server` with your SQL Server hostname
   - Use `Trusted_Connection=yes` for Windows authentication
   - Or use `UID=username;PWD=password` for SQL Server authentication

2. **Excel File Path**:
   ```json
   "excel_file_path": "C:\\Path\\To\\Your\\spreader_encoder.xlsx"
   ```
   - Update with the actual path to your Excel video encoder file

3. **Model Checkpoint Path**:
   ```json
   "model_checkpoint_path": "C:\\StradMonitoring\\models\\misalignment_detector_v2.pth"
   ```
   - Update with the path to your trained model checkpoint

4. **Storage Paths**:
   ```json
   "temp_snapshot_path": "C:\\StradMonitoring\\temp_snapshots",
   "permanent_snapshot_path": "D:\\StradMonitoring\\critical_snapshots",
   "log_file_path": "C:\\StradMonitoring\\logs"
   ```
   - Ensure these directories exist or will be created by the system
   - Use a separate drive (D:) for permanent snapshots if possible

### Step 3: Create Required Directories

```cmd
mkdir C:\StradMonitoring\temp_snapshots
mkdir D:\StradMonitoring\critical_snapshots
mkdir C:\StradMonitoring\logs
mkdir C:\StradMonitoring\models
```

### Step 4: Place Model Checkpoint

Copy your trained model checkpoint to the configured path:
```cmd
copy path\to\your\model.pth C:\StradMonitoring\models\misalignment_detector_v2.pth
```

---

## Database Setup

### Step 1: Create Database

Connect to your SQL Server instance and create the monitoring database:

```sql
-- Create database
CREATE DATABASE StradMonitoring;
GO

USE StradMonitoring;
GO
```

### Step 2: Create Required Tables

Execute the following SQL scripts to create the required tables:

```sql
-- ================================================================
-- Table: strad_action_check_by_id_and_timestamp
-- Purpose: Tracks when each strad was last checked
-- ================================================================
CREATE TABLE strad_action_check_by_id_and_timestamp (
    strad_id VARCHAR(10) PRIMARY KEY,  -- Format: SCXXX (e.g., SC001)
    last_check_timestamp DATETIME2 NOT NULL,
    INDEX idx_last_check (last_check_timestamp)
);
GO

-- ================================================================
-- Table: classification_results
-- Purpose: Stores classification outcomes
-- ================================================================
CREATE TABLE classification_results (
    id INT IDENTITY(1,1) PRIMARY KEY,
    strad_id VARCHAR(10) NOT NULL,
    classification VARCHAR(20) NOT NULL,  -- 'none', 'moderate', 'critical'
    confidence FLOAT NOT NULL,
    snapshot_path VARCHAR(500),
    created_at DATETIME2 DEFAULT GETDATE(),
    INDEX idx_strad_created (strad_id, created_at)
);
GO

-- ================================================================
-- Table: critical_strad_exclusions
-- Purpose: Tracks strads excluded from rotation due to critical classification
-- ================================================================
CREATE TABLE critical_strad_exclusions (
    strad_id VARCHAR(10) PRIMARY KEY,
    added_at DATETIME2 DEFAULT GETDATE(),
    adjustment_confirmed_at DATETIME2 NULL,
    technician_id VARCHAR(50) NULL
);
GO

-- ================================================================
-- Table: adjustment_confirmations
-- Purpose: Records when critical strads have been adjusted
-- ================================================================
CREATE TABLE adjustment_confirmations (
    id INT IDENTITY(1,1) PRIMARY KEY,
    strad_id VARCHAR(10) NOT NULL,
    technician_id VARCHAR(50) NOT NULL,
    confirmation_timestamp DATETIME2 DEFAULT GETDATE(),
    notes VARCHAR(500) NULL,
    INDEX idx_strad_timestamp (strad_id, confirmation_timestamp)
);
GO
```

### Step 3: Create Stored Procedure (Optional)

If using the stored procedure approach for strad selection:

```sql
-- ================================================================
-- Stored Procedure: strad_action_check_by_id_and_timestamp
-- Purpose: Query eligible strads for monitoring cycle
-- ================================================================
CREATE PROCEDURE strad_action_check_by_id_and_timestamp
    @count INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Select strads that:
    -- 1. Have not been checked in the last hour
    -- 2. Are not in the critical exclusion list
    -- 3. Return up to @count strads
    
    SELECT TOP (@count) strad_id
    FROM strad_action_check_by_id_and_timestamp
    WHERE 
        -- Not checked in last hour
        DATEDIFF(MINUTE, last_check_timestamp, GETDATE()) >= 60
        -- Not in critical exclusion list
        AND strad_id NOT IN (SELECT strad_id FROM critical_strad_exclusions)
    ORDER BY NEWID()  -- Random selection
END
GO
```

### Step 4: Initialize Strad Data

Populate the check history table with initial strad IDs:

```sql
-- Initialize all 135 strads with old timestamp to make them eligible
DECLARE @i INT = 1;
WHILE @i <= 135
BEGIN
    INSERT INTO strad_action_check_by_id_and_timestamp (strad_id, last_check_timestamp)
    VALUES (
        'SC' + RIGHT('000' + CAST(@i AS VARCHAR(3)), 3),
        DATEADD(HOUR, -2, GETDATE())  -- Set to 2 hours ago (eligible)
    );
    SET @i = @i + 1;
END
GO
```

### Step 5: Grant Permissions

Grant appropriate permissions to the application user:

```sql
-- Create application user (if using SQL Server authentication)
CREATE LOGIN StradMonitoringApp WITH PASSWORD = 'YourSecurePassword123!';
GO

USE StradMonitoring;
GO

CREATE USER StradMonitoringApp FOR LOGIN StradMonitoringApp;
GO

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON strad_action_check_by_id_and_timestamp TO StradMonitoringApp;
GRANT SELECT, INSERT ON classification_results TO StradMonitoringApp;
GRANT SELECT, INSERT, DELETE ON critical_strad_exclusions TO StradMonitoringApp;
GRANT SELECT, INSERT ON adjustment_confirmations TO StradMonitoringApp;
GRANT EXECUTE ON strad_action_check_by_id_and_timestamp TO StradMonitoringApp;
GO
```

### SQLite Fallback (Optional - for Local Testing)

The system includes SQLite fallback support for local testing when SQL Server is unavailable. No additional setup is required - the system will automatically create the SQLite database if enabled in configuration:

```json
{
  "enable_local_testing_mode": true,
  "use_sqlite_fallback": true,
  "sqlite_db_path": "tests/test.db"
}
```

---

## Windows Service Installation

To run the monitoring system as a Windows service for continuous operation:

### Step 1: Install NSSM (Non-Sucking Service Manager)

1. Download NSSM from [nssm.cc](https://nssm.cc/download)
2. Extract to `C:\nssm`
3. Add to PATH (optional)

### Step 2: Create Service

```cmd
cd C:\nssm\win64
nssm install StradMonitoring
```

### Step 3: Configure Service

In the NSSM GUI:

1. **Application** tab:
   - Path: `C:\StradMonitoring\.venv\Scripts\python.exe`
   - Startup directory: `C:\StradMonitoring`
   - Arguments: `-m src.strad_monitoring.main`

2. **Details** tab:
   - Display name: `Strad Carrier Monitoring Automation`
   - Description: `Automated monitoring system for Strad Carrier camera alignment`
   - Startup type: `Automatic (Delayed Start)`

3. **Log on** tab:
   - Select: `This account`
   - Username: Domain account with SQL Server and Excel access
   - Password: Account password

4. **I/O** tab:
   - Output (stdout): `C:\StradMonitoring\logs\service_output.log`
   - Error (stderr): `C:\StradMonitoring\logs\service_error.log`

5. **File rotation** tab:
   - ✓ Rotate files
   - Restrict rotation to files older than: `86400` seconds (1 day)

6. **Environment** tab (if needed):
   - Add environment variables if required

### Step 4: Start Service

```cmd
nssm start StradMonitoring
```

### Step 5: Verify Service Status

```cmd
nssm status StradMonitoring
```

Or check in Windows Services (`services.msc`).

### Service Management Commands

```cmd
# Start service
nssm start StradMonitoring

# Stop service
nssm stop StradMonitoring

# Restart service
nssm restart StradMonitoring

# Remove service (stops first if running)
nssm remove StradMonitoring confirm
```

---

## Running the System

### Manual Execution (Development/Testing)

```cmd
# Activate virtual environment
cd C:\StradMonitoring
.venv\Scripts\activate

# Run with default configuration
python -m src.strad_monitoring.main

# Run with custom configuration
python -m src.strad_monitoring.main --config custom_config.json
```

### Windows Service Execution (Production)

The service will automatically start on system boot if configured with `Automatic (Delayed Start)`.

Manual control:
```cmd
net start StradMonitoring
net stop StradMonitoring
```

### Monitoring System Output

**Log Files**:
```cmd
# View latest log file
type C:\StradMonitoring\logs\monitoring_log_YYYY-MM-DD.txt | more

# Tail log file (with PowerShell)
Get-Content C:\StradMonitoring\logs\monitoring_log_YYYY-MM-DD.txt -Wait -Tail 50
```

**Service Output**:
```cmd
# View service stdout
type C:\StradMonitoring\logs\service_output.log | more

# View service stderr
type C:\StradMonitoring\logs\service_error.log | more
```

---

## Troubleshooting

### Issue: "Configuration file not found"

**Symptoms**: System fails to start with error about missing `system_config.json`

**Solution**:
```cmd
# Verify file exists
dir system_config.json

# If missing, create from example
copy system_config_example.json system_config.json
notepad system_config.json
```

### Issue: "Database connectivity check failed"

**Symptoms**: System cannot connect to SQL Server

**Diagnosis**:
```cmd
python -c "import pyodbc; conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=your-server;DATABASE=StradMonitoring;Trusted_Connection=yes'); print('Connected successfully')"
```

**Solutions**:
1. **Check ODBC driver installed**:
   ```cmd
   python -c "import pyodbc; print(pyodbc.drivers())"
   ```

2. **Verify SQL Server running**:
   ```cmd
   sqlcmd -S your-server -Q "SELECT @@VERSION"
   ```

3. **Check network connectivity**:
   ```cmd
   ping your-server
   telnet your-server 1433
   ```

4. **Enable fallback mode** (for testing):
   ```json
   {
     "enable_local_testing_mode": true,
     "use_sqlite_fallback": true
   }
   ```

### Issue: "Excel automation failed"

**Symptoms**: Cannot open video feeds, Excel COM errors

**Diagnosis**:
```cmd
python -c "import win32com.client; excel = win32com.client.Dispatch('Excel.Application'); print(f'Excel Version: {excel.Version}'); excel.Quit()"
```

**Solutions**:
1. **Ensure Excel installed and activated**
2. **Run as user with Excel access** (for Windows service)
3. **Check Excel file path in configuration**
4. **Verify Excel file exists and is accessible**:
   ```cmd
   dir "C:\Path\To\spreader_encoder.xlsx"
   ```

### Issue: "VLC window not found"

**Symptoms**: Snapshot capture fails, VLC timeout errors

**Solutions**:
1. **Verify VLC installed**:
   ```cmd
   "C:\Program Files\VideoLAN\VLC\vlc.exe" --version
   ```

2. **Check VLC window title**:
   - Open VLC manually
   - Check window title matches "VLC media player"

3. **Increase timeout** in configuration (if video loads slowly):
   ```python
   # In excel_automation.py
   timeout_seconds = 60  # Increase from 30
   ```

### Issue: "CUDA not available"

**Symptoms**: DL classification slow, CPU warnings

**Diagnosis**:
```cmd
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

**Solutions**:
1. **Verify NVIDIA driver installed**:
   ```cmd
   nvidia-smi
   ```

2. **Check CUDA installation**:
   ```cmd
   nvcc --version
   ```

3. **Reinstall PyTorch with CUDA support**:
   ```cmd
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu117
   ```

### Issue: "Insufficient disk space"

**Symptoms**: Snapshot save failures, system slowdown

**Diagnosis**:
```cmd
# Check disk space
wmic logicaldisk get name,freespace,size
```

**Solutions**:
1. **Clean up old snapshots**:
   ```cmd
   # Remove snapshots older than 30 days
   forfiles /P "D:\StradMonitoring\critical_snapshots" /S /D -30 /C "cmd /c del @path"
   ```

2. **Clean up old logs**:
   ```cmd
   # Remove logs older than 14 days
   forfiles /P "C:\StradMonitoring\logs" /M *.txt /D -14 /C "cmd /c del @path"
   ```

3. **Reduce retention periods** in configuration:
   ```json
   {
     "snapshot_retention_days": 15,
     "log_retention_days": 7
   }
   ```

### Issue: "Permission denied" errors

**Symptoms**: Cannot write snapshots or logs, access denied errors

**Solutions**:
1. **Check directory permissions**:
   ```cmd
   icacls C:\StradMonitoring\temp_snapshots
   ```

2. **Grant permissions to service account**:
   ```cmd
   icacls C:\StradMonitoring /grant "DOMAIN\ServiceAccount:(OI)(CI)F" /T
   ```

3. **Run as administrator** (for testing):
   ```cmd
   # Right-click Command Prompt -> Run as Administrator
   ```

---

## Monitoring and Maintenance

### Daily Monitoring

**Check log files** for errors:
```cmd
# View today's log
type C:\StradMonitoring\logs\monitoring_log_%date:~-4,4%-%date:~-7,2%-%date:~-10,2%.txt | findstr /I "ERROR CRITICAL WARNING"
```

**Check service status**:
```cmd
sc query StradMonitoring
```

**Check database connectivity**:
```sql
-- Run in SQL Server Management Studio
SELECT COUNT(*) as TodaysChecks
FROM classification_results
WHERE CAST(created_at AS DATE) = CAST(GETDATE() AS DATE);
```

### Weekly Maintenance

1. **Review classification results**:
   ```sql
   SELECT 
       classification,
       COUNT(*) as count,
       AVG(confidence) as avg_confidence
   FROM classification_results
   WHERE created_at >= DATEADD(DAY, -7, GETDATE())
   GROUP BY classification;
   ```

2. **Check critical strads**:
   ```sql
   SELECT * FROM critical_strad_exclusions
   WHERE adjustment_confirmed_at IS NULL;
   ```

3. **Review disk space**:
   ```cmd
   dir /S D:\StradMonitoring\critical_snapshots
   ```

4. **Verify cycle completion rate**:
   ```cmd
   # Check logs for cycle completion messages
   findstr /C:"COMPLETED" C:\StradMonitoring\logs\*.txt
   ```

### Monthly Maintenance

1. **Database cleanup** (old records):
   ```sql
   -- Remove classification results older than 90 days
   DELETE FROM classification_results
   WHERE created_at < DATEADD(DAY, -90, GETDATE());
   
   -- Rebuild indexes
   ALTER INDEX ALL ON classification_results REBUILD;
   ```

2. **Log file rotation** (manual if needed):
   ```cmd
   forfiles /P "C:\StradMonitoring\logs" /M *.txt /D -30 /C "cmd /c del @path"
   ```

3. **Snapshot cleanup** (verify retention policy):
   ```cmd
   forfiles /P "D:\StradMonitoring\critical_snapshots" /S /D -30 /C "cmd /c del @path"
   ```

4. **Model performance review**:
   - Review classification confidence scores
   - Identify strads with frequent moderate/critical classifications
   - Consider model retraining if performance degrades

### Performance Metrics

**Key metrics to monitor**:

| Metric | Target | Action if Below Target |
|--------|--------|----------------------|
| Cycle completion rate | >95% | Investigate failures in logs |
| Avg cycle duration | <30 minutes | Check database/network performance |
| Classification confidence | >0.7 | Review model, consider retraining |
| Disk space available | >50GB | Clean up old snapshots |
| Service uptime | >99% | Check for crashes, resource issues |

---

## Support and Contact

For issues not covered in this guide:

1. **Check logs** for detailed error messages
2. **Review requirements** and configuration
3. **Consult the design document** for component details
4. **Contact the development team** with:
   - Log excerpts showing the error
   - Configuration file (redact sensitive info)
   - System specifications (OS, Python version, GPU)

---

## Additional Resources

- **SQLITE_FALLBACK_INTEGRATION.md**: SQLite fallback configuration for local testing
- **Design Document**: Component architecture and interfaces
- **Requirements Document**: System requirements and acceptance criteria
- **Model Training Guide**: How to retrain the DL misalignment detection model
- **API Documentation**: Component APIs and integration guides

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-15  
**Maintained By**: Strad Monitoring Development Team
