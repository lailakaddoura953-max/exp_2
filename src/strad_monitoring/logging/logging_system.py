"""
Logging System for Strad Monitoring Automation

This module provides structured logging with daily rotation for the monitoring system.
All component operations are logged with appropriate levels for debugging, auditing,
and monitoring system behavior.

Log Format:
    2024-01-15 14:30:22,145 [INFO] [Orchestrator] Cycle started: 10 strads selected
    2024-01-15 14:30:22,678 [INFO] [DatabaseInterface] Query returned strads: SC042, SC078...
    2024-01-15 14:30:30,456 [ERROR] [ExcelAutomation] VLC window not found for SC078 (attempt 1/3)

Log Levels:
    - DEBUG: Detailed component state for debugging
    - INFO: Normal operations and progress
    - WARNING: Recoverable errors and degraded performance
    - ERROR: Component failures requiring attention
    - CRITICAL: System-wide issues requiring manual intervention
"""

import logging
import os
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from pathlib import Path
from queue import Queue
from typing import Optional


class LoggingSystem:
    """
    Logging system with rotation and structured formatting.
    
    This class sets up system-wide logging configuration with:
    - Daily log rotation at midnight
    - Structured log format with timestamp, level, component, message
    - Asynchronous logging via QueueHandler to prevent I/O blocking
    - Automatic cleanup of old log files
    - Console handler for development/debugging
    """
    
    _initialized: bool = False
    _queue_listener: Optional[QueueListener] = None
    
    @staticmethod
    def setup_logging(
        log_file_path: str,
        log_level: str = "INFO",
        retention_days: int = 14,
        enable_console: bool = False
    ) -> None:
        """
        Configure system-wide logging.
        
        This method should be called once at system startup to initialize
        logging configuration. All subsequent logger instances will inherit
        this configuration.
        
        Args:
            log_file_path: Directory path for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            retention_days: Number of days to retain log files
            enable_console: Enable console output for development
            
        Example:
            >>> LoggingSystem.setup_logging(
            ...     log_file_path="C:/StradMonitoring/logs",
            ...     log_level="INFO",
            ...     retention_days=14
            ... )
        """
        if LoggingSystem._initialized:
            return  # Avoid re-initialization
        
        # Create log directory if it doesn't exist
        os.makedirs(log_file_path, exist_ok=True)
        
        # Generate log filename with current date
        log_filename = f"monitoring_log_{datetime.now().strftime('%Y-%m-%d')}.txt"
        log_filepath = os.path.join(log_file_path, log_filename)
        
        # Create formatter with structured format
        formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Create rotating file handler (rotates daily at midnight)
        file_handler = RotatingFileHandler(
            filename=log_filepath,
            maxBytes=100 * 1024 * 1024,  # 100MB max file size
            backupCount=retention_days,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Set up asynchronous logging with QueueHandler
        # This prevents I/O blocking during intensive operations
        log_queue = Queue(-1)  # No size limit
        queue_handler = QueueHandler(log_queue)
        
        # Create queue listener to process log records asynchronously
        LoggingSystem._queue_listener = QueueListener(
            log_queue,
            file_handler,
            respect_handler_level=True
        )
        LoggingSystem._queue_listener.start()
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        root_logger.addHandler(queue_handler)
        
        # Add console handler if enabled (for development)
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(getattr(logging, log_level.upper()))
            root_logger.addHandler(console_handler)
        
        # Clean up old log files
        LoggingSystem._cleanup_old_logs(log_file_path, retention_days)
        
        # Mark as initialized
        LoggingSystem._initialized = True
        
        # Log initialization
        logger = logging.getLogger("LoggingSystem")
        logger.info(f"Logging system initialized: {log_filepath}")
        logger.info(f"Log level: {log_level}, Retention: {retention_days} days")
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Get logger instance for a component.
        
        Each component should get its own named logger for clear log
        attribution and filtering.
        
        Args:
            name: Component name (e.g., "DatabaseInterface", "Orchestrator")
            
        Returns:
            Logger instance configured with system-wide settings
            
        Example:
            >>> logger = LoggingSystem.get_logger("DatabaseInterface")
            >>> logger.info("Query returned 10 eligible strads")
            2024-01-15 14:30:22,678 [INFO] [DatabaseInterface] Query returned 10 eligible strads
        """
        return logging.getLogger(name)
    
    @staticmethod
    def _cleanup_old_logs(log_file_path: str, retention_days: int) -> None:
        """
        Remove log files older than retention period.
        
        Scans the log directory and deletes any log files with dates
        older than the retention period.
        
        Args:
            log_file_path: Directory containing log files
            retention_days: Number of days to retain
        """
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Scan log directory
            log_dir = Path(log_file_path)
            if not log_dir.exists():
                return
            
            deleted_count = 0
            for log_file in log_dir.glob("monitoring_log_*.txt*"):
                try:
                    # Extract date from filename: monitoring_log_YYYY-MM-DD.txt
                    filename = log_file.stem  # Remove extension
                    if filename.startswith("monitoring_log_"):
                        date_str = filename.replace("monitoring_log_", "")
                        # Handle backup files (.txt.1, .txt.2, etc.)
                        date_str = date_str.split('.')[0]
                        
                        log_date = datetime.strptime(date_str, "%Y-%m-%d")
                        
                        # Delete if older than retention period
                        if log_date < cutoff_date:
                            log_file.unlink()
                            deleted_count += 1
                except (ValueError, OSError) as e:
                    # Skip files that don't match expected format
                    logging.warning(f"Could not process log file {log_file}: {e}")
            
            if deleted_count > 0:
                logger = logging.getLogger("LoggingSystem")
                logger.info(f"Cleaned up {deleted_count} old log files")
        
        except Exception as e:
            # Don't fail system startup if cleanup fails
            logging.warning(f"Log cleanup failed: {e}")
    
    @staticmethod
    def shutdown() -> None:
        """
        Shutdown logging system gracefully.
        
        Stops the queue listener and flushes all pending log records.
        Should be called during system shutdown to ensure all logs are written.
        
        Example:
            >>> LoggingSystem.shutdown()
        """
        if LoggingSystem._queue_listener:
            LoggingSystem._queue_listener.stop()
            LoggingSystem._queue_listener = None
            LoggingSystem._initialized = False


# ============================================================================
# LOGGING HELPER FUNCTIONS
# ============================================================================

def log_component_operation(
    logger: logging.Logger,
    operation: str,
    strad_id: Optional[str] = None,
    details: Optional[str] = None
) -> None:
    """
    Log a component operation with consistent formatting.
    
    Helper function to ensure consistent log message formatting across
    all components.
    
    Args:
        logger: Logger instance
        operation: Operation description
        strad_id: Strad ID if operation is strad-specific
        details: Additional details
        
    Example:
        >>> log_component_operation(
        ...     logger, "Snapshot captured", strad_id="SC042", details="1920x1080 pixels"
        ... )
        2024-01-15 14:30:28,445 [INFO] [VLCCapture] Snapshot captured: SC042 (1920x1080 pixels)
    """
    parts = [operation]
    if strad_id:
        parts.append(f": {strad_id}")
    if details:
        parts.append(f"({details})")
    
    logger.info(" ".join(parts))


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    operation: str,
    strad_id: Optional[str] = None
) -> None:
    """
    Log an error with full context and stack trace.
    
    Helper function for consistent error logging with component context.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        operation: Operation that failed
        strad_id: Strad ID if error is strad-specific
        
    Example:
        >>> try:
        ...     cursor.execute(query)
        ... except Exception as e:
        ...     log_error_with_context(logger, e, "Query eligible strads")
        2024-01-15 14:30:30,456 [ERROR] [DatabaseInterface] Query eligible strads failed: ConnectionError
    """
    parts = [f"{operation} failed", f"{type(error).__name__}"]
    if strad_id:
        parts.insert(1, f"for {strad_id}")
    
    error_msg = ": ".join(parts)
    logger.error(error_msg, exc_info=True)


def log_cycle_progress(
    logger: logging.Logger,
    cycle_info: dict
) -> None:
    """
    Log cycle progress with standardized format.
    
    Helper function for logging cycle completion statistics.
    
    Args:
        logger: Logger instance
        cycle_info: Dictionary with cycle statistics
            - start_time: Cycle start timestamp
            - end_time: Cycle end timestamp
            - strads_processed: Number of strads successfully processed
            - strads_failed: Number of strads that failed
            - duration_seconds: Total cycle duration
            
    Example:
        >>> log_cycle_progress(logger, {
        ...     "start_time": "2024-01-15 14:00:00",
        ...     "end_time": "2024-01-15 14:45:00",
        ...     "strads_processed": 8,
        ...     "strads_failed": 2,
        ...     "duration_seconds": 2700
        ... })
        2024-01-15 14:45:00 [INFO] [Orchestrator] Cycle complete: 8/10 strads processed, 2 failed, duration: 45m 0s
    """
    duration_min = int(cycle_info.get("duration_seconds", 0) // 60)
    duration_sec = int(cycle_info.get("duration_seconds", 0) % 60)
    
    processed = cycle_info.get("strads_processed", 0)
    failed = cycle_info.get("strads_failed", 0)
    total = processed + failed
    
    logger.info(
        f"Cycle complete: {processed}/{total} strads processed, "
        f"{failed} failed, duration: {duration_min}m {duration_sec}s"
    )
