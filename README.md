# Strad Carrier Monitoring Automation

**Automated monitoring system for Strad Carrier misalignment detection using deep learning classification.**

**Status:** Demo Presentable - Ready for Testing  
**Version:** 1.0.0  
**Last Updated:** 2024

---

## 🚀 Quick Start

### Option 1: Test Immediately (No Setup)

```cmd
cd c:\Users\Miles\Desktop\exp_2
.venv\Scripts\activate
python test_single_image.py --synthetic
```

### Option 2: Run Web App

```cmd
start_web_app.bat
```

### Option 3: Configure SQL Server

Read: `SQL_SERVER_SETUP_GUIDE.md` → Edit `system_config.json` → Test

---

## 📚 Documentation Guide

| What You Want | Read This Document |
|---------------|-------------------|
| **Complete setup checklist** | `CONFIGURATION_CHECKLIST.md` |
| Test without SQL Server | `HOW_TO_USE_RIGHT_NOW.md` |
| Run web app | `WEB_APP_QUICK_START.md` |
| Configure SQL Server | `SQL_SERVER_SETUP_GUIDE.md` |
| Configure Excel file | `EXCEL_CONFIGURATION_GUIDE.md` |
| Deploy to production | `DEPLOYMENT.md` |
| System architecture | `ARCHITECTURE.md` |
| Web app integration | `WEB_APP_INTEGRATION_SUMMARY.md` |

**👉 Start with `SETUP_COMPLETE_SUMMARY.md` for an overview of everything!**

---

## 📋 What's Included

### Core Monitoring System
- ✅ Configuration management with JSON validation
- ✅ Logging system with daily rotation (14-day retention)
- ✅ Database interface (SQL Server + SQLite fallback)
- ✅ Excel automation for video encoder control
- ✅ VLC window capture with retry logic
- ✅ DL classifier wrapper for misalignment detection
- ✅ Storage manager for temporary and permanent snapshots
- ✅ Moderate classification tracker (3-consecutive warning)
- ✅ Adjustment confirmation handler
- ✅ Main orchestrator with hourly scheduling
- ✅ Graceful shutdown with completion wait
- ✅ CLI with config argument support

### Web Application
- ✅ Visual kanban board interface
- ✅ Demo video playback (normal operation and impact scenarios)
- ✅ Live inference testing with image upload
- ✅ Real-time classification display
- ✅ Connection to strad_monitoring backend
- ✅ Real data integration from database
- ✅ Graceful fallback to demo mode

### Documentation
- ✅ 9 comprehensive guide documents
- ✅ SQL Server setup instructions
- ✅ Configuration quick reference
- ✅ Web app user guide
- ✅ Testing guide (without SQL Server)
- ✅ Deployment instructions
- ✅ Architecture documentation

---

## 🎯 System Overview

### How It Works

**Hourly Monitoring Cycle:**
1. Query 10 eligible strads from database (1-hour cooldown)
2. For each strad:
   - Open video feed via Excel automation
   - Capture snapshot from VLC window
   - Classify snapshot with DL model (none/moderate/critical)
   - Store results based on severity
3. Continue with remaining strads even if one fails
4. Log all operations

**Severity Handling:**
- **None:** Update check history only
- **Moderate:** Track consecutive occurrences, warn at 3
- **Critical:** Persist snapshot, add to exclusion list

**Web Interface:**
- Visual dashboard with kanban board
- Demo videos and real-time classification
- Live inference testing
- Connects to backend API for real data

---

## 🔧 Configuration

### Only ONE file to edit: `system_config.json`

**6 Settings to Update:**
1. `database_connection_string` - Your SQL Server connection
2. `excel_file_path` - Path to video encoder Excel file
3. `model_checkpoint_path` - Path to DL model file
4. `temp_snapshot_path` - Temporary storage directory
5. `permanent_snapshot_path` - Permanent storage directory
6. `log_file_path` - Log file directory

**Example Connection String:**
```json
"database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER;DATABASE=YOUR_DB;Trusted_Connection=yes"
```

**All other components automatically read from this file!**

See `CONFIGURATION_QUICK_REFERENCE.md` for details.

---

## 🧪 Testing

### Test Without SQL Server

Uses included SQLite database with 20 test strads:

```cmd
# Test single image classification
python test_single_image.py --synthetic

# Test SQLite fallback
python test_sqlite_fallback.py

# Test moderate tracker
python examples\moderate_tracker_demo.py

# Run web app (demo mode)
start_web_app.bat
```

See `HOW_TO_USE_RIGHT_NOW.md` for complete testing guide.

---

## 🌐 Web Application

### Start Web App

**Automated (Recommended):**
```cmd
start_web_app.bat
```

**Manual:**
```cmd
# Terminal 1: Start backend
python docs\backend\app.py

# Terminal 2 or Browser: Open web app
start docs\index.html
```

### Features

- **Kanban Board:** Visual display of strads by severity
- **Demo Videos:** Normal operation and impact scenarios
- **Live Inference:** Upload image for real-time classification
- **Real Data:** Connects to backend for actual strad data
- **Fallback Mode:** Works offline with demo content

See `WEB_APP_QUICK_START.md` for step-by-step guide.

---

## 🗄️ SQL Server Setup

### Prerequisites

- Microsoft SQL Server (2016+)
- SQL Server Management Studio (SSMS)
- ODBC Driver 17 for SQL Server

### Setup Steps

1. Create database and tables (SQL script provided)
2. Create stored procedure `strad_action_check_by_id_and_timestamp`
3. Edit `system_config.json` with connection string
4. Update file paths
5. Test connection: `python -m src.strad_monitoring.main`

See `SQL_SERVER_SETUP_GUIDE.md` for complete instructions.

---

## 📁 Project Structure

```
exp_2/
├── docs/                        # Web application
│   ├── backend/app.py          # Flask API
│   ├── index.html              # Web UI
│   ├── script.js               # JavaScript
│   └── styles.css              # Styling
│
├── src/strad_monitoring/       # Core system
│   ├── config/                 # Configuration
│   ├── database/               # Database interface
│   ├── dl_classifier/          # DL classifier
│   ├── orchestration/          # Main orchestrator
│   └── main.py                 # Entry point
│
├── tests/
│   └── test.db                 # SQLite test data (20 strads)
│
├── system_config.json          # MAIN CONFIG FILE
│
├── start_web_app.bat           # Web app launcher
│
└── Documentation/
    ├── SETUP_COMPLETE_SUMMARY.md
    ├── HOW_TO_USE_RIGHT_NOW.md
    ├── WEB_APP_QUICK_START.md
    ├── SQL_SERVER_SETUP_GUIDE.md
    ├── CONFIGURATION_QUICK_REFERENCE.md
    └── DEPLOYMENT.md
```

---

## ⚠️ Important Notes

### Status: Demo Presentable

This system is **demo presentable** but requires **official proof of concept approval** before production deployment.

### Fallback Mechanism

System MUST work without SQL Server for local testing:
- SQLite fallback (recommended)
- KITTI dataset fallback
- CSV/JSON file fallback
- Random strad ID generation

Set in `system_config.json`:
```json
"enable_local_testing_mode": true,
"use_sqlite_fallback": true
```

### Terminology

Say:
- ✅ "Demo presentable"
- ✅ "Ready for testing"

Don't say:
- ❌ "Production ready"
- ❌ "Deployment ready"

---

## 🔒 Security

### Best Practices

1. Use Windows Authentication when possible
2. Restrict database permissions (least privilege)
3. Secure `system_config.json` file permissions
4. Never commit passwords to version control
5. Enable SQL Server connection encryption
6. Keep ODBC drivers updated

See `SQL_SERVER_SETUP_GUIDE.md` for security details.

---

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution | Reference |
|-------|----------|-----------|
| SQL connection fails | Check connection string | `SQL_SERVER_SETUP_GUIDE.md` |
| Web app disconnected | Start backend server | `WEB_APP_QUICK_START.md` |
| Config won't load | Check JSON syntax | `CONFIGURATION_QUICK_REFERENCE.md` |
| Import errors | Activate venv | `HOW_TO_USE_RIGHT_NOW.md` |

---

## 📞 Getting Help

### Information to Provide

When asking for help:
1. What you're trying to do
2. Full error message (copy/paste)
3. Steps you followed
4. Documentation you referenced

### Where to Look

Start with `SETUP_COMPLETE_SUMMARY.md` for overview, then:
- Testing: `HOW_TO_USE_RIGHT_NOW.md`
- Web app: `WEB_APP_QUICK_START.md`
- SQL Server: `SQL_SERVER_SETUP_GUIDE.md`
- Configuration: `CONFIGURATION_QUICK_REFERENCE.md`

---

## 🎓 Next Steps

### 1. Immediate Testing (Right Now)

Read `HOW_TO_USE_RIGHT_NOW.md` and run:
```cmd
python test_single_image.py --synthetic
start_web_app.bat
```

### 2. SQL Server Integration (This Week)

Read `SQL_SERVER_SETUP_GUIDE.md`, then:
1. Create database tables
2. Edit `system_config.json`
3. Test connection

### 3. Production Deployment (After POC Approval)

Read `DEPLOYMENT.md`, then:
1. Install as Windows service
2. Set up monitoring
3. Conduct end-to-end testing
4. **Get official POC approval**
5. Deploy

---

## 📄 License

Proprietary - Internal use only  
Requires official proof of concept approval before production deployment

---

## 🙏 Acknowledgments

This system integrates:
- PyTorch for deep learning
- Flask for web backend
- SQL Server for data storage
- VLC for video capture
- Excel COM automation
- APScheduler for task scheduling

---

## ✨ Summary

Complete monitoring system with:
- ✅ 57 core components implemented
- ✅ Visual web interface with real data integration
- ✅ 9 comprehensive documentation guides
- ✅ SQL Server setup instructions
- ✅ SQLite fallback for testing (20 test strads)
- ✅ Automated web app launcher
- ✅ Test scripts for verification

**Status:** Demo presentable and ready for testing!

**Start here:** `SETUP_COMPLETE_SUMMARY.md`

Good luck! 🚀
