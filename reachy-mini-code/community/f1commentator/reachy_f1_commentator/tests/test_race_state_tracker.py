"""
Unit tests for the Race State Tracker module.

Tests the RaceStateTracker class functionality including state initialization,
event processing, position tracking, gap calculations, and race phase determination.
"""

import pytest
from datetime import datetime
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
from reachy_f1_commentator.src.models import (
    RaceEvent, EventType, DriverState, RacePhase
)


class TestRaceStateTrackerInitialization:
    """Test RaceStateTracker initialization."""
    
    def test_init_creates_empty_state(self):
        """Test that initialization creates an empty race state."""
        tracker = RaceStateTracker()
        assert tracker.get_positions() == []
        assert tracker.get_leader() is None
        assert tracker.get_race_phase() == RacePhase.START


class TestPositionTracking:
    """Test driver position tracking functionality."""
    
    def test_update_positions_creates_drivers(self):
        """Test that position updates create driver states."""
        tracker = RaceStateTracker()
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {
                    'Hamilton': 1,
                    'Verstappen': 2,
                    'Leclerc': 3
                },
                'lap_number': 1
            }
        )
        
        tracker.update(event)
        
        positions = tracker.get_positions()
        assert len(positions) == 3
        assert positions[0].name == 'Hamilton'
        assert positions[0].position == 1
        assert positions[1].name == 'Verstappen'
        assert positions[1].position == 2
    
    def test_get_driver_returns_correct_driver(self):
        """Test retrieving specific driver by name."""
        tracker = RaceStateTracker()
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {'Hamilton': 1, 'Verstappen': 2},
                'lap_number': 1
            }
        )
        
        tracker.update(event)
        
        driver = tracker.get_driver('Hamilton')
        assert driver is not None
        assert driver.name == 'Hamilton'
        assert driver.position == 1
    
    def test_get_driver_returns_none_for_unknown(self):
        """Test that get_driver returns None for unknown driver."""
        tracker = RaceStateTracker()
        driver = tracker.get_driver('Unknown')
        assert driver is None
    
    def test_get_leader_returns_p1_driver(self):
        """Test that get_leader returns the driver in P1."""
        tracker = RaceStateTracker()
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {'Hamilton': 1, 'Verstappen': 2, 'Leclerc': 3},
                'lap_number': 1
            }
        )
        
        tracker.update(event)
        
        leader = tracker.get_leader()
        assert leader is not None
        assert leader.name == 'Hamilton'
        assert leader.position == 1


class TestOvertakeHandling:
    """Test overtake event handling."""
    
    def test_overtake_updates_positions(self):
        """Test that overtake events update driver positions."""
        tracker = RaceStateTracker()
        
        # Initial positions
        init_event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {'Hamilton': 2, 'Verstappen': 1},
                'lap_number': 5
            }
        )
        tracker.update(init_event)
        
        # Overtake event
        overtake_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={
                'overtaking_driver': 'Hamilton',
                'overtaken_driver': 'Verstappen',
                'new_position': 1,
                'lap_number': 6
            }
        )
        tracker.update(overtake_event)
        
        hamilton = tracker.get_driver('Hamilton')
        verstappen = tracker.get_driver('Verstappen')
        
        assert hamilton.position == 1
        assert verstappen.position == 2


class TestPitStopHandling:
    """Test pit stop event handling."""
    
    def test_pit_stop_increments_count(self):
        """Test that pit stops increment the pit count."""
        tracker = RaceStateTracker()
        
        # Initial state
        init_event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={'positions': {'Hamilton': 1}, 'lap_number': 10}
        )
        tracker.update(init_event)
        
        # First pit stop
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={
                'driver': 'Hamilton',
                'tire_compound': 'soft',
                'lap_number': 15
            }
        )
        tracker.update(pit_event)
        
        driver = tracker.get_driver('Hamilton')
        assert driver.pit_count == 1
        assert driver.current_tire == 'soft'
    
    def test_multiple_pit_stops(self):
        """Test handling multiple pit stops for same driver."""
        tracker = RaceStateTracker()
        
        init_event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={'positions': {'Hamilton': 1}, 'lap_number': 10}
        )
        tracker.update(init_event)
        
        # First pit
        pit1 = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={'driver': 'Hamilton', 'tire_compound': 'medium', 'lap_number': 15}
        )
        tracker.update(pit1)
        
        # Second pit
        pit2 = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={'driver': 'Hamilton', 'tire_compound': 'soft', 'lap_number': 35}
        )
        tracker.update(pit2)
        
        driver = tracker.get_driver('Hamilton')
        assert driver.pit_count == 2
        assert driver.current_tire == 'soft'


class TestLeadChangeHandling:
    """Test lead change event handling."""
    
    def test_lead_change_updates_positions(self):
        """Test that lead changes update P1 and P2."""
        tracker = RaceStateTracker()
        
        # Initial positions
        init_event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={'positions': {'Verstappen': 1, 'Hamilton': 2}, 'lap_number': 20}
        )
        tracker.update(init_event)
        
        # Lead change
        lead_change = RaceEvent(
            event_type=EventType.LEAD_CHANGE,
            timestamp=datetime.now(),
            data={
                'new_leader': 'Hamilton',
                'old_leader': 'Verstappen',
                'lap_number': 25
            }
        )
        tracker.update(lead_change)
        
        leader = tracker.get_leader()
        assert leader.name == 'Hamilton'
        assert leader.position == 1
        
        verstappen = tracker.get_driver('Verstappen')
        assert verstappen.position == 2


class TestFastestLapHandling:
    """Test fastest lap event handling."""
    
    def test_fastest_lap_updates_state(self):
        """Test that fastest lap events update race state."""
        tracker = RaceStateTracker()
        
        # Initial state
        init_event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={'positions': {'Leclerc': 1}, 'lap_number': 30}
        )
        tracker.update(init_event)
        
        # Fastest lap
        fastest_lap = RaceEvent(
            event_type=EventType.FASTEST_LAP,
            timestamp=datetime.now(),
            data={
                'driver': 'Leclerc',
                'lap_time': 78.456,
                'lap_number': 32
            }
        )
        tracker.update(fastest_lap)
        
        assert tracker._state.fastest_lap_driver == 'Leclerc'
        assert tracker._state.fastest_lap_time == 78.456
        
        driver = tracker.get_driver('Leclerc')
        assert driver.last_lap_time == 78.456


class TestGapCalculations:
    """Test time gap calculations between drivers."""
    
    def test_gap_calculation_between_drivers(self):
        """Test calculating gaps between two drivers."""
        tracker = RaceStateTracker()
        
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {'Hamilton': 1, 'Verstappen': 2, 'Leclerc': 3},
                'gaps': {
                    'Hamilton': {'gap_to_leader': 0.0, 'gap_to_ahead': 0.0},
                    'Verstappen': {'gap_to_leader': 2.5, 'gap_to_ahead': 2.5},
                    'Leclerc': {'gap_to_leader': 5.0, 'gap_to_ahead': 2.5}
                },
                'lap_number': 10
            }
        )
        tracker.update(event)
        
        gap = tracker.get_gap('Hamilton', 'Verstappen')
        assert gap == 2.5
        
        gap2 = tracker.get_gap('Hamilton', 'Leclerc')
        assert gap2 == 5.0
    
    def test_gap_returns_zero_for_unknown_driver(self):
        """Test that gap calculation returns 0 for unknown drivers."""
        tracker = RaceStateTracker()
        gap = tracker.get_gap('Unknown1', 'Unknown2')
        assert gap == 0.0


class TestRacePhaseDetection:
    """Test race phase determination."""
    
    def test_start_phase_laps_1_to_3(self):
        """Test that laps 1-3 are START phase."""
        tracker = RaceStateTracker()
        
        for lap in [1, 2, 3]:
            event = RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={'positions': {'Hamilton': 1}, 'lap_number': lap, 'total_laps': 50}
            )
            tracker.update(event)
            assert tracker.get_race_phase() == RacePhase.START
    
    def test_mid_race_phase(self):
        """Test that middle laps are MID_RACE phase."""
        tracker = RaceStateTracker()
        
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={'positions': {'Hamilton': 1}, 'lap_number': 25, 'total_laps': 50}
        )
        tracker.update(event)
        assert tracker.get_race_phase() == RacePhase.MID_RACE
    
    def test_finish_phase_final_5_laps(self):
        """Test that final 5 laps are FINISH phase."""
        tracker = RaceStateTracker()
        
        for lap in [46, 47, 48, 49, 50]:
            event = RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={'positions': {'Hamilton': 1}, 'lap_number': lap, 'total_laps': 50}
            )
            tracker.update(event)
            assert tracker.get_race_phase() == RacePhase.FINISH


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_race_state(self):
        """Test operations on empty race state."""
        tracker = RaceStateTracker()
        
        assert tracker.get_positions() == []
        assert tracker.get_leader() is None
        assert tracker.get_driver('Anyone') is None
        assert tracker.get_gap('Driver1', 'Driver2') == 0.0
    
    def test_single_driver_scenario(self):
        """Test race with only one driver."""
        tracker = RaceStateTracker()
        
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={'positions': {'Hamilton': 1}, 'lap_number': 1}
        )
        tracker.update(event)
        
        assert len(tracker.get_positions()) == 1
        leader = tracker.get_leader()
        assert leader.name == 'Hamilton'
    
    def test_safety_car_status_update(self):
        """Test safety car status updates."""
        tracker = RaceStateTracker()
        
        # Safety car deployed
        sc_event = RaceEvent(
            event_type=EventType.SAFETY_CAR,
            timestamp=datetime.now(),
            data={'status': 'deployed', 'reason': 'incident', 'lap_number': 15}
        )
        tracker.update(sc_event)
        assert tracker._state.safety_car_active is True
        
        # Safety car ending
        sc_end = RaceEvent(
            event_type=EventType.SAFETY_CAR,
            timestamp=datetime.now(),
            data={'status': 'ending', 'reason': 'clear', 'lap_number': 18}
        )
        tracker.update(sc_end)
        assert tracker._state.safety_car_active is False
    
    def test_flag_tracking(self):
        """Test flag event tracking."""
        tracker = RaceStateTracker()
        
        flag_event = RaceEvent(
            event_type=EventType.FLAG,
            timestamp=datetime.now(),
            data={'flag_type': 'yellow', 'sector': 'sector1', 'lap_number': 10}
        )
        tracker.update(flag_event)
        
        assert 'yellow' in tracker._state.flags
