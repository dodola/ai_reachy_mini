"""
Frequency trackers for controlling reference rates in commentary.

This module provides frequency tracking classes that limit how often certain
types of references (historical, weather, championship, tire strategy) appear
in generated commentary to maintain variety and avoid repetition.

Each tracker maintains a sliding window of recent commentary pieces and
enforces frequency limits based on requirements.

Validates: Requirements 8.8, 11.7, 14.8, 13.8
"""

import logging
from collections import deque
from typing import Deque


logger = logging.getLogger(__name__)


class FrequencyTracker:
    """
    Base class for frequency tracking with sliding window.
    
    Maintains a sliding window of recent commentary pieces and tracks
    whether each piece included a specific type of reference.
    """
    
    def __init__(self, window_size: int, name: str = "FrequencyTracker"):
        """
        Initialize frequency tracker.
        
        Args:
            window_size: Size of sliding window to track
            name: Name of tracker for logging
        """
        self.window_size = window_size
        self.name = name
        self.window: Deque[bool] = deque(maxlen=window_size)
        self.total_pieces = 0
        self.total_references = 0
        
        logger.debug(f"Initialized {name} with window size {window_size}")
    
    def should_include(self) -> bool:
        """
        Check if a reference should be included based on frequency limit.
        
        This method should be overridden by subclasses to implement
        specific frequency logic.
        
        Returns:
            True if reference should be included, False otherwise
        """
        raise NotImplementedError("Subclasses must implement should_include()")
    
    def record(self, included: bool) -> None:
        """
        Record whether a reference was included in the latest commentary.
        
        Args:
            included: True if reference was included, False otherwise
        """
        self.window.append(included)
        self.total_pieces += 1
        if included:
            self.total_references += 1
        
        logger.debug(
            f"{self.name}: Recorded {'inclusion' if included else 'omission'} "
            f"(window: {sum(self.window)}/{len(self.window)})"
        )
    
    def get_current_count(self) -> int:
        """
        Get count of references in current window.
        
        Returns:
            Number of references in current window
        """
        return sum(self.window)
    
    def get_current_rate(self) -> float:
        """
        Get current reference rate in window.
        
        Returns:
            Rate as fraction (0.0 to 1.0), or 0.0 if window is empty
        """
        if len(self.window) == 0:
            return 0.0
        return sum(self.window) / len(self.window)
    
    def get_overall_rate(self) -> float:
        """
        Get overall reference rate across all pieces.
        
        Returns:
            Rate as fraction (0.0 to 1.0), or 0.0 if no pieces tracked
        """
        if self.total_pieces == 0:
            return 0.0
        return self.total_references / self.total_pieces
    
    def get_statistics(self) -> dict:
        """
        Get statistics for monitoring.
        
        Returns:
            Dictionary with tracker statistics
        """
        return {
            "name": self.name,
            "window_size": self.window_size,
            "current_window_count": self.get_current_count(),
            "current_window_rate": self.get_current_rate(),
            "total_pieces": self.total_pieces,
            "total_references": self.total_references,
            "overall_rate": self.get_overall_rate()
        }
    
    def reset(self) -> None:
        """Reset tracker to initial state."""
        self.window.clear()
        self.total_pieces = 0
        self.total_references = 0
        logger.debug(f"{self.name}: Reset")


class HistoricalReferenceTracker(FrequencyTracker):
    """
    Tracker for historical references (records, comparisons, "first time").
    
    Limits historical references to maximum 1 per 3 consecutive pieces.
    
    Validates: Requirements 8.8
    """
    
    def __init__(self):
        """Initialize historical reference tracker with window size 3."""
        super().__init__(window_size=3, name="HistoricalReferenceTracker")
        self.max_per_window = 1
    
    def should_include(self) -> bool:
        """
        Check if historical reference should be included.
        
        Returns True if fewer than 1 reference in last 3 pieces.
        
        Returns:
            True if reference should be included, False otherwise
            
        Validates: Requirements 8.8
        """
        current_count = self.get_current_count()
        should_include = current_count < self.max_per_window
        
        logger.debug(
            f"{self.name}: should_include={should_include} "
            f"(current: {current_count}/{self.max_per_window})"
        )
        
        return should_include


class WeatherReferenceTracker(FrequencyTracker):
    """
    Tracker for weather references (conditions, temperature, wind).
    
    Limits weather references to maximum 1 per 5 consecutive pieces.
    
    Validates: Requirements 11.7
    """
    
    def __init__(self):
        """Initialize weather reference tracker with window size 5."""
        super().__init__(window_size=5, name="WeatherReferenceTracker")
        self.max_per_window = 1
    
    def should_include(self) -> bool:
        """
        Check if weather reference should be included.
        
        Returns True if fewer than 1 reference in last 5 pieces.
        
        Returns:
            True if reference should be included, False otherwise
            
        Validates: Requirements 11.7
        """
        current_count = self.get_current_count()
        should_include = current_count < self.max_per_window
        
        logger.debug(
            f"{self.name}: should_include={should_include} "
            f"(current: {current_count}/{self.max_per_window})"
        )
        
        return should_include


class ChampionshipReferenceTracker(FrequencyTracker):
    """
    Tracker for championship references (standings, points, implications).
    
    Limits championship references to maximum 20% of pieces (2 per 10).
    
    Validates: Requirements 14.8
    """
    
    def __init__(self):
        """Initialize championship reference tracker with window size 10."""
        super().__init__(window_size=10, name="ChampionshipReferenceTracker")
        self.max_per_window = 2  # 20% of 10
        self.target_rate = 0.2
    
    def should_include(self) -> bool:
        """
        Check if championship reference should be included.
        
        Returns True if fewer than 2 references in last 10 pieces.
        
        Returns:
            True if reference should be included, False otherwise
            
        Validates: Requirements 14.8
        """
        current_count = self.get_current_count()
        should_include = current_count < self.max_per_window
        
        logger.debug(
            f"{self.name}: should_include={should_include} "
            f"(current: {current_count}/{self.max_per_window}, "
            f"rate: {self.get_current_rate():.1%})"
        )
        
        return should_include


class TireStrategyReferenceTracker(FrequencyTracker):
    """
    Tracker for tire strategy references (compound, age, degradation).
    
    Targets approximately 30% of pit stop and overtake pieces.
    Uses a more flexible approach than hard limits.
    
    Validates: Requirements 13.8
    """
    
    def __init__(self):
        """Initialize tire strategy reference tracker with window size 10."""
        super().__init__(window_size=10, name="TireStrategyReferenceTracker")
        self.target_rate = 0.3  # 30%
        self.min_rate = 0.2  # Allow 20-40% range
        self.max_rate = 0.4
    
    def should_include(self) -> bool:
        """
        Check if tire strategy reference should be included.
        
        Uses a probabilistic approach to target 30% inclusion rate:
        - If current rate < 20%, strongly encourage inclusion
        - If current rate > 40%, strongly discourage inclusion
        - If current rate is 20-40%, allow inclusion
        
        Returns:
            True if reference should be included, False otherwise
            
        Validates: Requirements 13.8
        """
        # If window not full yet, allow inclusion to build up to target
        if len(self.window) < self.window_size:
            current_rate = self.get_current_rate()
            should_include = current_rate < self.target_rate
            
            logger.debug(
                f"{self.name}: should_include={should_include} "
                f"(window filling: {len(self.window)}/{self.window_size}, "
                f"rate: {current_rate:.1%})"
            )
            
            return should_include
        
        # Window is full, use rate-based logic
        current_rate = self.get_current_rate()
        
        # If rate is below minimum, strongly encourage inclusion
        if current_rate < self.min_rate:
            should_include = True
        # If rate is above maximum, strongly discourage inclusion
        elif current_rate > self.max_rate:
            should_include = False
        # If rate is in target range, allow inclusion
        else:
            should_include = True
        
        logger.debug(
            f"{self.name}: should_include={should_include} "
            f"(rate: {current_rate:.1%}, target: {self.target_rate:.1%})"
        )
        
        return should_include


class FrequencyTrackerManager:
    """
    Manager for all frequency trackers.
    
    Provides a unified interface for checking and recording references
    across all tracker types.
    """
    
    def __init__(self):
        """Initialize all frequency trackers."""
        self.historical = HistoricalReferenceTracker()
        self.weather = WeatherReferenceTracker()
        self.championship = ChampionshipReferenceTracker()
        self.tire_strategy = TireStrategyReferenceTracker()
        
        logger.info("Frequency tracker manager initialized")
    
    def should_include_historical(self) -> bool:
        """
        Check if historical reference should be included.
        
        Returns:
            True if reference should be included, False otherwise
        """
        return self.historical.should_include()
    
    def should_include_weather(self) -> bool:
        """
        Check if weather reference should be included.
        
        Returns:
            True if reference should be included, False otherwise
        """
        return self.weather.should_include()
    
    def should_include_championship(self) -> bool:
        """
        Check if championship reference should be included.
        
        Returns:
            True if reference should be included, False otherwise
        """
        return self.championship.should_include()
    
    def should_include_tire_strategy(self) -> bool:
        """
        Check if tire strategy reference should be included.
        
        Returns:
            True if reference should be included, False otherwise
        """
        return self.tire_strategy.should_include()
    
    def record_historical(self, included: bool) -> None:
        """
        Record whether historical reference was included.
        
        Args:
            included: True if reference was included, False otherwise
        """
        self.historical.record(included)
    
    def record_weather(self, included: bool) -> None:
        """
        Record whether weather reference was included.
        
        Args:
            included: True if reference was included, False otherwise
        """
        self.weather.record(included)
    
    def record_championship(self, included: bool) -> None:
        """
        Record whether championship reference was included.
        
        Args:
            included: True if reference was included, False otherwise
        """
        self.championship.record(included)
    
    def record_tire_strategy(self, included: bool) -> None:
        """
        Record whether tire strategy reference was included.
        
        Args:
            included: True if reference was included, False otherwise
        """
        self.tire_strategy.record(included)
    
    def get_statistics(self) -> dict:
        """
        Get statistics for all trackers.
        
        Returns:
            Dictionary with statistics for all trackers
        """
        return {
            "historical": self.historical.get_statistics(),
            "weather": self.weather.get_statistics(),
            "championship": self.championship.get_statistics(),
            "tire_strategy": self.tire_strategy.get_statistics()
        }
    
    def reset_all(self) -> None:
        """Reset all trackers to initial state."""
        self.historical.reset()
        self.weather.reset()
        self.championship.reset()
        self.tire_strategy.reset()
        logger.info("All frequency trackers reset")
