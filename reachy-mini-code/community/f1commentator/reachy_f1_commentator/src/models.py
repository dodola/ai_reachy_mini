"""
Core data models and types for the F1 Commentary Robot.

This module defines all enumerations, dataclasses, and type definitions
used throughout the system for race events, state tracking, and configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ============================================================================
# Enumerations
# ============================================================================

class EventType(Enum):
    """Types of race events that can be detected."""
    OVERTAKE = "overtake"
    PIT_STOP = "pit_stop"
    LEAD_CHANGE = "lead_change"
    FASTEST_LAP = "fastest_lap"
    INCIDENT = "incident"
    FLAG = "flag"
    SAFETY_CAR = "safety_car"
    POSITION_UPDATE = "position_update"


class EventPriority(Enum):
    """Priority levels for event queue processing."""
    CRITICAL = 1  # Incidents, safety car, lead changes
    HIGH = 2      # Overtakes, pit stops
    MEDIUM = 3    # Fastest laps
    LOW = 4       # Routine position updates


class RacePhase(Enum):
    """Distinct periods of a race."""
    START = "start"        # Laps 1-3
    MID_RACE = "mid_race"  # Laps 4 to final-5
    FINISH = "finish"      # Final 5 laps


class Gesture(Enum):
    """Robot head movement gestures."""
    NEUTRAL = "neutral"
    NOD = "nod"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    EXCITED = "excited"      # Quick nod + turn
    CONCERNED = "concerned"  # Slow tilt


# ============================================================================
# Base Event Classes
# ============================================================================

@dataclass
class RaceEvent:
    """Base class for all race events."""
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Specific Event Classes
# ============================================================================

@dataclass
class OvertakeEvent:
    """Event representing a driver overtaking another driver."""
    overtaking_driver: str
    overtaken_driver: str
    new_position: int
    lap_number: int
    timestamp: datetime


@dataclass
class PitStopEvent:
    """Event representing a driver pit stop."""
    driver: str
    pit_count: int
    pit_duration: float
    tire_compound: str
    lap_number: int
    timestamp: datetime


@dataclass
class LeadChangeEvent:
    """Event representing a change in race leader."""
    new_leader: str
    old_leader: str
    lap_number: int
    timestamp: datetime


@dataclass
class FastestLapEvent:
    """Event representing a new fastest lap."""
    driver: str
    lap_time: float
    lap_number: int
    timestamp: datetime


@dataclass
class IncidentEvent:
    """Event representing a race incident."""
    description: str
    drivers_involved: List[str]
    lap_number: int
    timestamp: datetime


@dataclass
class SafetyCarEvent:
    """Event representing safety car deployment or withdrawal."""
    status: str  # "deployed", "in", "ending"
    reason: str
    lap_number: int
    timestamp: datetime


@dataclass
class FlagEvent:
    """Event representing flag deployment."""
    flag_type: str  # "yellow", "red", "green", "blue"
    sector: Optional[str]
    lap_number: int
    timestamp: datetime


@dataclass
class PositionUpdateEvent:
    """Event representing routine position update."""
    positions: Dict[str, int]  # driver_name -> position
    lap_number: int
    timestamp: datetime


# ============================================================================
# Race State Data Models
# ============================================================================

@dataclass
class DriverState:
    """State information for a single driver during a race."""
    name: str
    position: int
    gap_to_leader: float = 0.0
    gap_to_ahead: float = 0.0
    pit_count: int = 0
    current_tire: str = "unknown"
    last_lap_time: float = 0.0


@dataclass
class RaceState:
    """Complete race state including all drivers and race metadata."""
    drivers: List[DriverState] = field(default_factory=list)
    current_lap: int = 0
    total_laps: int = 0
    race_phase: RacePhase = RacePhase.START
    fastest_lap_driver: Optional[str] = None
    fastest_lap_time: Optional[float] = None
    safety_car_active: bool = False
    flags: List[str] = field(default_factory=list)
    
    def get_driver(self, driver_name: str) -> Optional[DriverState]:
        """Get driver state by name."""
        for driver in self.drivers:
            if driver.name == driver_name:
                return driver
        return None
    
    def get_leader(self) -> Optional[DriverState]:
        """Get the current race leader."""
        if not self.drivers:
            return None
        return min(self.drivers, key=lambda d: d.position)
    
    def get_positions(self) -> List[DriverState]:
        """Get drivers sorted by position."""
        return sorted(self.drivers, key=lambda d: d.position)


# ============================================================================
# Configuration Data Model
# ============================================================================

@dataclass
class Config:
    """System configuration parameters."""
    # OpenF1 API
    openf1_api_key: str = ""
    openf1_base_url: str = "https://api.openf1.org/v1"
    
    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    
    # AI Enhancement (optional)
    ai_enabled: bool = False
    ai_provider: str = "openai"  # "openai", "huggingface", "none"
    ai_api_key: Optional[str] = None
    ai_model: str = "gpt-3.5-turbo"
    
    # Polling intervals (seconds)
    position_poll_interval: float = 1.0
    laps_poll_interval: float = 2.0
    pit_poll_interval: float = 1.0
    race_control_poll_interval: float = 1.0
    
    # Event queue
    max_queue_size: int = 10
    
    # Audio
    audio_volume: float = 0.8
    
    # Motion
    movement_speed: float = 30.0  # degrees/second
    enable_movements: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/f1_commentary.log"
    
    # Mode
    replay_mode: bool = False
    replay_race_id: Optional[str] = None
    replay_speed: float = 1.0
