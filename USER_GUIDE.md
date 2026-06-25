# Strad Carrier Monitoring Automation - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start for Demo/Testing](#quick-start-for-demotesting)
3. [Understanding the System](#understanding-the-system)
4. [Running the System](#running-the-system)
5. [Local Testing with SQLite](#local-testing-with-sqlite)
6. [Running Individual Components](#running-individual-components)
7. [Configuration Guide](#configuration-guide)
8. [Understanding the Monitoring Cycle](#understanding-the-monitoring-cycle)
9. [Interpreting Logs and Output](#interpreting-logs-and-output)
10. [Common Operations](#common-operations)
11. [Testing the Confirmation Handler](#testing-the-confirmation-handler)
12. [Troubleshooting](#troubleshooting)
13. [Important Notes](#important-notes)

---

## Introduction

### What is This System?

The Strad Carrier Monitoring Automation system automates the process of checking camera alignment on Strad Carrier vehicles (SC001-SC135). Previously done manually, this system now:

- **Automatically selects** 10 random Strad Carriers every hour
- **Opens video feeds** through Excel-based video encoder controls
- **Captures snapshots** from VLC media player
- **Analyzes camera alignment** using deep learning models
- **Stores results** in SQL Server database with timestamp tracking
- **Manages critical units** by excluding severely misaligned cameras from rotation

### Current Status: DEMO PRESENTABLE / DEPLOYMENT DEMO READY

**⚠️ IMPORTANT: This system is NOT officially deployable until proof of concept is approved by management.**

This is a **demonstration-ready** system designed to:
- Showcase the automated monitoring workflow
- Validate the deep learning classification approach
- Demonstrate integration between Excel, VLC, database, and AI components
- Provide management with evidence for production deployment approval


### What Works vs What Needs Approval

**✅ COMPLETE - WORKS FOR DEMO:**
- Core orchestration and scheduling
- Component integration (Excel, VLC, Database, DL Classifier, Storage)
- Error handling and recovery
- Graceful shutdown
- Logging system with rotation
- Configuration management
- Fallback mechanisms for local testing
- SQLite test database with 20 realistic records

**⏳ PENDING MANAGEMENT APPROVAL:**
- Production database deployment
- Integration with production video encoder infrastructure
- Production model training with full dataset
- 24/7 automated operation
- Alert notification system integration
- Production validation and stress testing

---

## Quick Start for Demo/Testing

### Prerequisites

- **Operating System:** Windows 10/11
- **Python:** 3.10 or 3.11 installed
- **GPU:** NVIDIA GPU with CUDA 11.7+ (for DL inference)
- **SQLite Database:** `tests/test.db` (included - 20 test records)

### 5-Minute Quick Start

```bash
# 1. Navigate to project directory
cd C:\Users\Miles\Desktop\exp_2

# 2. Activate virtual environment (if using one)
.venv\Scripts\activate

# 3. Install dependencies (if not already installed)
pip install -r requirements.txt

# 4. Verify SQLite test database exists
dir tests\test.db

# 5. Run the system with SQLite fallback (no SQL Server required!)
python -m src.strad_monitoring.main

# System will:
# - Load configuration from system_config.json
# - Attempt SQL Server connection → FAIL (expected for demo)
# - Automatically switch to SQLite fallback
# - Load 10 random strads from tests/test.db
# - Start hourly monitoring cycle at XX:00:00
```

### What to Expect

When you run the system, you'll see:

```
================================================================================
STRAD CARRIER MONITORING AUTOMATION - STARTING
================================================================================
Loading configuration from: system_config.json
✓ Configuration loaded successfully
Validating configuration...
✓ Configuration validated successfully
Setting up logging system...
✓ Logging system initialized
Verifying database connectivity...
⚠ Database unavailable - using local testing mode with fallback
✓ Database connectivity verified
Creating MonitoringOrchestrator...
================================================================================
MONITORING ORCHESTRATOR INITIALIZATION
================================================================================
Logging system initialized
Initializing components...
  Initializing DatabaseInterface...
  ✓ DatabaseInterface initialized
  Initializing ExcelAutomation...
  ✓ ExcelAutomation initialized
  Initializing VLCCapture...
  ✓ VLCCapture initialized
  Initializing DLClassifierWrapper...
  ✓ DLClassifierWrapper initialized
  Initializing StorageManager...
  ✓ StorageManager initialized
✓ All components initialized successfully
================================================================================
STARTING MONITORING ORCHESTRATOR
================================================================================
Scheduler will trigger monitoring cycles at XX:00:00 every hour
Press Ctrl+C to stop
================================================================================
```

The system will now wait until the next hour (XX:00:00) to execute a monitoring cycle.

---

## Understanding the System

### System Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    MONITORING ORCHESTRATOR                    │
│                   (Coordinates Everything)                    │
└────────────────────────┬─────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼────────┐ ┌───▼────┐ ┌───────▼────────┐
│  DatabaseInterface │ │ Excel  │ │  VLC Capture   │
│  (SQL Server/     │ │ Auto   │ │  (Snapshot)    │
│   SQLite)         │ │        │ │                │
└───────────────────┘ └────────┘ └────────────────┘
         │                              │
┌────────▼────────┐          ┌─────────▼──────────┐
│  Storage        │          │  DL Classifier     │
│  Manager        │          │  (PyTorch Model)   │
└─────────────────┘          └────────────────────┘
```

### Key Components

1. **Database Interface**
   - **Primary:** SQL Server with stored procedures
   - **Fallback:** SQLite test database (`tests/test.db`)
   - **Purpose:** Store/retrieve strad data, check history, exclusions

2. **Excel Automation**
   - **Technology:** COM automation (pywin32)
   - **Purpose:** Control "spreader video encoder" button to open video feeds

3. **VLC Capture**
   - **Technology:** Window automation (pyautogui)
   - **Purpose:** Capture snapshots from VLC media player

4. **DL Classifier**
   - **Technology:** PyTorch (LiteFlowNet2 or SpyNet)
   - **Purpose:** Classify camera alignment: none/moderate/critical

5. **Storage Manager**
   - **Purpose:** Manage temporary/permanent snapshot storage
   - **Critical snapshots:** Saved for 30 days in date-organized folders

6. **Orchestrator**
   - **Purpose:** Coordinates all components, schedules hourly cycles
   - **Technology:** APScheduler with cron triggers

### Data Flow (One Strad)

```
1. SELECT strad → DatabaseInterface.get_eligible_strads()
                  ↓
2. OPEN video  → ExcelAutomation.open_video_feed(strad_id)
                  ↓
3. CAPTURE     → VLCCapture.capture_snapshot()
                  ↓
4. CLASSIFY    → DLClassifier.classify_snapshot(snapshot)
                  ↓
5. STORE       → If critical: StorageManager.persist_critical_snapshot()
                 → DatabaseInterface.store_classification_result()
                 → DatabaseInterface.update_check_history()
                  ↓
6. CLEANUP     → StorageManager.clear_temporary_snapshot()
```

---

## Running the System

### Method 1: Manual Execution (Recommended for Demo)

**Best for:** Testing, demonstration, development

```bash
# Navigate to project
cd C:\Users\Miles\Desktop\exp_2

# Activate virtual environment (if using)
.venv\Scripts\activate

# Run with default configuration
python -m src.strad_monitoring.main

# Run with custom configuration
python -m src.strad_monitoring.main --config demo_config/system_config.json

# Stop the system
# Press Ctrl+C (graceful shutdown - waits for current strad to complete)
```

### Method 2: Windows Service (Production - After Approval)

**Best for:** 24/7 automated operation (requires management approval)

See `DEPLOYMENT.md` for detailed Windows service installation instructions using NSSM.

### Understanding the Hourly Schedule

The system uses **cron-based scheduling**:
- **Schedule:** `0 * * * *` (minute=0, hour=*, every hour)
- **Execution time:** XX:00:00 (e.g., 10:00:00, 11:00:00, 12:00:00)
- **Cycle duration:** Typically 20-40 minutes for 10 strads
- **Wait between cycles:** Scheduler automatically waits until next hour

**Example timeline:**
```
10:00:00 - Cycle #1 starts (10 strads)
10:32:15 - Cycle #1 completes
10:32:15 - 11:00:00 - System waits
11:00:00 - Cycle #2 starts (10 strads)
11:28:42 - Cycle #2 completes
11:28:42 - 12:00:00 - System waits
12:00:00 - Cycle #3 starts...
```


---

## Local Testing with SQLite

### Why Use SQLite Fallback?

**PRIMARY PATH (Production):**
- Requires SQL Server connection
- Requires network access to production database
- Requires credentials and permissions
- Not available during development/demo

**FALLBACK PATH (Local Testing with SQLite):**
- No SQL Server required! ✅
- Works on any machine
- Includes realistic test data (20 records)
- Perfect for demo/development
- Automatically activated when SQL Server unavailable

### SQLite Test Database Details

**Location:** `tests/test.db`

**Table:** `container_demo`

**Records:** 20 realistic test records with:
- **CONT_ID:** 1001-1020
- **CHE Values (Strad IDs):** SC001, SC006, SC012, SC027, SC028, SC031, SC039, SC049, SC052, SC062, SC063, SC083, SC085, SC095, SC110, SC111, SC115, SC127
- **Actions:** PICKED and GROUNDED
- **Timestamps:** 2026-06-25 10:01:00 to 10:20:00

### Configuring SQLite Fallback

Edit `system_config.json`:

```json
{
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=invalid-server;...",
  
  "enable_local_testing_mode": true,
  "use_sqlite_fallback": true,
  "sqlite_db_path": "tests/test.db",
  "fallback_data_source": "sqlite"
}
```

**Key Parameters:**
- `enable_local_testing_mode: true` - Enables fallback when SQL Server fails
- `use_sqlite_fallback: true` - Uses SQLite instead of SQL Server
- `sqlite_db_path` - Path to test database
- `fallback_data_source: "sqlite"` - Selects SQLite fallback (OPTION 0)


### Running with SQLite

```bash
# 1. Verify test database exists
dir tests\test.db
# Output should show: test.db

# 2. Run system (will automatically use SQLite fallback)
python -m src.strad_monitoring.main

# 3. Watch for fallback activation in logs
# You'll see:
# ⚠ Database unavailable - using local testing mode with fallback
# [INFO] Loading strads from SQLite database: tests/test.db
# [INFO] Selected 10 strads from SQLite: ['SC001', 'SC006', ...]
```

### All Fallback Options

The system supports 4 fallback options (in priority order):

| Option | Source | Configuration | Best For |
|--------|--------|---------------|----------|
| **OPTION 0** (Recommended) | SQLite database | `fallback_data_source: "sqlite"` | Most realistic local testing |
| **OPTION 1** | KITTI dataset | `fallback_data_source: "kitti"` | Testing with camera data |
| **OPTION 2** | CSV/JSON file | `fallback_data_source: "local_folder"` | Custom test scenarios |
| **OPTION 3** | Random generation | `fallback_data_source: "random"` | Quick smoke testing |

See `.kiro/specs/strad-carrier-monitoring-automation/LOCAL_TESTING_GUIDE.md` for detailed documentation.

---

## Running Individual Components

### Testing Database Interface

```python
from src.strad_monitoring.database.database_interface import DatabaseInterface
from src.strad_monitoring.config.system_config import ConfigurationManager

# Load config
config = ConfigurationManager.load_config("system_config.json")

# Initialize database interface
db = DatabaseInterface(
    connection_string=config.database_connection_string,
    enable_fallback=True,
    use_sqlite_fallback=True,
    sqlite_db_path="tests/test.db",
    fallback_data_source="sqlite"
)

# Test: Get eligible strads
strads = db.get_eligible_strads(count=10)
print(f"Retrieved {len(strads)} strads: {strads}")
# Output: Retrieved 10 strads: ['SC001', 'SC085', 'SC039', ...]

# Test: Health check
is_healthy = db.health_check()
print(f"Database health: {'OK' if is_healthy else 'FAIL'}")
```

### Testing DL Classifier

```python
import numpy as np
from src.strad_monitoring.dl_classifier.classifier_wrapper import DLClassifierWrapper
from src.strad_monitoring.config.system_config import ConfigurationManager

# Load config
config = ConfigurationManager.load_config("system_config.json")

# Initialize classifier
classifier = DLClassifierWrapper(
    model_checkpoint_path=config.model_checkpoint_path,
    config=config.dl_model_config,
    device='cuda'
)

# Create test snapshot (or load from file)
snapshot = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

# Classify
result = classifier.classify_snapshot(snapshot)
print(f"Classification: {result.severity}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Processing time: {result.processing_time_ms:.1f}ms")
```


### Testing Storage Manager

```python
from src.strad_monitoring.storage.storage_manager import StorageManager
import numpy as np
from datetime import datetime

# Initialize storage manager
storage = StorageManager(
    temp_storage_path="temp_snapshots",
    permanent_storage_path="critical_snapshots",
    retention_days=30
)

# Create test snapshot
snapshot = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

# Test: Store temporary snapshot
temp_path = storage.store_temporary_snapshot("SC042", snapshot)
print(f"Temporary snapshot saved: {temp_path}")

# Test: Persist critical snapshot
permanent_path = storage.persist_critical_snapshot("SC042", snapshot, datetime.now())
print(f"Critical snapshot saved: {permanent_path}")

# Test: Check available space
space_gb = storage.check_available_space()
print(f"Available disk space: {space_gb:.1f} GB")

# Test: Clear temporary storage
storage.clear_all_temporary()
print("Temporary storage cleared")
```

---

## Configuration Guide

### Configuration File Structure

The `system_config.json` file contains all system parameters:

```json
{
  "_comment_database": "===== DATABASE CONFIGURATION =====",
  "database_connection_string": "...",
  
  "_comment_paths": "===== FILE PATHS =====",
  "excel_file_path": "...",
  "model_checkpoint_path": "...",
  "temp_snapshot_path": "...",
  "permanent_snapshot_path": "...",
  "log_file_path": "...",
  
  "_comment_timing": "===== TIMING CONFIGURATION =====",
  "cycle_schedule_cron": "0 * * * *",
  "strad_selection_count": 10,
  "cooldown_hours": 1,
  
  "_comment_snapshot": "===== SNAPSHOT CONFIGURATION =====",
  "snapshot_min_width": 640,
  "snapshot_min_height": 480,
  "snapshot_retention_days": 30,
  "log_retention_days": 14,
  
  "_comment_fallback": "===== FALLBACK CONFIGURATION =====",
  "enable_local_testing_mode": true,
  "use_sqlite_fallback": true,
  "sqlite_db_path": "tests/test.db",
  "fallback_data_source": "sqlite",
  
  "_comment_dl_model": "===== DL MODEL CONFIGURATION =====",
  "dl_model_config": {
    "flow_network": "liteflownet2",
    "target_resolution": [640, 640],
    "confidence_threshold": 0.5,
    "enable_uncertainty": false
  }
}
```

### Configuration Scenarios

#### Scenario 1: Demo/Testing (No SQL Server)

**Use case:** Demonstrate system without production database access

```json
{
  "database_connection_string": "DRIVER={...};SERVER=invalid-server;...",
  "enable_local_testing_mode": true,
  "use_sqlite_fallback": true,
  "sqlite_db_path": "tests/test.db",
  "fallback_data_source": "sqlite"
}
```

**Result:** Uses SQLite test database, works offline


#### Scenario 2: Production (SQL Server Required)

**Use case:** Production deployment after management approval

```json
{
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=prod-server;DATABASE=StradMonitoring;Trusted_Connection=yes",
  "enable_local_testing_mode": false,
  "use_sqlite_fallback": false
}
```

**Result:** Requires SQL Server connection, fails fast if unavailable

#### Scenario 3: Development with KITTI Data

**Use case:** Test with realistic camera sequences from KITTI dataset

```json
{
  "database_connection_string": "DRIVER={...};SERVER=invalid-server;...",
  "enable_local_testing_mode": true,
  "use_sqlite_fallback": false,
  "fallback_data_source": "kitti",
  "fallback_data_path": "kitti_data"
}
```

**Result:** Loads strads from KITTI dataset sequences

### Key Configuration Parameters Explained

| Parameter | Purpose | Demo Value | Production Value |
|-----------|---------|------------|------------------|
| `enable_local_testing_mode` | Allow fallback when DB unavailable | `true` | `false` |
| `cycle_schedule_cron` | When to run cycles | `"0 * * * *"` (hourly) | `"0 * * * *"` |
| `strad_selection_count` | Strads per cycle | `10` | `10` |
| `cooldown_hours` | Re-check interval | `1` | `1` |
| `snapshot_retention_days` | How long to keep critical snapshots | `30` | `30` or `90` |
| `log_retention_days` | How long to keep logs | `14` | `30` |

---

## Understanding the Monitoring Cycle

### Cycle Workflow (Detailed)

```
┌─────────────────────────────────────────────────────┐
│ HOURLY TRIGGER: XX:00:00                            │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│ STEP 1: SELECT ELIGIBLE STRADS                      │
│ - Query database for strads                         │
│ - Exclude: checked < 1 hour ago                     │
│ - Exclude: critical strads in exclusion list        │
│ - Return: 10 random eligible strads                 │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│ STEP 2: PROCESS EACH STRAD SERIALLY (1-10)         │
│                                                     │
│ For each strad:                                     │
│   ┌─────────────────────────────────────────────┐  │
│   │ 2a. OPEN VIDEO FEED                         │  │
│   │     - ExcelAutomation.open_video_feed()     │  │
│   │     - Waits for VLC window (30s timeout)    │  │
│   └─────────────┬───────────────────────────────┘  │
│                 │                                   │
│                 ▼                                   │
│   ┌─────────────────────────────────────────────┐  │
│   │ 2b. CAPTURE SNAPSHOT                        │  │
│   │     - Wait 5 seconds for feed stabilization │  │
│   │     - VLCCapture.capture_snapshot()         │  │
│   │     - Verify dimensions ≥ 640x480           │  │
│   └─────────────┬───────────────────────────────┘  │
│                 │                                   │
│                 ▼                                   │
│   ┌─────────────────────────────────────────────┐  │
│   │ 2c. CLASSIFY ALIGNMENT                      │  │
│   │     - DLClassifier.classify_snapshot()      │  │
│   │     - Returns: none/moderate/critical       │  │
│   │     - Includes confidence score (0.0-1.0)   │  │
│   └─────────────┬───────────────────────────────┘  │
│                 │                                   │
│                 ▼                                   │
│   ┌─────────────────────────────────────────────┐  │
│   │ 2d. STORE RESULTS                           │  │
│   │     IF critical:                            │  │
│   │       - Save snapshot permanently           │  │
│   │       - Add to exclusion list               │  │
│   │     ALWAYS:                                 │  │
│   │       - Store result in database            │  │
│   │       - Update check history                │  │
│   │       - Clear temporary snapshot            │  │
│   └─────────────────────────────────────────────┘  │
│                                                     │
│ Continue with next strad...                         │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│ STEP 3: CYCLE COMPLETION                            │
│ - Clear all temporary storage                       │
│ - Log cycle statistics                              │
│ - Wait for next hour trigger                        │
└─────────────────────────────────────────────────────┘
```


### Classification Severity Levels

| Severity | Probability Range | Meaning | Action |
|----------|------------------|---------|--------|
| **none** | < 0.3 | Camera properly aligned | Continue monitoring |
| **moderate** | 0.3 - 0.7 | Minor misalignment | Track consecutively, warn after 3 in 24h |
| **critical** | ≥ 0.7 | Severe misalignment | Exclude from rotation, save snapshot |

### Cooldown Period

**Purpose:** Prevent redundant checks of same strad

**Duration:** 1 hour (configurable)

**Implementation:**
- After processing strad SC042 at 10:15:00
- SC042 becomes ineligible until 11:15:00
- After 11:15:00, SC042 returns to eligible pool

**Edge case:** If all strads checked within last hour, system selects fewer than 10

### Critical Strad Exclusion

**Trigger:** Strad classified as "critical"

**Actions:**
1. Snapshot saved permanently (30-day retention)
2. Strad added to `critical_strad_exclusions` table
3. Strad excluded from all future selection queries

**Return to rotation:**
- Requires manual confirmation from maintenance technician
- Technician submits adjustment confirmation via ConfirmationHandler
- Strad immediately removed from exclusion list
- Eligible for selection in next cycle

---

## Interpreting Logs and Output

### Log File Locations

**Daily log files:** `{log_file_path}/monitoring_log_YYYY-MM-DD.txt`

**Example:** `C:\StradMonitoring\logs\monitoring_log_2024-01-15.txt`

**Retention:** 14 days (configurable)

### Log Format

```
2024-01-15 14:30:22,145 [INFO] [MonitoringOrchestrator] Cycle started: 10 strads selected
2024-01-15 14:30:22,678 [INFO] [DatabaseInterface] Query returned strads: SC042, SC078, SC115, ...
2024-01-15 14:30:23,112 [INFO] [ExcelAutomation] Opening video feed for SC042
2024-01-15 14:30:28,445 [INFO] [VLCCapture] Snapshot captured: 1920x1080 pixels
2024-01-15 14:30:29,234 [INFO] [DLClassifier] Classification: critical, confidence: 0.87
2024-01-15 14:30:29,890 [INFO] [StorageManager] Critical snapshot saved: D:\critical_snapshots\2024-01-15\SC042_20240115_143029.jpg
```

**Format breakdown:**
```
YYYY-MM-DD HH:MM:SS,mmm [LEVEL] [ComponentName] Message
│                       │        │                │
│                       │        │                └─ Log message
│                       │        └─ Component that generated log
│                       └─ Log level: INFO, WARNING, ERROR, CRITICAL
└─ Timestamp (precise to millisecond)
```

### Key Log Messages

#### Cycle Start
```
================================================================================
MONITORING CYCLE #5 STARTED
Cycle start time: 2024-01-15 14:00:00
================================================================================
```

#### Strad Processing
```
Processing strad 1/10: SC042
  ✓ SC042 processed successfully: critical (confidence: 0.87, time: 12.3s)

Processing strad 2/10: SC078
  ✗ SC078 processing failed: VLC window not found after 30s timeout
```


#### Cycle Completion
```
================================================================================
MONITORING CYCLE #5 COMPLETED
Cycle end time: 2024-01-15 14:32:15
Duration: 1935.2 seconds (32.3 minutes)
Strads processed: 9
Strads failed: 1
Success rate: 9/10
================================================================================
```

#### Database Fallback Activation
```
[WARNING] SQL Server unavailable: [Error details]. Using local testing fallback: sqlite
[INFO] Loading strads from SQLite database: tests/test.db
[INFO] Selected 10 strads from SQLite: ['SC001', 'SC006', 'SC012', ...]
```

#### Errors
```
[ERROR] [ExcelAutomation] Failed to open video feed for SC042: VLC timeout after 30s
[ERROR] [VLCCapture] Snapshot capture failed after 3 retries: Window not found
[CRITICAL] [DatabaseInterface] SQL Server connection lost - cannot store results
```

### Reading Logs in Real-Time

**PowerShell (Windows):**
```powershell
# Tail log file (watch in real-time)
Get-Content C:\StradMonitoring\logs\monitoring_log_2024-01-15.txt -Wait -Tail 50

# Search for errors
Get-Content C:\StradMonitoring\logs\monitoring_log_*.txt | Select-String "ERROR"

# Search for specific strad
Get-Content C:\StradMonitoring\logs\monitoring_log_*.txt | Select-String "SC042"
```

**Command Prompt:**
```cmd
# View latest log
type C:\StradMonitoring\logs\monitoring_log_2024-01-15.txt | more

# Search for errors
findstr /I "ERROR" C:\StradMonitoring\logs\*.txt
```

---

## Common Operations

### Start the System

```bash
# Navigate to project
cd C:\Users\Miles\Desktop\exp_2

# Activate virtual environment
.venv\Scripts\activate

# Start monitoring
python -m src.strad_monitoring.main

# System will:
# 1. Load configuration
# 2. Initialize components
# 3. Wait for next hour (XX:00:00)
# 4. Execute monitoring cycles hourly
```

### Stop the System (Graceful Shutdown)

**Method 1: Keyboard Interrupt**
```bash
# Press Ctrl+C in the terminal

# System will:
# 1. Set shutdown flag
# 2. Wait for current strad to complete (max 5 minutes)
# 3. Save partial results if timeout
# 4. Cleanup all resources (Excel COM, database connections)
# 5. Exit cleanly
```

**Method 2: Signal (Linux/Unix-style)**
```bash
# Send SIGTERM to process
kill -TERM <pid>

# Same graceful shutdown as Ctrl+C
```

### Check System Status

**View logs:**
```bash
# Latest log file
type C:\StradMonitoring\logs\monitoring_log_2024-01-15.txt | more

# Check for recent cycles
findstr "CYCLE.*COMPLETED" C:\StradMonitoring\logs\*.txt
```

**Check database:**
```sql
-- View recent classifications
SELECT TOP 20 *
FROM classification_results
ORDER BY created_at DESC;

-- Check critical strads
SELECT * FROM critical_strad_exclusions
WHERE adjustment_confirmed_at IS NULL;
```


### Force Immediate Cycle (Testing)

**Note:** For testing only - production uses hourly schedule

```python
from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator
from src.strad_monitoring.config.system_config import ConfigurationManager

# Load config
config = ConfigurationManager.load_config("system_config.json")

# Create orchestrator
orchestrator = MonitoringOrchestrator(config)

# Run single cycle immediately (doesn't start scheduler)
result = orchestrator.run_cycle()

# View results
print(f"Cycle #{result['cycle_number']}")
print(f"Duration: {result['duration_seconds']:.1f}s")
print(f"Processed: {result['strads_processed']}")
print(f"Failed: {result['strads_failed']}")

# Cleanup
orchestrator._cleanup_components()
```

### View Critical Snapshots

Critical snapshots are saved in date-organized folders:

```
D:\StradMonitoring\critical_snapshots\
├── 2024-01-15\
│   ├── SC042_20240115_143029.jpg
│   ├── SC078_20240115_145511.jpg
│   └── SC115_20240115_151234.jpg
├── 2024-01-16\
│   └── SC123_20240116_090234.jpg
└── 2024-01-17\
    ├── SC027_20240117_102215.jpg
    └── SC063_20240117_143022.jpg
```

**View in Explorer:**
```bash
explorer D:\StradMonitoring\critical_snapshots
```

**Count by date:**
```cmd
dir /S D:\StradMonitoring\critical_snapshots\2024-01-15
```

---

## Testing the Confirmation Handler

### What is the Confirmation Handler?

When a strad is classified as **critical**, it's excluded from monitoring rotation. The **ConfirmationHandler** allows maintenance technicians to report camera adjustments, returning the strad to active monitoring.

### Using the Confirmation Handler

```python
from src.strad_monitoring.orchestration.confirmation_handler import ConfirmationHandler
from src.strad_monitoring.database.database_interface import DatabaseInterface
from src.strad_monitoring.config.system_config import ConfigurationManager
from datetime import datetime

# Load config and initialize database
config = ConfigurationManager.load_config("system_config.json")
db = DatabaseInterface(
    connection_string=config.database_connection_string,
    enable_fallback=True,
    use_sqlite_fallback=True,
    sqlite_db_path="tests/test.db",
    fallback_data_source="sqlite"
)

# Create confirmation handler
handler = ConfirmationHandler(database_interface=db)

# Scenario 1: Confirm adjustment for critical strad
result = handler.process_confirmation(
    che_number="SC042",
    technician_id="TECH001",
    confirmation_timestamp=datetime.now(),
    notes="Adjusted camera mounting bracket, verified alignment"
)

print(result['message'])
# Output: "Confirmation processed successfully for SC042. Strad removed from exclusion list and eligible for monitoring in next cycle."

# Scenario 2: Try to confirm non-critical strad
result = handler.process_confirmation(
    che_number="SC001",  # Not in exclusion list
    technician_id="TECH001",
    confirmation_timestamp=datetime.now()
)

print(result['message'])
# Output: "No exclusion exists for SC001. No action taken."
```


### Confirmation Workflow

```
1. Strad classified as CRITICAL
   │
   ├─> Snapshot saved permanently
   ├─> Added to critical_strad_exclusions table
   └─> Excluded from all future monitoring cycles

2. Maintenance technician inspects and adjusts camera
   │
   └─> Physical adjustment completed

3. Technician submits confirmation
   │
   └─> ConfirmationHandler.process_confirmation(che_number, technician_id, ...)

4. System processes confirmation
   │
   ├─> Records confirmation in adjustment_confirmations table
   ├─> Removes strad from critical_strad_exclusions
   └─> Resets check history timestamp

5. Strad returns to monitoring rotation
   │
   └─> Eligible for selection in next cycle
```

### Database Records

**Before confirmation:**
```sql
SELECT * FROM critical_strad_exclusions WHERE strad_id = 'SC042';
-- strad_id | added_at            | adjustment_confirmed_at | technician_id
-- SC042    | 2024-01-15 14:30:29 | NULL                    | NULL
```

**After confirmation:**
```sql
SELECT * FROM critical_strad_exclusions WHERE strad_id = 'SC042';
-- No rows (removed from exclusion list)

SELECT * FROM adjustment_confirmations WHERE strad_id = 'SC042';
-- id | strad_id | technician_id | confirmation_timestamp  | notes
-- 1  | SC042    | TECH001       | 2024-01-15 16:45:00     | Adjusted camera mounting bracket
```

---

## Troubleshooting

### Issue: "Configuration file not found"

**Symptoms:**
```
✗ Configuration file not found: system_config.json
```

**Solution:**
```bash
# Check if file exists
dir system_config.json

# If missing, create from example
copy system_config.json.example system_config.json
notepad system_config.json
```

### Issue: "Database connectivity check failed"

**Symptoms:**
```
✗ Database connectivity verification failed
Cannot start monitoring system without database access
```

**Solutions:**

1. **Enable local testing mode (for demo):**
   ```json
   {
     "enable_local_testing_mode": true,
     "use_sqlite_fallback": true,
     "sqlite_db_path": "tests/test.db",
     "fallback_data_source": "sqlite"
   }
   ```

2. **Check SQL Server connectivity (for production):**
   ```bash
   # Test connection
   python -c "import pyodbc; conn = pyodbc.connect('YOUR_CONNECTION_STRING'); print('Connected')"
   ```

3. **Verify ODBC driver installed:**
   ```bash
   python -c "import pyodbc; print(pyodbc.drivers())"
   # Should show: ODBC Driver 17 for SQL Server
   ```

### Issue: "CUDA not available" or slow classification

**Symptoms:**
```
[WARNING] CUDA not available - using CPU
Classification taking > 30 seconds per snapshot
```

**Solution:**
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"

# If False, check:
# 1. NVIDIA driver installed: nvidia-smi
# 2. CUDA toolkit installed: nvcc --version
# 3. PyTorch with CUDA: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu117
```


### Issue: "Excel automation failed"

**Symptoms:**
```
[ERROR] [ExcelAutomation] Failed to open video feed: Excel application not found
```

**Solutions:**

1. **Verify Excel installed:**
   ```bash
   python -c "import win32com.client; excel = win32com.client.Dispatch('Excel.Application'); print(f'Excel Version: {excel.Version}'); excel.Quit()"
   ```

2. **Check Excel file exists:**
   ```bash
   dir "C:\VideoEncoder\spreader_encoder.xlsx"
   ```

3. **Run as user with Excel permissions** (for Windows service)

### Issue: "VLC window not found"

**Symptoms:**
```
[ERROR] [VLCCapture] VLC window not found after 30s timeout
```

**Solutions:**

1. **Verify VLC installed:**
   ```bash
   "C:\Program Files\VideoLAN\VLC\vlc.exe" --version
   ```

2. **Check VLC window title manually:**
   - Open VLC
   - Verify window title is exactly "VLC media player"

3. **Increase timeout** (temporary workaround):
   Edit `src/strad_monitoring/excel_automation/excel_automation.py`:
   ```python
   timeout_seconds = 60  # Increase from 30
   ```

### Issue: "Insufficient disk space"

**Symptoms:**
```
[ERROR] [StorageManager] Failed to save snapshot: Disk full
[WARNING] Available disk space: 2.3 GB (below 10 GB threshold)
```

**Solutions:**

1. **Clean old snapshots:**
   ```bash
   # Remove snapshots older than 30 days
   forfiles /P "D:\StradMonitoring\critical_snapshots" /S /D -30 /C "cmd /c del @path"
   ```

2. **Clean old logs:**
   ```bash
   forfiles /P "C:\StradMonitoring\logs" /M *.txt /D -14 /C "cmd /c del @path"
   ```

3. **Reduce retention in config:**
   ```json
   {
     "snapshot_retention_days": 15,
     "log_retention_days": 7
   }
   ```


### Issue: System hangs or doesn't process strads

**Symptoms:**
- System initializes but never processes strads
- Cycle never starts

**Possible causes:**

1. **Waiting for hourly trigger:**
   - System only runs at XX:00:00
   - If started at 10:32:00, waits until 11:00:00
   - **Solution:** Wait for next hour or force immediate cycle (see Common Operations)

2. **No eligible strads:**
   - All strads checked within last hour
   - All strads in critical exclusion list
   - **Solution:** Check database, adjust cooldown, or confirm critical strads

3. **Component initialization failure:**
   - Check logs for initialization errors
   - Verify all paths in config exist

### Issue: "Permission denied" writing snapshots/logs

**Symptoms:**
```
[ERROR] [StorageManager] Permission denied: C:\StradMonitoring\critical_snapshots\...
```

**Solutions:**

1. **Check directory permissions:**
   ```cmd
   icacls C:\StradMonitoring\critical_snapshots
   ```

2. **Grant permissions:**
   ```cmd
   icacls C:\StradMonitoring /grant "%USERNAME%:(OI)(CI)F" /T
   ```

3. **Run as administrator** (temporary):
   - Right-click Command Prompt → Run as Administrator
   - Run system from admin prompt

---

## Important Notes

### Demo vs Production Readiness

**✅ DEMO READY - What Works:**
- Complete end-to-end workflow (database → Excel → VLC → classification → storage)
- All 8 components integrated and functional
- Error handling and recovery
- Graceful shutdown with resource cleanup
- Comprehensive logging
- SQLite fallback for testing (20 realistic records)
- Configuration management
- Property-based tests (34 properties)
- Unit and integration tests

**⏳ PENDING APPROVAL - What Needs Management Sign-Off:**
- **Production database deployment:** Schema creation, permissions, stored procedures
- **Production video encoder access:** Integration with actual Excel video encoder infrastructure
- **Production model training:** Full training with complete dataset (not sample data)
- **24/7 automated operation:** Windows service deployment, monitoring
- **Alert system integration:** Email/SMS notifications for critical failures
- **Load testing:** Stress testing with concurrent strads, long-term reliability
- **Security audit:** Credentials management, access controls
- **Disaster recovery:** Backup procedures, failover mechanisms

### Performance Considerations

**Typical cycle time:** 20-40 minutes for 10 strads

**Breakdown per strad:**
- Excel automation: 5-10 seconds
- VLC stabilization wait: 5 seconds
- Snapshot capture: 1-2 seconds
- DL classification: 5-15 seconds (GPU), 30-60 seconds (CPU)
- Database operations: 1-2 seconds
- **Total per strad:** ~20-35 seconds (GPU) or ~50-80 seconds (CPU)

**Cycle delays:**
- Allowed to exceed 50 minutes if needed (requirement 9.6)
- Does NOT skip strads to meet time limit
- Continues until all 10 strads processed


### Known Limitations

1. **Windows-only:** Requires Windows for Excel COM automation
2. **Single-threaded:** Processes strads serially (not parallel)
3. **VLC dependency:** Requires VLC media player for snapshot capture
4. **GPU recommended:** CPU inference is 3-5x slower
5. **Network required:** Production mode needs SQL Server connectivity
6. **No web interface:** Command-line and log-based monitoring only

### Safety Features

**Cooldown period (1 hour):**
- Prevents redundant checking of same strad
- Distributes monitoring across fleet
- Configurable via `cooldown_hours`

**Critical exclusion:**
- Automatically removes severely misaligned cameras from rotation
- Requires explicit confirmation to return to monitoring
- Prevents wasted processing on known-bad units

**Graceful shutdown:**
- Waits up to 5 minutes for current strad to complete
- Saves partial results if forced shutdown
- Cleans up resources (COM objects, database connections, temp files)

**Error recovery:**
- Component failures don't stop entire cycle
- Failed strads are logged and skipped
- Remaining strads continue processing
- 3 retry attempts for transient errors

### Data Retention

| Data Type | Retention | Location | Cleanup |
|-----------|-----------|----------|---------|
| Critical snapshots | 30 days | `permanent_snapshot_path` | Automatic daily |
| Classification results | 90 days* | SQL Server database | Manual SQL script |
| Check history | 7 days | SQL Server database | Automatic daily |
| Log files | 14 days | `log_file_path` | Automatic daily |
| Temporary snapshots | End of cycle | `temp_snapshot_path` | Automatic after cycle |

*Configurable in database cleanup scripts


### Best Practices

**For Demonstration:**
1. Use SQLite fallback (`fallback_data_source: "sqlite"`)
2. Test with small cycles (5 strads instead of 10)
3. Review logs in real-time during demo
4. Prepare critical snapshot examples in advance
5. Have confirmation handler workflow ready to demonstrate

**For Production Deployment (Post-Approval):**
1. Disable local testing mode (`enable_local_testing_mode: false`)
2. Use SQL Server production connection
3. Install as Windows service for 24/7 operation
4. Set up log monitoring and alerting
5. Configure backup procedures for critical snapshots
6. Document maintenance procedures
7. Train operators on confirmation workflow

**For Development:**
1. Use KITTI fallback for realistic camera data
2. Test individual components in isolation first
3. Run property-based tests frequently
4. Monitor GPU memory usage during classification
5. Keep test database (`tests/test.db`) up to date

---

## Additional Resources

### Documentation

- **DEPLOYMENT.md** - Detailed installation and deployment guide
- **ARCHITECTURE.md** - System architecture and component design
- **SQLITE_FALLBACK_INTEGRATION.md** - SQLite fallback mechanism details
- **LOCAL_TESTING_GUIDE.md** - All fallback options and local testing
- **Requirements Document** - `.kiro/specs/.../requirements.md`
- **Design Document** - `.kiro/specs/.../design.md`
- **Tasks Document** - `.kiro/specs/.../tasks.md`

### Support

For questions or issues:
1. Check logs for detailed error messages
2. Review troubleshooting section above
3. Consult DEPLOYMENT.md for infrastructure issues
4. Review design document for component details
5. Contact development team with log excerpts and system specs

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-15  
**System Status:** DEMO READY / PENDING MANAGEMENT APPROVAL FOR PRODUCTION  
**Maintained By:** Strad Monitoring Development Team

