"""
Unit tests for the EventPrioritizer class.

Tests the event filtering logic including threshold checking, pit-cycle suppression,
and highest significance event selection.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from reachy_f1_commentator.src.event_prioritizer import EventPrioritizer, SignificanceCalculator
from reachy_f1_commentator.src.enhanced_models import ContextData, SignificanceScore
from reachy_f1_commentator.src.models import EventType, RaceEvent, RaceState


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    config.min_significance_threshold = 50
    return config


@pytest.fixture
def mock_race_state_tracker():
    """Create a mock race state tracker."""
    return Mock()


@pytest.fixture
def prioritizer(mock_config, mock_race_state_tracker):
    """Create an EventPrioritizer instance."""
    return EventPrioritizer(mock_config, mock_race_state_tracker)


@pytest.fixture
def base_context():
    """Create a base ContextData with minimal information."""
    return ContextData(
        event=RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={'driver': '44'}
        ),
        race_state=RaceState(current_lap=10)
    )


class TestShouldCommentate:
    """Test the should_commentate threshold checking."""
    
    def test_above_threshold_should_commentate(self, prioritizer):
        """Events above threshold should receive commentary."""
        significance = SignificanceScore(
            base_score=60,
            context_bonus=0,
            total_score=60,
            reasons=["Base score: 60"]
        )
        
        assert prioritizer.should_commentate(significance) is True
    
    def test_at_threshold_should_commentate(self, prioritizer):
        """Events at threshold should receive commentary."""
        significance = SignificanceScore(
            base_score=50,
            context_bonus=0,
            total_score=50,
            reasons=["Base score: 50"]
        )
        
        assert prioritizer.should_commentate(significance) is True
    
    def test_below_threshold_should_not_commentate(self, prioritizer):
        """Events below threshold should not receive commentary."""
        significance = SignificanceScore(
            base_score=40,
            context_bonus=0,
            total_score=40,
            reasons=["Base score: 40"]
        )
        
        assert prioritizer.should_commentate(significance) is False
    
    def test_zero_score_should_not_commentate(self, prioritizer):
        """Events with zero score should not receive commentary."""
        significance = SignificanceScore(
            base_score=0,
            context_bonus=0,
            total_score=0,
            reasons=["Base score: 0"]
        )
        
        assert prioritizer.should_commentate(significance) is False
    
    def test_custom_threshold(self, mock_race_state_tracker):
        """Custom threshold should be respected."""
        config = Mock()
        config.min_significance_threshold = 70
        prioritizer = EventPrioritizer(config, mock_race_state_tracker)
        
        significance = SignificanceScore(
            base_score=60,
            context_bonus=0,
            total_score=60,
            reasons=["Base score: 60"]
        )
        
        assert prioritizer.should_commentate(significance) is False
    
    def test_default_threshold_when_not_configured(self, mock_race_state_tracker):
        """Should use default threshold of 50 when not configured."""
        config = Mock(spec=[])  # Config without min_significance_threshold
        prioritizer = EventPrioritizer(config, mock_race_state_tracker)
        
        assert prioritizer.min_threshold == 50


class TestTrackPitStop:
    """Test pit stop tracking for pit-cycle detection."""
    
    def test_track_pit_stop(self, prioritizer, base_context):
        """Pit stops should be tracked with lap and position."""
        event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={'driver': '44'}
        )
        base_context.event = event
        base_context.position_before = 3
        base_context.race_state.current_lap = 15
        
        prioritizer.track_pit_stop(event, base_context)
        
        assert "44" in prioritizer.recent_pit_stops
        assert prioritizer.recent_pit_stops["44"] == (15, 3)
    
    def test_track_multiple_pit_stops(self, prioritizer, base_context):
        """Multiple pit stops should be tracked separately."""
        # First pit stop
        event1 = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = event1
        base_context.position_before = 3
        base_context.race_state.current_lap = 15
        prioritizer.track_pit_stop(event1, base_context)
        
        # Second pit stop
        event2 = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "33"}
        )
        base_context.event = event2
        base_context.position_before = 5
        base_context.race_state.current_lap = 16
        prioritizer.track_pit_stop(event2, base_context)
        
        assert "44" in prioritizer.recent_pit_stops
        assert "33" in prioritizer.recent_pit_stops
        assert prioritizer.recent_pit_stops["44"] == (15, 3)
        assert prioritizer.recent_pit_stops["33"] == (16, 5)
    
    def test_clean_up_old_pit_stops(self, prioritizer, base_context):
        """Old pit stops (>10 laps) should be cleaned up."""
        # Track a pit stop at lap 10
        event1 = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = event1
        base_context.position_before = 3
        base_context.race_state.current_lap = 10
        prioritizer.track_pit_stop(event1, base_context)
        
        # Track another pit stop at lap 22 (12 laps later)
        event2 = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "33"}
        )
        base_context.event = event2
        base_context.position_before = 5
        base_context.race_state.current_lap = 22
        prioritizer.track_pit_stop(event2, base_context)
        
        # Driver 44's pit stop should be cleaned up
        assert "44" not in prioritizer.recent_pit_stops
        assert "33" in prioritizer.recent_pit_stops


class TestPitCycleDetection:
    """Test pit-cycle position change detection."""
    
    def test_driver_regaining_position_after_pit(self, prioritizer, base_context):
        """Position regained within 5 laps of pit should be detected."""
        # Track pit stop at lap 10, position 3
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = pit_event
        base_context.position_before = 3
        base_context.race_state.current_lap = 10
        prioritizer.track_pit_stop(pit_event, base_context)
        
        # Overtake at lap 13 (3 laps later), regaining position 3
        overtake_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = overtake_event
        base_context.position_after = 3
        base_context.race_state.current_lap = 13
        
        assert prioritizer._is_pit_cycle_position_change(overtake_event, base_context) is True
    
    def test_driver_regaining_nearby_position_after_pit(self, prioritizer, base_context):
        """Position within 2 of pre-pit position should be detected."""
        # Track pit stop at lap 10, position 5
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = pit_event
        base_context.position_before = 5
        base_context.race_state.current_lap = 10
        prioritizer.track_pit_stop(pit_event, base_context)
        
        # Overtake at lap 12, reaching position 6 (within 2 of original)
        overtake_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = overtake_event
        base_context.position_after = 6
        base_context.race_state.current_lap = 12
        
        assert prioritizer._is_pit_cycle_position_change(overtake_event, base_context) is True
    
    def test_position_change_after_pit_window(self, prioritizer, base_context):
        """Position change >5 laps after pit should not be pit-cycle."""
        # Track pit stop at lap 10, position 3
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = pit_event
        base_context.position_before = 3
        base_context.race_state.current_lap = 10
        prioritizer.track_pit_stop(pit_event, base_context)
        
        # Overtake at lap 17 (7 laps later)
        overtake_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = overtake_event
        base_context.position_after = 3
        base_context.race_state.current_lap = 17
        
        assert prioritizer._is_pit_cycle_position_change(overtake_event, base_context) is False
    
    def test_overtaking_driver_who_just_pitted(self, prioritizer, base_context):
        """Overtaking a driver who just pitted should be pit-cycle."""
        # Track pit stop for driver 33 at lap 10
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "33"}
        )
        base_context.event = pit_event
        base_context.position_before = 5
        base_context.race_state.current_lap = 10
        prioritizer.track_pit_stop(pit_event, base_context)
        
        # Driver 44 overtakes driver 33 at lap 11
        overtake_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "44", "overtaken_driver": "33"}
        )
        base_context.event = overtake_event
        base_context.position_after = 5
        base_context.race_state.current_lap = 11
        
        assert prioritizer._is_pit_cycle_position_change(overtake_event, base_context) is True
    
    def test_overtaking_driver_who_pitted_3_laps_ago(self, prioritizer, base_context):
        """Overtaking a driver who pitted >2 laps ago should not be pit-cycle."""
        # Track pit stop for driver 33 at lap 10
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "33"}
        )
        base_context.event = pit_event
        base_context.position_before = 5
        base_context.race_state.current_lap = 10
        prioritizer.track_pit_stop(pit_event, base_context)
        
        # Driver 44 overtakes driver 33 at lap 14 (4 laps later)
        overtake_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "44", "overtaken_driver": "33"}
        )
        base_context.event = overtake_event
        base_context.position_after = 5
        base_context.race_state.current_lap = 14
        
        assert prioritizer._is_pit_cycle_position_change(overtake_event, base_context) is False
    
    def test_non_overtake_event_not_pit_cycle(self, prioritizer, base_context):
        """Non-overtake events should not be pit-cycle."""
        event = RaceEvent(
            event_type=EventType.FASTEST_LAP,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = event
        
        assert prioritizer._is_pit_cycle_position_change(event, base_context) is False


class TestSuppressPitCycleChanges:
    """Test the suppress_pit_cycle_changes method."""
    
    def test_suppress_pit_cycle_overtake(self, prioritizer, base_context):
        """Pit-cycle overtakes should be suppressed."""
        # Track pit stop
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = pit_event
        base_context.position_before = 3
        base_context.race_state.current_lap = 10
        prioritizer.track_pit_stop(pit_event, base_context)
        
        # Overtake regaining position
        overtake_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = overtake_event
        base_context.position_after = 3
        base_context.race_state.current_lap = 12
        
        assert prioritizer.suppress_pit_cycle_changes(overtake_event, base_context) is True
    
    def test_do_not_suppress_genuine_overtake(self, prioritizer, base_context):
        """Genuine overtakes should not be suppressed."""
        overtake_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = overtake_event
        base_context.position_after = 3
        base_context.race_state.current_lap = 12
        
        assert prioritizer.suppress_pit_cycle_changes(overtake_event, base_context) is False
    
    def test_do_not_suppress_non_overtake_events(self, prioritizer, base_context):
        """Non-overtake events should not be suppressed."""
        event = RaceEvent(
            event_type=EventType.FASTEST_LAP,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        base_context.event = event
        
        assert prioritizer.suppress_pit_cycle_changes(event, base_context) is False


class TestSelectHighestSignificance:
    """Test selection of highest significance event."""
    
    def test_select_highest_from_multiple_events(self, prioritizer):
        """Should select event with highest total score."""
        event1 = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        context1 = ContextData(
            event=event1,
            race_state=RaceState()
        )
        sig1 = SignificanceScore(
            base_score=50,
            context_bonus=10,
            total_score=60,
            reasons=[]
        )
        
        event2 = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "33"}
        )
        context2 = ContextData(
            event=event2,
            race_state=RaceState()
        )
        sig2 = SignificanceScore(
            base_score=70,
            context_bonus=20,
            total_score=90,
            reasons=[]
        )
        
        event3 = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={"driver": "1"}
        )
        context3 = ContextData(
            event=event3,
            race_state=RaceState()
        )
        sig3 = SignificanceScore(
            base_score=40,
            context_bonus=5,
            total_score=45,
            reasons=[]
        )
        
        events = [
            (event1, context1, sig1),
            (event2, context2, sig2),
            (event3, context3, sig3)
        ]
        
        selected = prioritizer.select_highest_significance(events)
        
        assert selected is not None
        assert selected[0] == event2
        assert selected[2].total_score == 90
    
    def test_select_from_single_event(self, prioritizer):
        """Should return the single event."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        context = ContextData(
            event=event,
            race_state=RaceState()
        )
        sig = SignificanceScore(
            base_score=50,
            context_bonus=10,
            total_score=60,
            reasons=[]
        )
        
        events = [(event, context, sig)]
        
        selected = prioritizer.select_highest_significance(events)
        
        assert selected is not None
        assert selected[0] == event
    
    def test_select_from_empty_list(self, prioritizer):
        """Should return None for empty list."""
        events = []
        
        selected = prioritizer.select_highest_significance(events)
        
        assert selected is None
    
    def test_select_with_tied_scores(self, prioritizer):
        """Should select one event when scores are tied."""
        event1 = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "44"}
        )
        context1 = ContextData(
            event=event1,
            race_state=RaceState()
        )
        sig1 = SignificanceScore(
            base_score=50,
            context_bonus=10,
            total_score=60,
            reasons=[]
        )
        
        event2 = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "33"}
        )
        context2 = ContextData(
            event=event2,
            race_state=RaceState()
        )
        sig2 = SignificanceScore(
            base_score=50,
            context_bonus=10,
            total_score=60,
            reasons=[]
        )
        
        events = [
            (event1, context1, sig1),
            (event2, context2, sig2)
        ]
        
        selected = prioritizer.select_highest_significance(events)
        
        assert selected is not None
        assert selected[2].total_score == 60
