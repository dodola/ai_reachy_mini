"""
Integration tests for Q&A Manager with other system components.

Tests the Q&A Manager's integration with Race State Tracker,
Event Queue, and the overall commentary system workflow.
"""

import pytest
from datetime import datetime
from reachy_f1_commentator.src.qa_manager import QAManager
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.models import RaceEvent, EventType


class TestQAIntegration:
    """Test Q&A Manager integration with system components."""
    
    def setup_method(self):
        """Set up test fixtures with realistic race scenario."""
        self.tracker = RaceStateTracker()
        self.event_queue = PriorityEventQueue(max_size=10)
        self.qa_manager = QAManager(self.tracker, self.event_queue)
        
        # Simulate a race in progress
        self._setup_race_scenario()
    
    def _setup_race_scenario(self):
        """Set up a realistic race scenario."""
        # Initial positions
        position_event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {
                    'Verstappen': 1,
                    'Hamilton': 2,
                    'Leclerc': 3,
                    'Sainz': 4,
                    'Perez': 5
                },
                'gaps': {
                    'Hamilton': {'gap_to_leader': 2.5, 'gap_to_ahead': 2.5},
                    'Leclerc': {'gap_to_leader': 6.8, 'gap_to_ahead': 4.3},
                    'Sainz': {'gap_to_leader': 10.2, 'gap_to_ahead': 3.4},
                    'Perez': {'gap_to_leader': 15.7, 'gap_to_ahead': 5.5}
                },
                'lap_number': 30,
                'total_laps': 58
            }
        )
        self.tracker.update(position_event)
        
        # Add some pit stops
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={
                'driver': 'Hamilton',
                'tire_compound': 'hard',
                'lap_number': 25
            }
        )
        self.tracker.update(pit_event)
        
        # Add events to queue
        self.event_queue.enqueue(RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={'overtaking_driver': 'Leclerc', 'overtaken_driver': 'Hamilton'}
        ))
        self.event_queue.enqueue(RaceEvent(
            event_type=EventType.FASTEST_LAP,
            timestamp=datetime.now(),
            data={'driver': 'Verstappen', 'lap_time': 84.123}
        ))
    
    def test_qa_interrupts_commentary_flow(self):
        """Test that Q&A properly interrupts commentary processing."""
        # Queue should have events
        assert self.event_queue.size() == 2
        assert not self.event_queue.is_paused()
        
        # Process a question
        response = self.qa_manager.process_question("Who's leading?")
        
        # Queue should be paused
        assert self.event_queue.is_paused()
        assert "Verstappen" in response
        
        # Resume queue
        self.qa_manager.resume_event_queue()
        assert not self.event_queue.is_paused()
    
    def test_qa_uses_current_race_state(self):
        """Test that Q&A responses reflect current race state."""
        # Ask about positions
        response = self.qa_manager.process_question("Where is Hamilton?")
        assert "P2" in response
        assert "2.5" in response  # Gap to leader
        
        # Ask about pit stops
        response = self.qa_manager.process_question("Has Hamilton pitted?")
        assert "1 pit stop" in response
        assert "hard" in response.lower()
    
    def test_qa_during_active_race(self):
        """Test Q&A during active race with multiple events."""
        # Simulate race progression
        for i in range(5):
            event = RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={
                    'positions': {'Verstappen': 1, 'Hamilton': 2},
                    'lap_number': 30 + i
                }
            )
            self.event_queue.enqueue(event)
        
        # Queue should have multiple events
        initial_size = self.event_queue.size()
        assert initial_size > 0
        
        # Process Q&A
        response = self.qa_manager.process_question("What's the gap to the leader?")
        
        # Queue should be paused but events preserved
        assert self.event_queue.is_paused()
        assert self.event_queue.size() == initial_size
        assert "gap" in response.lower() or "verstappen" in response.lower()
        
        # Resume and verify events can be processed
        self.qa_manager.resume_event_queue()
        event = self.event_queue.dequeue()
        assert event is not None
    
    def test_multiple_qa_interactions(self):
        """Test multiple Q&A interactions in sequence."""
        questions = [
            "Who's leading?",
            "Where is Leclerc?",
            "Has Sainz pitted?",
            "What's the gap to the leader?"
        ]
        
        for question in questions:
            # Process question
            response = self.qa_manager.process_question(question)
            assert isinstance(response, str)
            assert len(response) > 0
            assert self.event_queue.is_paused()
            
            # Resume queue
            self.qa_manager.resume_event_queue()
            assert not self.event_queue.is_paused()
    
    def test_qa_with_state_updates_during_pause(self):
        """Test that state updates work even when queue is paused."""
        # Pause queue via Q&A
        self.qa_manager.process_question("Who's leading?")
        assert self.event_queue.is_paused()
        
        # Update race state (simulating data ingestion continuing)
        new_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={
                'overtaking_driver': 'Hamilton',
                'overtaken_driver': 'Verstappen',
                'new_position': 1,
                'lap_number': 31
            }
        )
        self.tracker.update(new_event)
        
        # Resume and ask about new state
        self.qa_manager.resume_event_queue()
        response = self.qa_manager.process_question("Who's leading?")
        
        # Should reflect updated state
        assert "Hamilton" in response or "leading" in response.lower()
    
    def test_qa_error_handling_with_corrupted_state(self):
        """Test Q&A handles edge cases gracefully."""
        # Create new tracker with minimal state
        minimal_tracker = RaceStateTracker()
        qa = QAManager(minimal_tracker, self.event_queue)
        
        # Ask questions with no data
        response = qa.process_question("Where is Hamilton?")
        assert "don't have" in response.lower()
        
        # Queue should still be paused
        assert self.event_queue.is_paused()
        qa.resume_event_queue()


class TestQAWithCommentarySystem:
    """Test Q&A integration with commentary generation workflow."""
    
    def test_qa_priority_over_commentary(self):
        """Test that Q&A takes priority over pending commentary."""
        tracker = RaceStateTracker()
        event_queue = PriorityEventQueue(max_size=10)
        qa_manager = QAManager(tracker, event_queue)
        
        # Set up race state
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {'Verstappen': 1, 'Hamilton': 2},
                'lap_number': 20
            }
        )
        tracker.update(event)
        
        # Add high-priority events to queue
        for _ in range(5):
            event_queue.enqueue(RaceEvent(
                event_type=EventType.OVERTAKE,
                timestamp=datetime.now(),
                data={'overtaking_driver': 'A', 'overtaken_driver': 'B'}
            ))
        
        # Q&A should pause queue immediately
        response = qa_manager.process_question("Who's leading?")
        assert event_queue.is_paused()
        assert event_queue.size() == 5  # Events preserved
        
        # After Q&A, commentary can resume
        qa_manager.resume_event_queue()
        assert not event_queue.is_paused()
        assert event_queue.dequeue() is not None
