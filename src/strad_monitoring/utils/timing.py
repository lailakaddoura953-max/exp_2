"""
Timing Utilities for Strad Monitoring System

Provides functions for timestamp calculations, cooldown checks, and
time formatting for consistent time handling across the system.
"""

from datetime import datetime, timedelta
from typing import Union


def calculate_elapsed_time(
    start_time: Union[datetime, str],
    end_time: Union[datetime, str]
) -> float:
    """
    Calculate elapsed time between two timestamps in seconds.
    
    Args:
        start_time: Start timestamp (datetime object or ISO format string)
        end_time: End timestamp (datetime object or ISO format string)
    
    Returns:
        Elapsed time in seconds (float with second precision)
    
    Example:
        >>> start = datetime(2024, 1, 15, 10, 0, 0)
        >>> end = datetime(2024, 1, 15, 11, 30, 45)
        >>> elapsed = calculate_elapsed_time(start, end)
        >>> print(elapsed)
        5445.0
    """
    # Convert strings to datetime if needed
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)
    
    # Calculate difference in seconds
    delta = end_time - start_time
    return delta.total_seconds()


def is_in_cooldown(
    last_check_timestamp: Union[datetime, str],
    cooldown_hours: int = 1
) -> bool:
    """
    Check if a strad is in cooldown period.
    
    A strad is in cooldown if the elapsed time since last check is less
    than the cooldown period.
    
    Args:
        last_check_timestamp: Timestamp of last check
        cooldown_hours: Cooldown period in hours (default: 1)
    
    Returns:
        True if in cooldown period, False if eligible for re-checking
    
    Example:
        >>> last_check = datetime.now() - timedelta(minutes=30)
        >>> is_in_cooldown(last_check)
        True
        >>> last_check = datetime.now() - timedelta(hours=2)
        >>> is_in_cooldown(last_check)
        False
    """
    # Convert string to datetime if needed
    if isinstance(last_check_timestamp, str):
        last_check_timestamp = datetime.fromisoformat(last_check_timestamp)
    
    current_time = datetime.now()
    elapsed = calculate_elapsed_time(last_check_timestamp, current_time)
    
    cooldown_seconds = cooldown_hours * 3600
    return elapsed < cooldown_seconds


def format_timestamp(timestamp: Union[datetime, None] = None) -> str:
    """
    Format timestamp for consistent display and logging.
    
    Uses ISO 8601 format: YYYY-MM-DD HH:MM:SS
    
    Args:
        timestamp: Timestamp to format (default: current time)
    
    Returns:
        Formatted timestamp string
    
    Example:
        >>> format_timestamp(datetime(2024, 1, 15, 10, 30, 45))
        '2024-01-15 10:30:45'
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")
