"""
Unit tests for the PriorityEventQueue class.

Tests cover:
- Basic enqueue/dequeue operations
- Priority ordering
- Queue overflow handling
- Pause/resume functionality
- Thread safety
- Edge cases
"""

import pytest
from datetime import datetime
import threading
import time

from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.models import RaceEvent, EventType, EventPriority


class TestPriorityEventQueue:
    """Test suite for PriorityEventQueue class."""
    
    def test_init_default_max_size(self):
        """Test queue initialization with default max size."""
        queue = PriorityEventQueue()
        assert queue.size() == 0
        assert not queue.is_paused()
    
    def test_init_custom_max_size(self):
        """Test queue initialization with custom max size."""
        queue = PriorityEventQueue(max_size=5)
        assert queue.size() == 0
    
    def test_enqueue_single_event(self):
        """Test enqueueing a single event."""
        queue = PriorityEventQueue()
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "Hamilton"}
        )
        queue.enqueue(event)
        assert queue.size() == 1
    
    def test_dequeue_single_event(self):
        """Test dequeueing a single event."""
        queue = PriorityEventQueue()
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "Hamilton"}
        )
        queue.enqueue(event)
        dequeued = queue.dequeue()
        assert dequeued == event
        assert queue.size() == 0
    
    def test_dequeue_empty_queue(self):
        """Test dequeueing from empty queue returns None."""
        queue = PriorityEventQueue()
        assert queue.dequeue() is None
    
    def test_priority_ordering_critical_before_high(self):
        """Test that CRITICAL priority events are dequeued before HIGH."""
        queue = PriorityEventQueue()
        
        # Add HIGH priority event (overtake)
        high_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={"driver": "Hamilton"}
        )
        queue.enqueue(high_event)
        
        # Add CRITICAL priority event (incident)
        critical_event = RaceEvent(
            event_type=EventType.INCIDENT,
            timestamp=datetime.now(),
            data={"description": "Collision"}
        )
        queue.enqueue(critical_event)
        
        # CRITICAL should be dequeued first
        assert queue.dequeue() == critical_event
        assert queue.dequeue() == high_event
    
    def test_priority_ordering_all_levels(self):
        """Test priority ordering across all priority levels."""
        queue = PriorityEventQueue()
        
        # Add events in reverse priority order
        low_event = RaceEvent(EventType.POSITION_UPDATE, datetime.now())
        medium_event = RaceEvent(EventType.FASTEST_LAP, datetime.now())
        high_event = RaceEvent(EventType.PIT_STOP, datetime.now())
        critical_event = RaceEvent(EventType.SAFETY_CAR, datetime.now())
        
        queue.enqueue(low_event)
        queue.enqueue(medium_event)
        queue.enqueue(high_event)
        queue.enqueue(critical_event)
        
        # Should dequeue in priority order
        assert queue.dequeue() == critical_event
        assert queue.dequeue() == high_event
        assert queue.dequeue() == medium_event
        assert queue.dequeue() == low_event
    
    def test_fifo_within_same_priority(self):
        """Test FIFO ordering for events with same priority."""
        queue = PriorityEventQueue()
        
        # Add multiple HIGH priority events
        event1 = RaceEvent(EventType.OVERTAKE, datetime.now(), {"id": 1})
        event2 = RaceEvent(EventType.PIT_STOP, datetime.now(), {"id": 2})
        event3 = RaceEvent(EventType.OVERTAKE, datetime.now(), {"id": 3})
        
        queue.enqueue(event1)
        queue.enqueue(event2)
        queue.enqueue(event3)
        
        # Should dequeue in FIFO order (all are HIGH priority)
        assert queue.dequeue() == event1
        assert queue.dequeue() == event2
        assert queue.dequeue() == event3
    
    def test_queue_overflow_discards_lowest_priority(self):
        """Test that queue discards lowest priority events when full."""
        queue = PriorityEventQueue(max_size=3)
        
        # Fill queue with different priorities
        critical_event = RaceEvent(EventType.INCIDENT, datetime.now())
        high_event = RaceEvent(EventType.OVERTAKE, datetime.now())
        low_event = RaceEvent(EventType.POSITION_UPDATE, datetime.now())
        
        queue.enqueue(critical_event)
        queue.enqueue(high_event)
        queue.enqueue(low_event)
        
        assert queue.size() == 3
        
        # Add another HIGH priority event - should discard LOW
        another_high = RaceEvent(EventType.PIT_STOP, datetime.now())
        queue.enqueue(another_high)
        
        assert queue.size() == 3
        
        # Dequeue all - LOW should not be present
        events = []
        while queue.size() > 0:
            events.append(queue.dequeue())
        
        assert low_event not in events
        assert critical_event in events
        assert high_event in events
        assert another_high in events
    
    def test_queue_overflow_discards_new_low_priority(self):
        """Test that new low priority events are discarded when queue is full of high priority."""
        queue = PriorityEventQueue(max_size=2)
        
        # Fill with CRITICAL events
        critical1 = RaceEvent(EventType.INCIDENT, datetime.now(), {"id": 1})
        critical2 = RaceEvent(EventType.SAFETY_CAR, datetime.now(), {"id": 2})
        
        queue.enqueue(critical1)
        queue.enqueue(critical2)
        
        # Try to add LOW priority - should be discarded
        low_event = RaceEvent(EventType.POSITION_UPDATE, datetime.now())
        queue.enqueue(low_event)
        
        assert queue.size() == 2
        
        # Only CRITICAL events should remain
        assert queue.dequeue() == critical1
        assert queue.dequeue() == critical2
    
    def test_pause_prevents_dequeue(self):
        """Test that pause prevents dequeue operations."""
        queue = PriorityEventQueue()
        event = RaceEvent(EventType.OVERTAKE, datetime.now())
        queue.enqueue(event)
        
        queue.pause()
        assert queue.is_paused()
        assert queue.dequeue() is None
        assert queue.size() == 1  # Event still in queue
    
    def test_resume_allows_dequeue(self):
        """Test that resume allows dequeue after pause."""
        queue = PriorityEventQueue()
        event = RaceEvent(EventType.OVERTAKE, datetime.now())
        queue.enqueue(event)
        
        queue.pause()
        assert queue.dequeue() is None
        
        queue.resume()
        assert not queue.is_paused()
        assert queue.dequeue() == event
    
    def test_pause_resume_state_tracking(self):
        """Test pause/resume state is tracked correctly."""
        queue = PriorityEventQueue()
        
        assert not queue.is_paused()
        
        queue.pause()
        assert queue.is_paused()
        
        queue.resume()
        assert not queue.is_paused()
    
    def test_enqueue_while_paused(self):
        """Test that enqueue works while paused."""
        queue = PriorityEventQueue()
        queue.pause()
        
        event = RaceEvent(EventType.OVERTAKE, datetime.now())
        queue.enqueue(event)
        
        assert queue.size() == 1
        assert queue.dequeue() is None  # Still paused
        
        queue.resume()
        assert queue.dequeue() == event
    
    def test_size_returns_correct_count(self):
        """Test that size() returns accurate count."""
        queue = PriorityEventQueue()
        
        assert queue.size() == 0
        
        queue.enqueue(RaceEvent(EventType.OVERTAKE, datetime.now()))
        assert queue.size() == 1
        
        queue.enqueue(RaceEvent(EventType.PIT_STOP, datetime.now()))
        assert queue.size() == 2
        
        queue.dequeue()
        assert queue.size() == 1
        
        queue.dequeue()
        assert queue.size() == 0
    
    def test_priority_assignment_critical_events(self):
        """Test that CRITICAL priority is assigned to incidents, safety car, lead changes."""
        queue = PriorityEventQueue()
        
        incident = RaceEvent(EventType.INCIDENT, datetime.now())
        safety_car = RaceEvent(EventType.SAFETY_CAR, datetime.now())
        lead_change = RaceEvent(EventType.LEAD_CHANGE, datetime.now())
        low_priority = RaceEvent(EventType.POSITION_UPDATE, datetime.now())
        
        # Add low priority first, then critical
        queue.enqueue(low_priority)
        queue.enqueue(incident)
        queue.enqueue(safety_car)
        queue.enqueue(lead_change)
        
        # All critical should come out first
        assert queue.dequeue() == incident
        assert queue.dequeue() == safety_car
        assert queue.dequeue() == lead_change
        assert queue.dequeue() == low_priority
    
    def test_priority_assignment_high_events(self):
        """Test that HIGH priority is assigned to overtakes and pit stops."""
        queue = PriorityEventQueue()
        
        overtake = RaceEvent(EventType.OVERTAKE, datetime.now())
        pit_stop = RaceEvent(EventType.PIT_STOP, datetime.now())
        low_priority = RaceEvent(EventType.POSITION_UPDATE, datetime.now())
        
        queue.enqueue(low_priority)
        queue.enqueue(overtake)
        queue.enqueue(pit_stop)
        
        # HIGH priority should come out before LOW
        assert queue.dequeue() == overtake
        assert queue.dequeue() == pit_stop
        assert queue.dequeue() == low_priority
    
    def test_priority_assignment_medium_events(self):
        """Test that MEDIUM priority is assigned to fastest laps."""
        queue = PriorityEventQueue()
        
        fastest_lap = RaceEvent(EventType.FASTEST_LAP, datetime.now())
        low_priority = RaceEvent(EventType.POSITION_UPDATE, datetime.now())
        
        queue.enqueue(low_priority)
        queue.enqueue(fastest_lap)
        
        # MEDIUM should come before LOW
        assert queue.dequeue() == fastest_lap
        assert queue.dequeue() == low_priority
    
    def test_thread_safety_concurrent_enqueue(self):
        """Test thread safety with concurrent enqueue operations."""
        queue = PriorityEventQueue(max_size=100)
        
        def enqueue_events(count):
            for i in range(count):
                event = RaceEvent(EventType.OVERTAKE, datetime.now(), {"id": i})
                queue.enqueue(event)
        
        # Create multiple threads enqueueing simultaneously
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=enqueue_events, args=(10,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have 50 events total
        assert queue.size() == 50
    
    def test_thread_safety_concurrent_dequeue(self):
        """Test thread safety with concurrent dequeue operations."""
        num_events = 100
        queue = PriorityEventQueue(max_size=num_events)
        
        # Add events
        for i in range(num_events):
            queue.enqueue(RaceEvent(EventType.OVERTAKE, datetime.now(), {"id": i}))
        
        dequeued_events = []
        lock = threading.Lock()
        
        def dequeue_events(count):
            for _ in range(count):
                event = queue.dequeue()
                if event:
                    with lock:
                        dequeued_events.append(event)
                time.sleep(0.0001)  # Tiny delay to encourage concurrency
        
        # Create multiple threads dequeueing simultaneously
        # Each thread dequeues 25 events
        threads = []
        for _ in range(4):
            thread = threading.Thread(target=dequeue_events, args=(25,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have dequeued all events (no duplicates due to thread safety)
        assert len(dequeued_events) == num_events
        assert queue.size() == 0
        
        # Verify no duplicate events (all IDs should be unique)
        ids = [e.data["id"] for e in dequeued_events]
        assert len(ids) == len(set(ids))
    
    def test_flag_event_priority(self):
        """Test that FLAG events get LOW priority."""
        queue = PriorityEventQueue()
        
        flag = RaceEvent(EventType.FLAG, datetime.now())
        overtake = RaceEvent(EventType.OVERTAKE, datetime.now())
        
        queue.enqueue(flag)
        queue.enqueue(overtake)
        
        # HIGH priority overtake should come first
        assert queue.dequeue() == overtake
        assert queue.dequeue() == flag
