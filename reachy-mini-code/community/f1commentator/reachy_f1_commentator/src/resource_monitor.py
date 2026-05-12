"""
Resource Monitoring for F1 Commentary Robot.

This module monitors system resources (CPU, memory) and logs warnings
when usage exceeds configured thresholds.

Validates: Requirements 10.6, 11.3, 11.6
"""

import logging
import threading
import time
import psutil
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


class ResourceMonitor:
    """
    Monitors system resource usage (CPU and memory).
    
    Runs in a background thread and periodically checks resource usage,
    logging warnings when thresholds are exceeded.
    
    Validates: Requirements 10.6, 11.3, 11.6
    """
    
    def __init__(
        self,
        check_interval: float = 10.0,
        memory_warning_threshold: float = 0.8,
        memory_limit_mb: float = 2048.0,
        cpu_warning_threshold: float = 0.7
    ):
        """
        Initialize resource monitor.
        
        Args:
            check_interval: Interval between checks in seconds (default: 10s)
            memory_warning_threshold: Memory usage threshold for warnings (0.0-1.0, default: 0.8 = 80%)
            memory_limit_mb: Absolute memory limit in MB (default: 2048 MB = 2 GB)
            cpu_warning_threshold: CPU usage threshold for warnings (0.0-1.0, default: 0.7 = 70%)
        """
        self.check_interval = check_interval
        self.memory_warning_threshold = memory_warning_threshold
        self.memory_limit_mb = memory_limit_mb
        self.cpu_warning_threshold = cpu_warning_threshold
        
        # Monitoring state
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._process = psutil.Process()
        
        # Statistics
        self._peak_memory_mb = 0.0
        self._peak_cpu_percent = 0.0
        self._warning_count = 0
        self._last_warning_time = 0.0
        self._warning_cooldown = 60.0  # Don't spam warnings more than once per minute
        
        logger.info(
            f"ResourceMonitor initialized: check_interval={check_interval}s, "
            f"memory_threshold={memory_warning_threshold:.0%}, "
            f"memory_limit={memory_limit_mb}MB, "
            f"cpu_threshold={cpu_warning_threshold:.0%}"
        )
    
    def start(self) -> None:
        """
        Start resource monitoring in background thread.
        
        Validates: Requirements 10.6, 11.3, 11.6
        """
        if self._running:
            logger.warning("Resource monitor already running")
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ResourceMonitorThread"
        )
        self._monitor_thread.start()
        
        logger.info("Resource monitoring started")
    
    def stop(self) -> None:
        """Stop resource monitoring."""
        if not self._running:
            return
        
        logger.info("Stopping resource monitor...")
        self._running = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        
        logger.info("Resource monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """
        Main monitoring loop that runs in background thread.
        
        Validates: Requirements 10.6, 11.3, 11.6
        """
        logger.info("Resource monitoring loop started")
        
        while self._running:
            try:
                # Get current resource usage
                memory_info = self._process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)  # Convert bytes to MB
                memory_percent = self._process.memory_percent()
                
                # CPU usage (averaged over check_interval)
                cpu_percent = self._process.cpu_percent(interval=1.0) / 100.0
                
                # Update peak values
                if memory_mb > self._peak_memory_mb:
                    self._peak_memory_mb = memory_mb
                
                if cpu_percent > self._peak_cpu_percent:
                    self._peak_cpu_percent = cpu_percent
                
                # Log current usage (DEBUG level)
                logger.debug(
                    f"Resource usage: Memory={memory_mb:.1f}MB ({memory_percent:.1f}%), "
                    f"CPU={cpu_percent:.1%}"
                )
                
                # Check memory threshold (Requirement 10.6)
                if memory_percent / 100.0 >= self.memory_warning_threshold:
                    self._log_memory_warning(memory_mb, memory_percent)
                
                # Check absolute memory limit (Requirement 11.6)
                if memory_mb >= self.memory_limit_mb:
                    self._log_memory_limit_exceeded(memory_mb)
                
                # Check CPU threshold (Requirement 11.3)
                if cpu_percent >= self.cpu_warning_threshold:
                    self._log_cpu_warning(cpu_percent)
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"[ResourceMonitor] Error in monitoring loop: {e}", exc_info=True)
                time.sleep(self.check_interval)
        
        logger.info("Resource monitoring loop stopped")
    
    def _log_memory_warning(self, memory_mb: float, memory_percent: float) -> None:
        """
        Log memory usage warning.
        
        Args:
            memory_mb: Current memory usage in MB
            memory_percent: Current memory usage as percentage
            
        Validates: Requirement 10.6
        """
        current_time = time.time()
        
        # Apply cooldown to avoid spam
        if current_time - self._last_warning_time < self._warning_cooldown:
            return
        
        logger.warning(
            f"[ResourceMonitor] Memory usage exceeds {self.memory_warning_threshold:.0%} threshold: "
            f"{memory_mb:.1f}MB ({memory_percent:.1f}%)"
        )
        
        self._warning_count += 1
        self._last_warning_time = current_time
    
    def _log_memory_limit_exceeded(self, memory_mb: float) -> None:
        """
        Log memory limit exceeded.
        
        Args:
            memory_mb: Current memory usage in MB
            
        Validates: Requirement 11.6
        """
        current_time = time.time()
        
        # Apply cooldown to avoid spam
        if current_time - self._last_warning_time < self._warning_cooldown:
            return
        
        logger.error(
            f"[ResourceMonitor] Memory usage exceeds {self.memory_limit_mb}MB limit: "
            f"{memory_mb:.1f}MB"
        )
        
        self._warning_count += 1
        self._last_warning_time = current_time
    
    def _log_cpu_warning(self, cpu_percent: float) -> None:
        """
        Log CPU usage warning.
        
        Args:
            cpu_percent: Current CPU usage as decimal (0.0-1.0)
            
        Validates: Requirement 11.3
        """
        current_time = time.time()
        
        # Apply cooldown to avoid spam
        if current_time - self._last_warning_time < self._warning_cooldown:
            return
        
        logger.warning(
            f"[ResourceMonitor] CPU usage exceeds {self.cpu_warning_threshold:.0%} threshold: "
            f"{cpu_percent:.1%}"
        )
        
        self._warning_count += 1
        self._last_warning_time = current_time
    
    def get_current_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage statistics.
        
        Returns:
            Dictionary with current CPU and memory usage
        """
        try:
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            memory_percent = self._process.memory_percent()
            cpu_percent = self._process.cpu_percent(interval=0.1) / 100.0
            
            return {
                "memory_mb": memory_mb,
                "memory_percent": memory_percent,
                "cpu_percent": cpu_percent,
                "peak_memory_mb": self._peak_memory_mb,
                "peak_cpu_percent": self._peak_cpu_percent,
                "warning_count": self._warning_count
            }
        except Exception as e:
            logger.error(f"[ResourceMonitor] Error getting current usage: {e}", exc_info=True)
            return {}
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system-wide resource information.
        
        Returns:
            Dictionary with system CPU and memory info
        """
        try:
            virtual_memory = psutil.virtual_memory()
            
            return {
                "total_memory_mb": virtual_memory.total / (1024 * 1024),
                "available_memory_mb": virtual_memory.available / (1024 * 1024),
                "system_memory_percent": virtual_memory.percent,
                "cpu_count": psutil.cpu_count(),
                "system_cpu_percent": psutil.cpu_percent(interval=0.1)
            }
        except Exception as e:
            logger.error(f"[ResourceMonitor] Error getting system info: {e}", exc_info=True)
            return {}
    
    def reset_statistics(self) -> None:
        """Reset peak usage statistics and warning count."""
        self._peak_memory_mb = 0.0
        self._peak_cpu_percent = 0.0
        self._warning_count = 0
        logger.info("Resource monitor statistics reset")
    
    def is_running(self) -> bool:
        """Check if resource monitoring is running."""
        return self._running


# Global resource monitor instance
# Will be initialized by the main application
resource_monitor: Optional[ResourceMonitor] = None


def initialize_resource_monitor(
    check_interval: float = 10.0,
    memory_warning_threshold: float = 0.8,
    memory_limit_mb: float = 2048.0,
    cpu_warning_threshold: float = 0.7
) -> ResourceMonitor:
    """
    Initialize and start the global resource monitor.
    
    Args:
        check_interval: Interval between checks in seconds
        memory_warning_threshold: Memory usage threshold for warnings (0.0-1.0)
        memory_limit_mb: Absolute memory limit in MB
        cpu_warning_threshold: CPU usage threshold for warnings (0.0-1.0)
        
    Returns:
        Initialized ResourceMonitor instance
    """
    global resource_monitor
    
    resource_monitor = ResourceMonitor(
        check_interval=check_interval,
        memory_warning_threshold=memory_warning_threshold,
        memory_limit_mb=memory_limit_mb,
        cpu_warning_threshold=cpu_warning_threshold
    )
    
    resource_monitor.start()
    
    return resource_monitor


def get_resource_monitor() -> Optional[ResourceMonitor]:
    """
    Get the global resource monitor instance.
    
    Returns:
        ResourceMonitor instance or None if not initialized
    """
    return resource_monitor
