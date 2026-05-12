"""
Tests for error handling and resilience features.

Validates: Requirements 10.1, 10.2, 10.3, 10.5, 10.6, 11.3, 11.6
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from reachy_f1_commentator.src.fault_isolation import (
    isolate_module_failure,
    safe_module_operation,
    ModuleHealthMonitor,
    health_monitor
)
from reachy_f1_commentator.src.graceful_degradation import (
    DegradationManager,
    DegradationMode,
    degradation_manager
)
from reachy_f1_commentator.src.api_timeouts import (
    TimeoutMonitor,
    timeout_monitor,
    OPENF1_API_TIMEOUT,
    ELEVENLABS_API_TIMEOUT,
    AI_API_TIMEOUT
)
from reachy_f1_commentator.src.resource_monitor import ResourceMonitor


class TestFaultIsolation:
    """Test fault isolation utilities."""
    
    def test_isolate_module_failure_decorator_catches_exception(self):
        """Test that decorator catches exceptions and returns default value."""
        @isolate_module_failure("TestModule", default_return="default")
        def failing_function():
            raise ValueError("Test error")
        
        result = failing_function()
        assert result == "default"
    
    def test_isolate_module_failure_decorator_allows_success(self):
        """Test that decorator allows successful execution."""
        @isolate_module_failure("TestModule", default_return="default")
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_safe_module_operation_success(self):
        """Test safe_module_operation with successful operation."""
        def successful_op(x, y):
            return x + y
        
        success, result = safe_module_operation(
            "TestModule",
            "addition",
            successful_op,
            5, 3
        )
        
        assert success is True
        assert result == 8
    
    def test_safe_module_operation_failure(self):
        """Test safe_module_operation with failing operation."""
        def failing_op():
            raise ValueError("Test error")
        
        success, result = safe_module_operation(
            "TestModule",
            "failing operation",
            failing_op
        )
        
        assert success is False
        assert result is None
    
    def test_module_health_monitor_tracks_failures(self):
        """Test that health monitor tracks failure rates."""
        monitor = ModuleHealthMonitor()
        
        # Record some operations
        monitor.record_success("TestModule")
        monitor.record_success("TestModule")
        monitor.record_failure("TestModule")
        
        failure_rate = monitor.get_failure_rate("TestModule")
        assert failure_rate == pytest.approx(1/3)
        
        health_status = monitor.get_health_status("TestModule")
        assert health_status == "degraded"
    
    def test_module_health_monitor_reset_stats(self):
        """Test that health monitor can reset statistics."""
        monitor = ModuleHealthMonitor()
        
        monitor.record_failure("TestModule")
        monitor.record_failure("TestModule")
        
        monitor.reset_stats("TestModule")
        
        failure_rate = monitor.get_failure_rate("TestModule")
        assert failure_rate == 0.0


class TestGracefulDegradation:
    """Test graceful degradation functionality."""
    
    def test_degradation_manager_initialization(self):
        """Test that degradation manager initializes correctly."""
        manager = DegradationManager()
        
        assert manager.is_tts_available() is True
        assert manager.is_ai_enhancement_available() is True
        assert manager.is_motion_control_available() is True
        assert manager.get_current_mode() == DegradationMode.FULL_FUNCTIONALITY
    
    def test_degradation_manager_tts_failure_tracking(self):
        """Test that TTS failures are tracked and trigger degradation."""
        manager = DegradationManager()
        
        # Record failures below threshold
        manager.record_tts_failure()
        manager.record_tts_failure()
        assert manager.is_tts_available() is True
        
        # Record failure that exceeds threshold
        manager.record_tts_failure()
        assert manager.is_tts_available() is False
        assert manager.get_current_mode() == DegradationMode.TEXT_ONLY
    
    def test_degradation_manager_tts_recovery(self):
        """Test that TTS can recover after failures."""
        manager = DegradationManager()
        
        # Trigger degradation
        for _ in range(3):
            manager.record_tts_failure()
        
        assert manager.is_tts_available() is False
        
        # Record success to recover
        manager.record_tts_success()
        assert manager.is_tts_available() is True
        assert manager.get_current_mode() == DegradationMode.FULL_FUNCTIONALITY
    
    def test_degradation_manager_ai_failure_tracking(self):
        """Test that AI enhancement failures are tracked."""
        manager = DegradationManager()
        
        for _ in range(3):
            manager.record_ai_failure()
        
        assert manager.is_ai_enhancement_available() is False
        assert manager.get_current_mode() == DegradationMode.TEMPLATE_ONLY
    
    def test_degradation_manager_motion_failure_tracking(self):
        """Test that motion control failures are tracked."""
        manager = DegradationManager()
        
        for _ in range(3):
            manager.record_motion_failure()
        
        assert manager.is_motion_control_available() is False
        assert manager.get_current_mode() == DegradationMode.AUDIO_ONLY
    
    def test_degradation_manager_multiple_failures(self):
        """Test degradation with multiple component failures."""
        manager = DegradationManager()
        
        # Fail TTS and AI
        for _ in range(3):
            manager.record_tts_failure()
            manager.record_ai_failure()
        
        assert manager.get_current_mode() == DegradationMode.MINIMAL
    
    def test_degradation_manager_force_enable(self):
        """Test manual component enable."""
        manager = DegradationManager()
        
        # Disable TTS
        for _ in range(3):
            manager.record_tts_failure()
        
        # Force enable
        manager.force_enable_component("tts")
        assert manager.is_tts_available() is True
    
    def test_degradation_manager_status_report(self):
        """Test status report generation."""
        manager = DegradationManager()
        
        manager.record_tts_failure()
        manager.record_ai_failure()
        
        status = manager.get_status_report()
        
        assert "mode" in status
        assert "tts" in status
        assert "ai_enhancement" in status
        assert "motion_control" in status
        assert status["tts"]["consecutive_failures"] == 1
        assert status["ai_enhancement"]["consecutive_failures"] == 1


class TestAPITimeouts:
    """Test API timeout configuration and monitoring."""
    
    def test_timeout_constants(self):
        """Test that timeout constants are set correctly."""
        assert OPENF1_API_TIMEOUT == 5.0
        assert ELEVENLABS_API_TIMEOUT == 3.0
        assert AI_API_TIMEOUT == 1.5
    
    def test_timeout_monitor_tracks_timeouts(self):
        """Test that timeout monitor tracks timeout statistics."""
        monitor = TimeoutMonitor()
        
        monitor.record_timeout("TestAPI")
        monitor.record_success("TestAPI")
        monitor.record_timeout("TestAPI")
        
        timeout_rate = monitor.get_timeout_rate("TestAPI")
        assert timeout_rate == pytest.approx(2/3)
    
    def test_timeout_monitor_high_timeout_warning(self, caplog):
        """Test that high timeout rates trigger warnings."""
        monitor = TimeoutMonitor()
        
        # Generate high timeout rate
        for _ in range(6):
            monitor.record_timeout("TestAPI")
        for _ in range(4):
            monitor.record_success("TestAPI")
        
        # Should have logged warning
        assert any("high timeout rate" in record.message.lower() 
                  for record in caplog.records)
    
    def test_timeout_monitor_get_stats(self):
        """Test getting timeout statistics."""
        monitor = TimeoutMonitor()
        
        monitor.record_timeout("API1")
        monitor.record_success("API1")
        monitor.record_timeout("API2")
        
        stats = monitor.get_timeout_stats()
        
        assert "API1" in stats
        assert "API2" in stats
        assert stats["API1"]["total_calls"] == 2
        assert stats["API1"]["timeouts"] == 1
        assert stats["API2"]["total_calls"] == 1
        assert stats["API2"]["timeouts"] == 1
    
    def test_timeout_monitor_reset_stats(self):
        """Test resetting timeout statistics."""
        monitor = TimeoutMonitor()
        
        monitor.record_timeout("TestAPI")
        monitor.reset_stats("TestAPI")
        
        timeout_rate = monitor.get_timeout_rate("TestAPI")
        assert timeout_rate == 0.0


class TestResourceMonitor:
    """Test resource monitoring functionality."""
    
    def test_resource_monitor_initialization(self):
        """Test that resource monitor initializes correctly."""
        monitor = ResourceMonitor(
            check_interval=10.0,
            memory_warning_threshold=0.8,
            memory_limit_mb=2048.0,
            cpu_warning_threshold=0.7
        )
        
        assert monitor.check_interval == 10.0
        assert monitor.memory_warning_threshold == 0.8
        assert monitor.memory_limit_mb == 2048.0
        assert monitor.cpu_warning_threshold == 0.7
        assert monitor.is_running() is False
    
    def test_resource_monitor_get_current_usage(self):
        """Test getting current resource usage."""
        monitor = ResourceMonitor()
        
        usage = monitor.get_current_usage()
        
        assert "memory_mb" in usage
        assert "memory_percent" in usage
        assert "cpu_percent" in usage
        assert "peak_memory_mb" in usage
        assert "peak_cpu_percent" in usage
        assert "warning_count" in usage
    
    def test_resource_monitor_get_system_info(self):
        """Test getting system information."""
        monitor = ResourceMonitor()
        
        info = monitor.get_system_info()
        
        assert "total_memory_mb" in info
        assert "available_memory_mb" in info
        assert "system_memory_percent" in info
        assert "cpu_count" in info
        assert "system_cpu_percent" in info
    
    def test_resource_monitor_reset_statistics(self):
        """Test resetting resource statistics."""
        monitor = ResourceMonitor()
        
        # Get some usage to set peaks
        monitor.get_current_usage()
        
        # Reset
        monitor.reset_statistics()
        
        assert monitor._peak_memory_mb == 0.0
        assert monitor._peak_cpu_percent == 0.0
        assert monitor._warning_count == 0
    
    @pytest.mark.slow
    def test_resource_monitor_start_stop(self):
        """Test starting and stopping resource monitor."""
        monitor = ResourceMonitor(check_interval=1.0)
        
        monitor.start()
        assert monitor.is_running() is True
        
        time.sleep(0.5)  # Let it run briefly
        
        monitor.stop()
        assert monitor.is_running() is False


class TestIntegratedErrorHandling:
    """Test integrated error handling across modules."""
    
    def test_exception_logging_includes_module_name(self, caplog):
        """Test that exceptions are logged with module names."""
        @isolate_module_failure("TestModule", default_return=None)
        def failing_function():
            raise ValueError("Test error")
        
        failing_function()
        
        # Check that log includes module name
        assert any("[TestModule]" in record.message 
                  for record in caplog.records)
    
    def test_exception_logging_includes_stack_trace(self, caplog):
        """Test that exceptions are logged with stack traces."""
        @isolate_module_failure("TestModule", default_return=None)
        def failing_function():
            raise ValueError("Test error")
        
        failing_function()
        
        # Check that exc_info was logged (stack trace)
        assert any(record.exc_info is not None 
                  for record in caplog.records)
