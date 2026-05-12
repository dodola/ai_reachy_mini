"""Logging infrastructure for F1 Commentary Robot.

This module provides centralized logging configuration with rotating file handlers,
ISO 8601 timestamps, and structured logging for all system components.

Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class ISO8601Formatter(logging.Formatter):
    """Custom formatter that uses ISO 8601 timestamps.
    
    Validates: Requirement 14.3
    """
    
    def formatTime(self, record, datefmt=None):
        """Format timestamp as ISO 8601."""
        dt = datetime.fromtimestamp(record.created)
        return dt.isoformat()
    
    def format(self, record):
        """Format log record with ISO 8601 timestamp."""
        # Add ISO 8601 timestamp
        record.isotime = self.formatTime(record)
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/f1_commentary.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """Setup logging infrastructure with rotating file handler.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup log files to keep (default: 5)
        
    Validates: Requirements 14.1, 14.2, 14.6
    """
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create formatters with ISO 8601 timestamps
    detailed_format = '%(isotime)s - %(name)s - %(levelname)s - %(message)s'
    console_format = '%(isotime)s - %(levelname)s - %(message)s'
    
    detailed_formatter = ISO8601Formatter(detailed_format)
    console_formatter = ISO8601Formatter(console_format)
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Rotating file handler (Requirement 14.6)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Log initial message
    root_logger.info("Logging system initialized")
    root_logger.info(f"Log level: {log_level}")
    root_logger.info(f"Log file: {log_file}")
    root_logger.info(f"Max log file size: {max_bytes / (1024 * 1024):.1f}MB")
    root_logger.info(f"Backup count: {backup_count}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class APITimingLogger:
    """Context manager for logging API request/response times.
    
    Validates: Requirement 14.4
    """
    
    def __init__(self, logger: logging.Logger, api_name: str, operation: str):
        """Initialize API timing logger.
        
        Args:
            logger: Logger instance to use
            api_name: Name of the API (e.g., "OpenF1", "ElevenLabs")
            operation: Operation being performed (e.g., "fetch_positions", "text_to_speech")
        """
        self.logger = logger
        self.api_name = api_name
        self.operation = operation
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = datetime.now().timestamp()
        self.logger.debug(f"{self.api_name} API call started: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log duration."""
        if self.start_time is not None:
            duration = datetime.now().timestamp() - self.start_time
            if exc_type is None:
                self.logger.info(
                    f"{self.api_name} API call completed: {self.operation} "
                    f"(duration: {duration:.3f}s)"
                )
            else:
                self.logger.error(
                    f"{self.api_name} API call failed: {self.operation} "
                    f"(duration: {duration:.3f}s, error: {exc_val})"
                )
        return False  # Don't suppress exceptions


class EventLogger:
    """Helper class for logging significant system events.
    
    Validates: Requirement 14.5
    """
    
    def __init__(self, logger: logging.Logger):
        """Initialize event logger.
        
        Args:
            logger: Logger instance to use
        """
        self.logger = logger
    
    def log_event_detected(self, event_type: str, event_data: dict) -> None:
        """Log event detection.
        
        Args:
            event_type: Type of event detected
            event_data: Event data dictionary
        """
        self.logger.info(f"Event detected: {event_type} - {event_data}")
    
    def log_commentary_generated(self, event_type: str, commentary_text: str, duration: float) -> None:
        """Log commentary generation.
        
        Args:
            event_type: Type of event
            commentary_text: Generated commentary
            duration: Time taken to generate (seconds)
        """
        self.logger.info(
            f"Commentary generated for {event_type} "
            f"(duration: {duration:.3f}s): {commentary_text[:100]}..."
        )
    
    def log_audio_playback(self, audio_duration: float) -> None:
        """Log audio playback start.
        
        Args:
            audio_duration: Duration of audio clip (seconds)
        """
        self.logger.info(f"Audio playback started (duration: {audio_duration:.3f}s)")
    
    def log_movement_executed(self, gesture: str, duration: float) -> None:
        """Log robot movement execution.
        
        Args:
            gesture: Type of gesture executed
            duration: Duration of movement (seconds)
        """
        self.logger.info(f"Movement executed: {gesture} (duration: {duration:.3f}s)")
    
    def log_qa_interaction(self, question: str, response: str, duration: float) -> None:
        """Log Q&A interaction.
        
        Args:
            question: User question
            response: System response
            duration: Time taken to respond (seconds)
        """
        self.logger.info(
            f"Q&A interaction (duration: {duration:.3f}s) - "
            f"Q: {question[:50]}... A: {response[:50]}..."
        )
