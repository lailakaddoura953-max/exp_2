# Implementation Plan: Strad Carrier Monitoring Automation

## Overview

This implementation plan details the step-by-step development of an automated monitoring system that integrates deep learning camera misalignment detection with SQL Server database operations, Excel-based video feed automation, and VLC media player snapshot capture. The system orchestrates hourly monitoring cycles of 10 randomly selected Strad Carriers from a pool of 135 units, classifies camera alignment status, and manages check history with cooldown periods and critical unit exclusion.

The implementation follows a layered architecture approach, building from foundation components (configuration, logging) through interface layers (database, Excel, VLC) to the orchestration layer that coordinates the complete monitoring cycle.

## Tasks

- [x] 1. Set up project structure and configuration management
  - [x] 1.1 Create project directory structure and package initialization files
    - Create directory structure: `src/strad_monitoring/` with subdirectories: `config/`, `database/`, `excel_automation/`, `vlc_capture/`, `dl_classifier/`, `storage/`, `orchestration/`, `logging/`, `utils/`
    - Add `__init__.py` files to all packages
    - Create `tests/` directory with subdirectories: `properties/`, `integration/`, `unit/`
    - Create root-level `system_config.json` template file
    - _Requirements: 12.1, 12.2, 12.3_

  - [x] 1.2 Implement Configuration Manager with validation
    - Create `src/strad_monitoring/config/system_config.py` with `SystemConfig` dataclass
    - Implement `ConfigurationManager` class with `load_config()` method to parse JSON configuration
    - Implement `validate_config()` method to check all required fields: database_connection_string, excel_file_path, model_checkpoint_path, temp_snapshot_path, permanent_snapshot_path, log_file_path
    - Add validation for file path existence and numeric value ranges
    - Implement environment variable substitution for `${ENV_VAR}` syntax
    - Add singleton pattern for configuration access
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [x]* 1.3 Write property test for configuration validation completeness (Property 30)
    - **Property 30: Configuration Validation Completeness**
    - **Validates: Requirements 12.2, 12.3**

- [x] 2. Implement logging system
  - [x] 2.1 Create logging system with rotation and structured formatting
    - Create `src/strad_monitoring/logging/logging_system.py` with `LoggingSystem` class
    - Implement `setup_logging()` method with RotatingFileHandler for daily rotation
    - Configure log format: timestamp, level, component name, message
    - Set up file naming pattern: `monitoring_log_YYYY-MM-DD.txt`
    - Add QueueHandler for asynchronous logging to prevent I/O blocking
    - Implement cleanup job for removing logs older than retention period
    - _Requirements: 13.1, 13.4, 13.5_

  - [x]* 2.2 Write property test for error logging completeness (Property 31)
    - **Property 31: Error Logging Completeness**
    - **Validates: Requirements 13.1**

- [x] 3. Implement database interface with SQL Server connectivity
  - [x] 3.1 Create database interface class with connection pooling
    - Create `src/strad_monitoring/database/database_interface.py` with `DatabaseInterface` class
    - Implement `__init__()` with pyodbc connection using connection pooling (min=2, max=10)
    - Implement `health_check()` method to verify database connectivity
    - Add connection retry logic with exponential backoff (3 retries: 1s, 2s, 4s)
    - Implement `cleanup_old_history()` method to remove Check_History records older than 7 days
    - _Requirements: 12.6, 1.1_

  - [x] 3.2 Implement strad selection query with eligibility filtering and local testing fallback
    - Implement `get_eligible_strads(count: int)` method in DatabaseInterface
    - **PRIMARY PATH (Production SQL Server):**
      - Write SQL query to call stored procedure: `EXEC strad_action_check_by_id_and_timestamp @count=?`
      - Filter strads where last_check_timestamp < (current_time - 1 hour)
      - Exclude strads present in critical_strad_exclusions table
      - Return strad IDs in format SCXXX
    - **FALLBACK PATH (Local Testing Mode):**
      - Add try-except block to catch SQL Server connection failures
      - **FALLBACK OPTION 1:** Implement `_load_strads_from_kitti()` to load strad IDs from KITTI dataset (path: kitti_data/ or configured fallback_data_path)
      - **FALLBACK OPTION 2:** Implement `_load_strads_from_local_folder()` to read from CSV/JSON file with format: strad_id,last_check_timestamp,is_critical
      - **FALLBACK OPTION 3:** Implement `_generate_random_test_strads()` to create random SC001-SC135 IDs
      - Add configuration flags: `enable_local_testing_mode`, `fallback_data_path`, `fallback_data_source`
    - **CRITICAL: Add clear comments in code:**
      - Comment "PRIMARY PATH: Production SQL Server" above production query code
      - Comment "FALLBACK PATH: Local Testing Mode" above fallback logic
      - Comment "FALLBACK OPTION 1/2/3" above each fallback method
      - Add docstrings explaining when each fallback is used and expected file formats
    - Log which path is used (production or fallback) for debugging
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 8.2, 8.3, 8.4_

  - [x]* 3.3 Write property tests for strad selection filtering (Properties 1-3)
    - **Property 1: Strad Selection Eligibility Filtering**
    - **Validates: Requirements 1.2, 1.3, 8.3**
    - **Property 2: Strad Selection Uniqueness and Count**
    - **Validates: Requirements 1.4, 1.5**
    - **Property 3: Strad ID Format Validation**
    - **Validates: Requirements 1.6**

  - [x] 3.4 Implement classification result storage methods
    - Implement `store_classification_result()` method to insert into classification_results table
    - Store strad_id, classification (none/moderate/critical), confidence score, snapshot_path (nullable), timestamp
    - Use parameterized queries to prevent SQL injection
    - Implement query timeout of 30 seconds
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x]* 3.5 Write property tests for classification data storage (Properties 11-13)
    - **Property 11: Classification Data Association**
    - **Validates: Requirements 6.2, 6.4**
    - **Property 12: Timestamp Recording Precision**
    - **Validates: Requirements 6.3**
    - **Property 13: Critical Classification File Path Storage**
    - **Validates: Requirements 6.5**

  - [x] 3.6 Implement check history update method
    - Implement `update_check_history()` method to update strad_action_check_by_id_and_timestamp
    - Insert or update last_check_timestamp for given strad_id
    - Ensure timestamp precision to the second
    - Handle concurrent updates using appropriate isolation level
    - _Requirements: 6.6, 8.1_

  - [x]* 3.7 Write property test for check history update idempotence (Property 14)
    - **Property 14: Check History Update Idempotence**
    - **Validates: Requirements 6.6, 8.1**

  - [x] 3.8 Implement critical exclusion list management
    - Implement `add_to_critical_exclusion()` method to insert into critical_strad_exclusions table
    - Implement `remove_from_critical_exclusion()` method to delete from critical_strad_exclusions
    - Log all additions and removals with timestamp and operation type
    - Use serializable isolation level for exclusion list operations
    - _Requirements: 7.1, 7.2, 7.4, 7.5, 7.6_

  - [x]* 3.9 Write property tests for exclusion management (Properties 15-17)
    - **Property 15: Critical Exclusion State Transition**
    - **Validates: Requirements 7.1, 7.3**
    - **Property 16: Exclusion Removal on Confirmation**
    - **Validates: Requirements 7.4, 7.5**
    - **Property 17: Exclusion Operation Audit Logging**
    - **Validates: Requirements 7.6**

- [x] 4. Checkpoint - Verify database interface and configuration
  - Ensure configuration loads correctly and validates required fields
  - Verify database connection establishes successfully
  - Test strad selection query returns expected format and applies filters
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement storage manager for snapshot persistence
  - [x] 5.1 Create storage manager with temporary and permanent storage
    - Create `src/strad_monitoring/storage/storage_manager.py` with `StorageManager` class
    - Implement `__init__()` to set up temporary and permanent storage paths
    - Implement `store_temporary_snapshot()` to save snapshot to temp directory with naming: `{strad_id}_{uuid}.jpg`
    - Implement `persist_critical_snapshot()` to save to permanent storage with directory structure: `YYYY-MM-DD/{CHE_Number}_{timestamp}.jpg`
    - Use atomic write pattern: save to .tmp file, verify, then rename
    - Compress snapshots using PIL with JPEG quality 85
    - _Requirements: 5.1, 10.1, 10.2, 10.3, 10.4_

  - [x]* 5.2 Write property tests for snapshot storage (Properties 4-5, 23-25)
    - **Property 4: Snapshot Storage Association Preservation**
    - **Validates: Requirements 3.3, 3.4**
    - **Property 5: Snapshot Dimension Validation**
    - **Validates: Requirements 3.5**
    - **Property 23: Snapshot Directory Organization by Date**
    - **Validates: Requirements 10.2**
    - **Property 24: Snapshot Filename Format**
    - **Validates: Requirements 10.3**
    - **Property 25: Snapshot File Readability Verification**
    - **Validates: Requirements 10.5**

  - [x] 5.3 Implement temporary storage cleanup methods
    - Implement `clear_temporary_snapshot()` to remove single snapshot from temp storage
    - Implement `clear_all_temporary()` to remove all temp snapshots at end of cycle
    - Implement `cleanup_old_snapshots()` to remove permanent snapshots older than retention period (30 days)
    - Implement `check_available_space()` using shutil.disk_usage() to verify > 10GB available
    - _Requirements: 5.2, 5.4, 5.5, 10.6_

  - [x]* 5.4 Write property tests for storage cleanup (Properties 9-10, 27)
    - **Property 9: Temporary Storage Cleanup by Classification**
    - **Validates: Requirements 5.2**
    - **Property 10: Critical Snapshot Persistence Ordering**
    - **Validates: Requirements 5.3, 10.1**
    - **Property 27: Moderate Classification No Snapshot Persistence**
    - **Validates: Requirements 11.4**

- [x] 6. Implement DL classifier wrapper
  - [x] 6.1 Create DL classifier wrapper integrating existing inference engine
    - Create `src/strad_monitoring/dl_classifier/classifier_wrapper.py` with `DLClassifierWrapper` class and `ClassificationResult` dataclass
    - Import existing InferenceEngine from `src/dl_misalignment/inference/inference_engine.py`
    - Import ImagePreprocessor from `src/dl_misalignment/inference/preprocessing.py`
    - Implement `__init__()` to load PyTorch model checkpoint on GPU (cuda device)
    - Implement preprocessing pipeline: convert RGB numpy array to PIL Image, resize to 640x640, normalize, convert to tensor
    - Implement `classify_snapshot()` method to run inference and return ClassificationResult
    - _Requirements: 4.1, 4.2_

  - [x] 6.2 Implement severity mapping and confidence handling
    - Map model probability output to severity levels: < 0.3 = "none", 0.3-0.7 = "moderate", >= 0.7 = "critical"
    - Implement conservative default: confidence < 0.6 maps to "moderate"
    - Extract confidence score (0.0 to 1.0) from model output
    - Add timeout mechanism using threading.Timer to enforce 10-second classification limit
    - Track processing time in milliseconds and include in ClassificationResult
    - _Requirements: 4.3, 4.4, 4.5, 4.6_

  - [x]* 6.3 Write property tests for classification logic (Properties 6-8)
    - **Property 6: Classification Result Domain Constraint**
    - **Validates: Requirements 4.3**
    - **Property 7: Confidence Score Range Constraint**
    - **Validates: Requirements 4.4**
    - **Property 8: Low Confidence Conservative Mapping**
    - **Validates: Requirements 4.6**

- [x] 7. Implement Excel automation component
  - [x] 7.1 Create Excel automation interface with COM control
    - Create `src/strad_monitoring/excel_automation/excel_automation.py` with `ExcelAutomation` class
    - Implement `__init__()` using win32com.client.Dispatch("Excel.Application") for COM automation
    - Set Excel visible=False to avoid UI flickering
    - Open workbook using excel_file_path from configuration
    - _Requirements: 2.1_

  - [x] 7.2 Implement video feed opening via video encoder button
    - Implement `open_video_feed()` method accepting strad_id parameter
    - Locate "spreader video encoder" control using worksheet.OLEObjects()
    - Insert CHE_Number (SCXXX format) into control using control.Object.Value or control.Object.Text
    - Activate control using control.Object.Click()
    - Poll for VLC window using win32gui.FindWindow("VLC media player", None) with 30-second timeout
    - Return True if VLC window found, False if timeout
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 7.3 Implement Excel cleanup and error handling
    - Implement `close_video_feed()` method to close current video feed
    - Implement `cleanup()` method to properly release COM objects and prevent Excel process leaks
    - Use pythoncom.CoInitialize() for thread safety
    - Add try-finally blocks to ensure COM object cleanup
    - _Requirements: 13.2, 13.3_

  - [x]* 7.4 Write integration tests for Excel automation
    - Test Excel application opens workbook successfully
    - Test video encoder control can be located and activated
    - Test VLC window detection with timeout
    - Test COM object cleanup prevents process leaks

- [x] 8. Implement VLC capture component
  - [x] 8.1 Create VLC window capture with stabilization delay
    - Create `src/strad_monitoring/vlc_capture/vlc_capture.py` with `VLCCapture` class
    - Implement `__init__()` with configurable stabilization_delay (default 5.0 seconds), min_width (640), min_height (480)
    - Implement `capture_snapshot()` method that waits for stabilization delay before capturing
    - Use win32gui.FindWindow("VLC media player", None) to locate VLC window
    - Bring VLC window to foreground using win32gui.SetForegroundWindow(hwnd)
    - Get window rectangle using win32gui.GetWindowRect(hwnd)
    - _Requirements: 3.1, 3.2_

  - [x] 8.2 Implement snapshot capture and validation
    - Capture screenshot using pyautogui.screenshot(region=(x, y, width, height))
    - Convert PIL Image to numpy array in RGB format
    - Implement `validate_snapshot()` method to verify dimensions >= 640x480
    - Implement 3 retry attempts with 2-second intervals on capture failure
    - Handle multi-monitor scenarios by ensuring window is visible
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x]* 8.3 Write integration tests for VLC capture
    - Test VLC window can be located successfully
    - Test snapshot capture returns numpy array with correct dimensions
    - Test validation rejects snapshots below minimum dimensions
    - Test retry logic attempts up to 3 times on failure

- [x] 9. Checkpoint - Verify all interface components
  - Test storage manager creates correct directory structure and saves snapshots
  - Test DL classifier wrapper loads model and produces valid classifications
  - Test Excel automation can open video feeds (with mocked VLC)
  - Test VLC capture can capture and validate snapshots (with mocked window)
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement moderate classification tracking
  - [x] 10.1 Create moderate classification tracker
    - Create `src/strad_monitoring/database/moderate_tracker.py` with `ModerateClassificationTracker` class
    - Implement method to track consecutive moderate classifications per strad
    - Maintain in-memory counter that resets when non-moderate classification occurs
    - Query database for recent classifications within 24-hour window
    - Generate warning notification when strad receives 3 consecutive moderate classifications within 24 hours
    - _Requirements: 11.2, 11.3, 11.5, 11.6_

  - [x]* 10.2 Write property tests for moderate classification handling (Properties 26, 28-29)
    - **Property 26: Moderate Classification Non-Exclusion**
    - **Validates: Requirements 11.2**
    - **Property 28: Consecutive Moderate Classification Tracking**
    - **Validates: Requirements 11.5**
    - **Property 29: Moderate Classification Warning Threshold**
    - **Validates: Requirements 11.6**

- [x] 11. Implement adjustment confirmation interface
  - [x] 11.1 Create adjustment confirmation handler
    - Create `src/strad_monitoring/orchestration/confirmation_handler.py` with `ConfirmationHandler` class
    - Implement method to accept CHE_Number and confirmation timestamp
    - Validate CHE_Number exists in critical_strad_exclusions table
    - Record confirmation timestamp and technician_id in database
    - Call DatabaseInterface.remove_from_critical_exclusion() to remove from exclusion list
    - Reset Check_History timestamp to allow immediate re-checking
    - Return informational message if CHE_Number not in exclusion list
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

  - [x]* 11.2 Write property tests for adjustment confirmation (Properties 32-34)
    - **Property 32: Adjustment Confirmation Validation**
    - **Validates: Requirements 14.2, 14.6**
    - **Property 33: Confirmation Audit Data Recording**
    - **Validates: Requirements 14.3**
    - **Property 34: Confirmation Check History Reset**
    - **Validates: Requirements 14.5**

- [x] 12. Implement timing and cooldown calculation utilities
  - [x] 12.1 Create timing utility functions
    - Create `src/strad_monitoring/utils/timing.py` with utility functions
    - Implement `calculate_elapsed_time()` function to compute difference between two timestamps with second precision
    - Implement `is_in_cooldown()` function to check if elapsed time < 1 hour (3600 seconds)
    - Implement `format_timestamp()` function for consistent timestamp formatting
    - _Requirements: 8.2, 8.3, 8.4_

  - [x]* 12.2 Write property tests for timing calculations (Properties 18-19)
    - **Property 18: Elapsed Time Calculation Accuracy**
    - **Validates: Requirements 8.2**
    - **Property 19: Cooldown Re-Eligibility**
    - **Validates: Requirements 8.4**

- [ ] 13. Implement main orchestrator with cycle management
  - [~] 13.1 Create orchestrator class with scheduler integration
    - Create `src/strad_monitoring/orchestration/orchestrator.py` with `MonitoringOrchestrator` class
    - Implement `__init__()` to initialize all component instances: DatabaseInterface, ExcelAutomation, VLCCapture, DLClassifierWrapper, StorageManager
    - Integrate APScheduler with CronTrigger for hourly execution (hour="*", minute=0, second=0)
    - Implement `start()` method to begin scheduling (blocking call)
    - Implement `stop()` method for graceful shutdown
    - _Requirements: 9.1, 12.1_

  - [~] 13.2 Implement single strad processing workflow
    - Implement `process_single_strad()` method that accepts strad_id
    - Orchestrate sequence: Excel.open_video_feed() → VLC.capture_snapshot() → DL.classify_snapshot() → handle result based on classification
    - For critical classification: persist snapshot to permanent storage, store result with file path, add to critical exclusion list
    - For moderate/none classification: store result without snapshot path
    - Update check history with current timestamp
    - Clear temporary snapshot
    - Implement retry logic for component failures (3 attempts)
    - Return StradResult with success status, classification, confidence, processing time
    - _Requirements: 9.3, 4.1, 4.2, 4.3, 5.2, 5.3, 6.1, 6.2, 7.1, 7.2_

  - [~] 13.3 Implement complete cycle orchestration
    - Implement `run_cycle()` method to execute one monitoring cycle
    - Query database for 10 eligible strads using DatabaseInterface.get_eligible_strads(10)
    - Process strads serially using process_single_strad() for each strad
    - Track cycle statistics: start time, end time, strads processed, strads failed
    - Handle component failures gracefully: log error, mark strad as failed, continue with remaining strads
    - Clear all temporary storage at end of cycle
    - Log cycle completion with timestamp and count of strads processed
    - Ensure cycle completes within 50 minutes
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 5.4_

  - [x]* 13.4 Write property tests for orchestration logic (Properties 20-22)
    - **Property 20: Serial Processing Non-Overlap**
    - **Validates: Requirements 9.3**
    - **Property 21: Cycle Completion Logging**
    - **Validates: Requirements 9.4**
    - **Property 22: Error Recovery Continuation**
    - **Validates: Requirements 9.5, 13.2**

- [x] 14. Implement error handling and retry mechanisms
  - [x] 14.1 Create custom exception hierarchy
    - Create `src/strad_monitoring/utils/exceptions.py` with custom exception classes
    - Define base MonitoringSystemError exception
    - Define specialized exceptions: ConfigurationError, ComponentError, DatabaseError, ExcelAutomationError, VLCCaptureError, ClassificationError, StorageError, CriticalError
    - Add exception attributes for component name, strad_id, error details
    - _Requirements: 13.1_

  - [x] 14.2 Implement retry decorator with exponential backoff
    - Create `src/strad_monitoring/utils/retry.py` with retry decorator
    - Implement exponential backoff: attempts with delays 1s, 2s, 4s
    - Accept exception types parameter to specify which exceptions to retry
    - Log each retry attempt with attempt number
    - Raise original exception after all retries exhausted
    - _Requirements: 13.3_

  - [x] 14.3 Implement alerting for critical errors
    - Create `src/strad_monitoring/utils/alerting.py` with alert sending functionality
    - Implement method to send alert notifications for critical errors (email, SMS, dashboard)
    - Integrate with orchestrator to pause cycles on critical errors
    - Add health check endpoint for monitoring systems
    - _Requirements: 13.6_

  - [x]* 14.4 Write integration tests for error handling
    - Test retry decorator attempts correct number of times with backoff
    - Test component failures log errors and continue processing remaining strads
    - Test critical errors trigger alerts and pause scheduler
    - Test graceful shutdown completes current strad before stopping

- [ ] 15. Implement graceful shutdown handling
  - [~] 15.1 Create shutdown handler with signal interception
    - Add signal handlers for SIGTERM and SIGINT in orchestrator
    - Implement `graceful_shutdown()` method that sets shutdown_requested flag
    - Wait for current strad processing to complete (max 5 minutes timeout)
    - Save cycle progress and partial results
    - Cleanup resources: close database connections, release Excel COM objects, clear temporary storage
    - Log shutdown event with reason and state
    - _Requirements: 13.2_

- [~] 16. Checkpoint - Verify orchestration and error handling
  - Test orchestrator initializes all components correctly
  - Test single strad processing workflow completes all steps
  - Test cycle processes multiple strads serially without overlap
  - Test error recovery continues with remaining strads after failure
  - Test graceful shutdown waits for completion and cleans up resources
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 17. Create main entry point and deployment script
  - [~] 17.1 Create main application entry point
    - Create `src/strad_monitoring/main.py` with main() function
    - Load configuration using ConfigurationManager
    - Validate configuration and refuse to start if validation fails
    - Setup logging using LoggingSystem
    - Verify database connectivity during initialization
    - Create MonitoringOrchestrator instance and start scheduler
    - Setup signal handlers for graceful shutdown
    - _Requirements: 12.1, 12.4, 12.6_

  - [~] 17.2 Create requirements.txt with dependencies
    - Add Python dependencies: pyodbc (or pymssql), pywin32 (win32com, win32gui), pyautogui, APScheduler, Pillow, torch, torchvision, hypothesis (for testing), pytest, pytest-cov
    - Pin versions for stability: specify exact versions or compatible ranges
    - Document GPU requirements: CUDA 11.7+
    - _Requirements: 12.1_

  - [~] 17.3 Create deployment documentation
    - Document installation steps: Python 3.10+ installation, pip install requirements, GPU driver setup
    - Document configuration file setup with example system_config.json
    - Document database schema creation scripts
    - Document Windows service installation for continuous operation
    - Include troubleshooting guide for common issues
    - _Requirements: 12.1, 12.5_

- [ ]* 18. Write end-to-end integration tests
  - [~] 18.1 Create end-to-end cycle test with mocked components
    - Mock all external dependencies: SQL Server, Excel COM, VLC window, file system
    - Test complete cycle executes all steps in correct order
    - Verify database queries and updates called with correct parameters
    - Verify snapshots saved to correct paths for critical classifications
    - Verify Check_History updated for all processed strads
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [~] 18.2 Create integration test for critical strad workflow
    - Test critical classification triggers snapshot persistence
    - Test strad added to exclusion list after critical classification
    - Test excluded strad not returned in next eligible strads query
    - Test adjustment confirmation removes strad from exclusion list
    - Test previously critical strad becomes eligible after confirmation
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [~] 18.3 Create integration test for moderate classification workflow
    - Test moderate classification does not trigger snapshot persistence
    - Test moderate strad remains in eligible pool after cooldown
    - Test consecutive moderate count increments correctly
    - Test warning notification triggered after 3 consecutive moderates within 24 hours
    - _Requirements: 11.1, 11.2, 11.3, 11.5, 11.6_

- [~] 19. Final checkpoint - Complete system verification
  - Run all property-based tests (34 properties) and verify 100% pass rate
  - Run all integration tests and verify components interact correctly
  - Run all unit tests and verify 90%+ code coverage
  - Test complete cycle execution with real configuration (mock external systems)
  - Verify logging captures all operations with correct format and rotation
  - Verify configuration validation rejects invalid configurations
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test-related tasks that can be skipped for faster MVP
- Each task references specific requirements from the requirements document for traceability
- Checkpoints ensure incremental validation at key integration points
- Property tests validate the 34 universal correctness properties defined in the design document
- Integration tests verify component interactions with mocked external dependencies
- The implementation uses Python 3.10+ with PyTorch for DL inference, win32com for Excel automation, and pyodbc for SQL Server connectivity
- GPU with CUDA 11.7+ required for DL model inference performance
- All temporary storage is cleared at end of each cycle to manage memory efficiently
- Critical snapshots are persisted with 30-day retention in date-organized directory structure
- The system implements graceful error handling: retries for transient errors, continuation for component failures, pause for critical errors
- Deployment on Windows required for Excel COM automation and VLC window capture
- **CRITICAL: Local Testing Fallback - The database interface includes a fallback mechanism that allows full system testing without SQL Server connection. When database is unavailable, the system can load test strad IDs from KITTI dataset, local CSV/JSON file, or generate random test data. All fallback code paths must have clear comments (PRIMARY PATH, FALLBACK PATH, FALLBACK OPTION 1/2/3) so developers can easily understand and modify the behavior.**

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1", "1.2"]
    },
    {
      "id": 1,
      "tasks": ["1.3", "2.1", "14.1"]
    },
    {
      "id": 2,
      "tasks": ["2.2", "3.1", "12.1"]
    },
    {
      "id": 3,
      "tasks": ["3.2", "12.2"]
    },
    {
      "id": 4,
      "tasks": ["3.3", "3.4"]
    },
    {
      "id": 5,
      "tasks": ["3.5", "3.6"]
    },
    {
      "id": 6,
      "tasks": ["3.7", "3.8"]
    },
    {
      "id": 7,
      "tasks": ["3.9", "5.1"]
    },
    {
      "id": 8,
      "tasks": ["5.2", "5.3", "6.1"]
    },
    {
      "id": 9,
      "tasks": ["5.4", "6.2"]
    },
    {
      "id": 10,
      "tasks": ["6.3", "7.1", "8.1"]
    },
    {
      "id": 11,
      "tasks": ["7.2", "8.2"]
    },
    {
      "id": 12,
      "tasks": ["7.3", "7.4", "8.3"]
    },
    {
      "id": 13,
      "tasks": ["10.1", "14.2"]
    },
    {
      "id": 14,
      "tasks": ["10.2", "11.1", "14.3"]
    },
    {
      "id": 15,
      "tasks": ["11.2", "13.1", "14.4"]
    },
    {
      "id": 16,
      "tasks": ["13.2", "15.1"]
    },
    {
      "id": 17,
      "tasks": ["13.3"]
    },
    {
      "id": 18,
      "tasks": ["13.4", "17.1", "17.2"]
    },
    {
      "id": 19,
      "tasks": ["17.3", "18.1"]
    },
    {
      "id": 20,
      "tasks": ["18.2", "18.3"]
    }
  ]
}
```
