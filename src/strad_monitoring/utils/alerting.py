"""
Alerting Utilities for Strad Monitoring System

Provides alert notification functionality for critical errors, warnings,
and system health issues.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime


class AlertLevel:
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def send_alert(
    message: str,
    level: str = AlertLevel.WARNING,
    component: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Send alert notification for system issues.
    
    This is a placeholder implementation that logs alerts. In production,
    this would integrate with:
    - Email notification system (SMTP)
    - SMS notification service (Twilio, AWS SNS)
    - Dashboard/monitoring system (Grafana, Prometheus)
    - Ticketing system (JIRA, ServiceNow)
    
    Args:
        message: Alert message
        level: Alert severity level (info, warning, error, critical)
        component: Component name that generated the alert
        details: Additional context (error details, stack traces, etc.)
    
    Returns:
        True if alert sent successfully, False otherwise
    
    Example:
        >>> send_alert(
        ...     "Classification confidence 0.0 detected",
        ...     level=AlertLevel.WARNING,
        ...     component="DLClassifier",
        ...     details={"strad_id": "SC042", "confidence": 0.0}
        ... )
    """
    logger = logging.getLogger("AlertSystem")
    
    # Format alert message with context
    alert_msg = f"[{level.upper()}]"
    if component:
        alert_msg += f" [{component}]"
    alert_msg += f" {message}"
    
    if details:
        alert_msg += f" | Details: {details}"
    
    # Log based on severity
    if level == AlertLevel.CRITICAL:
        logger.critical(alert_msg)
    elif level == AlertLevel.ERROR:
        logger.error(alert_msg)
    elif level == AlertLevel.WARNING:
        logger.warning(alert_msg)
    else:
        logger.info(alert_msg)
    
    # TODO: Implement actual notification delivery
    # - Send email via SMTP
    # - Send SMS via Twilio/AWS SNS
    # - Post to dashboard API
    # - Create ticket in system
    
    return True


def send_critical_error_alert(
    error_message: str,
    component: str,
    strad_id: Optional[str] = None,
    exception: Optional[Exception] = None
) -> bool:
    """
    Send critical error alert to developers/operators.
    
    Used for system-level failures that require immediate attention:
    - Database connection loss
    - Model loading failure
    - Excel/VLC automation failure
    - Disk space exhaustion
    
    Args:
        error_message: Error description
        component: Component that failed
        strad_id: Strad being processed when error occurred (optional)
        exception: Original exception object (optional)
    
    Returns:
        True if alert sent successfully
    """
    details = {
        "timestamp": datetime.now().isoformat(),
        "component": component
    }
    
    if strad_id:
        details["strad_id"] = strad_id
    
    if exception:
        details["exception_type"] = type(exception).__name__
        details["exception_message"] = str(exception)
    
    return send_alert(
        message=f"CRITICAL ERROR: {error_message}",
        level=AlertLevel.CRITICAL,
        component=component,
        details=details
    )


def send_low_confidence_alert(
    strad_id: str,
    confidence: float,
    classification: str
) -> bool:
    """
    Send alert for low confidence classification (confidence = 0.0).
    
    Alerts developers when model produces zero confidence, which may indicate:
    - Model inference issue
    - Corrupted input image
    - Edge case not covered in training data
    
    Args:
        strad_id: Strad that produced low confidence
        confidence: Confidence score (typically 0.0)
        classification: Assigned classification (typically 'moderate')
    
    Returns:
        True if alert sent successfully
    """
    return send_alert(
        message=f"Low confidence classification detected for {strad_id}",
        level=AlertLevel.WARNING,
        component="DLClassifier",
        details={
            "strad_id": strad_id,
            "confidence": confidence,
            "classification": classification,
            "action": "Assigned 'moderate' per conservative fallback policy"
        }
    )


def send_consecutive_moderate_alert(
    strad_id: str,
    consecutive_count: int,
    time_window_hours: int = 24
) -> bool:
    """
    Send alert for consecutive moderate classifications.
    
    Alerts operators when a strad receives multiple consecutive moderate
    classifications within a time window, indicating persistent minor misalignment.
    
    Args:
        strad_id: Strad with consecutive moderate classifications
        consecutive_count: Number of consecutive moderate results
        time_window_hours: Time window in hours (default: 24)
    
    Returns:
        True if alert sent successfully
    """
    return send_alert(
        message=f"Strad {strad_id} has {consecutive_count} consecutive moderate classifications",
        level=AlertLevel.WARNING,
        component="ModerateTracker",
        details={
            "strad_id": strad_id,
            "consecutive_count": consecutive_count,
            "time_window_hours": time_window_hours,
            "recommendation": "Consider manual inspection or adjustment"
        }
    )
