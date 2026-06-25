# Configuration Quick Reference
## One-Page Guide to System Configuration

**Last Updated:** 2024  
**Purpose:** Quick reference for configuring Strad Carrier Monitoring system  
**Print this page for easy reference during setup**

---

## 📋 Configuration Checklist

### ✅ Step 1: Edit system_config.json

**File Location:** `c:\Users\Miles\Desktop\exp_2\system_config.json`

**Open with:** Notepad, VS Code, or any text editor

### ✅ Step 2: Update These 6 Settings

| # | Setting | What to Change | Example |
|---|---------|----------------|---------|
| 1 | `database_connection_string` | SQL Server details | See below |
| 2 | `excel_file_path` | Path to Excel video encoder | `C:\\Warehouse\\Apps\\spreader_encoder.xlsx` |
| 3 | `model_checkpoint_path` | Path to DL model file | `C:\\Models\\strad_classifier_v2.pth` |
| 4 | `temp_snapshot_path` | Temporary storage folder | `C:\\StradMonitoring\\TempSnapshots` |
| 5 | `permanent_snapshot_path` | Permanent storage folder | `D:\\Archives\\CriticalSnapshots` |
| 6 | `log_file_path` | Log file directory | `C:\\StradMonitoring\\Logs` |

---

## 🔌 Database Connection Strings

### Windows Authentication (Recommended)

```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER_NAME;DATABASE=YOUR_DATABASE_NAME;Trusted_Connection=yes"
```

**Real Example:**
```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=WAREHOUSE-SQL-01;DATABASE=StradCarrierDB;Trusted_Connection=yes"
```

### SQL Server Authentication

```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER_NAME;DATABASE=YOUR_DATABASE_NAME;UID=YOUR_USERNAME;PWD=YOUR_PASSWORD"
```

**Real Example:**
```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=WAREHOUSE-SQL-01;DATABASE=StradCarrierDB;UID=monitoring_app;PWD=SecurePass123!"
```

### Named Instance

```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER\\INSTANCE_NAME;DATABASE=YOUR_DATABASE_NAME;Trusted_Connection=yes"
```

**Real Example:**
```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=WAREHOUSE-SQL-01\\SQLEXPRESS;DATABASE=StradCarrierDB;Trusted_Connection=yes"
```

---

## 📂 File Path Examples

### ⚠️ IMPORTANT: Use Double Backslashes `\\` in JSON

| Wrong ❌ | Right ✅ |
|---------|---------|
| `C:\Path\To\File` | `C:\\Path\\To\\File` |
| `D:\Folder\file.xlsx` | `D:\\Folder\\file.xlsx` |

### Excel File Path

```json
"excel_file_path": "C:\\Warehouse\\Apps\\VideoEncoder\\spreader_encoder.xlsx"
```

### Model File Path

```json
"model_checkpoint_path": "C:\\Warehouse\\Models\\strad_classifier_v2.pth"
```

### Storage Paths

```json
"temp_snapshot_path": "C:\\StradMonitoring\\TempSnapshots",
"permanent_snapshot_path": "D:\\Archives\\CriticalSnapshots"
```

### Log Path

```json
"log_file_path": "C:\\StradMonitoring\\Logs"
```

---

## 🧪 Testing Configuration

### Test 1: Verify File Syntax

```cmd
python -c "import json; json.load(open('system_config.json')); print('✓ JSON syntax valid')"
```

### Test 2: Load Configuration

```cmd
python -c "from src.strad_monitoring.config.system_config import ConfigurationManager; config = ConfigurationManager.load_config('system_config.json'); print('✓ Configuration loaded successfully')"
```

### Test 3: Test Database Connection

```cmd
python -m src.strad_monitoring.main
```

**Look for:** `✓ Database connectivity verified`

---

## 🔧 Common Mistakes

### ❌ Mistake 1: Single Backslashes

**Wrong:**
```json
"excel_file_path": "C:\Warehouse\Apps\file.xlsx"
```

**Correct:**
```json
"excel_file_path": "C:\\Warehouse\\Apps\\file.xlsx"
```

### ❌ Mistake 2: Wrong ODBC Driver Name

**Wrong:**
```json
"DRIVER={SQL Server}"
```

**Correct:**
```json
"DRIVER={ODBC Driver 17 for SQL Server}"
```

### ❌ Mistake 3: Missing Database Name

**Wrong:**
```json
"SERVER=MY-SERVER;Trusted_Connection=yes"
```

**Correct:**
```json
"SERVER=MY-SERVER;DATABASE=StradMonitoring;Trusted_Connection=yes"
```

### ❌ Mistake 4: Trailing Comma

**Wrong:**
```json
{
  "log_file_path": "C:\\Logs",
}
```

**Correct:**
```json
{
  "log_file_path": "C:\\Logs"
}
```

---

## 🚀 Quick Start After Configuration

### 1. Test Configuration

```cmd
cd c:\Users\Miles\Desktop\exp_2
.venv\Scripts\activate
python -m src.strad_monitoring.main
```

### 2. Run Web App

```cmd
start_web_app.bat
```

### 3. Test Single Image Classification

```cmd
python test_single_image.py --synthetic
```

---

## 📞 Getting Help

### Information You Need to Provide

When asking for help, provide:

1. **Your SQL Server details:**
   - Server name: `________________`
   - Database name: `________________`
   - Authentication type: Windows / SQL Server
   - Instance name (if applicable): `________________`

2. **Error message:** (copy full error text)

3. **What you tried:** (steps you followed)

### Where to Look

| Issue | Check This |
|-------|-----------|
| SQL connection fails | `SQL_SERVER_SETUP_GUIDE.md` |
| Path errors | This document |
| Web app issues | `WEB_APP_QUICK_START.md` |
| Testing without SQL | `HOW_TO_USE_RIGHT_NOW.md` |
| Full setup guide | `DEPLOYMENT.md` |

---

## 🎯 Configuration Flow Diagram

```
system_config.json
       │
       ├─> database_connection_string ──> SQL Server
       │                                      │
       │                                      ├─> container_demo (strads)
       │                                      ├─> classification_results
       │                                      ├─> moderate_classifications
       │                                      └─> critical_exclusion_list
       │
       ├─> excel_file_path ──> Video Encoder Spreadsheet
       │                              │
       │                              └─> Strad IDs and Video URLs
       │
       ├─> model_checkpoint_path ──> DL Model File (.pth)
       │                                   │
       │                                   └─> Classification Engine
       │
       ├─> temp_snapshot_path ──> Temporary Image Storage
       │                               │
       │                               └─> Deleted after 30 days
       │
       ├─> permanent_snapshot_path ──> Critical Image Archive
       │                                    │
       │                                    └─> Permanent storage
       │
       └─> log_file_path ──> Application Logs
                                  │
                                  └─> Rotated daily, kept 14 days
```

---

## 📋 Pre-Deployment Checklist

Before running in production:

- [ ] SQL Server accessible from application server
- [ ] Database exists with required tables
- [ ] Stored procedure `strad_action_check_by_id_and_timestamp` created
- [ ] User has database permissions (SELECT, INSERT, UPDATE, DELETE, EXECUTE)
- [ ] ODBC Driver 17 for SQL Server installed
- [ ] Excel file accessible at specified path
- [ ] Model file exists at specified path
- [ ] Storage directories exist (or can be created)
- [ ] Log directory exists (or can be created)
- [ ] system_config.json validated with test script
- [ ] Database connection tested successfully
- [ ] Fallback mode disabled: `"enable_local_testing_mode": false`

---

## 🔐 Security Reminders

1. **Never commit passwords to version control**
2. **Use Windows Authentication when possible**
3. **Restrict file permissions on system_config.json**
4. **Use least-privilege database permissions**
5. **Keep ODBC drivers updated**
6. **Enable SQL Server connection encryption**

---

## 💾 Backup Configuration Template

Save this template with YOUR values:

```json
{
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=________;DATABASE=________;Trusted_Connection=yes",
  "excel_file_path": "C:\\________\\________\\spreader_encoder.xlsx",
  "model_checkpoint_path": "C:\\________\\________\\model.pth",
  "temp_snapshot_path": "C:\\________\\________\\TempSnapshots",
  "permanent_snapshot_path": "D:\\________\\________\\CriticalSnapshots",
  "log_file_path": "C:\\________\\________\\Logs",
  "cycle_schedule_cron": "0 * * * *",
  "strad_selection_count": 10,
  "cooldown_hours": 1,
  "classification_timeout_seconds": 10,
  "snapshot_min_width": 640,
  "snapshot_min_height": 480,
  "snapshot_retention_days": 30,
  "log_retention_days": 14,
  "enable_local_testing_mode": false,
  "use_sqlite_fallback": false,
  "sqlite_db_path": "tests/test.db",
  "fallback_data_source": "sqlite",
  "fallback_data_path": "C:\\test_data\\strad_list.csv",
  "dl_model_config": {
    "flow_network": "liteflownet2",
    "target_resolution": [640, 640],
    "confidence_threshold": 0.5,
    "enable_uncertainty": false
  }
}
```

---

## ✨ Summary

**Only ONE file to edit:** `system_config.json`

**Critical settings to update:**
1. Database connection string (with YOUR server and database)
2. Excel file path (YOUR actual path)
3. Model file path (YOUR actual path)
4. Storage paths (YOUR actual directories)
5. Log path (YOUR actual directory)

**All other files automatically read from this configuration!**

**After editing, test with:** `python -m src.strad_monitoring.main`

**Status:** Ready for deployment after configuration and testing complete!

---

**Print this page and keep it handy during configuration!**
