"""
Graceful Degradation utilities for F1 Commentary Robot.

This module provides utilities to enable graceful degradation when
components fail, allowing the system to continue operating with
reduced functionality.

Validates: Requirement 10.3
"""

import logging
from enum import Enum
from typing import Optional


logger = logging.getLogger(__name__)


class DegradationMode(Enum):
    """System degradation modes."""
    FULL_FUNCTIONALITY = "full"
    TEXT_ONLY = "text_only"  # TTS failed, commentary text only
    TEMPLATE_ONLY = "template_only"  # AI enhancement failed
    AUDIO_ONLY = "audio_only"  # Motion control failed
    MINIMAL = "minimal"  # Multiple failures, minimal functionality


class DegradationManager:
    """
    Manages system degradation modes and tracks component failures.
    
    Coordinates graceful degradation across modules when components fail,
    ensuring the system continues operating with reduced functionality.
    """
    
    def __init__(self):
        """Initialize degradation manager."""
        self._tts_available = True
        self._ai_enhancement_available = True
        self._motion_control_available = True
        self._current_mode = DegradationMode.FULL_FUNCTIONALITY
        
        # Failure tracking
        self._tts_consecutive_failures = 0
        self._ai_consecutive_failures = 0
        self._motion_consecutive_failures = 0
        
        # Thresholds for disabling components
        self._failure_threshold = 3  # Disable after 3 consecutive failures
    
    def record_tts_success(self) -> None:
        """Record successful TTS operation."""
        self._tts_consecutive_failures = 0
        if not self._tts_available:
            logger.info("[DegradationManager] TTS recovered, re-enabling")
            self._tts_available = True
            self._update_mode()
    
    def record_tts_failure(self) -> None:
        """Record TTS failure and potentially disable TTS."""
        self._tts_consecutive_failures += 1
        
        if self._tts_consecutive_failures >= self._failure_threshold:
            if self._tts_available:
                logger.warning(
                    f"[DegradationManager] TTS failed {self._tts_consecutive_failures} "
                    f"times, entering TEXT_ONLY mode"
                )
                self._tts_available = False
                self._update_mode()
    
    def record_ai_success(self) -> None:
        """Record successful AI enhancement operation."""
        self._ai_consecutive_failures = 0
        if not self._ai_enhancement_available:
            logger.info("[DegradationManager] AI enhancement recovered, re-enabling")
            self._ai_enhancement_available = True
            self._update_mode()
    
    def record_ai_failure(self) -> None:
        """Record AI enhancement failure and potentially disable AI."""
        self._ai_consecutive_failures += 1
        
        if self._ai_consecutive_failures >= self._failure_threshold:
            if self._ai_enhancement_available:
                logger.warning(
                    f"[DegradationManager] AI enhancement failed {self._ai_consecutive_failures} "
                    f"times, entering TEMPLATE_ONLY mode"
                )
                self._ai_enhancement_available = False
                self._update_mode()
    
    def record_motion_success(self) -> None:
        """Record successful motion control operation."""
        self._motion_consecutive_failures = 0
        if not self._motion_control_available:
            logger.info("[DegradationManager] Motion control recovered, re-enabling")
            self._motion_control_available = True
            self._update_mode()
    
    def record_motion_failure(self) -> None:
        """Record motion control failure and potentially disable motion."""
        self._motion_consecutive_failures += 1
        
        if self._motion_consecutive_failures >= self._failure_threshold:
            if self._motion_control_available:
                logger.warning(
                    f"[DegradationManager] Motion control failed {self._motion_consecutive_failures} "
                    f"times, entering AUDIO_ONLY mode"
                )
                self._motion_control_available = False
                self._update_mode()
    
    def is_tts_available(self) -> bool:
        """Check if TTS is available."""
        return self._tts_available
    
    def is_ai_enhancement_available(self) -> bool:
        """Check if AI enhancement is available."""
        return self._ai_enhancement_available
    
    def is_motion_control_available(self) -> bool:
        """Check if motion control is available."""
        return self._motion_control_available
    
    def get_current_mode(self) -> DegradationMode:
        """Get current degradation mode."""
        return self._current_mode
    
    def _update_mode(self) -> None:
        """Update current degradation mode based on component availability."""
        # Count unavailable components
        unavailable_count = sum([
            not self._tts_available,
            not self._ai_enhancement_available,
            not self._motion_control_available
        ])
        
        # Determine mode
        if unavailable_count == 0:
            self._current_mode = DegradationMode.FULL_FUNCTIONALITY
        elif unavailable_count >= 2:
            self._current_mode = DegradationMode.MINIMAL
        elif not self._tts_available:
            self._current_mode = DegradationMode.TEXT_ONLY
        elif not self._ai_enhancement_available:
            self._current_mode = DegradationMode.TEMPLATE_ONLY
        elif not self._motion_control_available:
            self._current_mode = DegradationMode.AUDIO_ONLY
        
        logger.info(f"[DegradationManager] Current mode: {self._current_mode.value}")
    
    def force_enable_component(self, component: str) -> None:
        """
        Force enable a component (for manual recovery).
        
        Args:
            component: Component name ("tts", "ai", "motion")
        """
        if component == "tts":
            self._tts_available = True
            self._tts_consecutive_failures = 0
        elif component == "ai":
            self._ai_enhancement_available = True
            self._ai_consecutive_failures = 0
        elif component == "motion":
            self._motion_control_available = True
            self._motion_consecutive_failures = 0
        
        self._update_mode()
        logger.info(f"[DegradationManager] Manually enabled {component}")
    
    def force_disable_component(self, component: str) -> None:
        """
        Force disable a component (for manual control).
        
        Args:
            component: Component name ("tts", "ai", "motion")
        """
        if component == "tts":
            self._tts_available = False
        elif component == "ai":
            self._ai_enhancement_available = False
        elif component == "motion":
            self._motion_control_available = False
        
        self._update_mode()
        logger.info(f"[DegradationManager] Manually disabled {component}")
    
    def get_status_report(self) -> dict:
        """
        Get status report of all components.
        
        Returns:
            Dictionary with component availability and failure counts
        """
        return {
            "mode": self._current_mode.value,
            "tts": {
                "available": self._tts_available,
                "consecutive_failures": self._tts_consecutive_failures
            },
            "ai_enhancement": {
                "available": self._ai_enhancement_available,
                "consecutive_failures": self._ai_consecutive_failures
            },
            "motion_control": {
                "available": self._motion_control_available,
                "consecutive_failures": self._motion_consecutive_failures
            }
        }


# Global degradation manager instance
degradation_manager = DegradationManager()
