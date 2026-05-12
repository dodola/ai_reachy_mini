"""
Race State Tracker module for the F1 Commentary Robot.

This module maintains the authoritative, up-to-date race state including
driver positions, gaps, pit stops, tire compounds, and race phase information.
"""

import logging
from typing import Optional, List
from reachy_f1_commentator.src.models import (
    RaceEvent, EventType, DriverState, RaceState, RacePhase,
    OvertakeEvent, PitStopEvent, LeadChangeEvent, FastestLapEvent,
    PositionUpdateEvent
)


logger = logging.getLogger(__name__)


class RaceStateTracker:
    """
    Maintains authoritative race state for commentary and Q&A.
    
    Processes incoming race events and updates the current state including:
    - Driver positions
    - Time gaps between drivers
    - Pit stop counts
    - Current tire compounds
    - Fastest lap information
    - Race phase (start, mid-race, finish)
    """
    
    def __init__(self):
        """Initialize empty race state."""
        self._state = RaceState()
    
    def update(self, event: RaceEvent) -> None:
        """
        Update state based on incoming event.
        
        Args:
            event: RaceEvent to process and apply to state
        """
        try:
            # Update current lap if available in event data
            if 'lap_number' in event.data:
                self._state.current_lap = event.data['lap_number']
            
            # Update total laps if available
            if 'total_laps' in event.data:
                self._state.total_laps = event.data['total_laps']
            
            # Process event based on type
            if event.event_type == EventType.POSITION_UPDATE:
                self._update_positions(event)
            elif event.event_type == EventType.OVERTAKE:
                self._update_overtake(event)
            elif event.event_type == EventType.PIT_STOP:
                self._update_pit_stop(event)
            elif event.event_type == EventType.LEAD_CHANGE:
                self._update_lead_change(event)
            elif event.event_type == EventType.FASTEST_LAP:
                self._update_fastest_lap(event)
            elif event.event_type == EventType.SAFETY_CAR:
                self._update_safety_car(event)
            elif event.event_type == EventType.FLAG:
                self._update_flag(event)
            
            # Update race phase based on current lap
            self._update_race_phase()
            
        except Exception as e:
            logger.error(f"[RaceStateTracker] Error updating state for event {event.event_type.value}: {e}", exc_info=True)
    
    def get_positions(self) -> List[DriverState]:
        """
        Return current driver positions sorted by position.
        
        Returns:
            List of DriverState objects sorted by position (P1, P2, P3, ...)
        """
        return self._state.get_positions()
    
    def get_driver(self, driver_name: str) -> Optional[DriverState]:
        """
        Return state for specific driver.
        
        Args:
            driver_name: Name of the driver to retrieve
            
        Returns:
            DriverState object if found, None otherwise
        """
        return self._state.get_driver(driver_name)
    
    def get_leader(self) -> Optional[DriverState]:
        """
        Return current race leader.
        
        Returns:
            DriverState of the driver in P1, or None if no drivers
        """
        return self._state.get_leader()
    
    def get_gap(self, driver1: str, driver2: str) -> float:
        """
        Calculate time gap between two drivers.
        
        Args:
            driver1: Name of first driver
            driver2: Name of second driver
            
        Returns:
            Time gap in seconds (positive if driver1 is ahead, negative if behind)
            Returns 0.0 if either driver not found
        """
        d1 = self.get_driver(driver1)
        d2 = self.get_driver(driver2)
        
        if not d1 or not d2:
            return 0.0
        
        # If driver1 is ahead (lower position number), gap is positive
        if d1.position < d2.position:
            return d2.gap_to_leader - d1.gap_to_leader
        else:
            return d1.gap_to_leader - d2.gap_to_leader
    
    def get_race_phase(self) -> RacePhase:
        """
        Return current race phase based on lap number.
        
        Returns:
            RacePhase enum (START, MID_RACE, or FINISH)
        """
        return self._state.race_phase
    
    # Private helper methods
    
    def _update_positions(self, event: RaceEvent) -> None:
        """Update driver positions from position update event."""
        positions = event.data.get('positions', {})
        gaps = event.data.get('gaps', {})
        
        # Update or create driver states
        for driver_name, position in positions.items():
            driver = self.get_driver(driver_name)
            if driver:
                driver.position = position
            else:
                # Create new driver state
                new_driver = DriverState(name=driver_name, position=position)
                self._state.drivers.append(new_driver)
        
        # Update gaps
        self._recalculate_gaps(gaps)
    
    def _update_overtake(self, event: RaceEvent) -> None:
        """Update positions from overtake event."""
        overtaking = event.data.get('overtaking_driver')
        overtaken = event.data.get('overtaken_driver')
        new_position = event.data.get('new_position')
        
        if overtaking and overtaken and new_position:
            driver = self.get_driver(overtaking)
            if driver:
                driver.position = new_position
            
            # Overtaken driver moves down one position
            overtaken_driver = self.get_driver(overtaken)
            if overtaken_driver:
                overtaken_driver.position = new_position + 1
    
    def _update_pit_stop(self, event: RaceEvent) -> None:
        """Update pit stop information."""
        driver_name = event.data.get('driver')
        tire_compound = event.data.get('tire_compound', 'unknown')
        
        if driver_name:
            driver = self.get_driver(driver_name)
            if driver:
                driver.pit_count += 1
                driver.current_tire = tire_compound
    
    def _update_lead_change(self, event: RaceEvent) -> None:
        """Update positions from lead change event."""
        new_leader = event.data.get('new_leader')
        old_leader = event.data.get('old_leader')
        
        if new_leader:
            driver = self.get_driver(new_leader)
            if driver:
                driver.position = 1
        
        if old_leader:
            driver = self.get_driver(old_leader)
            if driver:
                driver.position = 2
    
    def _update_fastest_lap(self, event: RaceEvent) -> None:
        """Update fastest lap information."""
        driver_name = event.data.get('driver')
        lap_time = event.data.get('lap_time')
        
        if driver_name and lap_time:
            self._state.fastest_lap_driver = driver_name
            self._state.fastest_lap_time = lap_time
            
            # Update driver's last lap time
            driver = self.get_driver(driver_name)
            if driver:
                driver.last_lap_time = lap_time
    
    def _update_safety_car(self, event: RaceEvent) -> None:
        """Update safety car status."""
        status = event.data.get('status', '')
        self._state.safety_car_active = status in ['deployed', 'in']
    
    def _update_flag(self, event: RaceEvent) -> None:
        """Update flag status."""
        flag_type = event.data.get('flag_type')
        if flag_type and flag_type not in self._state.flags:
            self._state.flags.append(flag_type)
    
    def _recalculate_gaps(self, gaps: dict) -> None:
        """
        Recalculate time gaps between drivers.
        
        Args:
            gaps: Dictionary mapping driver names to gap information
        """
        leader = self.get_leader()
        if not leader:
            return
        
        # Leader has 0 gap
        leader.gap_to_leader = 0.0
        leader.gap_to_ahead = 0.0
        
        # Update gaps for all drivers
        sorted_drivers = self.get_positions()
        for i, driver in enumerate(sorted_drivers):
            if i == 0:
                continue
            
            # Get gap from provided data or calculate
            if driver.name in gaps:
                driver.gap_to_leader = gaps[driver.name].get('gap_to_leader', 0.0)
                driver.gap_to_ahead = gaps[driver.name].get('gap_to_ahead', 0.0)
            elif i > 0:
                # Gap to ahead is the difference in gaps to leader
                prev_driver = sorted_drivers[i - 1]
                driver.gap_to_ahead = driver.gap_to_leader - prev_driver.gap_to_leader
    
    def _update_race_phase(self) -> None:
        """Update race phase based on current lap number."""
        if self._state.current_lap == 0:
            self._state.race_phase = RacePhase.START
        elif self._state.current_lap <= 3:
            self._state.race_phase = RacePhase.START
        elif self._state.total_laps > 0 and self._state.current_lap > self._state.total_laps - 5:
            self._state.race_phase = RacePhase.FINISH
        else:
            self._state.race_phase = RacePhase.MID_RACE
