# Project Architecture Overview
## Strad Carrier Monitoring Automation

**Last Updated:** 2024  
**Status:** Demo Presentable (Not Production Ready)  
**Requires:** Official POC approval before deployment

---

## Executive Summary

The Strad Carrier Monitoring Automation system integrates deep learning camera misalignment detection with SQL Server database operations, Excel-based video feed automation, and VLC media player snapshot capture. The system is designed to automatically execute monitoring cycles every hour, processing 10 randomly selected Strad Carriers from a pool of 135 units (SC001-SC135).

**Current State:**
- ✅ All core components implemented and tested individually
- ✅ Orchestration layer complete with scheduler integration
- ✅ Fallback mechanisms for local testing without external dependencies
- ⚠ Integration testing and end-to-end validation pending
- ⚠ Official proof of concept document required for production

---

## System Architecture

### High-Level Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                     MONITORING ORCHESTRATOR                           │
│                    (MonitoringOrchestrator)                          │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                  APScheduler (Hourly Trigger)                   │ │
│  │               CronTrigger: hour="*", minute=0                   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Coordinates:                                                         │
│  • Strad Selection (DatabaseInterface)                              │
│  • Video Feed Opening (ExcelAutomation)                             │
│  • Snapshot Capture (VLCCapture)                                    │
│  • DL Classification (DLClassifierWrapper)                          │
│  • Result Storage (StorageManager + DatabaseInterface)              │
│  • Moderate Tracking (ModerateClassificationTracker)                │
│  • Adjustment Confirmation (ConfirmationHandler)                    │
└───────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  PRODUCTION   │       │  FALLBACK     │       │  UTILITIES    │
│  COMPONENTS   │       │  COMPONENTS   │       │               │
└───────────────┘       └───────────────┘       └───────────────┘
        │                         │                         │
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ SQL Server    │       │ SQLite DB     │       │ Logging       │
│ Excel COM     │       │ KITTI Data    │       │ Config Mgr    │
│ VLC Window    │       │ CSV/JSON      │       │ Retry Logic   │
│ PyTorch GPU   │       │ Random Data   │       │ Timing Utils  │
└───────────────┘       └───────────────┘       └───────────────┘
```


### Component Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ENTRY POINT LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│  main.py                                                            │
│  • CLI argument parsing (--config)                                  │
│  • Configuration loading and validation                             │
│  • Database connectivity verification                               │
│  • Orchestrator initialization and startup                          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│  orchestrator.py                                                    │
│  • Hourly cycle scheduling (APScheduler)                           │
│  • Serial strad processing workflow                                 │
│  • Error handling and recovery                                      │
│  • Graceful shutdown with completion wait                           │
│                                                                      │
│  confirmation_handler.py                                            │
│  • Adjustment confirmation processing                               │
│  • Critical exclusion removal                                       │
│  • Check history reset                                              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌─────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ INTERFACE LAYER │   │  PROCESSING LAYER │   │   DATA LAYER     │
├─────────────────┤   ├──────────────────┤   ├──────────────────┤
│ ExcelAutomation │   │ DLClassifier     │   │ DatabaseInterface│
│ • Video encoder │   │ • PyTorch model  │   │ • SQL Server     │
│ • COM automation│   │ • Severity map   │   │ • SQLite fallback│
│                 │   │ • Confidence     │   │ • Strads query   │
│ VLCCapture      │   │                  │   │ • Result storage │
│ • Window find   │   │ StorageManager   │   │ • Check history  │
│ • Screenshot    │   │ • Temp storage   │   │ • Exclusion list │
│ • Validation    │   │ • Permanent path │   │                  │
│ • 3 retries     │   │ • JPEG compress  │   │ ModerateTracker  │
│                 │   │ • Cleanup        │   │ • Counter track  │
└─────────────────┘   └──────────────────┘   │ • Warning @3     │
                                              └──────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         UTILITY LAYER                               │
├─────────────────────────────────────────────────────────────────────┤
│  config/system_config.py       │  logging/logging_system.py         │
│  • JSON loading                │  • Daily rotation                  │
│  • Validation                  │  • Structured format               │
│  • Singleton pattern           │  • 14-day retention                │
│                                │                                    │
│  utils/retry.py                │  utils/timing.py                   │
│  • Exponential backoff         │  • Elapsed time                    │
│  • 3 attempts: 1s, 2s, 4s      │  • Cooldown check                  │
│                                │  • Timestamp format                │
│  utils/exceptions.py           │  utils/alerting.py                 │
│  • Custom hierarchy            │  • Notification system             │
│  • Component-specific          │  • Critical alerts                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Workflows

### Workflow 1: Hourly Monitoring Cycle

**Trigger:** APScheduler CronTrigger at XX:00:00 every hour

**Steps:**
1. **Query Eligible Strads** (DatabaseInterface)
   - PRIMARY PATH: SQL Server stored procedure `strad_action_check_by_id_and_timestamp`
   - FALLBACK PATH: SQLite database (20 test strads)
   - Filters: Cooldown > 1 hour, not in critical exclusion
   - Returns: 10 unique strad IDs

2. **Serial Processing** (for each strad)
   - Process one strad at a time
   - Complete all 6 steps before starting next
   - Continue with remaining strads if one fails

3. **Temporary Storage Cleanup**
   - Clear all temp snapshots at cycle end
   - Always executes in finally block

4. **Cycle Logging**
   - Log start/end timestamps
   - Record strads processed/failed counts
   - Calculate cycle duration
   - Warn if > 50 minutes

**Error Handling:**
- Component failures: Log error, mark strad as failed, continue
- Database unavailable: Use fallback data source
- VLC timeout: Discard strad, retry later in same cycle
- Classification error: Log error, skip strad


### Workflow 2: Single Strad Processing (6 Steps)

```
STEP 1: Excel Video Feed Opening
├─ Call: ExcelAutomation.open_video_feed(strad_id)
├─ Action: Insert CHE_Number into "spreader video encoder" button
├─ Wait: 30-second timeout for VLC window
├─ Success: VLC window found → Continue to Step 2
└─ Failure: VLC not found → Return error, discard strad for cycle

STEP 2: VLC Snapshot Capture
├─ Wait: 5 seconds for feed stabilization
├─ Call: VLCCapture.capture_snapshot()
├─ Action: Find VLC window, bring to foreground, capture screenshot
├─ Retry: 3 attempts with 2-second intervals
├─ Validate: Dimensions >= 640x480 pixels
├─ Success: Valid snapshot → Continue to Step 3
└─ Failure: All retries failed → Return error

STEP 3: Temporary Storage
├─ Call: StorageManager.store_temporary_snapshot(strad_id, snapshot)
├─ Format: {strad_id}_{uuid}.jpg
├─ Compression: JPEG quality 85
├─ Pattern: Write to .tmp → Verify → Rename
├─ Success: Temp path returned → Continue to Step 4
└─ Failure: Storage error → Return error

STEP 4: DL Classification
├─ Call: DLClassifierWrapper.classify_snapshot(snapshot)
├─ Model: InferenceEngine (PyTorch)
├─ Device: CUDA (GPU) or CPU fallback
├─ Timeout: 10 seconds max
├─ Output: Severity (none/moderate/critical), Confidence (0.0-1.0)
├─ Mapping: <0.3=none, 0.3-0.7=moderate, ≥0.7=critical
├─ Conservative: confidence<0.6 → moderate
├─ Alert: confidence=0.0 → notify OT developers
├─ Success: Classification result → Continue to Step 5
└─ Failure: Timeout or error → Return error

STEP 5: Result Handling (Critical vs Moderate/None)
├─ IF severity == 'critical':
│   ├─ Persist snapshot: YYYY-MM-DD/{CHE_Number}_{timestamp}.jpg
│   ├─ Store result WITH snapshot path
│   ├─ Add to critical exclusion list
│   ├─ Update moderate tracker (resets counter)
│   └─ Continue to Step 6
├─ ELSE (moderate or none):
│   ├─ Store result WITHOUT snapshot path
│   ├─ Do NOT persist snapshot (Requirement 11.4)
│   ├─ Update moderate tracker:
│   │   ├─ IF moderate: Increment counter
│   │   ├─ IF counter == 3 within 24h: Generate warning
│   │   └─ IF none: Reset counter
│   └─ Continue to Step 6

STEP 6: Finalization & Cleanup
├─ Update check history: Set timestamp for 1-hour cooldown
├─ Clear temporary snapshot: Remove temp file
├─ Return result: {strad_id, success, classification, confidence, time}
└─ Orchestrator continues with next strad
```

### Workflow 3: Critical Strad Management

**Scenario:** Strad receives critical classification

**Automatic Actions:**
1. Snapshot persisted to permanent storage
2. Strad added to critical_strad_exclusions table
3. Excluded from future eligible strads queries
4. Remains excluded until adjustment confirmed

**Manual Intervention:**
1. Technician physically adjusts camera
2. Submits adjustment confirmation via ConfirmationHandler
3. System validates CHE_Number in exclusion list
4. Records confirmation timestamp and technician ID
5. Removes CHE_Number from exclusion list
6. Resets check history (allows immediate re-checking)
7. Strad becomes eligible in next cycle

### Workflow 4: Moderate Classification Tracking

**Scenario:** Strad receives moderate classification

**Tracking Logic:**
1. Record classification in database with timestamp
2. Query recent classifications within 24-hour window
3. Count consecutive moderate classifications
4. If count == 3: Generate warning notification
5. If non-moderate classification: Reset counter to 0
6. Do NOT exclude from rotation (continue monitoring)

**Warning Trigger:**
- Exactly 3 consecutive moderate within 24 hours
- Warning generated once (not on 4th, 5th, etc.)
- Notifies operators of developing problem

---

## Database Schema

### Tables (SQL Server Primary, SQLite Fallback)

**1. strad_action_check_by_id_and_timestamp**
```sql
CREATE TABLE strad_action_check_by_id_and_timestamp (
    strad_id VARCHAR(5) PRIMARY KEY,  -- SCXXX format
    last_check_timestamp DATETIME NOT NULL,
    INDEX idx_timestamp (last_check_timestamp)
);
```
Purpose: Track check history for 1-hour cooldown enforcement

**2. classification_results**
```sql
CREATE TABLE classification_results (
    result_id INT IDENTITY(1,1) PRIMARY KEY,
    strad_id VARCHAR(5) NOT NULL,
    classification VARCHAR(10) NOT NULL,  -- 'none', 'moderate', 'critical'
    confidence FLOAT NOT NULL,            -- 0.0 to 1.0
    snapshot_path VARCHAR(255),           -- NULL for moderate/none
    timestamp DATETIME NOT NULL DEFAULT GETDATE(),
    INDEX idx_strad_timestamp (strad_id, timestamp)
);
```
Purpose: Store all classification results for trend analysis

**3. critical_strad_exclusions**
```sql
CREATE TABLE critical_strad_exclusions (
    strad_id VARCHAR(5) PRIMARY KEY,
    exclusion_timestamp DATETIME NOT NULL DEFAULT GETDATE(),
    adjustment_confirmed_at DATETIME,
    technician_id VARCHAR(50),
    reason VARCHAR(255)
);
```
Purpose: Manage critical strads excluded from monitoring rotation

**4. container_demo** (SQLite fallback only)
```sql
CREATE TABLE container_demo (
    CONT_ID INTEGER,
    CHE TEXT NOT NULL,               -- Format: SC001 - SC135
    TIME_STAMP TEXT NOT NULL,
    CONT_ACTION TEXT NOT NULL,
    -- ... other fields ...
    PRIMARY KEY (CONT_ID, CHE)
);
```
Purpose: Test data for local development (20 strads available)

