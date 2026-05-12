"""
API Timeout Configuration for F1 Commentary Robot.

This module centralizes all API timeout settings to ensure consistent
timeout enforcement across the system.

Validates: Requirement 10.5
"""

import logging
from typing import Optional, Callable, Any
import functools
import signal


logger = logging.getLogger(__name__)


# ============================================================================
# Timeout Constants (per Requirement 10.5)
# ============================================================================

OPENF1_API_TIMEOUT = 5.0  # seconds
ELEVENLABS_API_TIMEOUT = 3.0  # seconds
AI_API_TIMEOUT = 1.5  # seconds


# ============================================================================
# Timeout Enforcement Utilities
# ============================================================================

class TimeoutError(Exception):
    """Exception raised when an operation times out."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Operation timed out")


def with_timeout(timeout_seconds: float):
    """
    Decorator to enforce timeout on a function using signals.
    
    Note: This only works on Unix-like systems and only in the main thread.
    For cross-platform and thread-safe timeouts, use the timeout parameter
    in the respective API client libraries.
    
    Args:
        timeout_seconds: Maximum execution time in seconds
        
    Returns:
        Decorated function with timeout enforcement
        
    Example:
        @with_timeout(5.0)
        def slow_operation():
            # ... implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Set up signal handler
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout_seconds))
            
            try:
                result = func(*args, **kwargs)
            finally:
                # Restore old handler and cancel alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            
            return result
        
        return wrapper
    return decorator


def enforce_timeout(operation: Callable, timeout_seconds: float, 
                   *args, **kwargs) -> tuple[bool, Any]:
    """
    Execute an operation with timeout enforcement.
    
    This is a functional approach to timeout enforcement that doesn't
    require decorators. Returns a tuple indicating success/failure.
    
    Args:
        operation: Callable to execute
        timeout_seconds: Maximum execution time in seconds
        *args: Positional arguments for operation
        **kwargs: Keyword arguments for operation
        
    Returns:
        Tuple of (success: bool, result: Any)
        If timeout occurs, returns (False, None)
        
    Example:
        success, result = enforce_timeout(
            api_client.fetch_data,
            5.0,
            endpoint="/data"
        )
        if not success:
            # Handle timeout
            pass
    """
    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(timeout_seconds))
    
    try:
        result = operation(*args, **kwargs)
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        return True, result
    except TimeoutError:
        logger.warning(f"Operation {operation.__name__} timed out after {timeout_seconds}s")
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        return False, None
    except Exception as e:
        logger.error(f"Operation {operation.__name__} failed: {e}", exc_info=True)
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        return False, None


# ============================================================================
# Timeout Monitoring
# ============================================================================

class TimeoutMonitor:
    """
    Monitors API call timeouts and tracks timeout statistics.
    
    Helps identify APIs that frequently timeout and may need
    configuration adjustments or alternative approaches.
    """
    
    def __init__(self):
        """Initialize timeout monitor."""
        self._timeout_counts = {}
        self._total_calls = {}
    
    def record_timeout(self, api_name: str) -> None:
        """
        Record a timeout for an API.
        
        Args:
            api_name: Name of the API that timed out
        """
        self._timeout_counts[api_name] = self._timeout_counts.get(api_name, 0) + 1
        self._total_calls[api_name] = self._total_calls.get(api_name, 0) + 1
        
        # Log warning if timeout rate is high
        timeout_rate = self.get_timeout_rate(api_name)
        if timeout_rate > 0.3:  # More than 30% timeouts
            logger.warning(
                f"[TimeoutMonitor] API {api_name} has high timeout rate: "
                f"{timeout_rate:.1%} ({self._timeout_counts[api_name]} timeouts)"
            )
    
    def record_success(self, api_name: str) -> None:
        """
        Record a successful API call (no timeout).
        
        Args:
            api_name: Name of the API
        """
        self._total_calls[api_name] = self._total_calls.get(api_name, 0) + 1
    
    def get_timeout_rate(self, api_name: str) -> float:
        """
        Get timeout rate for an API.
        
        Args:
            api_name: Name of the API
            
        Returns:
            Timeout rate from 0.0 to 1.0
        """
        total = self._total_calls.get(api_name, 0)
        if total == 0:
            return 0.0
        
        timeouts = self._timeout_counts.get(api_name, 0)
        return timeouts / total
    
    def get_timeout_stats(self) -> dict:
        """
        Get timeout statistics for all APIs.
        
        Returns:
            Dictionary mapping API names to timeout statistics
        """
        return {
            api: {
                "total_calls": self._total_calls.get(api, 0),
                "timeouts": self._timeout_counts.get(api, 0),
                "timeout_rate": self.get_timeout_rate(api)
            }
            for api in self._total_calls.keys()
        }
    
    def reset_stats(self, api_name: Optional[str] = None) -> None:
        """
        Reset statistics for an API or all APIs.
        
        Args:
            api_name: API to reset, or None to reset all
        """
        if api_name:
            self._timeout_counts.pop(api_name, None)
            self._total_calls.pop(api_name, None)
        else:
            self._timeout_counts.clear()
            self._total_calls.clear()


# Global timeout monitor instance
timeout_monitor = TimeoutMonitor()
