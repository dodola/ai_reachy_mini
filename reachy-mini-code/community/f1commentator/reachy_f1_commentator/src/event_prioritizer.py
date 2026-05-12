"""
Event prioritization for organic F1 commentary generation.

This module implements the Event_Prioritizer component that assigns significance
scores to race events and filters out low-priority events to focus commentary
on important moments.
"""

from typing import Optional

from reachy_f1_commentator.src.enhanced_models import ContextData, SignificanceScore
from reachy_f1_commentator.src.models import EventType, RaceEvent


class SignificanceCalculator:
    """
    Calculates significance scores for race events.
    
    Assigns base scores based on event type and position, then applies
    context bonuses for championship contenders, narratives, close gaps,
    tire differentials, and other factors.
    """
    
    def __init__(self):
        """Initialize the significance calculator."""
        pass
    
    def calculate_significance(
        self,
        event: RaceEvent,
        context: ContextData
    ) -> SignificanceScore:
        """
        Calculate significance score for an event with context.
        
        Args:
            event: The race event to score
            context: Enriched context data for the event
            
        Returns:
            SignificanceScore with base score, bonuses, and total
        """
        # Calculate base score
        base_score = self._base_score_for_event(event, context)
        
        # Apply context bonuses
        context_bonus, reasons = self._apply_context_bonuses(context)
        
        # Calculate total (capped at 100)
        total_score = min(base_score + context_bonus, 100)
        
        # Build reasons list
        all_reasons = [f"Base score: {base_score}"]
        all_reasons.extend(reasons)
        
        return SignificanceScore(
            base_score=base_score,
            context_bonus=context_bonus,
            total_score=total_score,
            reasons=all_reasons
        )
    
    def _base_score_for_event(
        self,
        event: RaceEvent,
        context: ContextData
    ) -> int:
        """
        Calculate base significance score based on event type and position.
        
        Scoring rules:
        - Lead change: 100
        - Overtake P1-P3: 90
        - Overtake P4-P6: 70
        - Overtake P7-P10: 50
        - Overtake P11+: 30
        - Pit stop (leader): 80
        - Pit stop (P2-P5): 60
        - Pit stop (P6-P10): 40
        - Pit stop (P11+): 20
        - Fastest lap (leader): 70
        - Fastest lap (other): 50
        - Incident: 95
        - Safety car: 100
        
        Args:
            event: The race event
            context: Context data with position information
            
        Returns:
            Base score (0-100)
        """
        event_type = event.event_type
        
        # Lead change - highest priority
        if event_type == EventType.LEAD_CHANGE:
            return 100
        
        # Safety car - highest priority
        if event_type == EventType.SAFETY_CAR:
            return 100
        
        # Incident - very high priority
        if event_type == EventType.INCIDENT:
            return 95
        
        # Overtake - score by position
        if event_type == EventType.OVERTAKE:
            position = context.position_after
            if position is None:
                # Fallback if position not available
                return 50
            
            if position <= 3:
                return 90
            elif position <= 6:
                return 70
            elif position <= 10:
                return 50
            else:
                return 30
        
        # Pit stop - score by position
        if event_type == EventType.PIT_STOP:
            position = context.position_before
            if position is None:
                # Fallback if position not available
                return 40
            
            if position == 1:
                return 80
            elif position <= 5:
                return 60
            elif position <= 10:
                return 40
            else:
                return 20
        
        # Fastest lap - score by whether it's the leader
        if event_type == EventType.FASTEST_LAP:
            position = context.position_after or context.position_before
            if position == 1:
                return 70
            else:
                return 50
        
        # Flag events - medium priority
        if event_type == EventType.FLAG:
            return 60
        
        # Position update - low priority
        if event_type == EventType.POSITION_UPDATE:
            return 20
        
        # Default for unknown event types
        return 30
    
    def _apply_context_bonuses(
        self,
        context: ContextData
    ) -> tuple[int, list[str]]:
        """
        Apply context bonuses to base score.
        
        Bonuses:
        - Championship contender (top 5): +20
        - Active battle narrative: +15
        - Active comeback narrative: +15
        - Gap < 1s: +10
        - Tire age differential > 5 laps: +10
        - DRS available: +5
        - Purple sector: +10
        - Weather impact: +5
        - First of session: +10
        
        Args:
            context: Enriched context data
            
        Returns:
            Tuple of (total_bonus, list of reason strings)
        """
        total_bonus = 0
        reasons = []
        
        # Championship contender bonus
        if context.is_championship_contender:
            total_bonus += 20
            reasons.append("Championship contender: +20")
        
        # Battle narrative bonus
        if any("battle" in narrative.lower() for narrative in context.active_narratives):
            total_bonus += 15
            reasons.append("Battle narrative: +15")
        
        # Comeback narrative bonus
        if any("comeback" in narrative.lower() for narrative in context.active_narratives):
            total_bonus += 15
            reasons.append("Comeback narrative: +15")
        
        # Close gap bonus
        if context.gap_to_ahead is not None and context.gap_to_ahead < 1.0:
            total_bonus += 10
            reasons.append("Gap < 1s: +10")
        
        # Tire age differential bonus
        if context.tire_age_differential is not None and context.tire_age_differential > 5:
            total_bonus += 10
            reasons.append(f"Tire age diff > 5 laps: +10")
        
        # DRS bonus
        if context.drs_active:
            total_bonus += 5
            reasons.append("DRS active: +5")
        
        # Purple sector bonus
        if (context.sector_1_status == "purple" or 
            context.sector_2_status == "purple" or 
            context.sector_3_status == "purple"):
            total_bonus += 10
            reasons.append("Purple sector: +10")
        
        # Weather impact bonus
        if self._has_weather_impact(context):
            total_bonus += 5
            reasons.append("Weather impact: +5")
        
        # First of session bonus (check pit_count for first pit)
        if context.pit_count == 1:
            total_bonus += 10
            reasons.append("First pit stop: +10")
        
        return total_bonus, reasons
    
    def _has_weather_impact(self, context: ContextData) -> bool:
        """
        Determine if weather conditions are impactful.
        
        Weather is considered impactful if:
        - Rainfall > 0
        - Wind speed > 20 km/h
        - Track temperature change > 5°C (would need historical tracking)
        
        Args:
            context: Context data with weather information
            
        Returns:
            True if weather is impactful
        """
        # Rainfall
        if context.rainfall is not None and context.rainfall > 0:
            return True
        
        # High wind
        if context.wind_speed is not None and context.wind_speed > 20:
            return True
        
        # Note: Temperature change tracking would require historical data
        # which is not available in the current context. This could be
        # added in the future by tracking temperature over time.
        
        return False



class EventPrioritizer:
    """
    Event prioritizer that filters events by significance.
    
    Determines which events warrant commentary based on significance scores,
    suppresses pit-cycle position changes, and selects the highest significance
    event when multiple events occur simultaneously.
    """
    
    def __init__(self, config, race_state_tracker):
        """
        Initialize the event prioritizer.
        
        Args:
            config: Configuration object with min_significance_threshold
            race_state_tracker: Race state tracker for historical position data
        """
        self.config = config
        self.race_state_tracker = race_state_tracker
        self.significance_calculator = SignificanceCalculator()
        
        # Get threshold from config, default to 50
        self.min_threshold = getattr(
            config, 
            'min_significance_threshold', 
            50
        )
        
        # Track recent pit stops for pit-cycle detection
        # Format: {driver_number: (lap_number, position_before_pit)}
        self.recent_pit_stops: dict[str, tuple[int, int]] = {}
    
    def should_commentate(self, significance: SignificanceScore) -> bool:
        """
        Determine if an event meets the threshold for commentary.
        
        Args:
            significance: The significance score for the event
            
        Returns:
            True if the event should receive commentary
        """
        return significance.total_score >= self.min_threshold
    
    def suppress_pit_cycle_changes(
        self,
        event: RaceEvent,
        context: ContextData
    ) -> bool:
        """
        Determine if a position change should be suppressed as pit-cycle related.
        
        Pit-cycle position changes are temporary position changes that occur
        when a driver pits (drops positions) and then regains them as others pit.
        These are not interesting for commentary.
        
        Args:
            event: The race event
            context: Context data with position information
            
        Returns:
            True if the position change should be suppressed
        """
        # Only applies to overtakes and position updates
        if event.event_type not in [EventType.OVERTAKE, EventType.POSITION_UPDATE]:
            return False
        
        # Check if this is a pit-cycle position change
        return self._is_pit_cycle_position_change(event, context)
    
    def _is_pit_cycle_position_change(
        self,
        event: RaceEvent,
        context: ContextData
    ) -> bool:
        """
        Detect if a position change is due to pit cycle.
        
        A position change is pit-cycle related if:
        1. The driver recently pitted (within last 5 laps)
        2. The driver is regaining a position they held before pitting
        
        OR
        
        1. Another driver recently pitted
        2. This driver is gaining a position due to the other driver's pit
        
        Args:
            event: The race event
            context: Context data with position information
            
        Returns:
            True if this is a pit-cycle position change
        """
        # Get current lap from race state
        current_lap = context.race_state.current_lap
        
        # Get driver involved in the position change
        driver = event.data.get('driver', event.data.get('driver_number', ''))
        if not driver:
            return False
        
        # Check if this driver recently pitted
        if driver in self.recent_pit_stops:
            pit_lap, position_before_pit = self.recent_pit_stops[driver]
            
            # If pit was within last 5 laps
            if current_lap - pit_lap <= 5:
                # Check if driver is regaining their pre-pit position
                if context.position_after is not None:
                    # If current position is close to pre-pit position
                    # (within 2 positions), likely pit-cycle related
                    if abs(context.position_after - position_before_pit) <= 2:
                        return True
        
        # Check if the driver being overtaken recently pitted
        # This would indicate the overtake is due to pit cycle
        overtaken_driver = event.data.get('overtaken_driver', '')
        if overtaken_driver:
            if overtaken_driver in self.recent_pit_stops:
                pit_lap, _ = self.recent_pit_stops[overtaken_driver]
                
                # If the overtaken driver pitted within last 2 laps,
                # this overtake is likely pit-cycle related
                if current_lap - pit_lap <= 2:
                    return True
        
        return False
    
    def track_pit_stop(
        self,
        event: RaceEvent,
        context: ContextData
    ):
        """
        Track a pit stop for pit-cycle detection.
        
        Should be called whenever a pit stop event occurs.
        
        Args:
            event: The pit stop event
            context: Context data with position information
        """
        if event.event_type == EventType.PIT_STOP:
            driver = event.data.get('driver', event.data.get('driver_number', ''))
            if not driver:
                return
            
            current_lap = context.race_state.current_lap
            position_before = context.position_before or 0
            
            # Store pit stop info
            self.recent_pit_stops[driver] = (current_lap, position_before)
            
            # Clean up old pit stops (older than 10 laps)
            drivers_to_remove = []
            for d, (lap, _) in self.recent_pit_stops.items():
                if current_lap - lap > 10:
                    drivers_to_remove.append(d)
            
            for d in drivers_to_remove:
                del self.recent_pit_stops[d]
    
    def select_highest_significance(
        self,
        events_with_scores: list[tuple[RaceEvent, ContextData, SignificanceScore]]
    ) -> Optional[tuple[RaceEvent, ContextData, SignificanceScore]]:
        """
        Select the highest significance event from simultaneous events.
        
        When multiple events occur at the same time, we want to commentate
        on the most significant one.
        
        Args:
            events_with_scores: List of (event, context, significance) tuples
            
        Returns:
            The (event, context, significance) tuple with highest score,
            or None if the list is empty
        """
        if not events_with_scores:
            return None
        
        # Find the event with the highest total score
        return max(
            events_with_scores,
            key=lambda x: x[2].total_score
        )
