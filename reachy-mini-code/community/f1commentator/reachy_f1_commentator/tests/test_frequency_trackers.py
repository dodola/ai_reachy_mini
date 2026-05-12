"""
Unit tests for frequency trackers.

Tests the frequency tracking functionality for historical, weather,
championship, and tire strategy references.
"""

import pytest

from reachy_f1_commentator.src.frequency_trackers import (
    ChampionshipReferenceTracker,
    FrequencyTrackerManager,
    HistoricalReferenceTracker,
    TireStrategyReferenceTracker,
    WeatherReferenceTracker,
)


class TestHistoricalReferenceTracker:
    """Test historical reference tracker (1 per 3 pieces)."""
    
    def test_initialization(self):
        """Test tracker initializes with correct window size."""
        tracker = HistoricalReferenceTracker()
        assert tracker.window_size == 3
        assert tracker.max_per_window == 1
        assert tracker.total_pieces == 0
        assert tracker.total_references == 0
    
    def test_should_include_empty_window(self):
        """Test should_include returns True when window is empty."""
        tracker = HistoricalReferenceTracker()
        assert tracker.should_include() is True
    
    def test_should_include_after_one_reference(self):
        """Test should_include returns False after 1 reference in window."""
        tracker = HistoricalReferenceTracker()
        
        # Add one reference
        tracker.record(True)
        
        # Should not include another
        assert tracker.should_include() is False
    
    def test_should_include_after_window_slides(self):
        """Test should_include returns True after window slides past reference."""
        tracker = HistoricalReferenceTracker()
        
        # Add one reference
        tracker.record(True)
        assert tracker.should_include() is False
        
        # Add two non-references (window slides)
        tracker.record(False)
        tracker.record(False)
        
        # Window now has [True, False, False], still has 1 reference
        assert tracker.should_include() is False
        
        # Add one more non-reference (window slides, reference drops out)
        tracker.record(False)
        
        # Window now has [False, False, False], no references
        assert tracker.should_include() is True
    
    def test_get_current_count(self):
        """Test get_current_count returns correct count."""
        tracker = HistoricalReferenceTracker()
        
        tracker.record(True)
        assert tracker.get_current_count() == 1
        
        tracker.record(False)
        assert tracker.get_current_count() == 1
        
        tracker.record(True)
        assert tracker.get_current_count() == 2
    
    def test_get_current_rate(self):
        """Test get_current_rate returns correct rate."""
        tracker = HistoricalReferenceTracker()
        
        tracker.record(True)
        assert tracker.get_current_rate() == 1.0  # 1/1
        
        tracker.record(False)
        assert tracker.get_current_rate() == 0.5  # 1/2
        
        tracker.record(False)
        assert tracker.get_current_rate() == pytest.approx(0.333, rel=0.01)  # 1/3
    
    def test_get_overall_rate(self):
        """Test get_overall_rate tracks all-time rate."""
        tracker = HistoricalReferenceTracker()
        
        # Add 1 reference, 2 non-references
        tracker.record(True)
        tracker.record(False)
        tracker.record(False)
        
        assert tracker.get_overall_rate() == pytest.approx(0.333, rel=0.01)  # 1/3
        
        # Add 1 more non-reference (window slides, but overall rate includes all)
        tracker.record(False)
        
        assert tracker.get_overall_rate() == 0.25  # 1/4
    
    def test_reset(self):
        """Test reset clears all state."""
        tracker = HistoricalReferenceTracker()
        
        tracker.record(True)
        tracker.record(False)
        
        tracker.reset()
        
        assert tracker.total_pieces == 0
        assert tracker.total_references == 0
        assert len(tracker.window) == 0
        assert tracker.should_include() is True


class TestWeatherReferenceTracker:
    """Test weather reference tracker (1 per 5 pieces)."""
    
    def test_initialization(self):
        """Test tracker initializes with correct window size."""
        tracker = WeatherReferenceTracker()
        assert tracker.window_size == 5
        assert tracker.max_per_window == 1
    
    def test_should_include_empty_window(self):
        """Test should_include returns True when window is empty."""
        tracker = WeatherReferenceTracker()
        assert tracker.should_include() is True
    
    def test_should_include_after_one_reference(self):
        """Test should_include returns False after 1 reference in window."""
        tracker = WeatherReferenceTracker()
        
        tracker.record(True)
        assert tracker.should_include() is False
    
    def test_should_include_after_window_slides(self):
        """Test should_include returns True after window slides past reference."""
        tracker = WeatherReferenceTracker()
        
        # Add one reference
        tracker.record(True)
        
        # Add four non-references (window is full but still has reference)
        for _ in range(4):
            tracker.record(False)
        
        # Window has [True, False, False, False, False], still has 1 reference
        assert tracker.should_include() is False
        
        # Add one more non-reference (reference drops out)
        tracker.record(False)
        
        # Window has [False, False, False, False, False], no references
        assert tracker.should_include() is True
    
    def test_frequency_limit_enforced(self):
        """Test that frequency limit is enforced over multiple cycles."""
        tracker = WeatherReferenceTracker()
        
        # First cycle: add reference, then 4 non-references
        tracker.record(True)
        for _ in range(4):
            tracker.record(False)
        
        # Should not allow another reference yet
        assert tracker.should_include() is False
        
        # Add one more non-reference (reference drops out)
        tracker.record(False)
        
        # Now should allow reference
        assert tracker.should_include() is True


class TestChampionshipReferenceTracker:
    """Test championship reference tracker (20% = 2 per 10 pieces)."""
    
    def test_initialization(self):
        """Test tracker initializes with correct window size."""
        tracker = ChampionshipReferenceTracker()
        assert tracker.window_size == 10
        assert tracker.max_per_window == 2
        assert tracker.target_rate == 0.2
    
    def test_should_include_empty_window(self):
        """Test should_include returns True when window is empty."""
        tracker = ChampionshipReferenceTracker()
        assert tracker.should_include() is True
    
    def test_should_include_after_two_references(self):
        """Test should_include returns False after 2 references in window."""
        tracker = ChampionshipReferenceTracker()
        
        tracker.record(True)
        assert tracker.should_include() is True  # Still room for 1 more
        
        tracker.record(True)
        assert tracker.should_include() is False  # Limit reached
    
    def test_should_include_after_window_slides(self):
        """Test should_include returns True after window slides past references."""
        tracker = ChampionshipReferenceTracker()
        
        # Add two references
        tracker.record(True)
        tracker.record(True)
        assert tracker.should_include() is False
        
        # Add eight non-references (window is full)
        for _ in range(8):
            tracker.record(False)
        
        # Window has [True, True, False, False, False, False, False, False, False, False]
        # Still has 2 references
        assert tracker.should_include() is False
        
        # Add one more non-reference (one reference drops out)
        tracker.record(False)
        
        # Window has [True, False, False, False, False, False, False, False, False, False]
        # Now has 1 reference
        assert tracker.should_include() is True
    
    def test_target_rate_achieved(self):
        """Test that target rate of 20% is achieved over time."""
        tracker = ChampionshipReferenceTracker()
        
        # Simulate 50 pieces, including when allowed
        included_count = 0
        for i in range(50):
            if tracker.should_include():
                tracker.record(True)
                included_count += 1
            else:
                tracker.record(False)
        
        # Should have included roughly 10 times (20%)
        assert 8 <= included_count <= 12  # Allow some variance
        
        # Overall rate should be close to 20%
        overall_rate = tracker.get_overall_rate()
        assert 0.14 <= overall_rate <= 0.26  # Allow some variance


class TestTireStrategyReferenceTracker:
    """Test tire strategy reference tracker (target 30%)."""
    
    def test_initialization(self):
        """Test tracker initializes with correct parameters."""
        tracker = TireStrategyReferenceTracker()
        assert tracker.window_size == 10
        assert tracker.target_rate == 0.3
        assert tracker.min_rate == 0.2
        assert tracker.max_rate == 0.4
    
    def test_should_include_empty_window(self):
        """Test should_include returns True when window is empty."""
        tracker = TireStrategyReferenceTracker()
        assert tracker.should_include() is True
    
    def test_should_include_below_minimum_rate(self):
        """Test should_include returns True when rate is below minimum."""
        tracker = TireStrategyReferenceTracker()
        
        # Fill window with mostly non-references (rate = 10%)
        tracker.record(True)
        for _ in range(9):
            tracker.record(False)
        
        # Rate is 10%, below minimum of 20%
        assert tracker.get_current_rate() == 0.1
        assert tracker.should_include() is True
    
    def test_should_include_above_maximum_rate(self):
        """Test should_include returns False when rate is above maximum."""
        tracker = TireStrategyReferenceTracker()
        
        # Fill window with many references (rate = 50%)
        for i in range(10):
            tracker.record(i % 2 == 0)  # 5 True, 5 False
        
        # Rate is 50%, above maximum of 40%
        assert tracker.get_current_rate() == 0.5
        assert tracker.should_include() is False
    
    def test_should_include_in_target_range(self):
        """Test should_include returns True when rate is in target range."""
        tracker = TireStrategyReferenceTracker()
        
        # Fill window with references to achieve 30% rate
        for i in range(10):
            tracker.record(i < 3)  # 3 True, 7 False
        
        # Rate is 30%, in target range
        assert tracker.get_current_rate() == 0.3
        assert tracker.should_include() is True
    
    def test_target_rate_achieved(self):
        """Test that target rate of 30% is achieved over time."""
        tracker = TireStrategyReferenceTracker()
        
        # Simulate 50 pieces, including when should_include says yes
        for i in range(50):
            if tracker.should_include() and i % 3 == 0:  # Roughly every 3rd piece
                tracker.record(True)
            else:
                tracker.record(False)
        
        # Overall rate should be close to 30%
        overall_rate = tracker.get_overall_rate()
        assert 0.2 <= overall_rate <= 0.4  # Allow variance within min-max range


class TestFrequencyTrackerManager:
    """Test frequency tracker manager."""
    
    def test_initialization(self):
        """Test manager initializes all trackers."""
        manager = FrequencyTrackerManager()
        
        assert manager.historical is not None
        assert manager.weather is not None
        assert manager.championship is not None
        assert manager.tire_strategy is not None
    
    def test_should_include_methods(self):
        """Test all should_include methods work."""
        manager = FrequencyTrackerManager()
        
        # All should return True initially
        assert manager.should_include_historical() is True
        assert manager.should_include_weather() is True
        assert manager.should_include_championship() is True
        assert manager.should_include_tire_strategy() is True
    
    def test_record_methods(self):
        """Test all record methods work."""
        manager = FrequencyTrackerManager()
        
        # Record references
        manager.record_historical(True)
        manager.record_weather(True)
        manager.record_championship(True)
        manager.record_tire_strategy(True)
        
        # Verify counts
        assert manager.historical.get_current_count() == 1
        assert manager.weather.get_current_count() == 1
        assert manager.championship.get_current_count() == 1
        assert manager.tire_strategy.get_current_count() == 1
    
    def test_get_statistics(self):
        """Test get_statistics returns data for all trackers."""
        manager = FrequencyTrackerManager()
        
        # Record some data
        manager.record_historical(True)
        manager.record_weather(False)
        manager.record_championship(True)
        manager.record_tire_strategy(False)
        
        stats = manager.get_statistics()
        
        assert "historical" in stats
        assert "weather" in stats
        assert "championship" in stats
        assert "tire_strategy" in stats
        
        # Verify structure
        assert stats["historical"]["total_pieces"] == 1
        assert stats["weather"]["total_pieces"] == 1
        assert stats["championship"]["total_pieces"] == 1
        assert stats["tire_strategy"]["total_pieces"] == 1
    
    def test_reset_all(self):
        """Test reset_all clears all trackers."""
        manager = FrequencyTrackerManager()
        
        # Record some data
        manager.record_historical(True)
        manager.record_weather(True)
        manager.record_championship(True)
        manager.record_tire_strategy(True)
        
        # Reset
        manager.reset_all()
        
        # Verify all cleared
        assert manager.historical.total_pieces == 0
        assert manager.weather.total_pieces == 0
        assert manager.championship.total_pieces == 0
        assert manager.tire_strategy.total_pieces == 0
    
    def test_independent_tracking(self):
        """Test that trackers operate independently."""
        manager = FrequencyTrackerManager()
        
        # Fill historical tracker
        manager.record_historical(True)
        manager.record_historical(False)
        manager.record_historical(False)
        
        # Historical should not allow inclusion
        assert manager.should_include_historical() is False
        
        # But others should still allow
        assert manager.should_include_weather() is True
        assert manager.should_include_championship() is True
        assert manager.should_include_tire_strategy() is True


class TestFrequencyTrackerIntegration:
    """Integration tests for frequency trackers."""
    
    def test_historical_frequency_over_sequence(self):
        """Test historical tracker maintains 1 per 3 limit over long sequence."""
        tracker = HistoricalReferenceTracker()
        
        # Simulate 30 pieces, including when allowed
        included_count = 0
        for i in range(30):
            if tracker.should_include():
                tracker.record(True)
                included_count += 1
            else:
                tracker.record(False)
        
        # Should have included roughly 10 times (1 per 3)
        assert 8 <= included_count <= 12  # Allow some variance
        
        # Overall rate should be close to 33%
        overall_rate = tracker.get_overall_rate()
        assert 0.25 <= overall_rate <= 0.40
    
    def test_weather_frequency_over_sequence(self):
        """Test weather tracker maintains 1 per 5 limit over long sequence."""
        tracker = WeatherReferenceTracker()
        
        # Simulate 50 pieces, including when allowed
        included_count = 0
        for i in range(50):
            if tracker.should_include():
                tracker.record(True)
                included_count += 1
            else:
                tracker.record(False)
        
        # Should have included roughly 10 times (1 per 5)
        assert 8 <= included_count <= 12  # Allow some variance
        
        # Overall rate should be close to 20%
        overall_rate = tracker.get_overall_rate()
        assert 0.15 <= overall_rate <= 0.25
    
    def test_championship_frequency_over_sequence(self):
        """Test championship tracker maintains 20% limit over long sequence."""
        tracker = ChampionshipReferenceTracker()
        
        # Simulate 100 pieces, including when allowed
        included_count = 0
        for i in range(100):
            if tracker.should_include():
                tracker.record(True)
                included_count += 1
            else:
                tracker.record(False)
        
        # Should have included roughly 20 times (20%)
        assert 15 <= included_count <= 25  # Allow some variance
        
        # Overall rate should be close to 20%
        overall_rate = tracker.get_overall_rate()
        assert 0.15 <= overall_rate <= 0.25
    
    def test_tire_strategy_frequency_over_sequence(self):
        """Test tire strategy tracker maintains 30% target over long sequence."""
        tracker = TireStrategyReferenceTracker()
        
        # Simulate 100 pieces, including when allowed but not always
        included_count = 0
        for i in range(100):
            # Only include if tracker allows AND it's a reasonable opportunity
            if tracker.should_include() and i % 3 == 0:
                tracker.record(True)
                included_count += 1
            else:
                tracker.record(False)
        
        # Should have included roughly 30 times (30%)
        assert 20 <= included_count <= 40  # Allow variance within min-max range
        
        # Overall rate should be in target range
        overall_rate = tracker.get_overall_rate()
        assert 0.2 <= overall_rate <= 0.4
    
    def test_all_trackers_together(self):
        """Test all trackers working together in realistic scenario."""
        manager = FrequencyTrackerManager()
        
        # Simulate 100 commentary pieces
        for i in range(100):
            # Check and record for each type
            historical_included = manager.should_include_historical() and i % 4 == 0
            weather_included = manager.should_include_weather() and i % 6 == 0
            championship_included = manager.should_include_championship() and i % 5 == 0
            tire_included = manager.should_include_tire_strategy() and i % 3 == 0
            
            manager.record_historical(historical_included)
            manager.record_weather(weather_included)
            manager.record_championship(championship_included)
            manager.record_tire_strategy(tire_included)
        
        # Get statistics
        stats = manager.get_statistics()
        
        # Verify all trackers have reasonable rates
        assert 0.25 <= stats["historical"]["overall_rate"] <= 0.40  # ~33%
        assert 0.15 <= stats["weather"]["overall_rate"] <= 0.25  # ~20%
        assert 0.14 <= stats["championship"]["overall_rate"] <= 0.26  # ~20%
        assert 0.20 <= stats["tire_strategy"]["overall_rate"] <= 0.40  # ~30%
