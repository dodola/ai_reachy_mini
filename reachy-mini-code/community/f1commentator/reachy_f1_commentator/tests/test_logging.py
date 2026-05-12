"""Tests for logging infrastructure."""

import pytest
import tempfile
import os
from pathlib import Path
import logging
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from logging_config import (
    setup_logging,
    get_logger,
    ISO8601Formatter,
    APITimingLogger,
    EventLogger
)


class TestLoggingSetup:
    """Test logging setup and configuration."""
    
    def test_setup_logging_creates_log_file(self):
        """Test that setup_logging creates log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            setup_logging(log_level="INFO", log_file=log_file)
            
            # Log a message
            logger = get_logger("test")
            logger.info("Test message")
            
            # Check file exists
            assert os.path.exists(log_file)
    
    def test_iso8601_formatter(self):
        """Test that ISO8601Formatter produces correct format."""
        formatter = ISO8601Formatter('%(isotime)s - %(message)s')
        
        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Check that it contains ISO 8601 timestamp (contains 'T' separator)
        assert 'T' in formatted
        assert 'Test message' in formatted
    
    def test_get_logger(self):
        """Test getting logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"


class TestAPITimingLogger:
    """Test API timing logger."""
    
    def test_api_timing_logger_success(self):
        """Test API timing logger for successful call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            setup_logging(log_level="DEBUG", log_file=log_file)
            logger = get_logger("test")
            
            with APITimingLogger(logger, "TestAPI", "test_operation"):
                pass  # Simulate API call
            
            # Check log file contains timing info
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert "TestAPI API call started" in log_content
                assert "TestAPI API call completed" in log_content
                assert "duration:" in log_content
    
    def test_api_timing_logger_failure(self):
        """Test API timing logger for failed call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            setup_logging(log_level="DEBUG", log_file=log_file)
            logger = get_logger("test")
            
            try:
                with APITimingLogger(logger, "TestAPI", "test_operation"):
                    raise ValueError("Test error")
            except ValueError:
                pass
            
            # Check log file contains error info
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert "TestAPI API call failed" in log_content
                assert "Test error" in log_content


class TestEventLogger:
    """Test event logger."""
    
    def test_log_event_detected(self):
        """Test logging event detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            setup_logging(log_level="INFO", log_file=log_file)
            logger = get_logger("test")
            event_logger = EventLogger(logger)
            
            event_logger.log_event_detected("OVERTAKE", {"driver": "Hamilton"})
            
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert "Event detected: OVERTAKE" in log_content
                assert "Hamilton" in log_content
    
    def test_log_commentary_generated(self):
        """Test logging commentary generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            setup_logging(log_level="INFO", log_file=log_file)
            logger = get_logger("test")
            event_logger = EventLogger(logger)
            
            event_logger.log_commentary_generated(
                "OVERTAKE",
                "Hamilton overtakes Verstappen!",
                0.5
            )
            
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert "Commentary generated" in log_content
                assert "OVERTAKE" in log_content
                assert "duration: 0.500s" in log_content
