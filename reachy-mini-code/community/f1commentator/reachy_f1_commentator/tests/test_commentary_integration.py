"""
Integration test demonstrating Commentary Generator with full system.

This test shows how the Commentary Generator integrates with:
- Race State Tracker
- Event Queue
- Data Ingestion Module
"""

import pytest
from datetime import datetime
from reachy_f1_commentator.src.commentary_generator import CommentaryGenerator
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.models import RaceEvent, EventType, DriverState
from reachy_f1_commentator.src.config import Config


class TestCommentarySystemIntegration:
    """Test commentary generator integration with other system components."""
    
    def test_full_race_commentary_flow(self):
        """Test complete flow from event detection to commentary generation."""
        # Initialize components
        config = Config(ai_enabled=False)
        state_tracker = RaceStateTracker()
        event_queue = PriorityEventQueue(max_size=10)
        generator = CommentaryGenerator(config, state_tracker)
        
        # Set up initial race state
        state_tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=2.5),
            DriverState(name="Leclerc", position=3, gap_to_leader=5.0),
        ]
        state_tracker._state.current_lap = 10
        state_tracker._state.total_laps = 50
        
        # Simulate race events
        events = [
            # Overtake event
            RaceEvent(
                event_type=EventType.OVERTAKE,
                timestamp=datetime.now(),
                data={
                    "overtaking_driver": "Hamilton",
                    "overtaken_driver": "Verstappen",
                    "new_position": 1,
                    "lap_number": 10
                }
            ),
            # Pit stop event
            RaceEvent(
                event_type=EventType.PIT_STOP,
                timestamp=datetime.now(),
                data={
                    "driver": "Leclerc",
                    "pit_count": 1,
                    "tire_compound": "soft",
                    "pit_duration": 2.3,
                    "lap_number": 11
                }
            ),
            # Lead change event
            RaceEvent(
                event_type=EventType.LEAD_CHANGE,
                timestamp=datetime.now(),
                data={
                    "new_leader": "Hamilton",
                    "old_leader": "Verstappen",
                    "lap_number": 10
                }
            ),
        ]
        
        # Process events through the system
        commentaries = []
        for event in events:
            # Add to event queue
            event_queue.enqueue(event)
            
            # Update race state
            state_tracker.update(event)
            
            # Dequeue and generate commentary
            queued_event = event_queue.dequeue()
            if queued_event:
                commentary = generator.generate(queued_event)
                commentaries.append(commentary)
        
        # Verify all commentaries were generated
        assert len(commentaries) == 3
        
        # Verify commentary content
        assert any("Hamilton" in c for c in commentaries)
        assert any("Leclerc" in c for c in commentaries)
        assert any("Verstappen" in c for c in commentaries)
        
        # Verify race state was updated
        hamilton = state_tracker.get_driver("Hamilton")
        assert hamilton is not None
        assert hamilton.position == 1  # After overtake
        
        leclerc = state_tracker.get_driver("Leclerc")
        assert leclerc is not None
        assert leclerc.pit_count == 1  # After pit stop
    
    def test_commentary_adapts_to_race_progression(self):
        """Test that commentary style adapts as race progresses."""
        config = Config(ai_enabled=False)
        state_tracker = RaceStateTracker()
        generator = CommentaryGenerator(config, state_tracker)
        
        # Set up race state
        state_tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=1.0),
        ]
        state_tracker._state.total_laps = 50
        
        # Create same event type at different race phases
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={
                "overtaking_driver": "Hamilton",
                "overtaken_driver": "Verstappen",
                "new_position": 1
            }
        )
        
        # Test at race start (lap 2)
        state_tracker._state.current_lap = 2
        commentary_start = generator.generate(event)
        
        # Test at mid-race (lap 25)
        state_tracker._state.current_lap = 25
        commentary_mid = generator.generate(event)
        
        # Test at race finish (lap 48)
        state_tracker._state.current_lap = 48
        commentary_finish = generator.generate(event)
        
        # All should generate valid commentary
        assert isinstance(commentary_start, str) and len(commentary_start) > 0
        assert isinstance(commentary_mid, str) and len(commentary_mid) > 0
        assert isinstance(commentary_finish, str) and len(commentary_finish) > 0
        
        # Commentary should mention the drivers
        assert "Hamilton" in commentary_start or "Verstappen" in commentary_start
        assert "Hamilton" in commentary_mid or "Verstappen" in commentary_mid
        assert "Hamilton" in commentary_finish or "Verstappen" in commentary_finish
    
    def test_priority_queue_affects_commentary_order(self):
        """Test that event priority affects commentary generation order."""
        config = Config(ai_enabled=False)
        state_tracker = RaceStateTracker()
        event_queue = PriorityEventQueue(max_size=10)
        generator = CommentaryGenerator(config, state_tracker)
        
        # Set up race state
        state_tracker._state.current_lap = 20
        state_tracker._state.total_laps = 50
        
        # Add events in non-priority order
        events = [
            # Low priority - fastest lap
            RaceEvent(
                event_type=EventType.FASTEST_LAP,
                timestamp=datetime.now(),
                data={"driver": "Leclerc", "lap_time": 78.5, "lap_number": 20}
            ),
            # Critical priority - incident
            RaceEvent(
                event_type=EventType.INCIDENT,
                timestamp=datetime.now(),
                data={"description": "Collision at turn 1", "lap_number": 20}
            ),
            # High priority - overtake
            RaceEvent(
                event_type=EventType.OVERTAKE,
                timestamp=datetime.now(),
                data={
                    "overtaking_driver": "Hamilton",
                    "overtaken_driver": "Verstappen",
                    "new_position": 2
                }
            ),
        ]
        
        # Enqueue all events
        for event in events:
            event_queue.enqueue(event)
        
        # Dequeue and generate commentary
        commentaries = []
        while event_queue.size() > 0:
            event = event_queue.dequeue()
            if event:
                commentary = generator.generate(event)
                commentaries.append((event.event_type, commentary))
        
        # Verify order: incident (critical) -> overtake (high) -> fastest lap (medium)
        assert len(commentaries) == 3
        assert commentaries[0][0] == EventType.INCIDENT
        assert commentaries[1][0] == EventType.OVERTAKE
        assert commentaries[2][0] == EventType.FASTEST_LAP
        
        # Verify all commentaries are valid
        for event_type, commentary in commentaries:
            assert isinstance(commentary, str)
            assert len(commentary) > 0
