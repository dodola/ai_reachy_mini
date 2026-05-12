"""
Event Queue with prioritization for the F1 Commentary Robot.

This module implements a priority-based event queue that manages race events
awaiting commentary generation. Events are prioritized by importance and
processed in priority order rather than arrival order.
"""

import logging
import heapq
import threading
from typing import Optional, Tuple
from datetime import datetime

from reachy_f1_commentator.src.models import RaceEvent, EventType, EventPriority


logger = logging.getLogger(__name__)


class PriorityEventQueue:
    """
    Priority queue for managing race events.
    
    Events are prioritized by importance (CRITICAL > HIGH > MEDIUM > LOW)
    and processed in priority order. The queue has a maximum size and
    discards lowest priority events when full. Supports pause/resume
    for Q&A interruption.
    """
    
    def __init__(self, max_size: int = 10):
        """
        Initialize priority event queue.
        
        Args:
            max_size: Maximum number of events to hold (default: 10)
        """
        self._max_size = max_size
        self._queue: list[Tuple[int, int, RaceEvent]] = []  # (priority, counter, event)
        self._counter = 0  # Ensures FIFO for same priority
        self._paused = False
        self._lock = threading.Lock()
    
    def enqueue(self, event: RaceEvent) -> None:
        """
        Add event to queue with priority assignment.
        
        If queue is full, discards lowest priority event to make room.
        Priority is assigned based on event type.
        
        Args:
            event: Race event to enqueue
        """
        try:
            with self._lock:
                priority = self._assign_priority(event)
                
                # If queue is full, check if we should discard
                if len(self._queue) >= self._max_size:
                    # Find lowest priority event (highest priority value)
                    if self._queue:
                        lowest_priority_item = max(self._queue, key=lambda x: x[0])
                        
                        # Only add new event if it has higher priority than lowest
                        if priority.value < lowest_priority_item[0]:
                            # Remove lowest priority event
                            self._queue.remove(lowest_priority_item)
                            heapq.heapify(self._queue)
                        else:
                            # New event has lower priority, discard it
                            return
                
                # Add event to queue
                # Use counter to maintain FIFO order for same priority
                heapq.heappush(self._queue, (priority.value, self._counter, event))
                self._counter += 1
        except Exception as e:
            logger.error(f"[EventQueue] Error enqueueing event: {e}", exc_info=True)
    
    def dequeue(self) -> Optional[RaceEvent]:
        """
        Remove and return highest priority event.
        
        Returns None if queue is empty or paused.
        
        Returns:
            Highest priority event, or None if empty/paused
        """
        try:
            with self._lock:
                if self._paused or not self._queue:
                    return None
                
                # Pop highest priority (lowest priority value)
                _, _, event = heapq.heappop(self._queue)
                return event
        except Exception as e:
            logger.error(f"[EventQueue] Error dequeueing event: {e}", exc_info=True)
            return None
    
    def pause(self) -> None:
        """
        Pause event processing (for Q&A interruption).
        
        When paused, dequeue() returns None even if events are available.
        """
        with self._lock:
            self._paused = True
    
    def resume(self) -> None:
        """
        Resume event processing after pause.
        """
        with self._lock:
            self._paused = False
    
    def is_paused(self) -> bool:
        """
        Check if queue is currently paused.
        
        Returns:
            True if paused, False otherwise
        """
        with self._lock:
            return self._paused
    
    def size(self) -> int:
        """
        Get current number of events in queue.
        
        Returns:
            Number of events currently queued
        """
        with self._lock:
            return len(self._queue)
    
    def _assign_priority(self, event: RaceEvent) -> EventPriority:
        """
        Assign priority based on event type.
        
        Priority assignment logic:
        - CRITICAL: Starting grid, race start, overtakes, pit stops, incidents, safety car, lead changes
        - HIGH: Fastest laps
        - MEDIUM: Race control messages (flags, etc.)
        - LOW: Routine position updates
        
        Args:
            event: Race event to prioritize
            
        Returns:
            EventPriority enum value
        """
        # Starting grid and race start get highest priority
        if event.data.get('is_starting_grid') or event.data.get('is_race_start'):
            return EventPriority.CRITICAL
        
        # Overtakes and pit stops are the most interesting events - make them CRITICAL
        if event.event_type in [EventType.OVERTAKE, EventType.PIT_STOP]:
            return EventPriority.CRITICAL
        
        # Safety car and lead changes also CRITICAL (incidents disabled for now)
        if event.event_type in [EventType.SAFETY_CAR, EventType.LEAD_CHANGE]:
            return EventPriority.CRITICAL
        
        # Fastest laps are interesting but less critical
        elif event.event_type == EventType.FASTEST_LAP:
            return EventPriority.HIGH
        
        # Race control messages (flags, etc.) are medium priority
        elif event.event_type == EventType.FLAG:
            return EventPriority.MEDIUM
        
        # Everything else is low priority
        else:
            return EventPriority.LOW
