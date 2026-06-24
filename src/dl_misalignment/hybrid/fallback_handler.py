"""
Automatic Fallback Handler

This module implements automatic fallback from neural network to rule-based
detection when neural network inference fails.

Task 12.4: Implement Automatic Fallback on Neural Network Failure
Requirements: 26.1, 26.2, 26.3, 26.4, 26.5, 26.6, 26.7
"""

import logging
import time
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ==============================================================================
# Task 12.4: Fallback Status Enumeration
# ==============================================================================

class FallbackStatus(Enum):
    """
    Status of fallback system.
    
    Requirements: 26.7
    """
    NORMAL = "normal"                    # Neural network operating normally
    FALLBACK_ACTIVE = "fallback_active"  # Fallen back to rule-based
    RECOVERY_ATTEMPT = "recovery_attempt"  # Attempting to recover neural network
    PERMANENT_FALLBACK = "permanent_fallback"  # 3+ failures, manual intervention needed


# ==============================================================================
# Task 12.4: Fallback Event Data Structure
# ==============================================================================

@dataclass
class FallbackEvent:
    """
    Records a fallback event for monitoring and diagnostics.
    
    Requirements: 26.2 (logging), 26.7 (monitoring API)
    """
    timestamp: datetime
    event_type: str  # 'fallback', 'recovery_success', 'recovery_failure'
    error_message: str
    exception_type: Optional[str] = None
    consecutive_failures: int = 0


# ==============================================================================
# Task 12.4: Fallback Handler
# ==============================================================================

class FallbackHandler:
    """
    Manages automatic fallback from neural network to rule-based detection.
    
    What does the fallback handler do?
    1. Wraps neural network inference in exception handling
    2. Auto-switches to rule-based on inference failure
    3. Attempts recovery after configurable delay
    4. Enters permanent fallback after repeated failures
    5. Exposes fallback status via monitoring API
    
    Why is this important?
    - Ensures system continues operating despite neural network issues
    - Provides graceful degradation for safety-critical applications
    - Enables automatic recovery without manual intervention
    - Maintains service availability
    
    Requirements: 26.1, 26.2, 26.3, 26.4, 26.5, 26.6, 26.7
    """
    
    def __init__(
        self,
        recovery_delay_seconds: int = 60,
        max_consecutive_failures: int = 3
    ):
        """
        Initialize fallback handler.
        
        Args:
            recovery_delay_seconds: Time to wait before attempting recovery (default 60)
            max_consecutive_failures: Failures before permanent fallback (default 3)
        
        Requirements: 26.4 (60 second delay), 26.5 (3 failures threshold)
        
        Example:
            >>> handler = FallbackHandler(recovery_delay_seconds=60, max_consecutive_failures=3)
            >>> handler.status
            <FallbackStatus.NORMAL: 'normal'>
        """
        self.recovery_delay_seconds = recovery_delay_seconds
        self.max_consecutive_failures = max_consecutive_failures
        
        # Current status
        self.status = FallbackStatus.NORMAL
        
        # Failure tracking
        self.consecutive_failures = 0
        self.total_failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_recovery_attempt: Optional[datetime] = None
        
        # Event history
        self.event_history: list[FallbackEvent] = []
        self.max_history_size = 100  # Keep last 100 events
        
        # Statistics
        self.fallback_count = 0
        self.recovery_success_count = 0
        self.recovery_failure_count = 0
        
        logger.info(
            f"FallbackHandler initialized: "
            f"recovery_delay={recovery_delay_seconds}s, "
            f"max_failures={max_consecutive_failures}"
        )
    
    def wrap_neural_inference(
        self,
        inference_func,
        *args,
        **kwargs
    ):
        """
        Wrap neural network inference with exception handling.
        
        If inference fails, automatically switches to fallback mode.
        
        Args:
            inference_func: Neural network inference function to wrap
            *args: Positional arguments for inference function
            **kwargs: Keyword arguments for inference function
        
        Returns:
            Inference result if successful, None if failed
        
        Requirements: 26.1, 26.2
        
        Example:
            >>> def neural_infer(frames):
            ...     return model.predict(frames)
            >>> result = handler.wrap_neural_inference(neural_infer, frames)
            >>> if result is None:
            ...     # Fallback to rule-based
            ...     result = rule_based_infer(frames)
        """
        # Check if we should attempt recovery
        if self.status == FallbackStatus.FALLBACK_ACTIVE:
            if self._should_attempt_recovery():
                logger.info("Attempting neural network recovery...")
                self.status = FallbackStatus.RECOVERY_ATTEMPT
                self.last_recovery_attempt = datetime.now()
            else:
                # Still in fallback period, don't try neural network
                return None
        
        # Check if in permanent fallback
        if self.status == FallbackStatus.PERMANENT_FALLBACK:
            # Don't attempt inference, need manual intervention
            return None
        
        # Try neural network inference
        try:
            result = inference_func(*args, **kwargs)
            
            # Success!
            if self.status == FallbackStatus.RECOVERY_ATTEMPT:
                # Recovery successful
                self._handle_recovery_success()
            
            return result
        
        except Exception as e:
            # Inference failed
            self._handle_inference_failure(e)
            return None
    
    def _handle_inference_failure(self, exception: Exception):
        """
        Handle neural network inference failure.
        
        Requirements: 26.1, 26.2, 26.3, 26.5
        
        Args:
            exception: The exception that occurred
        """
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()
        
        # Log error with details (Requirement 26.2)
        error_msg = f"Neural network inference failed: {exception}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(exception).__name__}")
        logger.error(f"Consecutive failures: {self.consecutive_failures}")
        
        # Record event
        event = FallbackEvent(
            timestamp=datetime.now(),
            event_type='fallback' if self.status == FallbackStatus.NORMAL else 'recovery_failure',
            error_message=str(exception),
            exception_type=type(exception).__name__,
            consecutive_failures=self.consecutive_failures
        )
        self._add_event(event)
        
        # Determine new status
        if self.consecutive_failures >= self.max_consecutive_failures:
            # Requirement 26.5: After 3 failures, permanent fallback
            self.status = FallbackStatus.PERMANENT_FALLBACK
            logger.error(
                f"⚠ PERMANENT FALLBACK: {self.consecutive_failures} consecutive failures. "
                f"Manual intervention required."
            )
        else:
            # Requirement 26.3: Switch to rule-based mode
            if self.status != FallbackStatus.RECOVERY_ATTEMPT:
                self.fallback_count += 1
            
            self.status = FallbackStatus.FALLBACK_ACTIVE
            logger.warning(
                f"Switched to rule-based fallback mode. "
                f"Will attempt recovery after {self.recovery_delay_seconds}s"
            )
            
            if self.status == FallbackStatus.RECOVERY_ATTEMPT:
                self.recovery_failure_count += 1
    
    def _handle_recovery_success(self):
        """
        Handle successful recovery of neural network.
        
        Requirements: 26.4
        """
        logger.info("✓ Neural network recovery successful!")
        
        # Reset failure counter
        self.consecutive_failures = 0
        self.status = FallbackStatus.NORMAL
        self.recovery_success_count += 1
        
        # Record event
        event = FallbackEvent(
            timestamp=datetime.now(),
            event_type='recovery_success',
            error_message='Neural network recovered successfully',
            consecutive_failures=0
        )
        self._add_event(event)
    
    def _should_attempt_recovery(self) -> bool:
        """
        Check if enough time has passed to attempt recovery.
        
        Requirement 26.4: Attempt recovery after 60 seconds
        
        Returns:
            True if should attempt recovery
        """
        if self.last_failure_time is None:
            return False
        
        time_since_failure = datetime.now() - self.last_failure_time
        recovery_delay = timedelta(seconds=self.recovery_delay_seconds)
        
        return time_since_failure >= recovery_delay
    
    def _add_event(self, event: FallbackEvent):
        """Add event to history with size limit."""
        self.event_history.append(event)
        
        # Maintain max size
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
    
    def reset_to_normal(self):
        """
        Manually reset to normal status.
        
        Use this after fixing neural network issues in permanent fallback.
        
        Requirements: 26.5 (manual intervention for permanent fallback)
        """
        logger.info("Manually resetting fallback handler to NORMAL status")
        
        self.status = FallbackStatus.NORMAL
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.last_recovery_attempt = None
        
        event = FallbackEvent(
            timestamp=datetime.now(),
            event_type='manual_reset',
            error_message='Manually reset to normal status',
            consecutive_failures=0
        )
        self._add_event(event)
    
    def get_status(self) -> Dict:
        """
        Get fallback status for monitoring API.
        
        Requirements: 26.7 (expose fallback status via monitoring API)
        
        Returns:
            Dictionary with current status and statistics
        
        Example:
            >>> handler.get_status()
            {
                'status': 'normal',
                'consecutive_failures': 0,
                'total_failures': 5,
                'fallback_count': 3,
                'recovery_success_count': 2,
                'recovery_failure_count': 1,
                'last_failure_time': '2024-01-15T10:30:45',
                'time_since_failure_seconds': 125.3,
                'next_recovery_attempt_in_seconds': 0
            }
        """
        status = {
            'status': self.status.value,
            'consecutive_failures': self.consecutive_failures,
            'total_failures': self.total_failures,
            'fallback_count': self.fallback_count,
            'recovery_success_count': self.recovery_success_count,
            'recovery_failure_count': self.recovery_failure_count,
            'max_consecutive_failures': self.max_consecutive_failures,
            'recovery_delay_seconds': self.recovery_delay_seconds
        }
        
        if self.last_failure_time:
            status['last_failure_time'] = self.last_failure_time.isoformat()
            
            time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
            status['time_since_failure_seconds'] = time_since_failure
            
            # Calculate time until next recovery attempt
            if self.status == FallbackStatus.FALLBACK_ACTIVE:
                time_until_recovery = max(0, self.recovery_delay_seconds - time_since_failure)
                status['next_recovery_attempt_in_seconds'] = time_until_recovery
        
        if self.last_recovery_attempt:
            status['last_recovery_attempt'] = self.last_recovery_attempt.isoformat()
        
        # Add recent events
        status['recent_events'] = [
            {
                'timestamp': event.timestamp.isoformat(),
                'type': event.event_type,
                'message': event.error_message,
                'exception_type': event.exception_type,
                'consecutive_failures': event.consecutive_failures
            }
            for event in self.event_history[-10:]  # Last 10 events
        ]
        
        return status
    
    def get_statistics(self) -> Dict:
        """Get fallback handler statistics."""
        return {
            'status': self.status.value,
            'consecutive_failures': self.consecutive_failures,
            'total_failures': self.total_failures,
            'fallback_count': self.fallback_count,
            'recovery_success_count': self.recovery_success_count,
            'recovery_failure_count': self.recovery_failure_count,
            'event_count': len(self.event_history)
        }
    
    def reset_statistics(self):
        """
        Reset statistics counters (but not current status).
        
        Note: This does NOT reset consecutive_failures or status.
        Use reset_to_normal() to manually reset status.
        """
        self.total_failures = 0
        self.fallback_count = 0
        self.recovery_success_count = 0
        self.recovery_failure_count = 0
    
    def is_neural_available(self) -> bool:
        """
        Check if neural network is currently available for inference.
        
        Returns:
            True if neural network should be used, False if in fallback
        """
        return self.status in [FallbackStatus.NORMAL, FallbackStatus.RECOVERY_ATTEMPT]
    
    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"FallbackHandler(status={self.status.value}, "
            f"consecutive_failures={self.consecutive_failures}, "
            f"total_failures={self.total_failures})"
        )


# ==============================================================================
# Utility Functions
# ==============================================================================

def create_monitoring_endpoint(fallback_handler: FallbackHandler) -> Dict:
    """
    Create monitoring endpoint response for health checks.
    
    This is a helper function for exposing fallback status via monitoring API.
    
    Requirements: 26.7
    
    Args:
        fallback_handler: FallbackHandler instance
    
    Returns:
        Dictionary formatted for health check API
    
    Example:
        >>> handler = FallbackHandler()
        >>> response = create_monitoring_endpoint(handler)
        >>> response['healthy']
        True
        >>> response['fallback_status']
        'normal'
    """
    status = fallback_handler.get_status()
    
    # Determine overall health
    healthy = status['status'] in ['normal', 'fallback_active']
    
    return {
        'healthy': healthy,
        'fallback_status': status['status'],
        'neural_network_available': fallback_handler.is_neural_available(),
        'consecutive_failures': status['consecutive_failures'],
        'requires_manual_intervention': status['status'] == 'permanent_fallback',
        'details': status
    }
