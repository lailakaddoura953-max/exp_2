# Configuration Checklist
## Strad Carrier Monitoring Automation

**Last Updated:** 2024  
**Purpose:** Complete checklist for system configuration  
**Status:** Pre-Production Setup Guide

---

## Overview

This checklist guides you through all configuration steps needed to run the Strad Carrier Monitoring Automation system. Complete each section in order.

---

## Section 1: System Requirements

### Software Installation

- [ ] **Python 3.8 or later** installed
  ```cmd
  python --version
  ```

- [ ] **Virtual environment** created and activated
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate
  ```

- [ ] **Dependencies** installed
  ```cmd
  pip install -r requirements.txt
  ```

- [ ] **Microsoft SQL Server** (2016+) accessible
  - SQL Server Express (free) OR
  - SQL Server Standard/Enterprise

- [ ] **SQL Server Management Studio (SSMS)** installed (recommended)
  - Download: https://aka.ms/ssmsfullsetup

- [ ] **Microsoft Excel** installed
  - Excel 2016 or later recommended

- [ ] **VLC Media Player** installed
  - Download: https://www.videolan.org/vlc/

- [ ] **ODBC Driver for SQL Server** installed
  - ODBC Driver 17 or 18
  - Check: Windows Key → "ODBC Data Sources (64-bit)"

---

## Section 2: Database Configuration

### Step 1: SQL Server Information

- [ ] Server name identified: ________________
  - Example: `localhost`, `DESKTOP-ABC123\SQLEXPRESS`, `prod-server.company.com`

- [ ] Database name identified: ________________
  - Example: `StradMonitoring`

- [ ] Authentication method chosen:
  - [ ] Windows Authentication (Trusted_Connection=yes)
  - [ ] SQL Server Authentication (UID/PWD required)

- [ ] ODBC driver version identified: ________________
  - Example: `ODBC Driver 17 for SQL Server`

### Step 2: Connection String Setup

- [ ] Connection string created

**Windows Authentication example:**
```
DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;Trusted_Connection=yes
```

**SQL Server Authentication example:**
```
DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;UID=strad_user;PWD=YourPassword
```

- [ ] Connection string added to `system_config.json`:
  ```json
  {
    "database_connection_string": "YOUR_CONNECTION_STRING_HERE"
  }
  ```

### Step 3: Database Schema Setup

- [ ] Database exists (or created with setup script)

- [ ] Required tables created:
  - [ ] `classification_results`
  - [ ] `moderate_tracking`
  - [ ] `critical_exclusion_list`

- [ ] Stored procedure created:
  - [ ] `strad_action_check_by_id_and_timestamp`
  - [ ] Updated with actual query logic (not placeholder)

- [ ] User permissions granted:
  - [ ] SELECT permission
  - [ ] INSERT permission
  - [ ] UPDATE permission
  - [ ] DELETE permission
  - [ ] EXECUTE permission

### Step 4: Database Testing

- [ ] Connection test passed:
  ```cmd
  python test_database_connection.py
  ```

- [ ] Required tables verified
- [ ] Stored procedure verified
- [ ] Sample query executed successfully

**Documentation:** `SQL_SERVER_SETUP_GUIDE.md`

---

## Section 3: Excel Configuration

### Step 1: Locate Excel File

- [ ] Video encoder Excel file located

  Full path: ________________

  Example: `C:\VideoEncoder\spreader_encoder.xlsx`

### Step 2: Excel File Path Setup

- [ ] Path added to `system_config.json` (use double backslashes):
  ```json
  {
    "excel_file_path": "C:\\VideoEncoder\\spreader_encoder.xlsx"
  }
  ```

### Step 3: Excel Spreadsheet Structure

- [ ] Spreadsheet has:
  - [ ] Cell for Strad ID input (e.g., A1)
  - [ ] Button to trigger video opening
  - [ ] VBA macro for VLC launching
  - [ ] Camera URL lookup (table or formula)

- [ ] VBA macro includes:
  - [ ] Strad ID reading from cell
  - [ ] Camera URL lookup logic
  - [ ] VLC path (correct location)
  - [ ] Shell command to launch VLC

### Step 4: VLC Configuration

- [ ] VLC installed at standard location
  - [ ] `C:\Program Files\VideoLAN\VLC\vlc.exe` OR
  - [ ] `C:\Program Files (x86)\VideoLAN\VLC\vlc.exe`

- [ ] VLC path in Excel macro is correct

### Step 5: Excel Testing

- [ ] Excel file path test passed:
  ```cmd
  python test_excel_connection.py
  ```

- [ ] Excel COM automation test passed
- [ ] Manual test: Open Excel → Enter Strad ID → Click button → VLC opens

**Documentation:** `EXCEL_CONFIGURATION_GUIDE.md`

---

## Section 4: File Paths Configuration

### Model Checkpoint Path

- [ ] Deep learning model file exists

  Path: ________________

  Example: `C:\Models\misalignment_detector_v2.pth`

- [ ] Added to `system_config.json`:
  ```json
  {
    "model_checkpoint_path": "C:\\Models\\misalignment_detector_v2.pth"
  }
  ```

**Note:** If model doesn't exist, system will use mock classification mode.

### Snapshot Storage Paths

- [ ] Temporary snapshot directory path defined:

  Path: ________________

  Example: `C:\StradMonitoring\temp_snapshots`

- [ ] Permanent snapshot directory path defined:

  Path: ________________

  Example: `D:\StradMonitoring\critical_snapshots`

- [ ] Directories will be created automatically by system

- [ ] Added to `system_config.json`:
  ```json
  {
    "temp_snapshot_path": "C:\\StradMonitoring\\temp_snapshots",
    "permanent_snapshot_path": "D:\\StradMonitoring\\critical_snapshots"
  }
  ```

### Log File Path

- [ ] Log directory path defined:

  Path: ________________

  Example: `C:\StradMonitoring\logs`

- [ ] Added to `system_config.json`:
  ```json
  {
    "log_file_path": "C:\\StradMonitoring\\logs"
  }
  ```

---

## Section 5: Complete Configuration File

### system_config.json Template

- [ ] All paths configured in `system_config.json`:

```json
{
  "_comment_header": "===== STRAD CARRIER MONITORING AUTOMATION - SYSTEM CONFIGURATION =====",
  "_comment_instructions": "Update paths and connection strings for your environment before running",
  
  "_comment_database": "===== DATABASE CONFIGURATION =====",
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER;DATABASE=YOUR_DATABASE;Trusted_Connection=yes",
  
  "_comment_paths": "===== FILE PATHS =====",
  "excel_file_path": "C:\\VideoEncoder\\spreader_encoder.xlsx",
  "model_checkpoint_path": "C:\\Models\\misalignment_detector_v2.pth",
  "temp_snapshot_path": "C:\\StradMonitoring\\temp_snapshots",
  "permanent_snapshot_path": "D:\\StradMonitoring\\critical_snapshots",
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

### Configuration Validation

- [ ] JSON file is valid (no syntax errors)
  ```cmd
  python -c "import json; json.load(open('system_config.json'))"
  ```

- [ ] All required fields present
- [ ] All paths use double backslashes `\\`
- [ ] All paths are absolute (not relative)

---

## Section 6: Fallback Configuration (Optional)

### SQLite Fallback (Recommended for Testing)

- [ ] SQLite database exists: `tests/test.db`

- [ ] SQLite test data populated

- [ ] Fallback enabled in `system_config.json`:
  ```json
  {
    "enable_local_testing_mode": true,
    "use_sqlite_fallback": true,
    "sqlite_db_path": "tests/test.db",
    "fallback_data_source": "sqlite"
  }
  ```

- [ ] Fallback tested:
  ```cmd
  python test_sqlite_fallback.py
  ```

**Documentation:** `LOCAL_TESTING_GUIDE.md`

---

## Section 7: System Testing

### Component Tests

- [ ] Configuration loads successfully:
  ```cmd
  python -c "from src.strad_monitoring.config.system_config import ConfigurationManager; config = ConfigurationManager.load_config('system_config.json'); print('✓ Config loaded')"
  ```

- [ ] Database connection works:
  ```cmd
  python test_database_connection.py
  ```

- [ ] Excel automation works:
  ```cmd
  python test_excel_connection.py
  ```

- [ ] SQLite fallback works (if enabled):
  ```cmd
  python test_sqlite_fallback.py
  ```

### Integration Tests

- [ ] Single image classification test:
  ```cmd
  python test_single_image.py --synthetic
  ```

- [ ] Moderate tracker test:
  ```cmd
  python test_moderate_tracker_simple.py
  ```

- [ ] Orchestrator initialization:
  ```cmd
  python -c "from src.strad_monitoring.config.system_config import ConfigurationManager; from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator; config = ConfigurationManager.load_config('system_config.json'); orch = MonitoringOrchestrator(config); print('✓ Orchestrator initialized')"
  ```

### Web App Testing (Optional)

- [ ] Backend starts successfully:
  ```cmd
  python docs\backend\app.py
  ```

- [ ] Web app opens:
  ```cmd
  start docs\index.html
  ```

- [ ] Connection status shows correctly
- [ ] Demo videos play
- [ ] Live inference works

**Documentation:** `WEB_APP_QUICK_START.md`

---

## Section 8: Production Readiness

### Security Checklist

- [ ] SQL Server uses Windows Authentication (recommended)
- [ ] Database user has minimum required permissions only
- [ ] Excel file is not password protected (or password provided in code)
- [ ] VBA macros are digitally signed (production)
- [ ] Log files are in secure location
- [ ] Snapshot directories have appropriate permissions

### Performance Checklist

- [ ] SQL Server has adequate resources
- [ ] Snapshot storage has sufficient space
- [ ] Log directory has sufficient space (14 days retention)
- [ ] Network bandwidth adequate for video streams
- [ ] GPU available for DL inference (recommended)

### Monitoring Checklist

- [ ] Log file location known and accessible
- [ ] Windows Event Log monitoring configured (optional)
- [ ] Email alerts configured (optional)
- [ ] Dashboard/monitoring tool configured (optional)

### Documentation Checklist

- [ ] All configuration documented
- [ ] Contact information for support documented
- [ ] Escalation procedures documented
- [ ] Backup and recovery procedures documented

---

## Section 9: First Run

### Pre-Flight Checks

- [ ] All checklist items above completed
- [ ] System configuration file validated
- [ ] All tests passed
- [ ] Team members notified
- [ ] Support contacts available

### Launch Commands

**Test mode (SQLite fallback):**
```cmd
cd c:\Users\Miles\Desktop\exp_2
.venv\Scripts\activate
python -m src.strad_monitoring.main
```

**Production mode (SQL Server):**
```cmd
cd c:\Users\Miles\Desktop\exp_2
.venv\Scripts\activate
python -m src.strad_monitoring.main --config system_config.json
```

### What to Expect

- [ ] System initialization messages appear
- [ ] Configuration loads successfully
- [ ] Database connection verified
- [ ] Components initialized (7 total)
- [ ] Scheduler started
- [ ] Message: "System will execute monitoring cycles at XX:00:00 every hour"

### Monitoring First Cycle

- [ ] Wait for next hour (XX:00:00)
- [ ] Cycle starts automatically
- [ ] 10 strads selected
- [ ] Each strad processed serially
- [ ] Results logged
- [ ] Cycle completes

---

## Section 10: Troubleshooting

### Common Issues

**Database connection fails:**
- Check `SQL_SERVER_SETUP_GUIDE.md`
- Run `python test_database_connection.py`
- Verify SQL Server is running
- Check firewall settings

**Excel automation fails:**
- Check `EXCEL_CONFIGURATION_GUIDE.md`
- Run `python test_excel_connection.py`
- Verify Excel is installed
- Install pywin32: `pip install pywin32`

**VLC capture fails:**
- Check VLC is installed
- Verify VLC path in Excel macro
- Test manual launch from Excel

**Model not loading:**
- Check model file exists
- Verify path in config
- System will use mock mode if model missing

---

## Quick Reference

### Test Commands

```cmd
# Test database
python test_database_connection.py

# Test Excel
python test_excel_connection.py

# Test SQLite fallback
python test_sqlite_fallback.py

# Test single image
python test_single_image.py --synthetic

# Test web app backend
python test_web_app_backend.py

# Start web app
python docs\backend\app.py
start docs\index.html
```

### Main System Commands

```cmd
# Run system (default config)
python -m src.strad_monitoring.main

# Run system (custom config)
python -m src.strad_monitoring.main --config custom_config.json

# Stop system
Ctrl+C (in terminal)
```

---

## Documentation Quick Links

| Topic | Document |
|-------|----------|
| SQL Server Setup | `SQL_SERVER_SETUP_GUIDE.md` |
| Excel Configuration | `EXCEL_CONFIGURATION_GUIDE.md` |
| Web App Setup | `WEB_APP_QUICK_START.md` |
| Local Testing | `LOCAL_TESTING_GUIDE.md` |
| SQLite Fallback | `SQLITE_FALLBACK_INTEGRATION.md` |
| Deployment | `DEPLOYMENT.md` |
| What You Can Test | `HOW_TO_USE_RIGHT_NOW.md` |
| Architecture | `ARCHITECTURE.md` |
| Project Status | `PROJECT_STATUS_SUMMARY.md` |

---

## Sign-Off

### Configuration Completed By

- Name: ________________
- Date: ________________
- Configuration verified: [ ] Yes [ ] No

### Review and Approval (Production Only)

- Reviewed by: ________________
- Date: ________________
- Approved for deployment: [ ] Yes [ ] No
- POC document reference: ________________

---

## Notes

**Remember:** This system is **demo presentable** but requires official Proof of Concept (POC) approval before production deployment!

All configuration items should be reviewed and approved by appropriate stakeholders before production use.
