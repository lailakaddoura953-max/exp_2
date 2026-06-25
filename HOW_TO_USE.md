# How to Use: Strad Carrier Monitoring Automation

## Current Project Status

**Status**: Demo Presentable (Proof of Concept Stage)

This system is currently in the **proof of concept phase** and requires official approval from management/supervisors before any production deployment. The implementation demonstrates the full workflow architecture but needs thorough testing and validation.

---

## Table of Contents

1. [What Works Right Now](#what-works-right-now)
2. [Quick Start: Test Individual Components](#quick-start-test-individual-components)
3. [Available Demo Scripts](#available-demo-scripts)
4. [Testing with Local Data](#testing-with-local-data)
5. [Understanding the System Architecture](#understanding-the-system-architecture)
6. [Next Steps for POC Validation](#next-steps-for-poc-validation)

---

## What Works Right Now

### ✅ Fully Implemented Components

| Component | Status | What You Can Do |
|-----------|--------|-----------------|
| **DL Classifier** | ✅ Working | Classify camera misalignment from images |
| **Database Interface** | ✅ Working | Query/store data with SQLite fallback |
| **Storage Manager** | ✅ Working | Save snapshots to temp/permanent storage |
| **Moderate Tracker** | ✅ Working | Track consecutive moderate classifications |
| **Confirmation Handler** | ✅ Working | Process adjustment confirmations |
| **Orchestrator** | ✅ Working | Coordinate full monitoring cycles |
| **Configuration System** | ✅ Working | Load and validate settings |
| **Logging System** | ✅ Working | Structured logging with rotation |

### ⚠️ Requires External Dependencies

| Component | Status | Requirement |
|-----------|--------|-------------|
| **Excel Automation** | ⚠️ Needs Excel | Requires Microsoft Excel installed |
| **VLC Capture** | ⚠️ Needs VLC | Requires VLC Media Player installed |
| **SQL Server** | ⚠️ Fallback Available | Uses SQLite fallback if unavailable |

---

## Quick Start: Test Individual Components

### 1. Test DL Classifier on a Single Image

**Test with synthetic image** (works immediately):
```cmd
python test_single_image.py --synthetic
```

**Test with your own image**:
```cmd
python test_single_image.py --image path\to\your\image.jpg
```

**Test with demo video frame** (requires opencv-python):
```cmd
pip install opencv-python
python test_single_image.py --demo
```

**Expected Output**:
```
Classification: MODERATE
Confidence: 0.654
Processing time: 45.3 ms

🟡 MODERATE MISALIGNMENT DETECTED
   Action: Continue monitoring in regular rotation
   System: Will track consecutive occurrences
```

---

### 2. Test Database Interface with SQLite Fallback

```python
# test_database.py
import sys
sys.path.insert(0, 'src')

from strad_monitoring.database.database_interface import DatabaseInterface

# Initialize with SQLite fallback
db = DatabaseInterface(
    connection_string="",  # Empty triggers fallback
    enable_fallback=True,
    use_sqlite_fallback=True,
    sqlite_db_path='tests/test.db'
)

# Get eligible strads
strads = db.get_eligible_strads(count=10)
print(f"Eligible strads: {strads}")

# Store a classification result
db.store_classification_result(
    strad_id='SC042',
    classification='moderate',
    confidence=0.65,
    snapshot_path=None
)
print("✓ Classification result stored")
```

---

### 3. Test Moderate Classification Tracker

```cmd
python examples\moderate_tracker_demo.py
```

This demonstrates:
- Recording multiple classifications
- Tracking consecutive moderates
- Warning notification at 3 consecutive

---

### 4. Test Storage Manager

```python
# test_storage.py
import sys
import numpy as np
sys.path.insert(0, 'src')

from strad_monitoring.storage.storage_manager import StorageManager

# Initialize storage
storage = StorageManager(
    temp_storage_path='temp_snapshots',
    permanent_storage_path='permanent_snapshots',
    retention_days=30
)

# Create test image
test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

# Store temporarily
temp_path = storage.store_temporary_snapshot('SC042', test_image)
print(f"✓ Stored temporarily: {temp_path}")

# Persist as critical
from datetime import datetime
perm_path = storage.persist_critical_snapshot('SC042', test_image, datetime.now())
print(f"✓ Persisted permanently: {perm_path}")

# Cleanup
storage.clear_temporary_snapshot(temp_path)
print("✓ Temporary snapshot cleaned up")
```

---

## Available Demo Scripts

### Existing Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `test_single_image.py` | Test classifier on one image | `python test_single_image.py --synthetic` |
| `examples/moderate_tracker_demo.py` | Demo moderate tracking | `python examples/moderate_tracker_demo.py` |
| `scripts/example_inference.py` | Demo inference engine | `python scripts/example_inference.py` |
| `scripts/verify_installation.py` | Check dependencies | `python scripts/verify_installation.py` |

### Test Individual Workflow Steps

```python
# test_workflow_step_by_step.py
import sys
sys.path.insert(0, 'src')

from datetime import datetime
import numpy as np

# Step 1: Initialize all components
print("Step 1: Initializing components...")
from strad_monitoring.database.database_interface import DatabaseInterface
from strad_monitoring.storage.storage_manager import StorageManager
from strad_monitoring.dl_classifier.classifier_wrapper import DLClassifierWrapper
from strad_monitoring.database.moderate_tracker import ModerateClassificationTracker

db = DatabaseInterface(
    connection_string="",
    enable_fallback=True,
    use_sqlite_fallback=True,
    sqlite_db_path='tests/test.db'
)

storage = StorageManager(
    temp_storage_path='temp_snapshots',
    permanent_storage_path='permanent_snapshots',
    retention_days=30
)

classifier = DLClassifierWrapper(
    model_checkpoint_path='checkpoints/architecture_a_epoch_20.pt',
    config='config/architecture_a.yaml',
    device='cuda'
)

tracker = ModerateClassificationTracker(
    database_interface=db,
    time_window_hours=24
)

print("✓ All components initialized\n")

# Step 2: Get eligible strads
print("Step 2: Querying eligible strads...")
strads = db.get_eligible_strads(count=3)
print(f"✓ Found {len(strads)} eligible strads: {strads}\n")

# Step 3: Process one strad (simulated)
strad_id = strads[0] if strads else 'SC042'
print(f"Step 3: Processing {strad_id}...")

# Create synthetic snapshot
snapshot = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
print("  ✓ Snapshot captured (synthetic)")

# Store temporarily
temp_path = storage.store_temporary_snapshot(strad_id, snapshot)
print(f"  ✓ Stored temporarily: {temp_path}")

# Classify
result = classifier.classify_snapshot(snapshot)
print(f"  ✓ Classification: {result.severity} (confidence: {result.confidence:.3f})")

# Handle result based on classification
if result.severity == 'critical':
    perm_path = storage.persist_critical_snapshot(strad_id, snapshot, datetime.now())
    print(f"  ✓ Critical snapshot persisted: {perm_path}")
    db.add_to_critical_exclusion(strad_id, f"Critical misalignment (conf: {result.confidence:.3f})")
    print(f"  ✓ Added to critical exclusion list")
else:
    print(f"  ℹ Non-critical classification, no snapshot persistence")

# Store result
db.store_classification_result(
    strad_id=strad_id,
    classification=result.severity,
    confidence=result.confidence,
    snapshot_path=perm_path if result.severity == 'critical' else None
)
print(f"  ✓ Result stored in database")

# Track with moderate tracker
tracker.record_classification(strad_id, result.severity, result.confidence, datetime.now())
print(f"  ✓ Recorded in moderate tracker")

# Update check history
db.update_check_history(strad_id)
print(f"  ✓ Check history updated")

# Cleanup temporary
storage.clear_temporary_snapshot(temp_path)
print(f"  ✓ Temporary snapshot cleaned up\n")

print("=" * 80)
print("✓ Complete workflow step executed successfully!")
print("=" * 80)
```

---

## Testing with Local Data

### Option 1: SQLite Test Database (Recommended)

The system includes a SQLite test database with 20 pre-populated strad records:

```python
# Location: tests/test.db
# Records: SC001, SC006, SC012, SC027, SC028, SC031, SC039, SC049, 
#          SC052, SC062, SC063, SC083, SC085, SC095, SC110, SC111, 
#          SC115, SC127
```

**Test fallback**:
```cmd
python test_sqlite_fallback.py
```

### Option 2: Use Demo Videos

Extract frames from demo videos for testing:

```python
import cv2

# Extract frame from demo video
video_path = 'demo_videos/01_normal_operation.mp4'
cap = cv2.VideoCapture(video_path)
cap.set(cv2.CAP_PROP_POS_FRAMES, 30)  # Frame 30
ret, frame = cap.read()
cap.release()

# Now classify this frame
# ... (use classifier as shown above)
```

### Option 3: Synthetic Test Data

Generate random test images:

```python
import numpy as np

# Create synthetic 640x640 RGB image
test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

# Or create gradient pattern
x = np.linspace(0, 255, 640)
y = np.linspace(0, 255, 640)
X, Y = np.meshgrid(x, y)
gradient = np.stack([
    ((X + Y) / 2).astype(np.uint8),
    X.astype(np.uint8),
    Y.astype(np.uint8)
], axis=-1)
```

---

## Understanding the System Architecture

### Current Implementation Status

```
┌─────────────────────────────────────────────────────────────┐
│                    MONITORING ORCHESTRATOR                  │
│                                                             │
│  Status: ✅ Fully Implemented                              │
│  - Hourly cycle scheduling (APScheduler)                    │
│  - Serial strad processing                                  │
│  - Error recovery and retry logic                           │
│  - Graceful shutdown with completion wait                   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Database   │    │  DL Classifier│   │   Storage    │
│  Interface   │    │    Wrapper    │   │   Manager    │
│              │    │               │   │              │
│ Status: ✅   │    │  Status: ✅   │   │  Status: ✅  │
│              │    │               │   │              │
│ • SQL Server │    │ • PyTorch     │   │ • Temp save  │
│ • SQLite     │    │ • GPU/CPU     │   │ • Permanent  │
│   fallback   │    │ • 640x640     │   │ • Cleanup    │
└──────────────┘    └──────────────┘    └──────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Moderate   │    │ Confirmation │   │    Excel     │
│   Tracker    │    │   Handler    │   │  Automation  │
│              │    │               │   │              │
│ Status: ✅   │    │  Status: ✅   │   │  Status: ⚠️  │
│              │    │               │   │              │
│ • 24hr track │    │ • CHE valid   │   │ • Requires   │
│ • 3x warning │    │ • Exclusion   │   │   Excel      │
│ • Counter    │    │ • Reset check │   │   installed  │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Component Dependencies

**Can Work Standalone** (Test Immediately):
- ✅ DL Classifier
- ✅ Database Interface (with SQLite)
- ✅ Storage Manager
- ✅ Moderate Tracker
- ✅ Confirmation Handler
- ✅ Configuration System
- ✅ Logging System

**Requires External Systems** (For Full Workflow):
- ⚠️ Excel Automation → Needs Microsoft Excel
- ⚠️ VLC Capture → Needs VLC Media Player
- ⚠️ SQL Server → Works with SQLite fallback

---

## Next Steps for POC Validation

### Phase 1: Component Validation (You Are Here)
- [x] Test individual components work correctly
- [ ] Verify DL classifier accuracy on known images
- [ ] Test database operations with SQLite fallback
- [ ] Validate storage manager creates correct directory structure
- [ ] Confirm moderate tracker warning triggers correctly

### Phase 2: Integration Testing (Next)
- [ ] Test complete workflow with mocked Excel/VLC
- [ ] Verify error handling and retry logic
- [ ] Test graceful shutdown scenarios
- [ ] Validate cycle statistics and logging
- [ ] Check memory usage during extended operation

### Phase 3: POC Demonstration
- [ ] Prepare demonstration with synthetic data
- [ ] Document system capabilities and limitations
- [ ] Create POC presentation for management review
- [ ] Identify production requirements and gaps
- [ ] Obtain management/supervisor approval

### Phase 4: Production Preparation (After Approval)
- [ ] Set up production SQL Server connection
- [ ] Configure Excel automation with actual spreadsheet
- [ ] Test VLC capture with live camera feeds
- [ ] Implement monitoring and alerting
- [ ] Create deployment runbook
- [ ] Conduct security review
- [ ] Perform load and stress testing

---

## Important Notes

### Proof of Concept Status

🚨 **This system is NOT ready for production deployment**

Current status: **Demo Presentable / POC Stage**

Required before production:
1. ✅ Component implementation complete
2. ⏳ POC validation in progress
3. ⏳ Management/supervisor review pending
4. ⏳ Production environment setup pending
5. ⏳ Security and compliance review pending
6. ⏳ Load testing and performance validation pending

### What "Demo Presentable" Means

**You CAN**:
- ✅ Demonstrate individual component functionality
- ✅ Show the complete workflow architecture
- ✅ Test with synthetic/local data
- ✅ Validate the design approach
- ✅ Present to management for POC approval

**You CANNOT**:
- ❌ Deploy to production systems
- ❌ Process real strad carrier data
- ❌ Connect to production SQL Server
- ❌ Automate actual Excel/VLC operations
- ❌ Make operational decisions based on results

### Recommended Usage Right Now

1. **Test components individually** using the scripts provided above
2. **Validate the workflow** with synthetic data
3. **Document findings** for POC presentation
4. **Prepare demonstration** for management review
5. **Gather requirements** for production deployment

---

## Getting Help

### Documentation Files

- `DEPLOYMENT.md` - Full deployment guide (for future reference)
- `HOW_TO_USE.md` - This guide (current capabilities)
- `SQLITE_FALLBACK_INTEGRATION.md` - SQLite testing documentation
- `LOCAL_TESTING_GUIDE.md` - Local testing without SQL Server
- `README.md` - Project overview

### Common Issues

**"Model checkpoint not found"**:
- You need a trained model checkpoint to run classification
- Train using: `python scripts/train_architecture_a.py`
- Or update `model_checkpoint_path` in `system_config.json`

**"Excel.Application COM object error"**:
- Excel automation requires Microsoft Excel installed
- Currently can be mocked for testing
- Not required for component validation

**"VLC window not found"**:
- VLC capture requires VLC Media Player installed
- Currently can be mocked for testing
- Not required for component validation

**"Database connection failed"**:
- System automatically falls back to SQLite if SQL Server unavailable
- Use `use_sqlite_fallback: true` in configuration
- SQLite test database: `tests/test.db`

---

## Contact and Approval

Before proceeding to production deployment:

1. **Document POC results** with this testing
2. **Prepare presentation** showing component functionality
3. **Submit POC proposal** to management/supervisor
4. **Obtain written approval** for production deployment
5. **Work with IT/DevOps** for production environment setup

**Current Status**: ✅ POC Components Complete, ⏳ Awaiting Management Review
