"""
Retry Decorator with Exponential Backoff

Provides a decorator for automatic retry logic with exponential backoff
for handling transient failures in external system interactions.
"""

import functools
import logging
import time
from typing import Callable, Tuple, Type


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.
    
    Retries the decorated function up to max_attempts times with exponential
    backoff delays between attempts. Only retries on specified exception types.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        backoff_factor: Base delay factor for exponential backoff (default: 1.0)
            Delay sequence: backoff_factor * (2 ** attempt_number)
            Example with backoff_factor=1.0: 1s, 2s, 4s
        exceptions: Tuple of exception types to catch and retry (default: (Exception,))
    
    Returns:
        Decorated function with retry logic
    
    Example:
        @retry(max_attempts=3, backoff_factor=1.0, exceptions=(ConnectionError,))
        def connect_to_database():
            # Connection logic that might fail transiently
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        # Last attempt failed, re-raise the exception
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    # Calculate exponential backoff delay
                    delay = backoff_factor * (2 ** attempt)
                    
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    
                    time.sleep(delay)
            
            # Should never reach here, but for type safety
            return None
        
        return wrapper
    return decorator
