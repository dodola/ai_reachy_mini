"""
Fault Isolation utilities for F1 Commentary Robot.

This module provides utilities to ensure module failures don't cascade
and that healthy modules continue operating when one fails.

Validates: Requirement 10.2
"""

import logging
import functools
from typing import Callable, Any, Optional


logger = logging.getLogger(__name__)


def isolate_module_failure(module_name: str, default_return: Any = None, 
                          continue_on_error: bool = True):
    """
    Decorator to isolate module failures and prevent cascading.
    
    Wraps a function to catch all exceptions, log them with full context,
    and optionally return a default value to allow continued operation.
    
    Args:
        module_name: Name of the module for logging
        default_return: Value to return if function fails
        continue_on_error: If True, return default_return on error; if False, re-raise
        
    Returns:
        Decorated function with fault isolation
        
    Example:
        @isolate_module_failure("CommentaryGenerator", default_return="")
        def generate_commentary(event):
            # ... implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"[{module_name}] Isolated failure in {func.__name__}: {e}",
                    exc_info=True
                )
                
                if continue_on_error:
                    logger.info(
                        f"[{module_name}] Continuing operation with default return value"
                    )
                    return default_return
                else:
                    raise
        
        return wrapper
    return decorator


def safe_module_operation(module_name: str, operation_name: str, 
                         operation: Callable, *args, **kwargs) -> tuple[bool, Any]:
    """
    Execute a module operation with fault isolation.
    
    Executes the given operation and catches any exceptions, logging them
    with full context. Returns a tuple indicating success/failure and the result.
    
    Args:
        module_name: Name of the module for logging
        operation_name: Description of the operation
        operation: Callable to execute
        *args: Positional arguments for operation
        **kwargs: Keyword arguments for operation
        
    Returns:
        Tuple of (success: bool, result: Any)
        If success is False, result will be None
        
    Example:
        success, audio = safe_module_operation(
            "SpeechSynthesizer",
            "TTS synthesis",
            elevenlabs_client.text_to_speech,
            text="Hello world"
        )
        if not success:
            # Handle failure, continue with degraded functionality
            pass
    """
    try:
        result = operation(*args, **kwargs)
        return True, result
    except Exception as e:
        logger.error(
            f"[{module_name}] Failed operation '{operation_name}': {e}",
            exc_info=True
        )
        return False, None


class ModuleHealthMonitor:
    """
    Monitors health of individual modules and tracks failure rates.
    
    Helps identify problematic modules and can trigger alerts or
    automatic recovery actions.
    """
    
    def __init__(self):
        """Initialize health monitor."""
        self._failure_counts = {}
        self._success_counts = {}
        self._total_operations = {}
    
    def record_success(self, module_name: str) -> None:
        """
        Record a successful operation for a module.
        
        Args:
            module_name: Name of the module
        """
        self._success_counts[module_name] = self._success_counts.get(module_name, 0) + 1
        self._total_operations[module_name] = self._total_operations.get(module_name, 0) + 1
    
    def record_failure(self, module_name: str) -> None:
        """
        Record a failed operation for a module.
        
        Args:
            module_name: Name of the module
        """
        self._failure_counts[module_name] = self._failure_counts.get(module_name, 0) + 1
        self._total_operations[module_name] = self._total_operations.get(module_name, 0) + 1
        
        # Log warning if failure rate is high
        failure_rate = self.get_failure_rate(module_name)
        if failure_rate > 0.5:  # More than 50% failures
            logger.warning(
                f"[HealthMonitor] Module {module_name} has high failure rate: "
                f"{failure_rate:.1%} ({self._failure_counts[module_name]} failures)"
            )
    
    def get_failure_rate(self, module_name: str) -> float:
        """
        Get failure rate for a module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Failure rate from 0.0 to 1.0
        """
        total = self._total_operations.get(module_name, 0)
        if total == 0:
            return 0.0
        
        failures = self._failure_counts.get(module_name, 0)
        return failures / total
    
    def get_health_status(self, module_name: str) -> str:
        """
        Get health status for a module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Health status: "healthy", "degraded", or "failing"
        """
        failure_rate = self.get_failure_rate(module_name)
        
        if failure_rate < 0.1:
            return "healthy"
        elif failure_rate < 0.5:
            return "degraded"
        else:
            return "failing"
    
    def get_all_health_status(self) -> dict[str, str]:
        """
        Get health status for all monitored modules.
        
        Returns:
            Dictionary mapping module names to health status
        """
        return {
            module: self.get_health_status(module)
            for module in self._total_operations.keys()
        }
    
    def reset_stats(self, module_name: Optional[str] = None) -> None:
        """
        Reset statistics for a module or all modules.
        
        Args:
            module_name: Module to reset, or None to reset all
        """
        if module_name:
            self._failure_counts.pop(module_name, None)
            self._success_counts.pop(module_name, None)
            self._total_operations.pop(module_name, None)
        else:
            self._failure_counts.clear()
            self._success_counts.clear()
            self._total_operations.clear()


# Global health monitor instance
health_monitor = ModuleHealthMonitor()
