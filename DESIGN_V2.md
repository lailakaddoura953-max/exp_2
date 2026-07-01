# Design Document — Class Dependencies & Flow Diagrams

## Class Dependency Graph

```
                         ┌──────────────┐
                         │   main.py    │
                         │  (entry pt)  │
                         └──────┬───────┘
                                │ creates
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                    MonitoringOrchestrator                          │
│                    (orchestration/orchestrator.py)                 │
│                                                                   │
│  Owns and coordinates all components below.                       │
│  Runs hourly cycle via APScheduler.                               │
└───┬────────┬────────┬────────┬─────────┬────────┬────────┬───────┘
    │        │        │        │         │        │        │
    ▼        ▼        ▼        ▼         ▼        ▼        ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌──────┐┌────────┐┌──────────┐
│Database││IPAddr  ││Web     ││DL      ││Store ││Moderate││Local     │
│Interf. ││Loader  ││Capture ││Classif.││Mgr   ││Tracker ││StateStore│
└───┬────┘└───┬────┘└───┬────┘└───┬────┘└──┬───┘└───┬────┘└────┬─────┘
    │         │         │         │        │        │          │
    │         │         │         │        │        │          │
    ▼         ▼         ▼         ▼        ▼        ▼          ▼
 SQL Server  JSON     Playwright  PyTorch  File    DB/JSON   JSON
 (DSN/ODBC)  file    (Chromium)   model   system  hybrid    file
```

---

## Detailed Class Relationships

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MonitoringOrchestrator                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  self.db_interface ──────────► DatabaseInterface                        │
│       │                           • get_eligible_strads(count)          │
│       │                           • store_classification_result(...)    │
│       │                           • update_check_history(strad_id)      │
│       │                           • add_to_critical_exclusion(...)      │
│       │                                                                 │
│  self.local_state ───────────► LocalStateStore                          │
│       │                           • record_check(strad_id)             │
│       │                           • store_classification(...)          │
│       │                           • add_critical_exclusion(...)        │
│       │                           • filter_eligible_strads(list)       │
│       │                           • get_recently_checked(hours)        │
│       │                           • get_critical_exclusions()          │
│       │                                                                 │
│  self.ip_loader ─────────────► IPAddressLoader                          │
│       │                           • get_ip(strad_id) → ip_address      │
│       │                           • get_all_mappings() → dict          │
│       │                           • validate() → errors                │
│       │                                                                 │
│  self.web_capture ───────────► WebCapture                               │
│       │                           • capture_frame(ip, strad_id, dir)   │
│       │                             → (filepath, success)              │
│       │                                                                 │
│  self.dl_classifier ─────────► SimpleClassifierWrapper                  │
│       │                           • classify_snapshot(numpy_array)      │
│       │                             → ClassificationResult             │
│       │                                                                 │
│  self.storage_manager ───────► StorageManager                           │
│       │                           • store_temporary_snapshot(...)       │
│       │                           • persist_critical_snapshot(...)      │
│       │                           • clear_temporary_snapshot(path)      │
│       │                           • clear_all_temporary()              │
│       │                                                                 │
│  self.moderate_tracker ──────► ModerateClassificationTracker            │
│       │                           • record_classification(...)         │
│       │                                                                 │
│  self.scheduler ─────────────► APScheduler (BlockingScheduler)          │
│                                   • hourly CronTrigger → run_cycle()   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Execution Flow Diagram

```
main.py
  │
  ├─ ConfigurationManager.load_config("system_config.json")
  │     └─ Returns SystemConfig dataclass
  │
  ├─ validate_database_connectivity(config)
  │
  ├─ MonitoringOrchestrator(config)
  │     ├─ _initialize_logging()
  │     ├─ _initialize_components()
  │     │     ├─ DatabaseInterface(connection_string, ...)
  │     │     ├─ LocalStateStore("data/monitoring_state.json")
  │     │     ├─ IPAddressLoader(ip_addresses_json_path)
  │     │     ├─ WebCapture(username, password, timeout, ...)
  │     │     ├─ SimpleClassifierWrapper(checkpoint_path, device)
  │     │     ├─ StorageManager(temp_path, permanent_path)
  │     │     ├─ ModerateClassificationTracker(db_interface)
  │     │     └─ ConfirmationHandler(db_interface)
  │     ├─ _initialize_scheduler()  →  CronTrigger(hour="*", min=0)
  │     └─ _setup_signal_handlers()
  │
  └─ orchestrator.start()  ←── BLOCKS HERE (runs until Ctrl+C)
        │
        └─ [Every hour at XX:00:00] → run_cycle()
```

---

## run_cycle() Internal Flow

```
run_cycle()
│
├─ 1. QUERY STRADS
│     db_interface.get_eligible_strads(count=10+exclusions)
│     → ["SC001", "SC042", "SC075", ...]
│
├─ 1b. LOCAL FILTER
│     local_state.filter_eligible_strads(list, cooldown_hours=1)
│     → removes recently-checked + critical
│     → caps to 10
│
├─ 2. FOR EACH STRAD (serial):
│     └─ process_single_strad(strad_id)
│           │
│           ├─ [1/6] ip_loader.get_ip(strad_id)
│           │         → ip_address or None (skip if None)
│           │
│           ├─ [2/6] web_capture.capture_frame(ip, strad_id, temp_dir)
│           │         → (screenshot_path, success)
│           │
│           ├─ [3/6] PIL.Image.open(screenshot_path) → numpy array
│           │
│           ├─ [4/6] dl_classifier.classify_snapshot(array)
│           │         → ClassificationResult(severity, confidence)
│           │
│           ├─ [5/6] STORE RESULT
│           │         ├─ Try: db_interface.store_classification_result(...)
│           │         │   └─ Fail → local_state.store_classification(...)
│           │         │
│           │         ├─ If critical:
│           │         │   ├─ storage_manager.persist_critical_snapshot(...)
│           │         │   ├─ Try: db_interface.add_to_critical_exclusion(...)
│           │         │   │   └─ Fail → local_state.add_critical_exclusion(...)
│           │         │   └─ moderate_tracker.record_classification(...)
│           │         │
│           │         └─ If moderate/none:
│           │             └─ moderate_tracker.record_classification(...)
│           │
│           └─ [6/6] FINALIZE
│                 ├─ Try: db_interface.update_check_history(strad_id)
│                 │   └─ Fail → local_state.record_check(strad_id)
│                 └─ storage_manager.clear_temporary_snapshot(path)
│
├─ 3. CLEAR TEMP STORAGE
│     storage_manager.clear_all_temporary()
│
└─ 4. LOG CYCLE STATS
      → {cycle_number, strads_processed, strads_failed, duration}
```

---

## File Interaction Map

```
                    CONFIGURATION
                    ─────────────
system_config.json ──────► ConfigurationManager ──────► SystemConfig
config/ip_addresses.json ─► IPAddressLoader ──────────► {strad_id → IP}


                    EXTERNAL SERVICES
                    ─────────────────
SQL Server (DSN) ◄────────► DatabaseInterface
                              │ read: get_eligible_strads
                              │ write: store_result (FAILS currently)
                              
Camera Web Pages ◄────────► WebCapture (Playwright/Chromium)
  http://{IP}/camera/          │ navigate, login, screenshot
  http://{IP}/view/            │


                    LOCAL FILES (read/write)
                    ────────────────────────
data/monitoring_state.json ◄──► LocalStateStore
                                  │ check history
                                  │ classification results
                                  │ critical exclusions

temp_snapshots/ ◄─────────────► StorageManager
permanent_snapshots/ ◄─────────► StorageManager
                                  │ temp: per-cycle working space
                                  │ perm: critical photos (long-term)

logs/ ◄────────────────────────► LoggingSystem
                                  │ rotating log files


                    MODEL FILE (read-only)
                    ───────────────────────
*.pth checkpoint ──────────────► SimpleClassifierWrapper
                                  │ load model weights
                                  │ classify numpy arrays
```

---

## Production Upgrade Points

What to modify when moving toward production:

| Change | Files to Modify | Notes |
|--------|----------------|-------|
| **Get DB write permissions** | `database_interface.py` (no code change needed — just run `scripts/create_monitoring_tables.sql`) | Local JSON fallback becomes unused automatically since DB writes succeed |
| **Tighten login form selectors** | `video_capture/web_capture.py` — `USERNAME_SELECTORS`, `PASSWORD_SELECTORS`, `SUBMIT_SELECTORS` constants | Inspect real camera page HTML and use exact `name`/`id` attributes |
| **Add new camera IPs** | `config/ip_addresses.json` — add new row | No code change needed |
| **Change stabilization delay** | `system_config.json` → `web_capture_stabilization_delay_seconds` | Per-environment tuning |
| **Improve model accuracy** | Train new model, update `model_checkpoint_path` in config | No code change needed |
| **Parallel strad processing** | `orchestration/orchestrator.py` → replace serial loop with thread pool in `run_cycle()` | Each WebCapture instance is self-contained (launches own browser) |
| **Add system management CLI** | New file: `management/commands.py` | `clear_all_strads()`, `show_critical_strads()` backed by `local_state` |
| **Switch to real DB writes** | Run SQL script, remove fallback log noise | `local_state` stays as secondary backup |
| **Add more classification classes** | Retrain model, update `SimpleClassifierWrapper` severity mapping | May need new thresholds in config |
| **Change cycle frequency** | `system_config.json` → `cycle_schedule_cron` | e.g., "*/30 * * * *" for every 30 minutes |
| **Support HTTPS cameras** | `video_capture/web_capture.py` — change `http://` to `https://` in `_navigate_to_viewer` | Already has `ignore_https_errors=True` set |
| **Remove legacy Excel/VLC code** | Delete `src/strad_monitoring/excel_automation/`, `vlc_capture/`, and their tests | Not referenced by orchestrator anymore |

---

## Dependency Direction (what imports what)

```
main.py
  └─► orchestrator.py
        ├─► system_config.py (config loading)
        ├─► ip_address_loader.py (IP lookup)
        ├─► database_interface.py (SQL Server reads)
        ├─► local_state_store.py (JSON state fallback)
        ├─► web_capture.py (Playwright screenshot)
        ├─► simple_classifier_wrapper.py (DL inference)
        ├─► storage_manager.py (file I/O)
        ├─► moderate_tracker.py (consecutive moderate tracking)
        └─► confirmation_handler.py (adjustment confirmations)

web_capture.py
  └─► playwright (external: headless Chromium)

simple_classifier_wrapper.py
  └─► torch (external: PyTorch model loading + inference)

database_interface.py
  └─► pyodbc (external: SQL Server connectivity)

local_state_store.py
  └─► json, datetime (stdlib only — no external deps)

ip_address_loader.py
  └─► pathlib, re (stdlib only — no external deps)
```

---

## State Lifecycle

```
STARTUP
  │
  ├─ Load monitoring_state.json (if exists)
  │    → Restores: check_history, results, critical_exclusions
  │
  └─ All state from previous session is preserved

DURING CYCLE
  │
  ├─ After each strad processed:
  │    → record_check(strad_id)         [cooldown tracking]
  │    → store_classification(...)      [result history]
  │    → add_critical_exclusion(...)    [if critical]
  │    → File saved after each write    [crash-safe]
  │
  └─ monitoring_state.json always reflects latest state

BETWEEN CYCLES
  │
  └─ State persists in file, survives restarts

MANUAL RESET
  │
  └─ local_state.clear_all()  →  Wipes everything, fresh start
```

---

## Failure Modes & Recovery

```
┌──────────────────────┬───────────────────────────────────────────────┐
│ Failure              │ System Behavior                               │
├──────────────────────┼───────────────────────────────────────────────┤
│ Camera unreachable   │ 3 retries, then skip strad, continue cycle   │
│ Login form changed   │ Capture fails, skip strad, log error         │
│ DB write fails       │ Fall back to local JSON, cycle continues     │
│ DB read fails        │ Use fallback data source (SQLite/random)     │
│ Model file missing   │ Testing mode: random classification          │
│                      │ Production: refuse to start                  │
│ IP not in JSON       │ Skip strad, log warning, continue           │
│ Disk full            │ Screenshot save fails, skip strad            │
│ Process killed       │ Graceful shutdown, waits for current strad   │
│ All strads excluded  │ Cycle runs with empty list, logs, exits     │
└──────────────────────┴───────────────────────────────────────────────┘
```

---

## Summary

The system is a **serial pipeline** orchestrated by a single class (`MonitoringOrchestrator`) that runs hourly. Each component is independently testable and replaceable. The main extension points for production are:
1. Database write permissions (tables already designed)
2. Login form selector tightening (once page is inspected)
3. Model accuracy improvements (separate training pipeline)
4. Optional parallelization of strad processing
