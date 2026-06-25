"""
Custom Exception Hierarchy for Strad Monitoring System

This module defines all custom exceptions used throughout the system for
error handling and categorization. Exceptions are organized hierarchically
to allow catching errors at different levels of specificity.

Exception Hierarchy:
    MonitoringSystemError (base)
    ├── ConfigurationError (fail-fast at startup)
    ├── ComponentError (recoverable, log and continue)
    │   ├── DatabaseError
    │   ├── ExcelAutomationError
    │   ├── VLCCaptureError
    │   ├── ClassificationError
    │   └── StorageError
    └── CriticalError (alert and pause system)

Usage Example:
    try:
        db.get_eligible_strads()
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        # Skip this strad, continue with others
    except CriticalError as e:
        logger.critical(f"Critical error: {e}")
        send_alert("System paused", str(e))
        scheduler.pause()
"""

from typing import Optional


class MonitoringSystemError(Exception):
    """
    Base exception for all Strad Monitoring System errors.
    
    All custom exceptions inherit from this base class, allowing
    broad exception handling when needed.
    
    Attributes:
        component: Name of the component where error occurred
        strad_id: Strad ID being processed when error occurred (if applicable)
        original_error: Original exception that caused this error (if applicable)
    """
    
    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        strad_id: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize monitoring system error.
        
        Args:
            message: Human-readable error description
            component: Component name (e.g., "DatabaseInterface", "VLCCapture")
            strad_id: Strad ID (e.g., "SC042") if error is strad-specific
            original_error: Original exception if this is a wrapped error
        """
        super().__init__(message)
        self.message = message
        self.component = component
        self.strad_id = strad_id
        self.original_error = original_error
    
    def __str__(self) -> str:
        """Format error message with component and strad_id context."""
        parts = []
        if self.component:
            parts.append(f"[{self.component}]")
        if self.strad_id:
            parts.append(f"(Strad: {self.strad_id})")
        parts.append(self.message)
        
        if self.original_error:
            parts.append(f"- Caused by: {type(self.original_error).__name__}: {str(self.original_error)}")
        
        return " ".join(parts)


class ConfigurationError(MonitoringSystemError):
    """
    Configuration validation failed.
    
    Raised when system configuration is invalid or missing required fields.
    This error should cause the system to FAIL FAST at startup - do not
    start monitoring cycles if configuration is invalid.
    
    Usage:
        if validation_errors:
            raise ConfigurationError(
                "Invalid configuration",
                component="ConfigurationManager"
            )
    """
    pass


class ComponentError(MonitoringSystemError):
    """
    Component operation failed (recoverable).
    
    Base class for errors from system components (database, Excel, VLC, etc.).
    These errors are recoverable - the system should log the error, skip the
    failed strad, and continue processing remaining strads in the cycle.
    
    Usage:
        try:
            # Component operation
        except ComponentError as e:
            logger.error(f"Component failure: {e}")
            failed_strads.append(strad_id)
            continue  # Process next strad
    """
    pass


class DatabaseError(ComponentError):
    """
    Database operation failed.
    
    Raised when SQL Server queries, connections, or updates fail.
    Includes both production database errors and fallback mechanism errors.
    
    Usage:
        try:
            cursor.execute(query)
        except pyodbc.Error as e:
            raise DatabaseError(
                "Failed to query eligible strads",
                component="DatabaseInterface",
                original_error=e
            )
    """
    pass


class ExcelAutomationError(ComponentError):
    """
    Excel COM automation failed.
    
    Raised when Excel operations fail: opening workbook, locating controls,
    activating video encoder button, or verifying VLC window opens.
    
    Usage:
        if not vlc_window_found:
            raise ExcelAutomationError(
                "VLC window not found after 30 seconds",
                component="ExcelAutomation",
                strad_id=strad_id
            )
    """
    pass


class VLCCaptureError(ComponentError):
    """
    VLC window capture failed.
    
    Raised when VLC media player snapshot capture fails: window not found,
    capture operation failed, or snapshot validation failed.
    
    Usage:
        if not snapshot_valid:
            raise VLCCaptureError(
                f"Snapshot dimensions too small: {width}x{height}",
                component="VLCCapture",
                strad_id=strad_id
            )
    """
    pass


class ClassificationError(ComponentError):
    """
    Deep learning classification failed.
    
    Raised when DL model inference fails: model loading errors, inference
    timeout, invalid output, or classification mapping errors.
    
    Usage:
        if processing_time > timeout:
            raise ClassificationError(
                f"Classification exceeded {timeout}s timeout",
                component="DLClassifierWrapper",
                strad_id=strad_id
            )
    """
    pass


class StorageError(ComponentError):
    """
    Storage operation failed.
    
    Raised when file system operations fail: snapshot save errors, directory
    creation failures, disk space issues, or file verification errors.
    
    Usage:
        if not file_readable:
            raise StorageError(
                f"Saved snapshot not readable: {file_path}",
                component="StorageManager",
                strad_id=strad_id
            )
    """
    pass


class CriticalError(MonitoringSystemError):
    """
    Critical system error requiring manual intervention.
    
    Raised when the system encounters unrecoverable errors that prevent
    continued operation. This error should trigger:
    1. Alert notifications (email, SMS, dashboard)
    2. Scheduler pause
    3. Wait for manual resolution
    
    Examples of critical errors:
    - Database server completely unreachable (all retries exhausted)
    - DL model checkpoint file missing or corrupted
    - GPU out of memory
    - Disk space below critical threshold (< 10GB)
    - Excel application crashes repeatedly
    
    Usage:
        if disk_space_gb < 10:
            raise CriticalError(
                f"Disk space critically low: {disk_space_gb}GB remaining",
                component="StorageManager"
            )
            # Caller should: send_alert(), scheduler.pause()
    """
    pass


# ============================================================================
# EXCEPTION HELPER FUNCTIONS
# ============================================================================

def wrap_component_error(
    error: Exception,
    component: str,
    message: str,
    strad_id: Optional[str] = None
) -> ComponentError:
    """
    Wrap a generic exception into a ComponentError with context.
    
    This helper function converts standard Python exceptions (IOError,
    ConnectionError, etc.) into typed ComponentError instances with
    full context about where and why the error occurred.
    
    Args:
        error: Original exception to wrap
        component: Name of component where error occurred
        message: Human-readable description
        strad_id: Strad ID if error is strad-specific
        
    Returns:
        ComponentError (or subclass) with full context
        
    Example:
        try:
            file.write(data)
        except IOError as e:
            raise wrap_component_error(
                e, "StorageManager", "Failed to save snapshot", strad_id
            )
    """
    # Map exception types to specific ComponentError subclasses
    error_type = type(error).__name__
    
    if 'sql' in error_type.lower() or 'database' in error_type.lower():
        return DatabaseError(message, component, strad_id, error)
    elif 'com' in error_type.lower() or 'excel' in error_type.lower():
        return ExcelAutomationError(message, component, strad_id, error)
    elif 'io' in error_type.lower() or 'file' in error_type.lower():
        return StorageError(message, component, strad_id, error)
    else:
        return ComponentError(message, component, strad_id, error)
