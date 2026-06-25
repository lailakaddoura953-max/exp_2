# How to Use - Strad Carrier Monitoring Automation
## What You Can Test Right Now

**Last Updated:** 2024  
**Project Status:** Demo Presentable (Not Production Ready)  
**Note:** This system requires official proof of concept approval before deployment

---

## Table of Contents

1. [Quick Start - Test Single Image Classification](#quick-start---test-single-image-classification)
2. [Test SQLite Fallback Database](#test-sqlite-fallback-database)
3. [Test Individual Components](#test-individual-components)
4. [Test Moderate Classification Tracker](#test-moderate-classification-tracker)
5. [Run Full System Simulation](#run-full-system-simulation)
6. [Project Architecture Overview](#project-architecture-overview)
7. [Current State & Limitations](#current-state--limitations)

---

## Quick Start - Test Single Image Classification

### What You Can Do Right Now

Test the deep learning misalignment detection classifier on images without needing Excel, VLC, or SQL Server.

### Prerequisites

```cmd
# Activate virtual environment (if using)
.venv\Scripts\activate

# Ensure dependencies installed
pip install -r requirements.txt
```

### Option 1: Test with Synthetic Image

```cmd
python test_single_image.py --synthetic
```

**What happens:**
- Generates a synthetic test image (640x640 RGB gradient)
- Runs DL classifier inference
- Shows classification result: none/moderate/critical
- Displays confidence score and processing time

### Option 2: Test with Demo Video Frame

```cmd
python test_single_image.py --demo
```

**What happens:**
- Extracts frame 30 from `demo_videos/01_normal_operation.mp4`
- Classifies the extracted frame
- Shows detailed results with interpretation

**Requirements:**
- Demo video file must exist: `demo_videos/01_normal_operation.mp4`
- Needs opencv-python: `pip install opencv-python`

### Option 3: Test with Your Own Image

```cmd
python test_single_image.py --image path\to\your\image.jpg
```

**What happens:**
- Loads your image file
- Resizes to 640x640 if needed
- Runs classification
- Shows results

**Supported formats:** JPG, PNG, BMP

### Expected Output

```
================================================================================
SINGLE IMAGE CLASSIFICATION TEST
================================================================================

Loading image from: test_image.jpg
✓ Image loaded: (640, 640, 3) (H×W×C)

--------------------------------------------------------------------------------
Initializing DL Classifier...
--------------------------------------------------------------------------------
Using device: cuda
Model checkpoint: checkpoints/model_best.pth
Model config: config/architecture_a.yaml
✓ DL Classifier initialized

--------------------------------------------------------------------------------
Classifying image...
--------------------------------------------------------------------------------

================================================================================
CLASSIFICATION RESULTS
================================================================================

Image source: test_image.jpg
Image shape: (640, 640, 3)

Classification: MODERATE
Confidence: 0.456
Processing time: 123.4 ms

--------------------------------------------------------------------------------
INTERPRETATION
--------------------------------------------------------------------------------
🟡 MODERATE MISALIGNMENT DETECTED
   Action: Continue monitoring in regular rotation
   System: Will track consecutive occurrences
   Warning: Notification after 3 consecutive moderate results

⚠ LOW CONFIDENCE WARNING
   Confidence (0.456) is below 0.6 threshold
   System assigns 'moderate' classification as conservative default

================================================================================
✓ Classification completed successfully
================================================================================
```

---

## Test SQLite Fallback Database

### What You Can Do Right Now

Test the database interface without needing SQL Server connection.

### Check Available Test Data

```cmd
# View SQLite database content
sqlite3 tests\test.db "SELECT CHE, COUNT(*) as records FROM container_demo GROUP BY CHE;"
```

**Expected output:**
```
SC001|3
SC006|2
SC012|1
SC027|1
...
```

**20 Strad Carriers available:** SC001, SC006, SC012, SC027, SC028, SC031, SC039, SC049, SC052, SC062, SC063, SC083, SC085, SC095, SC110, SC111, SC115, SC127

### Test Database Interface

```cmd
python test_sqlite_fallback.py
```

**What this tests:**
- ✓ SQLite database connection
- ✓ Loading strads from SQLite
- ✓ CHE_Number format validation (SCXXX)
- ✓ Eligible strad selection with cooldown filtering
- ✓ Fallback mechanism when SQL Server unavailable

**Expected output:**
```
Testing SQLite Fallback Integration
====================================

Test 1: Load strads from SQLite database
----------------------------------------
✓ Loaded 18 unique strads from SQLite
✓ All strads have valid CHE_Number format (SCXXX)

Test 2: Get eligible strads (no cooldown)
------------------------------------------
✓ Retrieved 10 eligible strads
✓ All returned strads are valid

Test 3: Test configuration loading
-----------------------------------
✓ System config loaded successfully
✓ SQLite fallback options present in config

All tests passed!
```

---

## Test Individual Components

### 1. Test Moderate Classification Tracker

```cmd
python test_moderate_tracker_simple.py
```

**What this tests:**
- Recording classifications for strads
- Tracking consecutive moderate classifications
- Warning notification at 3 consecutive moderates within 24 hours
- Counter reset on non-moderate classification

**Expected output:**
```
Testing ModerateClassificationTracker
======================================

Test 1: Record moderate classification
✓ Classification recorded for SC042

Test 2: Query consecutive count
✓ Consecutive moderate count: 1

Test 3: Record 3rd consecutive moderate (should trigger warning)
⚠ Warning: SC042 has 3 consecutive moderate classifications within 24 hours

All tests passed!
```

### 2. Test Storage Manager

```cmd
python -c "from src.strad_monitoring.storage.storage_manager import StorageManager; import numpy as np; sm = StorageManager('temp_snapshots', 'permanent_snapshots', 30); test_img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8); path = sm.store_temporary_snapshot('SC042', test_img); print(f'✓ Snapshot saved: {path}')"
```

**What this tests:**
- Creating temporary snapshot storage
- JPEG compression (quality 85)
- Atomic write pattern (write to .tmp → verify → rename)
- Filename format: `{strad_id}_{uuid}.jpg`

### 3. Test Timing Utilities

```cmd
python -c "from src.strad_monitoring.utils.timing import calculate_elapsed_time, is_in_cooldown, format_timestamp; from datetime import datetime, timedelta; now = datetime.now(); past = now - timedelta(minutes=30); print(f'Elapsed: {calculate_elapsed_time(past, now)} seconds'); print(f'In cooldown: {is_in_cooldown(past, now)}'); print(f'Formatted: {format_timestamp(now)}')"
```

**Expected output:**
```
Elapsed: 1800.0 seconds
In cooldown: True
Formatted: 2024-01-15 14:30:45
```

### 4. Test Configuration Manager

```cmd
python -c "from src.strad_monitoring.config.system_config import ConfigurationManager; config = ConfigurationManager.load_config('system_config.json'); print(f'✓ Config loaded'); print(f'Database: {config.database_connection_string[:50]}...'); print(f'Fallback enabled: {config.enable_local_testing_mode}')"
```

---

## Test Moderate Classification Tracker

### Interactive Demo

```cmd
python examples\moderate_tracker_demo.py
```

**What this does:**
- Simulates processing multiple strads
- Records classifications (none/moderate/critical)
- Tracks consecutive moderate patterns
- Demonstrates warning notification at 3 consecutive moderates

**Sample output:**
```
==============================================
Moderate Classification Tracker Demo
==============================================

Simulating classification recordings...

Recording classification for SC042: moderate (confidence: 0.45)
  → Consecutive moderate count: 1

Recording classification for SC042: moderate (confidence: 0.52)
  → Consecutive moderate count: 2

Recording classification for SC042: moderate (confidence: 0.48)
  ⚠ WARNING: SC042 has 3 consecutive moderate classifications!
  → Consecutive moderate count: 3

Recording classification for SC042: none (confidence: 0.85)
  → Counter reset - classification changed to: none
  → Consecutive moderate count: 0
```

---

## Run Full System Simulation

### Simulated Cycle (No External Dependencies)

**Note:** This requires mocking Excel, VLC, and SQL Server since they're external dependencies.

```cmd
# Create a test script to run one simulated cycle
python -c "
from src.strad_monitoring.config.system_config import ConfigurationManager
from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator

# Load configuration
config = ConfigurationManager.load_config('system_config.json')

# Create orchestrator
print('Creating orchestrator...')
orchestrator = MonitoringOrchestrator(config)
print('✓ Orchestrator initialized')

# Get statistics
stats = orchestrator.get_statistics()
print(f'Cycle count: {stats[\"cycle_count\"]}')
print(f'Total strads processed: {stats[\"total_strads_processed\"]}')
print(f'Is running: {stats[\"is_running\"]}')
"
```

**What happens:**
- Loads system configuration
- Initializes all 7 components (DatabaseInterface, ExcelAutomation, VLCCapture, DLClassifierWrapper, StorageManager, ModerateTracker, ConfirmationHandler)
- Sets up APScheduler with hourly trigger
- Shows orchestrator statistics

**Expected output:**
```
Creating orchestrator...
================================================================================
MONITORING ORCHESTRATOR INITIALIZATION
================================================================================
Initializing components...
  Initializing DatabaseInterface...
  ✓ DatabaseInterface initialized
  Initializing ExcelAutomation...
  ✓ ExcelAutomation initialized
  ...
✓ Orchestrator initialized

Cycle count: 0
Total strads processed: 0
Is running: False
```

---

## Project Architecture Overview

### Component Structure

```
src/strad_monitoring/
├── config/                     # Configuration management
│   ├── system_config.py       # ConfigurationManager, SystemConfig dataclass
│   └── __init__.py
│
├── logging/                    # Logging system
│   ├── logging_system.py      # Daily rotation, structured format
│   └── __init__.py
│
├── database/                   # Database interface
│   ├── database_interface.py  # SQL Server + SQLite fallback
│   ├── moderate_tracker.py    # Moderate classification tracking
│   └── __init__.py
│
├── excel_automation/           # Excel COM automation
│   ├── excel_automation.py    # Video encoder control
│   └── __init__.py
│
├── vlc_capture/               # VLC snapshot capture
│   ├── vlc_capture.py         # Window capture with retry
│   └── __init__.py
│
├── dl_classifier/             # DL classification wrapper
│   ├── classifier_wrapper.py  # InferenceEngine integration
│   └── __init__.py
│
├── storage/                    # Snapshot storage management
│   ├── storage_manager.py     # Temporary + permanent storage
│   └── __init__.py
│
├── orchestration/             # Main orchestration layer
│   ├── orchestrator.py        # MonitoringOrchestrator (cycle management)
│   ├── confirmation_handler.py # Adjustment confirmation handling
│   └── __init__.py
│
├── utils/                      # Utility functions
│   ├── exceptions.py          # Custom exception hierarchy
│   ├── retry.py               # Retry decorator with backoff
│   ├── timing.py              # Timing and cooldown utilities
│   ├── alerting.py            # Alert notification system
│   └── __init__.py
│
└── main.py                     # Main entry point
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     HOURLY MONITORING CYCLE                      │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. Query Eligible Strads (DatabaseInterface)                   │
│    - SQL Server (PRIMARY) or SQLite (FALLBACK)                  │
│    - Filter: cooldown > 1 hour, not in critical exclusion       │
│    - Returns: 10 unique strad IDs (SCXXX format)                │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────┐
        │   FOR EACH STRAD (Serial Processing)        │
        └─────────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌─────────────────────┐       ┌─────────────────────┐
│ 2. Open Video Feed  │       │ 6. Update Check     │
│    (Excel → VLC)    │       │    History          │
│    - 30s timeout    │       │    - Current time   │
│    - Discard if     │       │    - 1hr cooldown   │
│      fail           │       └─────────────────────┘
└─────────────────────┘                 ▲
        │                               │
        ▼                               │
┌─────────────────────┐                 │
│ 3. Capture Snapshot │                 │
│    (VLC Window)     │                 │
│    - 5s stabilize   │                 │
│    - 3 retries      │                 │
│    - 640x480 min    │                 │
└─────────────────────┘                 │
        │                               │
        ▼                               │
┌─────────────────────┐                 │
│ 4. DL Classify      │                 │
│    (PyTorch)        │                 │
│    - Severity map   │                 │
│    - Confidence     │                 │
│    - 10s timeout    │                 │
└─────────────────────┘                 │
        │                               │
        ├───────┬───────┬───────────────┘
        │       │       │
        ▼       ▼       ▼
    ┌─────┐ ┌──────┐ ┌──────┐
    │CRIT │ │MODER │ │NONE  │
    └─────┘ └──────┘ └──────┘
        │       │       │
        │       └───┬───┘
        │           │
        ▼           ▼
┌─────────────┐ ┌─────────────┐
│5a. Critical │ │5b. Moderate │
│  - Persist  │ │  - Store    │
│    snapshot │ │    result   │
│  - Add to   │ │  - Track    │
│    exclusion│ │    counter  │
│  - Store w/ │ │  - Warn @3  │
│    path     │ │    consec   │
└─────────────┘ └─────────────┘
```

### Component Dependencies

```
MonitoringOrchestrator
├── ConfigurationManager (system_config.json)
├── LoggingSystem (daily rotation)
├── DatabaseInterface
│   ├── pyodbc (SQL Server) OR
│   └── sqlite3 (Fallback)
├── ExcelAutomation
│   └── win32com.client (Windows COM)
├── VLCCapture
│   └── win32gui, pyautogui
├── DLClassifierWrapper
│   ├── torch (PyTorch)
│   └── InferenceEngine (existing DL model)
├── StorageManager
│   └── PIL (JPEG compression)
├── ModerateClassificationTracker
│   └── DatabaseInterface
└── ConfirmationHandler
    └── DatabaseInterface
```

---

## Current State & Limitations

### ✅ What's Implemented (Demo Presentable)

**Core Components:**
- ✅ Configuration management with JSON validation
- ✅ Logging system with daily rotation and 14-day retention
- ✅ Database interface with SQL Server + SQLite fallback
- ✅ Storage manager for temporary and permanent snapshots
- ✅ DL classifier wrapper integrating existing inference engine
- ✅ Moderate classification tracker with 3-consecutive warning
- ✅ Adjustment confirmation handler for critical exclusion removal
- ✅ Timing utilities for cooldown calculation
- ✅ Retry decorator with exponential backoff
- ✅ Custom exception hierarchy

**Orchestration:**
- ✅ MonitoringOrchestrator with APScheduler integration
- ✅ Single strad processing workflow (6 steps)
- ✅ Complete cycle orchestration (serial processing)
- ✅ Error handling and recovery (continue with remaining strads)
- ✅ Graceful shutdown with completion wait (5-minute timeout)
- ✅ Signal handlers (SIGINT, SIGTERM)

**Entry Points:**
- ✅ Main entry point (`src/strad_monitoring/main.py`)
- ✅ CLI with `--config` argument support
- ✅ Configuration validation with startup refusal

**Documentation:**
- ✅ Deployment guide (DEPLOYMENT.md)
- ✅ Requirements.txt with pinned versions
- ✅ SQLite fallback integration guide
- ✅ Local testing guide with 3 fallback options

**Testing:**
- ✅ SQLite fallback verification script
- ✅ Single image classification test script
- ✅ Moderate tracker demo script
- ✅ VLC capture unit tests (25 tests passing)
- ✅ Confirmation handler unit tests (32 tests passing)

### ⚠ Current Limitations (Demo Environment)

**External Dependencies (Not Connected):**
- ⚠ Excel COM automation requires Microsoft Excel installed
- ⚠ VLC capture requires VLC Media Player installed
- ⚠ SQL Server connectivity requires production database access
- ⚠ GPU inference requires CUDA-capable GPU

**Not Production-Ready:**
- ⚠ No integration tests for complete workflow
- ⚠ No end-to-end tests with mocked components
- ⚠ No property-based tests for correctness properties
- ⚠ No performance benchmarking or load testing
- ⚠ No monitoring and alerting integration
- ⚠ No Windows service configuration tested
- ⚠ No official proof of concept document
- ⚠ No manager/supervisor approval

**Testing Gaps:**
- Missing: End-to-end cycle test with all components
- Missing: Critical strad workflow integration test
- Missing: Moderate classification workflow integration test
- Missing: 34 property-based tests for correctness validation
- Missing: Windows service deployment verification

### 🔧 What You Can Test Locally (Right Now)

**Without External Dependencies:**
1. ✅ Single image classification (synthetic, demo video, custom images)
2. ✅ SQLite database fallback (20 test strads available)
3. ✅ Moderate classification tracker
4. ✅ Storage manager (temporary and permanent storage)
5. ✅ Configuration loading and validation
6. ✅ Timing and cooldown utilities
7. ✅ Exception handling and retry logic
8. ✅ Orchestrator initialization (component setup)

**With External Dependencies (Manual Setup Required):**
9. ⚠ Excel automation (requires Excel + video encoder spreadsheet)
10. ⚠ VLC capture (requires VLC player + active video window)
11. ⚠ SQL Server connectivity (requires production database access)
12. ⚠ GPU inference (requires CUDA-capable GPU)

### 📋 Next Steps for Production Readiness

**Before Official Deployment:**
1. **Proof of Concept Document**
   - Formal POC with results and analysis
   - Manager/supervisor review and approval
   - Sign-off on architecture and approach

2. **Integration Testing**
   - End-to-end workflow tests with mocked components
   - Critical strad workflow verification
   - Moderate classification workflow verification

3. **Property-Based Testing**
   - Implement 34 correctness properties
   - Validate requirements with hypothesis tests
   - Ensure 100% property test pass rate

4. **Performance Testing**
   - Benchmark cycle execution time
   - Memory usage profiling
   - GPU utilization monitoring
   - Load testing with concurrent cycles

5. **Production Environment Setup**
   - SQL Server database schema creation
   - Excel video encoder configuration
   - VLC media player installation
   - Network connectivity verification

6. **Windows Service Deployment**
   - NSSM service configuration
   - Auto-restart and recovery settings
   - Service monitoring and health checks

7. **Monitoring and Alerting**
   - Integration with monitoring systems
   - Critical error alert configuration
   - Performance metric collection
   - Dashboard setup

---

## Run Web App with Real Data Integration

### What the Web App Does

The web app provides a visual interface for:
- Viewing demo videos of normal operation and impact scenarios
- Testing live inference with image uploads
- **NEW:** Connecting to strad_monitoring backend for real data
- **NEW:** Displaying real classification results and snapshots
- **NEW:** Live inference with real DL classifier

### Important: Why Two Servers?

The web app requires **TWO servers**:

1. **Backend Server (port 5000)** - Flask API
   - Handles strad_monitoring integration
   - Provides REST API endpoints
   - Runs DL classification

2. **Frontend Server (port 8000)** - HTTP file server
   - Serves HTML, CSS, JS files
   - Required for proper CORS handling
   - Browser can't access backend from file://

**Note:** Opening `docs\index.html` directly won't work! You'll get CORS errors. Use the frontend server.

### Step-by-Step: Run the Web App Locally

#### Quick Method: Use the Automated Launcher

```cmd
# Navigate to project directory
cd c:\Users\Miles\Desktop\exp_2

# Run the launcher script
start_web_app.bat
```

**What this does:**
- ✅ Starts backend server in new window (port 5000)
- ✅ Starts frontend server in new window (port 8000)
- ✅ Opens browser to http://localhost:8000
- ✅ Everything configured automatically

**You'll see 3 windows open:**
1. Launcher window (this one)
2. Backend server window
3. Frontend server window

**Keep all server windows open while using the web app!**

---

#### Manual Method: Step-by-Step

If you prefer manual control or the batch file doesn't work:

**Step 1: Open First Terminal - Start Backend Server**

```cmd
# Navigate to project directory (if not already there)
cd c:\Users\Miles\Desktop\exp_2

# Activate virtual environment
.venv\Scripts\activate

# Start the Flask backend server
python docs\backend\app.py
```

**Expected Output:**
```
============================================================
Camera Misalignment Detection - Backend API
============================================================

Strad Monitoring Connected: True/False
Database Connected: True/False
DL Classifier Loaded: True/False

Starting Flask server on http://localhost:5000
API Endpoints:
  - GET  /                     Health check
  - POST /api/inference        Run inference on camera images
  - GET  /api/model/status     Check model status
  - GET  /api/strads/recent    Get recent strad classifications
  - GET  /api/snapshot/<id>    Get snapshot image for strad
  - GET  /api/strads/stats     Get classification statistics

Press CTRL+C to stop the server
============================================================
```

**What the backend does:**
- ✓ Checks if strad_monitoring components are available
- ✓ Loads system_config.json if it exists
- ✓ Connects to database (or uses SQLite fallback)
- ✓ Loads DL classifier model if available
- ✓ Starts Flask server on port 5000
- ✓ Provides REST API for web app

**If you see errors:**
- "Strad monitoring components not available" → That's OK! Backend runs in mock mode
- "Config file not found" → That's OK! Backend uses fallback mode
- "Database not connected" → That's OK! Backend returns placeholder data
- "DL classifier not available" → That's OK! Backend uses mock classification

**Important:** Keep this terminal open! Do NOT close it.

---

**Step 2: Open Second Terminal - Start Frontend Server**

**Important:** Do NOT close the first terminal! The backend must stay running.

Open a new terminal (Windows key → type "cmd" → Enter)

```cmd
# Navigate to project directory
cd c:\Users\Miles\Desktop\exp_2

# Activate virtual environment
.venv\Scripts\activate

# Start the frontend HTTP server
python start_frontend_server.py
```

**Expected Output:**
```
================================================================================
STRAD CARRIER MONITORING - FRONTEND SERVER
================================================================================

Serving files from: docs/
Server running on: http://localhost:8000

================================================================================
HOW TO USE:
================================================================================

1. Keep this terminal open (frontend server)
2. In another terminal, start the backend:
   python docs\backend\app.py

3. Open in your browser:
   http://localhost:8000

4. Check connection status in top right corner
   - Green dot (●) = Backend connected
   - Red dot (○) = Disconnected (demo mode)

================================================================================
Press Ctrl+C to stop the server
================================================================================
```

**What the frontend server does:**
- ✓ Serves HTML, CSS, JavaScript files
- ✓ Runs on port 8000
- ✓ Enables proper CORS for API calls
- ✓ Required for backend connection to work

**Important:** Keep this terminal open too!

---

**Step 3: Open Web App in Browser**

```cmd
# Option A: Command line (opens in default browser)
start http://localhost:8000

# Option B: Manual - paste this in your browser:
http://localhost:8000
```

**Important:** Must use `http://localhost:8000` - NOT `file://` path!

---

**Step 4: Check Connection Status**

**In the web app (browser), look at the top right corner:**

**Connected Mode:**
```
● Strad Monitoring: Connected
```
- Green dot (●) = Backend is connected
- Strad monitoring components are available
- Real data will be loaded from database
- Live inference will use real DL classifier

**Disconnected Mode:**
```
○ Strad Monitoring: Disconnected
```
- Red dot (○) = Backend is not connected or unavailable
- Demo mode active (placeholder data)
- Live inference will use mock classifier

#### Step 5: Test the Features

**A. Test Demo Videos (Works Always)**
1. Click any "View Demo" button on the kanban cards
2. Watch the demo video play
3. Click "Details" to see scenario information
4. Click X or press Escape to close

**B. Test Live Inference Upload (Bottom of Page)**
1. Scroll down to "🔬 Test Live Inference" section
2. Click the drop zone or drag an image file
3. Image should preview
4. Click "🚀 Run Inference"
5. Results will show:
   - If **connected**: Real DL classification with confidence
   - If **disconnected**: Mock classification results

**C. Check Real Data (If Connected)**
Open browser console (F12) and look for:
```javascript
Backend connection: {status: 'running', strad_monitoring_connected: true, ...}
Loaded recent strads: [{strad_id: 'SC042', classification: 'moderate', ...}]
Real strad data available: {none: [...], moderate: [...], critical: [...]}
```

#### Step 6: Test Backend API Directly (Optional)

While backend is running, test the API endpoints:

**Health Check:**
```cmd
curl http://localhost:5000/
```

**Get Recent Strads:**
```cmd
curl http://localhost:5000/api/strads/recent?limit=5
```

**Get Statistics:**
```cmd
curl http://localhost:5000/api/strads/stats
```

**Model Status:**
```cmd
curl http://localhost:5000/api/model/status
```

#### Step 7: Stop the Servers

When you're done testing:

1. **Stop frontend server:** Go to terminal with frontend server, press `Ctrl+C`
2. **Stop backend server:** Go to terminal with backend server, press `Ctrl+C`
3. Both servers will shut down gracefully

### Troubleshooting

**Problem: Backend won't start**
```
Solution 1: Check if port 5000 is already in use
netstat -ano | findstr :5000

Solution 2: Check dependencies are installed
pip install flask flask-cors numpy pillow

Solution 3: Check Python virtual environment is activated
.venv\Scripts\activate
```

**Problem: Frontend server won't start**
```
Solution 1: Check if port 8000 is already in use
netstat -ano | findstr :8000

Solution 2: Check you're in the correct directory
cd c:\Users\Miles\Desktop\exp_2

Solution 3: Check docs/ folder exists
dir docs\index.html
```

**Problem: Web app shows disconnected**
```
Solution 1: Make sure BOTH servers are running
- Backend on port 5000 (one terminal)
- Frontend on port 8000 (another terminal)

Solution 2: Check you're using http://localhost:8000
NOT file:// path!

Solution 3: Try refreshing the web page (F5)

Solution 4: Check browser console (F12) for CORS errors
```

**Problem: CORS errors in browser console**
```
Error: "Access to fetch at 'http://localhost:5000' from origin 'file://' 
has been blocked by CORS policy"

Solution: You're opening the file directly!
Use frontend server instead:
  python start_frontend_server.py
  Then: http://localhost:8000
```

**Problem: Live inference shows mock results even when connected**
```
Solution: This is expected if DL classifier is not loaded
The backend will show: "DL Classifier Loaded: False"

To load real classifier:
1. Ensure model_checkpoint_path in system_config.json points to valid model
2. Restart backend server
```

**Problem: No real strad data shown**
```
Solution: This is expected if database has no records yet
The kanban board will show placeholder counts

To populate data:
1. Run test classifications (see test_single_image.py)
2. Results will be stored in database
3. Refresh web app to see real data
```

### What You Can Test Right Now

**Without Any Servers Running:**
- ❌ Nothing works properly due to CORS restrictions
- File:// access is blocked by browser security

**With Frontend Server Only (port 8000):**
- ✅ View all demo videos
- ✅ Open modal dialogs with scenario details
- ✅ UI and navigation (all buttons work)
- ✅ Drag and drop image upload interface
- ❌ Live inference won't work (backend needed)
- ❌ Connection status shows disconnected

**With Backend Running (Mock Mode - port 5000):**
- ✅ API endpoint testing works
- ✅ Mock classification responses
- ✅ Placeholder data responses
- ❌ Frontend can't connect without frontend server (CORS)

**With Both Servers Running (Full Demo Mode):**
- ✅ Connection status indicator shows connected
- ✅ Live inference with mock classification
- ✅ All demo videos and UI features
- ✅ API endpoint testing
- ✅ Placeholder data responses
- ✅ No CORS errors

**With Both Servers + Configuration (Full Mode):**
- ✅ Everything from demo mode
- ✅ Real DL classification on uploaded images
- ✅ Real strad data from database
- ✅ Snapshot image retrieval
- ✅ Classification statistics
- ✅ Real confidence scores and processing times

### Web App Features Reference

**Kanban Board:**
- 3 columns: Normal Operation | Misaligned - Low Priority | Misaligned - Critical
- Cards show strad scenarios with metrics
- "View Demo" plays video
- "Details" shows detailed information

**Live Inference Test:**
- Upload composite image (drag & drop or click)
- Single image OR multi-camera mode supported
- Shows classification result, confidence, 6-DOF pose
- Displays uncertainty estimates
- Download results as JSON
- Mock mode or real classifier (depending on backend)

**Connection Indicator:**
- Green dot (●) = Backend connected, real data available
- Red dot (○) = Disconnected, demo mode active

---

## Command Reference

### Quick Commands

```cmd
# ===== WEB APP COMMANDS =====

# Start backend server
python docs\backend\app.py

# Open web app in browser
start docs\index.html

# Test backend health
curl http://localhost:5000/

# Test recent strads API
curl http://localhost:5000/api/strads/recent

# ===== TESTING COMMANDS =====

# Test single image with synthetic data
python test_single_image.py --synthetic

# Test single image with demo video
python test_single_image.py --demo

# Test SQLite fallback
python test_sqlite_fallback.py

# Test moderate tracker
python test_moderate_tracker_simple.py

# Run moderate tracker demo
python examples\moderate_tracker_demo.py

# ===== DATABASE COMMANDS =====

# View SQLite database content
sqlite3 tests\test.db "SELECT * FROM container_demo LIMIT 10;"

# Count strads in SQLite
sqlite3 tests\test.db "SELECT COUNT(DISTINCT CHE) as strad_count FROM container_demo;"

# List all CHE numbers
sqlite3 tests\test.db "SELECT DISTINCT CHE FROM container_demo ORDER BY CHE;"

# ===== ORCHESTRATOR COMMANDS =====

# Check orchestrator initialization
python -c "from src.strad_monitoring.config.system_config import ConfigurationManager; from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator; config = ConfigurationManager.load_config('system_config.json'); orch = MonitoringOrchestrator(config); print('✓ Orchestrator initialized')"
```

---

## Configuration Guides

### SQL Server Database Setup

**Guide:** `SQL_SERVER_SETUP_GUIDE.md`

This guide covers:
- Finding your SQL Server connection information
- Connection string formats (Windows Auth vs SQL Auth)
- Database schema requirements
- Creating required tables and stored procedures
- Testing your connection

**Quick test:**
```cmd
python test_database_connection.py
```

### Excel File Configuration

**Guide:** `EXCEL_CONFIGURATION_GUIDE.md`

This guide covers:
- Locating your video encoder Excel file
- Configuring file path in system_config.json
- Excel spreadsheet structure requirements
- VBA macro setup for VLC launching
- Testing Excel automation

**Quick test:**
```cmd
python test_excel_connection.py
```

### Web App Setup

**Guide:** `WEB_APP_QUICK_START.md`

This guide covers:
- Starting the backend server
- Opening the web app
- Testing connection status
- Using live inference
- Troubleshooting common issues

**Quick start:**
```cmd
# Start backend
python docs\backend\app.py

# Open web app (in another terminal)
start docs\index.html
```

---

## Support and Questions

For questions or issues:
1. **Database setup:** Check `SQL_SERVER_SETUP_GUIDE.md`
2. **Excel configuration:** Check `EXCEL_CONFIGURATION_GUIDE.md`
3. **Web app:** Check `WEB_APP_QUICK_START.md`
4. **Deployment:** Check `DEPLOYMENT.md` for troubleshooting
5. **Local testing:** Review `LOCAL_TESTING_GUIDE.md` for fallback options
6. **SQLite fallback:** Check `SQLITE_FALLBACK_INTEGRATION.md` for database details
7. **Spec details:** Consult `.kiro/specs/strad-carrier-monitoring-automation/`

**Remember:** This is a demo presentable system. Official proof of concept and approval required before production deployment.
