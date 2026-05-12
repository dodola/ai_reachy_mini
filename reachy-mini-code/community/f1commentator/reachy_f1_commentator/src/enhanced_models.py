"""
Enhanced data models for organic F1 commentary generation.

This module defines all dataclasses and enumerations used by the enhanced
commentary system for context enrichment, event prioritization, narrative
tracking, style management, template selection, and phrase combination.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from reachy_f1_commentator.src.models import RaceEvent, RaceState


# ============================================================================
# Enumerations
# ============================================================================

class ExcitementLevel(Enum):
    """Excitement levels for commentary style."""
    CALM = 0.1  # Routine events, stable racing
    MODERATE = 0.3  # Minor position changes, routine pits
    ENGAGED = 0.5  # Interesting overtakes, strategy plays
    EXCITED = 0.7  # Top-5 battles, lead challenges
    DRAMATIC = 0.9  # Lead changes, incidents, championship moments


class CommentaryPerspective(Enum):
    """Commentary perspective types."""
    TECHNICAL = "technical"  # Sector times, telemetry, speeds
    STRATEGIC = "strategic"  # Tire strategy, pit windows, undercuts
    DRAMATIC = "dramatic"  # Battles, emotions, narratives
    POSITIONAL = "positional"  # Championship impact, standings
    HISTORICAL = "historical"  # Records, comparisons, "first time"


class NarrativeType(Enum):
    """Types of narrative threads."""
    BATTLE = "battle"  # Two drivers within 2s for 3+ laps
    COMEBACK = "comeback"  # Driver gaining 3+ positions in 10 laps
    STRATEGY_DIVERGENCE = "strategy"  # Different tire strategies
    CHAMPIONSHIP_FIGHT = "championship"  # Close championship battle
    UNDERCUT_ATTEMPT = "undercut"  # Pit stop undercut strategy
    OVERCUT_ATTEMPT = "overcut"  # Staying out longer strategy


# ============================================================================
# Context Data Models
# ============================================================================

@dataclass
class ContextData:
    """
    Enriched context data from multiple OpenF1 endpoints.
    
    This dataclass contains all available context information for a race event,
    gathered from telemetry, gaps, laps, tires, weather, and championship data.
    """
    # Core event data
    event: RaceEvent
    race_state: RaceState
    
    # Telemetry data (from car_data endpoint)
    speed: Optional[float] = None
    throttle: Optional[float] = None
    brake: Optional[float] = None
    drs_active: Optional[bool] = None
    rpm: Optional[int] = None
    gear: Optional[int] = None
    
    # Gap data (from intervals endpoint)
    gap_to_leader: Optional[float] = None
    gap_to_ahead: Optional[float] = None
    gap_to_behind: Optional[float] = None
    gap_trend: Optional[str] = None  # "closing", "stable", "increasing"
    
    # Lap data (from laps endpoint)
    sector_1_time: Optional[float] = None
    sector_2_time: Optional[float] = None
    sector_3_time: Optional[float] = None
    sector_1_status: Optional[str] = None  # "purple", "green", "yellow", "white"
    sector_2_status: Optional[str] = None
    sector_3_status: Optional[str] = None
    speed_trap: Optional[float] = None
    
    # Tire data (from stints endpoint)
    current_tire_compound: Optional[str] = None
    current_tire_age: Optional[int] = None
    previous_tire_compound: Optional[str] = None
    previous_tire_age: Optional[int] = None
    tire_age_differential: Optional[int] = None  # vs opponent in overtake
    
    # Pit data (from pit endpoint)
    pit_duration: Optional[float] = None
    pit_lane_time: Optional[float] = None
    pit_count: int = 0
    
    # Weather data (from weather endpoint)
    air_temp: Optional[float] = None
    track_temp: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[int] = None
    
    # Championship data (from championship_drivers endpoint)
    driver_championship_position: Optional[int] = None
    driver_championship_points: Optional[int] = None
    championship_gap_to_leader: Optional[int] = None
    is_championship_contender: bool = False  # Top 5 in standings
    
    # Position data (from position endpoint)
    position_before: Optional[int] = None
    position_after: Optional[int] = None
    positions_gained: Optional[int] = None
    
    # Narrative context
    active_narratives: List[str] = field(default_factory=list)
    
    # Metadata
    enrichment_time_ms: float = 0.0
    missing_data_sources: List[str] = field(default_factory=list)


# ============================================================================
# Event Prioritization Models
# ============================================================================

@dataclass
class SignificanceScore:
    """
    Significance score for an event with breakdown of components.
    
    Used by Event_Prioritizer to determine which events warrant commentary.
    """
    base_score: int  # 0-100 based on event type and position
    context_bonus: int  # Bonus from context (championship, narrative, etc.)
    total_score: int  # base_score + context_bonus (capped at 100)
    reasons: List[str] = field(default_factory=list)  # Explanation of score components


# ============================================================================
# Narrative Tracking Models
# ============================================================================

@dataclass
class NarrativeThread:
    """
    Represents an ongoing race narrative (battle, comeback, strategy).
    
    Used by Narrative_Tracker to maintain story threads across multiple laps.
    """
    narrative_id: str
    narrative_type: NarrativeType
    drivers_involved: List[str]
    start_lap: int
    last_update_lap: int
    context_data: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


# ============================================================================
# Commentary Style Models
# ============================================================================

@dataclass
class CommentaryStyle:
    """
    Commentary style parameters for a specific event.
    
    Used by Commentary_Style_Manager to determine tone and perspective.
    """
    excitement_level: ExcitementLevel
    perspective: CommentaryPerspective
    include_technical_detail: bool = False
    include_narrative_reference: bool = False
    include_championship_context: bool = False


# ============================================================================
# Template Models
# ============================================================================

@dataclass
class Template:
    """
    Commentary template with metadata and requirements.
    
    Used by Template_Selector to choose appropriate templates based on context.
    """
    template_id: str
    event_type: str  # "overtake", "pit_stop", "fastest_lap", etc.
    excitement_level: str  # "calm", "moderate", "engaged", "excited", "dramatic"
    perspective: str  # "technical", "strategic", "dramatic", "positional", "historical"
    template_text: str
    required_placeholders: List[str] = field(default_factory=list)
    optional_placeholders: List[str] = field(default_factory=list)
    context_requirements: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Enhanced Event Models
# ============================================================================

@dataclass
class EnhancedRaceEvent:
    """
    Extended race event with enriched context and metadata.
    
    Combines base event with all enrichment data for commentary generation.
    """
    base_event: RaceEvent
    context: ContextData
    significance: SignificanceScore
    style: CommentaryStyle
    narratives: List[NarrativeThread] = field(default_factory=list)


# ============================================================================
# Commentary Output Models
# ============================================================================

@dataclass
class CommentaryOutput:
    """
    Generated commentary with metadata and timing information.
    
    Contains the final commentary text along with all metadata about
    how it was generated for debugging and monitoring.
    """
    text: str
    event: EnhancedRaceEvent
    template_used: Optional[Template] = None
    generation_time_ms: float = 0.0
    context_enrichment_time_ms: float = 0.0
    missing_data: List[str] = field(default_factory=list)
