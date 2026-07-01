# Architecture Overview — Strad Carrier Monitoring System (v2)

## What This System Does

Automatically monitors strad carrier camera feeds for misalignment issues. Every hour, it selects a batch of strads from a database, navigates to each camera's web viewer page, captures a screenshot, classifies it using a trained deep learning model, and records the result.

---

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Hourly Cycle (XX:00:00)                      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  1. SELECT STRADS                                                   │
│     Remote SQL Server (DSN) → get 10+ eligible strad IDs            │
│     Local JSON filter → remove recently-checked & critical strads   │
│     Result: 10 strads to process this cycle                         │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. LOOK UP CAMERA IP                                               │
│     ip_addresses.json (tab-separated SC# → IP mapping)              │
│     135 strads mapped to their Axis encoder IP addresses            │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. CAPTURE SCREENSHOT                                              │
│     Headless Chromium (Playwright) navigates to camera web viewer   │
│     Tries: /camera/index.html then /view/viewer_index.shtml?id=0   │
│     Logs in via username/password form                              │
│     Waits 15s for video to stabilize                                │
│     Takes full-window JPEG screenshot                               │
│     Saves: SC{id}_{YYYYMMDD}_{HHMMSS}.jpg                          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. CLASSIFY                                                        │
│     SimpleClassifierWrapper loads trained .pth model                 │
│     Classifies screenshot → none / moderate / critical              │
│     Returns severity + confidence score                             │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. STORE RESULTS                                                   │
│     Primary: SQL Server tables (when permissions available)         │
│     Fallback: data/monitoring_state.json (local file)               │
│     Critical snapshots → permanent storage                          │
│     Critical strads → excluded from future cycles until cleared     │
│     Check history → enables 1-hour cooldown between checks          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Map

```
src/strad_monitoring/
├── config/
│   ├── system_config.py          # SystemConfig dataclass + ConfigurationManager
│   └── ip_address_loader.py      # Parse ip_addresses.json → strad-to-IP mapping
│
├── database/
│   ├── database_interface.py     # SQL Server reads (DSN), write attempts
│   ├── local_state_store.py      # JSON fallback for writes (cooldown, results, exclusions)
│   └── moderate_tracker.py       # Tracks consecutive moderate classifications
│
├── video_capture/
│   └── web_capture.py            # Playwright-based headless browser screenshot capture
│
├── dl_classifier/
│   ├── classifier_wrapper.py     # DLClassifierWrapper (legacy inference engine)
│   └── simple_classifier_wrapper.py  # SimpleClassifierWrapper (current, lightweight)
│
├── orchestration/
│   ├── orchestrator.py           # Main loop: select → capture → classify → store
│   └── confirmation_handler.py   # Adjustment confirmation handling
│
├── storage/
│   └── storage_manager.py        # Temp + permanent snapshot file management
│
├── logging/
│   └── logging_system.py         # Centralized logging with file rotation
│
└── main.py                       # Entry point: load config → validate → start orchestrator
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `system_config.json` | Main config: DB connection, credentials, paths, timing |
| `config/ip_addresses.json` | Tab-separated SC# → camera IP mapping (135 entries) |
| `data/monitoring_state.json` | Auto-generated local state (check history, results, exclusions) |

---

## Key Design Decisions

### Why Playwright (headless browser) instead of RTSP/FFmpeg?

The camera IPs serve an Axis web viewer page with a login form and embedded video panel — not a raw RTSP stream. Direct RTSP access was tested and confirmed unreliable (browser access fails outright, VLC only renders one corner). A headless browser renders the actual page correctly and captures exactly what the model was trained on (full-window screenshots including the viewer UI chrome).

### Why JSON file for state instead of database writes?

Current database permissions are read-only (can SELECT strads, cannot CREATE TABLE or INSERT). Rather than block on getting DBA permissions, the system uses a local JSON file as fallback — same data (check history, classification results, critical exclusions), just stored locally. The SQL creation script is ready for when permissions are granted.

### Why over-fetch strads from the database?

The remote SQL query doesn't know about local cooldown/exclusion state (since we can't write to its tables). So we request more than 10 strads, then filter locally using `monitoring_state.json`, then cap back to 10. This ensures we always process a full batch even when some strads are excluded.

### Why two Axis URL patterns?

Different firmware versions serve the viewer at different paths (`/camera/index.html` vs `/view/viewer_index.shtml?id=0`). Since firmware can be upgraded independently per camera, both are tried in order. This avoids maintaining a per-camera URL column in the config file.

---

## Data Flow Detail

### Strad Selection
```
SQL Server (via DSN=Db_test)
    │
    │  SELECT top N strad IDs
    │  (query from .sql file, filters by existing server-side logic)
    │
    ▼
Raw list: [SC001, SC042, SC075, SC087, ...]  (N = 10 + known exclusions)
    │
    │  Local filter (monitoring_state.json):
    │  - Remove strads checked within last hour
    │  - Remove critical-excluded strads
    │
    ▼
Filtered list: [SC042, SC075, SC087, ...]  (capped to 10)
```

### Screenshot Capture (per strad)
```
IPAddressLoader.get_ip("SC042") → "192.168.1.141"
    │
    ▼
WebCapture.capture_frame("192.168.1.141", "SC042", snapshot_dir)
    │
    ├─ Launch headless Chromium
    ├─ Try http://192.168.1.141/camera/index.html
    │   └─ If 404/timeout → try /view/viewer_index.shtml?id=0
    ├─ Detect login form → fill username/password → submit
    ├─ Wait 15 seconds (stabilization)
    ├─ Take full-window screenshot (JPEG, quality 85)
    ├─ Validate: exists, non-empty, meets min dimensions
    ├─ Save: SC042_20260701_100015.jpg
    └─ Close browser
    │
    ▼
(filepath, success=True)
```

### Classification
```
Load screenshot from file → numpy RGB array
    │
    ▼
SimpleClassifierWrapper.classify_snapshot(array)
    │
    ├─ Resize to 640x640
    ├─ Normalize (ImageNet stats)
    ├─ Forward pass through trained model
    ├─ Apply confidence threshold
    │
    ▼
ClassificationResult:
  - severity: "none" | "moderate" | "critical"
  - confidence: 0.0 - 1.0
  - processing_time_ms
```

### Result Storage
```
Try: DB write (store_classification_result, update_check_history)
    │
    ├─ Success → done
    │
    └─ Failure (table doesn't exist) →
         Fallback: local_state.store_classification(...)
         Fallback: local_state.record_check(...)
         Fallback: local_state.add_critical_exclusion(...)  [if critical]
```

---

## Scheduling

- **APScheduler** with `CronTrigger(hour="*", minute=0, second=0)`
- Cycle runs at the top of every hour
- Cycle target: <50 minutes for 10 strads
- Actual timing: ~15-20 seconds per strad (mostly stabilization delay) = ~3 minutes total
- Graceful shutdown via SIGINT/SIGTERM (waits for current strad to finish)

---

## Error Handling Philosophy

Every step in the cycle is wrapped in try/except. Failures are:
1. Logged with full context
2. Handled with fallback if available (e.g., local JSON when DB fails)
3. Skipped if no fallback (strad marked failed, cycle continues)

No single strad failure stops the cycle. The system processes as many as it can and reports results.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `playwright` | Headless browser for screenshot capture |
| `torch` | DL model inference |
| `pillow` | Image loading/saving |
| `numpy` | Array operations for classifier input |
| `pyodbc` | SQL Server connection via DSN |
| `apscheduler` | Hourly cycle scheduling |
| `pyyaml` | Config file parsing |

---

## File Naming Convention

Screenshots: `SC{3-digit-id}_{YYYYMMDD}_{HHMMSS}.jpg`

Examples:
- `SC042_20260701_100015.jpg`
- `SC087_20260701_100245.jpg`

---

## Current Limitations

1. **Database writes** — read-only access, results stored locally in JSON until CREATE TABLE permissions are granted
2. **Login form selectors** — using broad best-effort CSS selectors for the Axis login form; may need tightening once actual page HTML is inspected
3. **Model accuracy** — classification labels are approximate; model was retrained on full-window captures but may need further tuning
4. **Single-threaded capture** — strads processed serially (one browser instance at a time); parallelization possible but not implemented

---

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure
# 1. Copy config/ip_addresses_template.json → config/ip_addresses.json
# 2. Fill in real camera IPs
# 3. Set credentials in system_config.json (web_viewer_username/password)
# 4. Set model checkpoint path

# Start
python -m src.strad_monitoring.main
```

---

## How to Test

```bash
# Run all tests (excluding legacy Excel/VLC tests)
python -m pytest tests/ --ignore=tests/unit/test_excel_automation.py --ignore=tests/unit/test_excel_open_video_feed.py --ignore=tests/unit/test_vlc_capture.py

# Run just the local state store tests
python -m pytest tests/test_local_state_store.py -v

# Single strad integration test
python test_orchestrator_single.py
```
