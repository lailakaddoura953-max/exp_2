"""
Monitoring Orchestrator for Strad Carrier Monitoring Automation

This module provides the main orchestration layer that coordinates all components
and schedules hourly monitoring cycles.

The orchestrator:
- Initializes all component instances
- Schedules hourly monitoring cycles using APScheduler
- Coordinates serial processing of 10 strads per cycle
- Handles component failures with retry logic
- Ensures proper resource cleanup

Requirements addressed:
- 9.1: Initiate new Hourly_Cycle at start of each clock hour (XX:00:00)
- 12.1: Load configuration from system_config.json at startup
- 13.1: Provide graceful shutdown mechanism
"""

import logging
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config.system_config import ConfigurationManager, SystemConfig
from ..logging.logging_system import LoggingSystem
from ..database.database_interface import DatabaseInterface
from ..excel_automation.excel_automation import ExcelAutomation
from ..vlc_capture.vlc_capture import VLCCapture
from ..dl_classifier.classifier_wrapper import DLClassifierWrapper
from ..storage.storage_manager import StorageManager
from ..database.moderate_tracker import ModerateClassificationTracker
from ..orchestration.confirmation_handler import ConfirmationHandler


class MonitoringOrchestrator:
    """
    Main orchestrator for Strad Carrier monitoring automation.
    
    This class coordinates all components and schedules hourly monitoring cycles.
    It implements the main control loop and ensures proper resource management.
    
    Attributes:
        config: SystemConfig with all configuration parameters
        scheduler: APScheduler instance for hourly cycle scheduling
        logger: Logger instance for orchestrator operations
        db_interface: DatabaseInterface for database operations
        excel_automation: ExcelAutomation for video feed control
        vlc_capture: VLCCapture for snapshot capture
        dl_classifier: DLClassifierWrapper for misalignment classification
        storage_manager: StorageManager for snapshot storage
        moderate_tracker: ModerateClassificationTracker for tracking moderate classifications
        confirmation_handler: ConfirmationHandler for adjustment confirmations
    """
    
    def __init__(self, config: SystemConfig):
        """
        Initialize orchestrator with configuration.
        
        This method:
        1. Loads configuration from system_config.json
        2. Sets up logging system
        3. Initializes all component instances
        4. Sets up APScheduler with CronTrigger for hourly execution
        
        Args:
            config: SystemConfig object with validated configuration
            
        Raises:
            Exception: If any component initialization fails
            
        Requirements:
            - 12.1: Load configuration from system_config.json at startup
            - 9.1: Set up scheduler for hourly cycle execution
        """
        self.config = config
        self.logger = None
        self.scheduler = None
        self.db_interface = None
        self.excel_automation = None
        self.vlc_capture = None
        self.dl_classifier = None
        self.storage_manager = None
        self.moderate_tracker = None
        self.confirmation_handler = None
        
        # Track orchestrator state
        self._is_running = False
        self._shutdown_requested = False
        self._current_strad_id = None
        self._cycle_count = 0
        self._total_strads_processed = 0
        self._total_strads_failed = 0
        self._cycle_in_progress = False
        
        # Initialize logging first (required for all other components)
        self._initialize_logging()
        
        self.logger.info("=" * 80)
        self.logger.info("MONITORING ORCHESTRATOR INITIALIZATION")
        self.logger.info("=" * 80)
        
        # Initialize all components
        self._initialize_components()
        
        # Set up scheduler with hourly trigger
        self._initialize_scheduler()
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        self.logger.info("✓ Orchestrator initialized successfully")
        self.logger.info("=" * 80)
    
    def _initialize_logging(self) -> None:
        """
        Initialize logging system.
        
        Requirements: 13.1 (logging configuration)
        """
        LoggingSystem.setup_logging(
            log_file_path=self.config.log_file_path,
            log_level="INFO",
            retention_days=self.config.log_retention_days,
            enable_console=True  # Enable console for development/debugging
        )
        
        self.logger = LoggingSystem.get_logger("MonitoringOrchestrator")
        self.logger.info("Logging system initialized")
    
    def _initialize_components(self) -> None:
        """
        Initialize all monitoring system components.
        
        Components initialized:
        1. DatabaseInterface - SQL Server connectivity
        2. ExcelAutomation - Excel video encoder control
        3. VLCCapture - VLC snapshot capture
        4. DLClassifierWrapper - Deep learning classification
        5. StorageManager - Snapshot storage management
        6. ModerateClassificationTracker - Moderate classification tracking
        7. ConfirmationHandler - Adjustment confirmation handling
        
        Requirements: 12.1 (component initialization)
        """
        self.logger.info("Initializing components...")
        
        # 1. Initialize DatabaseInterface
        try:
            self.logger.info("  Initializing DatabaseInterface...")
            self.db_interface = DatabaseInterface(
                connection_string=self.config.database_connection_string,
                enable_fallback=self.config.enable_local_testing_mode,
                fallback_data_path=self.config.fallback_data_path,
                fallback_data_source=self.config.fallback_data_source,
                use_sqlite_fallback=getattr(self.config, 'use_sqlite_fallback', False),
                sqlite_db_path=getattr(self.config, 'sqlite_db_path', 'tests/test.db'),
                strad_query_sql_file=getattr(self.config, 'strad_query_sql_file', 'strad_query.sql')
            )
            self.logger.info("  ✓ DatabaseInterface initialized")
        except Exception as e:
            self.logger.error(f"  ✗ DatabaseInterface initialization failed: {e}")
            raise
        
        # 2. Initialize ExcelAutomation
        try:
            self.logger.info("  Initializing ExcelAutomation...")
            self.excel_automation = ExcelAutomation(
                excel_file_path=self.config.excel_file_path,
                timeout_seconds=30,
                visible=False  # Keep Excel hidden to avoid UI flickering
            )
            self.logger.info("  ✓ ExcelAutomation initialized")
        except Exception as e:
            self.logger.error(f"  ✗ ExcelAutomation initialization failed: {e}")
            raise
        
        # 3. Initialize VLCCapture
        try:
            self.logger.info("  Initializing VLCCapture...")
            self.vlc_capture = VLCCapture(
                stabilization_delay=5.0,  # 5 seconds for feed stabilization
                min_width=self.config.snapshot_min_width,
                min_height=self.config.snapshot_min_height,
                rtsp_username=getattr(self.config, 'rtsp_username', None),
                rtsp_password=getattr(self.config, 'rtsp_password', None)
            )
            self.logger.info("  ✓ VLCCapture initialized")
        except Exception as e:
            self.logger.error(f"  ✗ VLCCapture initialization failed: {e}")
            raise
        
        # 4. Initialize DLClassifierWrapper (skip in testing mode if model not available)
        try:
            self.logger.info("  Initializing DLClassifierWrapper...")
            self.dl_classifier = DLClassifierWrapper(
                model_checkpoint_path=self.config.model_checkpoint_path,
                config=self.config.dl_model_config,
                device='cuda'  # Use GPU for inference
            )
            self.logger.info("  ✓ DLClassifierWrapper initialized")
        except Exception as e:
            if self.config.enable_local_testing_mode:
                self.logger.warning(f"  ⚠ DLClassifierWrapper initialization failed (testing mode - using fallback): {e}")
                self.dl_classifier = None  # Will use fallback classification
            else:
                self.logger.error(f"  ✗ DLClassifierWrapper initialization failed: {e}")
                raise
        
        # 5. Initialize StorageManager
        try:
            self.logger.info("  Initializing StorageManager...")
            self.storage_manager = StorageManager(
                temp_storage_path=self.config.temp_snapshot_path,
                permanent_storage_path=self.config.permanent_snapshot_path,
                retention_days=self.config.snapshot_retention_days
            )
            self.logger.info("  ✓ StorageManager initialized")
        except Exception as e:
            self.logger.error(f"  ✗ StorageManager initialization failed: {e}")
            raise
        
        # 6. Initialize ModerateClassificationTracker
        try:
            self.logger.info("  Initializing ModerateClassificationTracker...")
            self.moderate_tracker = ModerateClassificationTracker(
                database_interface=self.db_interface,
                time_window_hours=24
            )
            self.logger.info("  ✓ ModerateClassificationTracker initialized")
        except Exception as e:
            self.logger.error(f"  ✗ ModerateClassificationTracker initialization failed: {e}")
            raise
        
        # 7. Initialize ConfirmationHandler
        try:
            self.logger.info("  Initializing ConfirmationHandler...")
            self.confirmation_handler = ConfirmationHandler(
                database_interface=self.db_interface
            )
            self.logger.info("  ✓ ConfirmationHandler initialized")
        except Exception as e:
            self.logger.error(f"  ✗ ConfirmationHandler initialization failed: {e}")
            raise
        
        self.logger.info("✓ All components initialized successfully")
    
    def _initialize_scheduler(self) -> None:
        """
        Initialize APScheduler with CronTrigger for hourly execution.
        
        Sets up blocking scheduler with cron trigger:
        - hour="*": Every hour
        - minute=0: At minute 0
        - second=0: At second 0
        
        This triggers the monitoring cycle at XX:00:00 every hour.
        
        Requirements: 9.1 (hourly cycle initiation at XX:00:00)
        """
        self.logger.info("Setting up scheduler...")
        
        # Create blocking scheduler (blocks on start() call)
        self.scheduler = BlockingScheduler()
        
        # Parse cron schedule from configuration
        # Default: "0 * * * *" (minute hour day month weekday)
        cron_parts = self.config.cycle_schedule_cron.split()
        
        if len(cron_parts) != 5:
            raise ValueError(
                f"Invalid cron schedule: {self.config.cycle_schedule_cron}. "
                "Expected format: 'minute hour day month weekday'"
            )
        
        # Create CronTrigger for hourly execution
        # For hourly at XX:00:00, use: hour="*", minute=0, second=0
        trigger = CronTrigger(
            hour="*",      # Every hour
            minute=0,      # At minute 0
            second=0       # At second 0
        )
        
        # Add job to scheduler
        # run_cycle will be called at XX:00:00 every hour
        self.scheduler.add_job(
            func=self.run_cycle,
            trigger=trigger,
            id='hourly_monitoring_cycle',
            name='Hourly Monitoring Cycle',
            replace_existing=True
        )
        
        self.logger.info(
            f"✓ Scheduler configured with hourly trigger (XX:00:00)"
        )
        self.logger.info(
            f"  Trigger: hour='*', minute=0, second=0"
        )
    
    def _setup_signal_handlers(self) -> None:
        """
        Set up signal handlers for graceful shutdown.
        
        Handles:
        - SIGINT (Ctrl+C)
        - SIGTERM (kill command)
        
        Requirements: 13.1 (graceful shutdown)
        """
        def signal_handler(signum, frame):
            """Handle shutdown signals."""
            signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
            self.logger.info(f"Received {signal_name} signal - initiating graceful shutdown")
            self.stop()
            sys.exit(0)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.logger.info("✓ Signal handlers registered for graceful shutdown")
    
    def start(self) -> None:
        """
        Start hourly scheduling (blocking call).
        
        This method starts the APScheduler and blocks until stop() is called
        or a shutdown signal is received. The scheduler will trigger run_cycle()
        at the start of each hour (XX:00:00).
        
        This is a blocking call - it will not return until the scheduler is stopped.
        
        Requirements:
            - 9.1: Initiate monitoring cycles at XX:00:00 every hour
            - 13.1: Provide blocking execution model
            
        Example:
            >>> orchestrator = MonitoringOrchestrator(config)
            >>> orchestrator.start()  # Blocks here, runs cycles hourly
        """
        if self._is_running:
            self.logger.warning("Orchestrator is already running")
            return
        
        self._is_running = True
        
        self.logger.info("=" * 80)
        self.logger.info("STARTING MONITORING ORCHESTRATOR")
        self.logger.info("=" * 80)
        self.logger.info("Scheduler will trigger monitoring cycles at XX:00:00 every hour")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("=" * 80)
        
        try:
            # Start scheduler (blocking call)
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Scheduler stopped by user")
        except Exception as e:
            self.logger.error(f"Scheduler encountered error: {e}")
            raise
        finally:
            self._is_running = False
    
    def stop(self) -> None:
        """
        Stop scheduler and cleanup resources (graceful shutdown).
        
        This method implements graceful shutdown by:
        1. Setting shutdown_requested flag
        2. Waiting for current strad processing to complete (max 5 minutes timeout)
        3. Saving cycle progress and partial results
        4. Stopping the APScheduler
        5. Cleaning up all component resources
        6. Shutting down logging system
        
        Requirements: 13.2 (graceful shutdown with completion wait)
        """
        if not self._is_running:
            self.logger.warning("Orchestrator is not running")
            return
        
        self.logger.info("=" * 80)
        self.logger.info("INITIATING GRACEFUL SHUTDOWN")
        self.logger.info("=" * 80)
        
        # Step 1: Set shutdown requested flag
        self._shutdown_requested = True
        self.logger.info("Shutdown flag set")
        
        # Step 2: Wait for current strad processing to complete (max 5 minutes)
        if self._cycle_in_progress and self._current_strad_id:
            self.logger.info(
                f"Waiting for current strad processing to complete: {self._current_strad_id}"
            )
            self.logger.info("Maximum wait time: 5 minutes")
            
            max_wait_seconds = 300  # 5 minutes
            wait_start = time.time()
            
            while self._cycle_in_progress and (time.time() - wait_start) < max_wait_seconds:
                time.sleep(1)  # Check every second
                elapsed = time.time() - wait_start
                if elapsed % 30 == 0:  # Log every 30 seconds
                    self.logger.info(
                        f"Still waiting for {self._current_strad_id}... "
                        f"({elapsed:.0f}s / {max_wait_seconds}s)"
                    )
            
            if self._cycle_in_progress:
                self.logger.warning(
                    "Timeout reached (5 minutes) - forcing shutdown while cycle is in progress"
                )
                # Step 3: Save cycle progress before forcing shutdown
                self._save_partial_cycle_results()
            else:
                self.logger.info("✓ Current strad processing completed successfully")
        else:
            self.logger.info("No cycle in progress - proceeding with shutdown")
        
        # Step 4: Stop scheduler
        if self.scheduler and self.scheduler.running:
            self.logger.info("Stopping scheduler...")
            self.scheduler.shutdown(wait=False)  # Don't wait since we already waited above
            self.logger.info("✓ Scheduler stopped")
        
        # Step 5: Cleanup components
        self._cleanup_components()
        
        # Step 6: Shutdown logging
        self.logger.info("✓ Orchestrator stopped successfully")
        self.logger.info("=" * 80)
        LoggingSystem.shutdown()
        
        self._is_running = False
    
    def _save_partial_cycle_results(self) -> None:
        """
        Save partial cycle results when shutdown occurs mid-cycle.
        
        This method logs the current state when a forced shutdown occurs:
        - Current cycle number
        - Strads processed so far
        - Current strad being processed (if any)
        - Timestamp of shutdown
        
        Requirements: 15.1 (save cycle progress on shutdown)
        """
        self.logger.warning("=" * 80)
        self.logger.warning("SAVING PARTIAL CYCLE RESULTS (FORCED SHUTDOWN)")
        self.logger.warning("=" * 80)
        self.logger.warning(f"Cycle number: {self._cycle_count}")
        self.logger.warning(f"Total strads processed in this session: {self._total_strads_processed}")
        self.logger.warning(f"Current strad (incomplete): {self._current_strad_id}")
        self.logger.warning(f"Shutdown timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.warning(
            "Note: Current strad may not have been fully processed and "
            "may need to be retried in the next cycle"
        )
        self.logger.warning("=" * 80)
    
    def _cleanup_components(self) -> None:
        """
        Cleanup all component resources.
        
        Ensures proper resource release for:
        - Excel COM objects
        - Database connections
        - File handles
        """
        self.logger.info("Cleaning up component resources...")
        
        # Cleanup ExcelAutomation (COM objects)
        if self.excel_automation:
            try:
                self.logger.info("  Cleaning up ExcelAutomation...")
                self.excel_automation.cleanup()
                self.logger.info("  ✓ ExcelAutomation cleaned up")
            except Exception as e:
                self.logger.error(f"  ✗ ExcelAutomation cleanup failed: {e}")
        
        # Cleanup DatabaseInterface (connections)
        if self.db_interface:
            try:
                self.logger.info("  Cleaning up DatabaseInterface...")
                if hasattr(self.db_interface, 'connection') and self.db_interface.connection:
                    self.db_interface.connection.close()
                self.logger.info("  ✓ DatabaseInterface cleaned up")
            except Exception as e:
                self.logger.error(f"  ✗ DatabaseInterface cleanup failed: {e}")
        
        # Clear temporary snapshots
        if self.storage_manager:
            try:
                self.logger.info("  Clearing temporary snapshots...")
                self.storage_manager.clear_all_temporary()
                self.logger.info("  ✓ Temporary snapshots cleared")
            except Exception as e:
                self.logger.error(f"  ✗ Temporary snapshot cleanup failed: {e}")
        
        self.logger.info("✓ Component cleanup complete")
    
    def run_cycle(self) -> Dict:
        """
        Execute one monitoring cycle (10 strads).
        
        This method orchestrates a complete monitoring cycle:
        1. Query database for 10 eligible strads (using DatabaseInterface.get_eligible_strads)
        2. Process each strad serially using process_single_strad()
        3. Track cycle statistics: start time, end time, strads processed, strads failed
        4. Handle component failures gracefully: log error, mark strad as failed, continue with remaining
        5. Clear all temporary storage at end of cycle
        6. Log cycle completion with timestamp and count of strads processed
        
        Ensures cycle completes within 50 minutes (per requirement 9.6, delayed cycles allowed to complete).
        
        Returns:
            Dictionary with cycle statistics:
            - cycle_number: Cycle sequence number
            - start_time: Cycle start timestamp
            - end_time: Cycle end timestamp
            - strads_processed: Number of successfully processed strads
            - strads_failed: Number of failed strads
            - duration_seconds: Total cycle duration in seconds
            - strad_results: List of individual strad results
            
        Requirements:
            - 9.1: Execute monitoring cycle at XX:00:00
            - 9.2: Execute strad selection, snapshot capture, classification, result storage in sequence
            - 9.3: Process strads serially, completing one before starting next
            - 9.4: Log cycle completion with timestamp and count
            - 9.5: When errors occur, log error, skip failed strad, continue with remaining
            - 9.6: Allow delayed cycles to complete all strads
            - 5.4: Clear all temporary storage at end of cycle
        """
        # Check if shutdown requested before starting cycle
        if self._shutdown_requested:
            self.logger.info("Shutdown requested - skipping cycle execution")
            return {
                'cycle_number': self._cycle_count,
                'start_time': datetime.now(),
                'end_time': datetime.now(),
                'strads_processed': 0,
                'strads_failed': 0,
                'duration_seconds': 0,
                'strad_results': [],
                'skipped': True,
                'reason': 'shutdown_requested'
            }
        
        cycle_start_time = datetime.now()
        self._cycle_count += 1
        self._cycle_in_progress = True
        
        self.logger.info("=" * 80)
        self.logger.info(f"MONITORING CYCLE #{self._cycle_count} STARTED")
        self.logger.info(f"Cycle start time: {cycle_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 80)
        
        # Initialize cycle statistics
        strads_processed = 0
        strads_failed = 0
        strad_results = []
        
        try:
            # =================================================================
            # Step 1: Query database for 10 eligible strads
            # =================================================================
            # Requirements: 9.2 (strad selection)
            self.logger.info("Querying database for eligible strads...")
            
            try:
                eligible_strads = self.db_interface.get_eligible_strads(
                    count=self.config.strad_selection_count
                )
                self.logger.info(
                    f"Retrieved {len(eligible_strads)} eligible strads: {eligible_strads}"
                )
            except Exception as e:
                self.logger.error(f"Failed to query eligible strads: {e}")
                # Critical error - cannot proceed with cycle
                return {
                    'cycle_number': self._cycle_count,
                    'start_time': cycle_start_time,
                    'end_time': datetime.now(),
                    'strads_processed': 0,
                    'strads_failed': 0,
                    'duration_seconds': (datetime.now() - cycle_start_time).total_seconds(),
                    'strad_results': [],
                    'error': str(e)
                }
            
            # =================================================================
            # Step 2: Process each strad serially
            # =================================================================
            # Requirements: 9.3 (serial processing)
            self.logger.info(f"Processing {len(eligible_strads)} strads serially...")
            
            for index, strad_id in enumerate(eligible_strads, start=1):
                self.logger.info("-" * 80)
                self.logger.info(f"Processing strad {index}/{len(eligible_strads)}: {strad_id}")
                
                try:
                    # Process single strad (capture, classify, store)
                    result = self.process_single_strad(strad_id)
                    
                    strad_results.append(result)
                    
                    if result['success']:
                        strads_processed += 1
                        self.logger.info(
                            f"✓ {strad_id} processed successfully: {result['classification']} "
                            f"(confidence: {result['confidence']:.2f}, time: {result['processing_time_seconds']:.1f}s)"
                        )
                    else:
                        strads_failed += 1
                        self.logger.warning(
                            f"✗ {strad_id} processing failed: {result.get('error', 'Unknown error')}"
                        )
                
                except Exception as e:
                    # =================================================================
                    # Step 3: Handle component failures gracefully
                    # =================================================================
                    # Requirements: 9.5 (error recovery - log error, skip strad, continue)
                    strads_failed += 1
                    self.logger.error(
                        f"✗ Unexpected error processing {strad_id}: {e}",
                        exc_info=True
                    )
                    
                    strad_results.append({
                        'strad_id': strad_id,
                        'success': False,
                        'error': str(e),
                        'classification': None,
                        'confidence': 0.0,
                        'processing_time_seconds': 0.0
                    })
                    
                    # Continue with remaining strads (requirement 9.5)
                    self.logger.info(f"Continuing with remaining strads...")
        
        finally:
            # =================================================================
            # Step 4: Clear all temporary storage at end of cycle
            # =================================================================
            # Requirements: 5.4 (clear temporary storage at cycle end)
            self.logger.info("Clearing temporary storage...")
            try:
                self.storage_manager.clear_all_temporary()
                self.logger.info("✓ Temporary storage cleared")
            except Exception as e:
                self.logger.error(f"Failed to clear temporary storage: {e}")
        
        # =================================================================
        # Step 5: Calculate cycle statistics and log completion
        # =================================================================
        cycle_end_time = datetime.now()
        duration_seconds = (cycle_end_time - cycle_start_time).total_seconds()
        
        # Requirements: 9.4 (log cycle completion with timestamp and count)
        self.logger.info("=" * 80)
        self.logger.info(f"MONITORING CYCLE #{self._cycle_count} COMPLETED")
        self.logger.info(f"Cycle end time: {cycle_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Duration: {duration_seconds:.1f} seconds ({duration_seconds/60:.1f} minutes)")
        self.logger.info(f"Strads processed: {strads_processed}")
        self.logger.info(f"Strads failed: {strads_failed}")
        self.logger.info(f"Success rate: {strads_processed}/{len(eligible_strads) if eligible_strads else 0}")
        self.logger.info("=" * 80)
        
        # Update orchestrator statistics
        self._total_strads_processed += strads_processed
        self._total_strads_failed += strads_failed
        
        # Check if cycle exceeded 50 minutes (warning only, per requirement 9.6)
        if duration_seconds > 3000:  # 50 minutes = 3000 seconds
            self.logger.warning(
                f"Cycle exceeded 50-minute target: {duration_seconds/60:.1f} minutes"
            )
        
        # Mark cycle as completed
        self._cycle_in_progress = False
        self._current_strad_id = None
        
        return {
            'cycle_number': self._cycle_count,
            'start_time': cycle_start_time,
            'end_time': cycle_end_time,
            'strads_processed': strads_processed,
            'strads_failed': strads_failed,
            'duration_seconds': duration_seconds,
            'strad_results': strad_results
        }
    
    def process_single_strad(self, strad_id: str) -> Dict:
        """
        Process one strad: capture, classify, store.
        
        This method orchestrates the complete workflow for processing a single strad:
        1. Open video feed via Excel automation (Excel.open_video_feed)
        2. Capture snapshot from VLC media player (VLC.capture_snapshot)
        3. Classify snapshot using DL model (DL.classify_snapshot)
        4. Handle result based on classification:
           - Critical: persist snapshot to permanent storage, store result with file path,
                      add to critical exclusion list, track with moderate_tracker
           - Moderate/None: store result without snapshot path, track with moderate_tracker
        5. Update check history with current timestamp
        6. Clear temporary snapshot
        
        Implements retry logic for component failures (3 attempts with exponential backoff).
        
        Args:
            strad_id: Strad CHE number in format SCXXX (e.g., "SC042")
            
        Returns:
            Dictionary with processing result:
            - strad_id: The strad identifier
            - success: True if processing succeeded, False otherwise
            - classification: Classification result ('none', 'moderate', 'critical')
            - confidence: Confidence score (0.0-1.0)
            - processing_time_seconds: Time taken to process this strad
            - snapshot_path: Path to persisted snapshot (only for critical)
            - error: Error message if processing failed
            
        Requirements:
            - 9.3: Serial strad processing workflow
            - 4.1: DL classification integration
            - 4.2: Snapshot classification
            - 4.3: Severity level mapping
            - 5.2: Temporary storage cleanup after classification
            - 5.3: Critical snapshot persistence
            - 6.1: Store classification result
            - 6.2: Associate result with strad ID
            - 7.1: Add critical strads to exclusion list
            - 7.2: Exclude critical strads from future selection
        """
        # Track current strad for graceful shutdown
        self._current_strad_id = strad_id
        strad_start_time = time.time()
        temp_snapshot_path = None
        
        try:
            # =================================================================
            # Step 1: Open video feed via Excel automation
            # =================================================================
            # Requirements: 2.1-2.6 (Excel video feed automation)
            self.logger.info(f"  [1/6] Opening video feed for {strad_id}...")
            
            try:
                # Retry logic implemented inside open_video_feed (3 attempts)
                video_feed_opened = self.excel_automation.open_video_feed(strad_id)
                
                if not video_feed_opened:
                    # VLC window not found within timeout (30 seconds)
                    # Requirement 2.6: discard strad for current cycle, retry later
                    error_msg = "VLC window not found within timeout"
                    self.logger.warning(f"  ✗ {strad_id}: {error_msg}")
                    return {
                        'strad_id': strad_id,
                        'success': False,
                        'error': error_msg,
                        'classification': None,
                        'confidence': 0.0,
                        'processing_time_seconds': time.time() - strad_start_time
                    }
                
                self.logger.info(f"  ✓ Video feed opened for {strad_id}")
                
            except Exception as e:
                error_msg = f"Excel automation failed: {e}"
                self.logger.error(f"  ✗ {strad_id}: {error_msg}")
                return {
                    'strad_id': strad_id,
                    'success': False,
                    'error': error_msg,
                    'classification': None,
                    'confidence': 0.0,
                    'processing_time_seconds': time.time() - strad_start_time
                }
            
            # =================================================================
            # Step 2: Capture snapshot from VLC media player
            # =================================================================
            # Requirements: 3.1-3.6 (VLC snapshot capture with retry)
            self.logger.info(f"  [2/6] Capturing snapshot for {strad_id}...")
            
            try:
                # Includes stabilization delay and 3 retry attempts
                snapshot = self.vlc_capture.capture_snapshot()
                self.logger.info(
                    f"  ✓ Snapshot captured: {snapshot.shape[1]}x{snapshot.shape[0]} pixels"
                )
            except Exception as e:
                error_msg = f"VLC capture failed: {e}"
                self.logger.error(f"  ✗ {strad_id}: {error_msg}")
                return {
                    'strad_id': strad_id,
                    'success': False,
                    'error': error_msg,
                    'classification': None,
                    'confidence': 0.0,
                    'processing_time_seconds': time.time() - strad_start_time
                }
            
            # =================================================================
            # Step 3: Store snapshot temporarily
            # =================================================================
            # Requirements: 5.1 (temporary storage)
            self.logger.info(f"  [3/6] Storing snapshot temporarily...")
            
            try:
                temp_snapshot_path = self.storage_manager.store_temporary_snapshot(
                    strad_id=strad_id,
                    snapshot=snapshot
                )
                self.logger.debug(f"  ✓ Temporary snapshot: {temp_snapshot_path}")
            except Exception as e:
                error_msg = f"Temporary storage failed: {e}"
                self.logger.error(f"  ✗ {strad_id}: {error_msg}")
                return {
                    'strad_id': strad_id,
                    'success': False,
                    'error': error_msg,
                    'classification': None,
                    'confidence': 0.0,
                    'processing_time_seconds': time.time() - strad_start_time
                }
            
            # =================================================================
            # Step 4: Classify snapshot using DL model
            # =================================================================
            # Requirements: 4.1-4.6 (DL classification)
            self.logger.info(f"  [4/6] Classifying snapshot...")
            
            try:
                # Use fallback classification if DL model not available (testing mode)
                if self.dl_classifier is None:
                    self.logger.warning(f"  ⚠ DL model not available - using random fallback classification")
                    import random
                    from ..dl_classifier.classifier_wrapper import ClassificationResult
                    
                    # Generate random classification for testing
                    severity = random.choice(['none', 'moderate', 'critical'])
                    confidence = random.uniform(0.5, 0.95)
                    
                    classification_result = ClassificationResult(
                        severity=severity,
                        confidence=confidence,
                        processing_time_ms=10.0,
                        model_name='fallback_random',
                        threshold_used=0.5
                    )
                else:
                    classification_result = self.dl_classifier.classify_snapshot(snapshot)
                
                self.logger.info(
                    f"  ✓ Classification: {classification_result.severity} "
                    f"(confidence: {classification_result.confidence:.3f}, "
                    f"time: {classification_result.processing_time_ms:.1f}ms)"
                )
                
                # Check for zero confidence alert (Requirement 4.4)
                if classification_result.confidence == 0.0:
                    self.logger.warning(
                        f"  ⚠ Zero confidence detected for {strad_id} - alert should be sent"
                    )
                
            except Exception as e:
                error_msg = f"Classification failed: {e}"
                self.logger.error(f"  ✗ {strad_id}: {error_msg}")
                # Clean up temporary snapshot
                if temp_snapshot_path:
                    try:
                        self.storage_manager.clear_temporary_snapshot(temp_snapshot_path)
                    except Exception:
                        pass
                return {
                    'strad_id': strad_id,
                    'success': False,
                    'error': error_msg,
                    'classification': None,
                    'confidence': 0.0,
                    'processing_time_seconds': time.time() - strad_start_time
                }
            
            # =================================================================
            # Step 5: Handle result based on classification
            # =================================================================
            self.logger.info(f"  [5/6] Processing classification result...")
            
            snapshot_path = None
            current_timestamp = datetime.now()
            
            if classification_result.severity == 'critical':
                # =============================================================
                # CRITICAL CLASSIFICATION WORKFLOW
                # =============================================================
                # Requirements: 5.3, 10.1-10.5 (critical snapshot persistence)
                # Requirements: 7.1, 7.2 (critical exclusion management)
                
                self.logger.info(f"  ⚠ CRITICAL misalignment detected for {strad_id}")
                
                try:
                    # Persist snapshot to permanent storage
                    snapshot_path = self.storage_manager.persist_critical_snapshot(
                        strad_id=strad_id,
                        snapshot=snapshot,
                        timestamp=current_timestamp
                    )
                    self.logger.info(f"  ✓ Critical snapshot persisted: {snapshot_path}")
                except Exception as e:
                    self.logger.error(f"  ✗ Failed to persist critical snapshot: {e}")
                    # Continue processing even if snapshot persistence fails
                
                try:
                    # Store result in database with snapshot path
                    self.db_interface.store_classification_result(
                        strad_id=strad_id,
                        classification=classification_result.severity,
                        confidence=classification_result.confidence,
                        snapshot_path=snapshot_path
                    )
                    self.logger.info(f"  ✓ Classification result stored in database")
                except Exception as e:
                    self.logger.error(f"  ✗ Failed to store classification result: {e}")
                
                try:
                    # Add to critical exclusion list
                    self.db_interface.add_to_critical_exclusion(
                        strad_id=strad_id,
                        reason=f"Critical misalignment (confidence: {classification_result.confidence:.3f})"
                    )
                    self.logger.info(f"  ✓ {strad_id} added to critical exclusion list")
                except Exception as e:
                    self.logger.error(f"  ✗ Failed to add to critical exclusion: {e}")
                
                try:
                    # Track with moderate tracker (resets counter for critical)
                    self.moderate_tracker.record_classification(
                        strad_id=strad_id,
                        classification=classification_result.severity,
                        confidence=classification_result.confidence,
                        timestamp=current_timestamp
                    )
                except Exception as e:
                    self.logger.error(f"  ✗ Failed to update moderate tracker: {e}")
                
            else:
                # =============================================================
                # MODERATE/NONE CLASSIFICATION WORKFLOW
                # =============================================================
                # Requirements: 11.1-11.6 (moderate classification handling)
                
                self.logger.info(
                    f"  ℹ {classification_result.severity.upper()} classification for {strad_id}"
                )
                
                try:
                    # Store result in database without snapshot path
                    self.db_interface.store_classification_result(
                        strad_id=strad_id,
                        classification=classification_result.severity,
                        confidence=classification_result.confidence,
                        snapshot_path=None  # No snapshot for moderate/none
                    )
                    self.logger.info(f"  ✓ Classification result stored in database")
                except Exception as e:
                    self.logger.error(f"  ✗ Failed to store classification result: {e}")
                
                try:
                    # Track with moderate tracker (may trigger warning at 3 consecutive)
                    self.moderate_tracker.record_classification(
                        strad_id=strad_id,
                        classification=classification_result.severity,
                        confidence=classification_result.confidence,
                        timestamp=current_timestamp
                    )
                except Exception as e:
                    self.logger.error(f"  ✗ Failed to update moderate tracker: {e}")
            
            # =================================================================
            # Step 6: Update check history and cleanup
            # =================================================================
            self.logger.info(f"  [6/6] Finalizing processing...")
            
            try:
                # Update check history with current timestamp
                # Requirements: 6.6, 8.1 (check history update)
                self.db_interface.update_check_history(strad_id)
                self.logger.info(f"  ✓ Check history updated for {strad_id}")
            except Exception as e:
                self.logger.error(f"  ✗ Failed to update check history: {e}")
            
            try:
                # Clear temporary snapshot
                # Requirements: 5.2 (temporary storage cleanup)
                if temp_snapshot_path:
                    self.storage_manager.clear_temporary_snapshot(temp_snapshot_path)
                    self.logger.debug(f"  ✓ Temporary snapshot cleared")
            except Exception as e:
                self.logger.error(f"  ✗ Failed to clear temporary snapshot: {e}")
            
            # =================================================================
            # Return successful result
            # =================================================================
            processing_time = time.time() - strad_start_time
            
            return {
                'strad_id': strad_id,
                'success': True,
                'classification': classification_result.severity,
                'confidence': classification_result.confidence,
                'processing_time_seconds': processing_time,
                'snapshot_path': snapshot_path  # Only set for critical classifications
            }
        
        except Exception as e:
            # =================================================================
            # Unexpected error handling
            # =================================================================
            self.logger.error(
                f"  ✗ Unexpected error processing {strad_id}: {e}",
                exc_info=True
            )
            
            # Clean up temporary snapshot if it exists
            if temp_snapshot_path:
                try:
                    self.storage_manager.clear_temporary_snapshot(temp_snapshot_path)
                except Exception:
                    pass  # Ignore cleanup errors
            
            return {
                'strad_id': strad_id,
                'success': False,
                'error': f"Unexpected error: {e}",
                'classification': None,
                'confidence': 0.0,
                'processing_time_seconds': time.time() - strad_start_time
            }
    
    def get_statistics(self) -> Dict:
        """
        Get orchestrator runtime statistics.
        
        Returns:
            Dictionary with runtime statistics including:
            - cycle_count: Number of cycles executed
            - total_strads_processed: Total strads successfully processed
            - total_strads_failed: Total strads that failed processing
            - is_running: Whether orchestrator is currently running
            
        Example:
            >>> stats = orchestrator.get_statistics()
            >>> print(f"Cycles: {stats['cycle_count']}")
        """
        return {
            'cycle_count': self._cycle_count,
            'total_strads_processed': self._total_strads_processed,
            'total_strads_failed': self._total_strads_failed,
            'is_running': self._is_running
        }


# ==============================================================================
# Main Entry Point
# ==============================================================================

def main():
    """
    Main entry point for the monitoring system.
    
    This function:
    1. Loads configuration from system_config.json
    2. Creates MonitoringOrchestrator instance
    3. Starts the orchestrator (blocking)
    
    Usage:
        python -m strad_monitoring.orchestration.orchestrator
    """
    try:
        # Load configuration
        print("Loading configuration from system_config.json...")
        config = ConfigurationManager.load_config("system_config.json")
        print("✓ Configuration loaded successfully")
        
        # Create orchestrator
        print("\nInitializing monitoring orchestrator...")
        orchestrator = MonitoringOrchestrator(config)
        print("✓ Orchestrator initialized")
        
        # Start orchestrator (blocking call)
        print("\nStarting monitoring system...")
        orchestrator.start()
        
    except KeyboardInterrupt:
        print("\n\nShutdown requested by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
