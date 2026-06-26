# System Configuration Guide
## Strad Carrier Monitoring Automation

**Last Updated:** 2024  
**Configuration File:** `system_config.json` (root directory)

---

## Quick Start

1. Open `system_config.json` in the root directory
2. Update `database_connection_string` with your SQL Server details
3. Update `excel_file_path` with path to your Excel encoder file
4. Test: `python test_database_connection.py`
5. Test: `python test_excel_connection.py`
6. Run: `python -m src.strad_monitoring.main`

---

## Configuration File Location

**File:** `system_config.json` (in the project root directory, NOT in a subdirectory)

This file already exists with default values. You need to **update** the existing values.

---

## 1. Database Configuration

### Find this line (around line 5):

```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=prod-server;DATABASE=StradMonitoring;Trusted_Connection=yes",
```

### Update with your details:

**Windows Authentication (Recommended):**
```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER;DATABASE=YOUR_DB;Trusted_Connection=yes",
```

**SQL Server Authentication:**
```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER;DATABASE=YOUR_DB;UID=YOUR_USER;PWD=YOUR_PASSWORD",
```

### Examples:

**Local SQL Server Express:**
```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=StradMonitoring;Trusted_Connection=yes",
```

**Remote SQL Server:**
```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=prod-server.company.com;DATABASE=StradMonitoring;Trusted_Connection=yes",
```

**With SQL Authentication:**
```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;UID=strad_user;PWD=SecurePassword123!",
```

### Test:
```cmd
python test_database_connection.py
```

---

## 2. Excel File Configuration

### Find this line (around line 8):

```json
"excel_file_path": "C:\\VideoEncoder\\spreader_encoder.xlsx",
```

### Update with your file path:

**IMPORTANT:** Use double backslashes (`\\`) in JSON!

### Examples:

**Local drive:**
```json
"excel_file_path": "C:\\VideoEncoder\\spreader_encoder.xlsx",
```

**Desktop:**
```json
"excel_file_path": "C:\\Users\\YourUsername\\Desktop\\spreader_encoder.xlsx",
```

**Documents:**
```json
"excel_file_path": "C:\\Users\\YourUsername\\Documents\\spreader_encoder.xlsx",
```

**Network share:**
```json
"excel_file_path": "\\\\NetworkServer\\Share\\VideoEncoder\\spreader_encoder.xlsx",
```

**Mapped drive:**
```json
"excel_file_path": "Z:\\VideoEncoder\\spreader_encoder.xlsx",
```

### Test:
```cmd
python test_excel_connection.py
```

---

## 3. Other Configuration (Optional)

The file contains additional settings you can customize:

### Model Path:
```json
"model_checkpoint_path": "C:\\Models\\misalignment_detector_v2.pth",
```

### Snapshot Paths:
```json
"temp_snapshot_path": "C:\\StradMonitoring\\temp_snapshots",
"permanent_snapshot_path": "D:\\StradMonitoring\\critical_snapshots",
```

### Log Path:
```json
"log_file_path": "C:\\StradMonitoring\\logs",
```

### Timing:
```json
"cycle_schedule_cron": "0 * * * *",
"strad_selection_count": 10,
"cooldown_hours": 1,
```

---

## Common Mistakes

### ❌ Wrong: Single backslashes
```json
"excel_file_path": "C:\Path\To\File.xlsx"
```

### ✅ Correct: Double backslashes
```json
"excel_file_path": "C:\\Path\\To\\File.xlsx"
```

### ❌ Wrong: Looking for demo_config/system_config.json
The code uses the ROOT `system_config.json`, not `demo_config/system_config.json`

### ✅ Correct: Use root system_config.json
```
c:\Users\Miles\Desktop\exp_2\system_config.json  ← Edit this file
```

---

## Configuration File Structure

The file uses a **flat structure** (not nested). Here's what it looks like:

```json
{
  "_comment_database": "===== DATABASE CONFIGURATION =====",
  "database_connection_string": "DRIVER={...};SERVER=...;DATABASE=...;Trusted_Connection=yes",
  
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

## Test Scripts

After updating configuration, run these tests:

```cmd
# Test database connection
python test_database_connection.py

# Test Excel file access
python test_excel_connection.py

# Test SQLite fallback (for local testing without SQL Server)
python test_sqlite_fallback.py
```

---

## Troubleshooting

### Database Connection Fails
1. Check server name is correct
2. Verify database exists
3. Confirm ODBC driver installed: Windows Key → "ODBC Data Sources (64-bit)"
4. Test SQL Server is running: Services → "SQL Server (MSSQLSERVER)"
5. Check firewall allows port 1433

### Excel File Not Found
1. Verify file exists at specified path
2. Check for typos in filename
3. Remember to use double backslashes (`\\`)
4. Right-click file in Explorer → Properties → Copy location

### JSON Syntax Error
1. Check all quotes are doubled: `"field": "value"`
2. Check commas between fields
3. Verify backslashes are doubled: `C:\\Path`
4. Use a JSON validator: https://jsonlint.com/

---

## SQL Server Setup

For detailed SQL Server setup (creating database, tables, stored procedures):

**See:** `SQL_SERVER_SETUP_GUIDE.md`

---

## Excel File Setup

For detailed Excel encoder file setup (macros, VBA, button configuration):

**See:** `EXCEL_CONFIGURATION_GUIDE.md`

---

## Quick Reference

| Configuration | Field Name | Example Value |
|---------------|------------|---------------|
| Database | `database_connection_string` | `"DRIVER={...};SERVER=localhost;DATABASE=StradMonitoring;Trusted_Connection=yes"` |
| Excel File | `excel_file_path` | `"C:\\VideoEncoder\\spreader_encoder.xlsx"` |
| Model | `model_checkpoint_path` | `"C:\\Models\\misalignment_detector_v2.pth"` |
| Temp Snapshots | `temp_snapshot_path` | `"C:\\StradMonitoring\\temp_snapshots"` |
| Critical Snapshots | `permanent_snapshot_path` | `"D:\\StradMonitoring\\critical_snapshots"` |
| Logs | `log_file_path` | `"C:\\StradMonitoring\\logs"` |

---

## Support

- **Database setup:** SQL_SERVER_SETUP_GUIDE.md
- **Excel setup:** EXCEL_CONFIGURATION_GUIDE.md
- **Complete docs:** DOCUMENTATION_INDEX.md
- **Quick start:** HOW_TO_USE_RIGHT_NOW.md
