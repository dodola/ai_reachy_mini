"""
Unit tests for core data models and types.
"""

from datetime import datetime
import pytest

from reachy_f1_commentator.src.models import (
    EventType, EventPriority, RacePhase, Gesture,
    RaceEvent, OvertakeEvent, PitStopEvent, LeadChangeEvent,
    FastestLapEvent, IncidentEvent, SafetyCarEvent, FlagEvent,
    PositionUpdateEvent, DriverState, RaceState, Config
)


class TestEnumerations:
    """Test enumeration types."""
    
    def test_event_type_enum(self):
        """Test EventType enum has all required values."""
        assert EventType.OVERTAKE.value == "overtake"
        assert EventType.PIT_STOP.value == "pit_stop"
        assert EventType.LEAD_CHANGE.value == "lead_change"
        assert EventType.FASTEST_LAP.value == "fastest_lap"
        assert EventType.INCIDENT.value == "incident"
        assert EventType.FLAG.value == "flag"
        assert EventType.SAFETY_CAR.value == "safety_car"
        assert EventType.POSITION_UPDATE.value == "position_update"
    
    def test_event_priority_enum(self):
        """Test EventPriority enum has correct priority values."""
        assert EventPriority.CRITICAL.value == 1
        assert EventPriority.HIGH.value == 2
        assert EventPriority.MEDIUM.value == 3
        assert EventPriority.LOW.value == 4
    
    def test_race_phase_enum(self):
        """Test RacePhase enum has all phases."""
        assert RacePhase.START.value == "start"
        assert RacePhase.MID_RACE.value == "mid_race"
        assert RacePhase.FINISH.value == "finish"
    
    def test_gesture_enum(self):
        """Test Gesture enum has all gestures."""
        assert Gesture.NEUTRAL.value == "neutral"
        assert Gesture.NOD.value == "nod"
        assert Gesture.TURN_LEFT.value == "turn_left"
        assert Gesture.TURN_RIGHT.value == "turn_right"
        assert Gesture.EXCITED.value == "excited"
        assert Gesture.CONCERNED.value == "concerned"


class TestEventDataClasses:
    """Test event dataclasses."""
    
    def test_race_event_creation(self):
        """Test RaceEvent base class creation."""
        now = datetime.now()
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=now,
            data={"driver": "Hamilton"}
        )
        assert event.event_type == EventType.OVERTAKE
        assert event.timestamp == now
        assert event.data["driver"] == "Hamilton"
    
    def test_overtake_event_creation(self):
        """Test OvertakeEvent creation."""
        now = datetime.now()
        event = OvertakeEvent(
            overtaking_driver="Hamilton",
            overtaken_driver="Verstappen",
            new_position=1,
            lap_number=10,
            timestamp=now
        )
        assert event.overtaking_driver == "Hamilton"
        assert event.overtaken_driver == "Verstappen"
        assert event.new_position == 1
        assert event.lap_number == 10
    
    def test_pit_stop_event_creation(self):
        """Test PitStopEvent creation."""
        now = datetime.now()
        event = PitStopEvent(
            driver="Leclerc",
            pit_count=2,
            pit_duration=2.3,
            tire_compound="soft",
            lap_number=25,
            timestamp=now
        )
        assert event.driver == "Leclerc"
        assert event.pit_count == 2
        assert event.pit_duration == 2.3
        assert event.tire_compound == "soft"
    
    def test_lead_change_event_creation(self):
        """Test LeadChangeEvent creation."""
        now = datetime.now()
        event = LeadChangeEvent(
            new_leader="Verstappen",
            old_leader="Hamilton",
            lap_number=15,
            timestamp=now
        )
        assert event.new_leader == "Verstappen"
        assert event.old_leader == "Hamilton"
    
    def test_fastest_lap_event_creation(self):
        """Test FastestLapEvent creation."""
        now = datetime.now()
        event = FastestLapEvent(
            driver="Norris",
            lap_time=78.456,
            lap_number=30,
            timestamp=now
        )
        assert event.driver == "Norris"
        assert event.lap_time == 78.456
    
    def test_incident_event_creation(self):
        """Test IncidentEvent creation."""
        now = datetime.now()
        event = IncidentEvent(
            description="Collision at Turn 1",
            drivers_involved=["Alonso", "Stroll"],
            lap_number=5,
            timestamp=now
        )
        assert event.description == "Collision at Turn 1"
        assert len(event.drivers_involved) == 2
    
    def test_safety_car_event_creation(self):
        """Test SafetyCarEvent creation."""
        now = datetime.now()
        event = SafetyCarEvent(
            status="deployed",
            reason="Debris on track",
            lap_number=20,
            timestamp=now
        )
        assert event.status == "deployed"
        assert event.reason == "Debris on track"


class TestRaceStateModels:
    """Test race state data models."""
    
    def test_driver_state_creation(self):
        """Test DriverState creation with defaults."""
        driver = DriverState(name="Hamilton", position=1)
        assert driver.name == "Hamilton"
        assert driver.position == 1
        assert driver.gap_to_leader == 0.0
        assert driver.pit_count == 0
        assert driver.current_tire == "unknown"
    
    def test_driver_state_with_all_fields(self):
        """Test DriverState with all fields populated."""
        driver = DriverState(
            name="Verstappen",
            position=2,
            gap_to_leader=3.5,
            gap_to_ahead=3.5,
            pit_count=1,
            current_tire="medium",
            last_lap_time=79.123
        )
        assert driver.gap_to_leader == 3.5
        assert driver.pit_count == 1
        assert driver.current_tire == "medium"
    
    def test_race_state_creation(self):
        """Test RaceState creation with defaults."""
        state = RaceState()
        assert len(state.drivers) == 0
        assert state.current_lap == 0
        assert state.race_phase == RacePhase.START
        assert not state.safety_car_active
    
    def test_race_state_get_driver(self):
        """Test RaceState.get_driver method."""
        driver1 = DriverState(name="Hamilton", position=1)
        driver2 = DriverState(name="Verstappen", position=2)
        state = RaceState(drivers=[driver1, driver2])
        
        found = state.get_driver("Hamilton")
        assert found is not None
        assert found.name == "Hamilton"
        
        not_found = state.get_driver("Nonexistent")
        assert not_found is None
    
    def test_race_state_get_leader(self):
        """Test RaceState.get_leader method."""
        driver1 = DriverState(name="Hamilton", position=2)
        driver2 = DriverState(name="Verstappen", position=1)
        driver3 = DriverState(name="Leclerc", position=3)
        state = RaceState(drivers=[driver1, driver2, driver3])
        
        leader = state.get_leader()
        assert leader is not None
        assert leader.name == "Verstappen"
        assert leader.position == 1
    
    def test_race_state_get_leader_empty(self):
        """Test RaceState.get_leader with no drivers."""
        state = RaceState()
        leader = state.get_leader()
        assert leader is None
    
    def test_race_state_get_positions(self):
        """Test RaceState.get_positions returns sorted list."""
        driver1 = DriverState(name="Hamilton", position=3)
        driver2 = DriverState(name="Verstappen", position=1)
        driver3 = DriverState(name="Leclerc", position=2)
        state = RaceState(drivers=[driver1, driver2, driver3])
        
        positions = state.get_positions()
        assert len(positions) == 3
        assert positions[0].name == "Verstappen"
        assert positions[1].name == "Leclerc"
        assert positions[2].name == "Hamilton"


class TestConfig:
    """Test configuration data model."""
    
    def test_config_defaults(self):
        """Test Config has sensible defaults."""
        config = Config()
        assert config.openf1_base_url == "https://api.openf1.org/v1"
        assert config.position_poll_interval == 1.0
        assert config.max_queue_size == 10
        assert config.audio_volume == 0.8
        assert config.movement_speed == 30.0
        assert config.log_level == "INFO"
        assert not config.replay_mode
    
    def test_config_custom_values(self):
        """Test Config with custom values."""
        config = Config(
            openf1_api_key="test_key",
            elevenlabs_api_key="test_elevenlabs",
            ai_enabled=True,
            max_queue_size=20,
            replay_mode=True
        )
        assert config.openf1_api_key == "test_key"
        assert config.ai_enabled is True
        assert config.max_queue_size == 20
        assert config.replay_mode is True
