"""
Placeholder Resolver for Enhanced Commentary System.

This module provides placeholder resolution for commentary templates,
converting template placeholders into formatted values based on context data.

Validates: Requirements 10.2
"""

import logging
from typing import Optional

from reachy_f1_commentator.src.enhanced_models import ContextData
from reachy_f1_commentator.src.openf1_data_cache import OpenF1DataCache


logger = logging.getLogger(__name__)


class PlaceholderResolver:
    """
    Resolves template placeholders to formatted values.
    
    Handles all placeholder types including driver names, positions, times,
    gaps, tire data, weather, speeds, and narrative references.
    
    Validates: Requirements 10.2
    """
    
    def __init__(self, data_cache: OpenF1DataCache):
        """
        Initialize placeholder resolver.
        
        Args:
            data_cache: OpenF1 data cache for driver info and other static data
        """
        self.data_cache = data_cache
        logger.debug("PlaceholderResolver initialized")
    
    def resolve(self, placeholder: str, context: ContextData) -> Optional[str]:
        """
        Resolve a single placeholder to its value.
        
        Args:
            placeholder: Placeholder name (e.g., "driver1", "gap", "tire_compound")
            context: Context data containing all available information
            
        Returns:
            Formatted string value if placeholder can be resolved, None otherwise
        """
        # Remove curly braces if present
        placeholder = placeholder.strip('{}')
        
        try:
            # Driver placeholders
            if placeholder in ["driver1", "driver"]:
                return self._resolve_driver_name(context.event.driver, context)
            elif placeholder == "driver2":
                # For overtake events, get the overtaken driver
                if hasattr(context.event, 'overtaken_driver'):
                    return self._resolve_driver_name(context.event.overtaken_driver, context)
                return None
            
            # Pronoun placeholders
            elif placeholder in ["pronoun", "pronoun1"]:
                return self._resolve_pronoun(context.event.driver)
            elif placeholder == "pronoun2":
                if hasattr(context.event, 'overtaken_driver'):
                    return self._resolve_pronoun(context.event.overtaken_driver)
                return None
            
            # Team placeholders
            elif placeholder in ["team1", "team"]:
                return self._resolve_team_name(context.event.driver)
            elif placeholder == "team2":
                if hasattr(context.event, 'overtaken_driver'):
                    return self._resolve_team_name(context.event.overtaken_driver)
                return None
            
            # Position placeholders
            elif placeholder == "position":
                if context.position_after is not None:
                    return self._resolve_position(context.position_after)
                return None
            elif placeholder == "position_before":
                if context.position_before is not None:
                    return self._resolve_position(context.position_before)
                return None
            elif placeholder == "positions_gained":
                if context.positions_gained is not None:
                    return str(context.positions_gained)
                return None
            
            # Gap placeholders
            elif placeholder == "gap":
                if context.gap_to_leader is not None:
                    return self._resolve_gap(context.gap_to_leader)
                elif context.gap_to_ahead is not None:
                    return self._resolve_gap(context.gap_to_ahead)
                return None
            elif placeholder == "gap_to_leader":
                if context.gap_to_leader is not None:
                    return self._resolve_gap(context.gap_to_leader)
                return None
            elif placeholder == "gap_to_ahead":
                if context.gap_to_ahead is not None:
                    return self._resolve_gap(context.gap_to_ahead)
                return None
            elif placeholder == "gap_trend":
                return context.gap_trend
            
            # Time placeholders
            elif placeholder == "lap_time":
                if hasattr(context.event, 'lap_time') and context.event.lap_time:
                    return self._resolve_lap_time(context.event.lap_time)
                return None
            elif placeholder == "sector_1_time":
                if context.sector_1_time is not None:
                    return self._resolve_sector_time(context.sector_1_time)
                return None
            elif placeholder == "sector_2_time":
                if context.sector_2_time is not None:
                    return self._resolve_sector_time(context.sector_2_time)
                return None
            elif placeholder == "sector_3_time":
                if context.sector_3_time is not None:
                    return self._resolve_sector_time(context.sector_3_time)
                return None
            
            # Sector status placeholders
            elif placeholder == "sector_status":
                # Return the best sector status available
                if context.sector_1_status == "purple":
                    return "purple sector in sector 1"
                elif context.sector_2_status == "purple":
                    return "purple sector in sector 2"
                elif context.sector_3_status == "purple":
                    return "purple sector in sector 3"
                return None
            
            # Tire placeholders
            elif placeholder == "tire_compound":
                if context.current_tire_compound:
                    return self._resolve_tire_compound(context.current_tire_compound)
                return None
            elif placeholder == "tire_age":
                if context.current_tire_age is not None:
                    return f"{context.current_tire_age} laps old"
                return None
            elif placeholder == "tire_age_diff":
                if context.tire_age_differential is not None:
                    return str(abs(context.tire_age_differential))
                return None
            elif placeholder == "new_tire_compound":
                if context.current_tire_compound:
                    return self._resolve_tire_compound(context.current_tire_compound)
                return None
            elif placeholder == "old_tire_compound":
                if context.previous_tire_compound:
                    return self._resolve_tire_compound(context.previous_tire_compound)
                return None
            elif placeholder == "old_tire_age":
                if context.previous_tire_age is not None:
                    return f"{context.previous_tire_age} laps"
                return None
            
            # Speed placeholders
            elif placeholder == "speed":
                if context.speed is not None:
                    return self._resolve_speed(context.speed)
                return None
            elif placeholder == "speed_trap":
                if context.speed_trap is not None:
                    return self._resolve_speed(context.speed_trap)
                return None
            
            # DRS placeholder
            elif placeholder == "drs_status":
                if context.drs_active:
                    return "with DRS"
                return ""
            
            # Weather placeholders
            elif placeholder == "track_temp":
                if context.track_temp is not None:
                    return f"{context.track_temp:.1f}°C"
                return None
            elif placeholder == "air_temp":
                if context.air_temp is not None:
                    return f"{context.air_temp:.1f}°C"
                return None
            elif placeholder == "weather_condition":
                return self._resolve_weather_condition(context)
            
            # Pit stop placeholders
            elif placeholder == "pit_duration":
                if context.pit_duration is not None:
                    return f"{context.pit_duration:.1f} seconds"
                return None
            elif placeholder == "pit_count":
                return str(context.pit_count)
            
            # Narrative placeholders
            elif placeholder == "narrative_reference":
                return self._resolve_narrative_reference(context)
            elif placeholder == "battle_laps":
                # Extract from narrative context if available
                for narrative_id in context.active_narratives:
                    if "battle" in narrative_id.lower():
                        # Try to extract lap count from narrative
                        # This would need to be enhanced with actual narrative data
                        return "several"
                return None
            elif placeholder == "positions_gained_total":
                if context.positions_gained is not None:
                    return str(context.positions_gained)
                return None
            
            # Championship placeholders
            elif placeholder == "championship_position":
                if context.driver_championship_position is not None:
                    return self._resolve_championship_position(context.driver_championship_position)
                return None
            elif placeholder == "championship_gap":
                if context.championship_gap_to_leader is not None:
                    return f"{context.championship_gap_to_leader} points"
                return None
            elif placeholder == "championship_context":
                return self._resolve_championship_context(context)
            
            # Unknown placeholder
            else:
                logger.warning(f"Unknown placeholder: {placeholder}")
                return None
                
        except Exception as e:
            logger.error(f"Error resolving placeholder '{placeholder}': {e}")
            return None
    
    def _resolve_driver_name(self, driver_identifier: str, context: ContextData) -> str:
        """
        Resolve driver name to last name only for brevity.
        
        Args:
            driver_identifier: Driver identifier (name, number, or acronym)
            context: Context data
            
        Returns:
            Driver's last name, or identifier if not found
        """
        # Try to get driver info from cache
        driver_info = self.data_cache.get_driver_info(driver_identifier)
        
        if driver_info and driver_info.last_name:
            return driver_info.last_name
        
        # Fallback: return the identifier as-is
        return str(driver_identifier)
    
    def _resolve_pronoun(self, driver_identifier: str) -> str:
        """
        Resolve pronoun (he/she) for driver.
        
        Note: Currently defaults to "he" as gender information is not
        available in OpenF1 API. This could be enhanced with a manual
        mapping if needed.
        
        Args:
            driver_identifier: Driver identifier
            
        Returns:
            Pronoun string ("he" or "she")
        """
        # TODO: Add gender mapping if needed
        # For now, default to "he" as most F1 drivers are male
        # This could be enhanced with a configuration mapping
        return "he"
    
    def _resolve_team_name(self, driver_identifier: str) -> Optional[str]:
        """
        Resolve team name for driver.
        
        Args:
            driver_identifier: Driver identifier
            
        Returns:
            Team name if found, None otherwise
        """
        driver_info = self.data_cache.get_driver_info(driver_identifier)
        
        if driver_info and driver_info.team_name:
            return driver_info.team_name
        
        return None
    
    def _resolve_gap(self, gap_seconds: float) -> str:
        """
        Format gap appropriately based on size.
        
        Rules:
        - Under 1s: "0.8 seconds" (one decimal)
        - 1-10s: "2.3 seconds" (one decimal)
        - Over 10s: "15 seconds" (nearest second)
        
        Args:
            gap_seconds: Gap in seconds
            
        Returns:
            Formatted gap string
        """
        if gap_seconds < 1.0:
            return f"{gap_seconds:.1f} seconds"
        elif gap_seconds < 10.0:
            return f"{gap_seconds:.1f} seconds"
        else:
            return f"{int(round(gap_seconds))} seconds"
    
    def _resolve_tire_compound(self, compound: str) -> str:
        """
        Format tire compound name.
        
        Ensures lowercase and correct terminology.
        
        Args:
            compound: Tire compound (SOFT, MEDIUM, HARD, INTERMEDIATE, WET)
            
        Returns:
            Formatted compound name (lowercase)
        """
        compound_lower = compound.lower()
        
        # Map common variations to standard names
        compound_map = {
            "soft": "soft",
            "medium": "medium",
            "hard": "hard",
            "intermediate": "intermediate",
            "inter": "intermediate",
            "wet": "wet",
            "wets": "wet"
        }
        
        return compound_map.get(compound_lower, compound_lower)
    
    def _resolve_position(self, position: int) -> str:
        """
        Format position as P1, P2, etc.
        
        Args:
            position: Position number
            
        Returns:
            Formatted position string
        """
        return f"P{position}"
    
    def _resolve_sector_time(self, sector_time: float) -> str:
        """
        Format sector time.
        
        Args:
            sector_time: Sector time in seconds
            
        Returns:
            Formatted sector time (e.g., "23.456")
        """
        return f"{sector_time:.3f}"
    
    def _resolve_lap_time(self, lap_time: float) -> str:
        """
        Format lap time.
        
        Args:
            lap_time: Lap time in seconds
            
        Returns:
            Formatted lap time (e.g., "1:23.456")
        """
        minutes = int(lap_time // 60)
        seconds = lap_time % 60
        return f"{minutes}:{seconds:06.3f}"
    
    def _resolve_speed(self, speed_kmh: float) -> str:
        """
        Format speed in km/h.
        
        Args:
            speed_kmh: Speed in kilometers per hour
            
        Returns:
            Formatted speed string (e.g., "315 kilometers per hour")
        """
        return f"{int(round(speed_kmh))} kilometers per hour"
    
    def _resolve_weather_condition(self, context: ContextData) -> Optional[str]:
        """
        Generate weather condition phrase.
        
        Creates appropriate phrases based on weather data:
        - "in these conditions" (general)
        - "as the track heats up" (rising temperature)
        - "with the wind picking up" (high wind)
        - "in the wet conditions" (rain)
        
        Args:
            context: Context data with weather information
            
        Returns:
            Weather phrase if conditions are notable, None otherwise
        """
        phrases = []
        
        # Check for rain
        if context.rainfall is not None and context.rainfall > 0:
            return "in the wet conditions"
        
        # Check for high wind
        if context.wind_speed is not None and context.wind_speed > 20:
            phrases.append("with the wind picking up")
        
        # Check for high track temperature
        if context.track_temp is not None and context.track_temp > 45:
            phrases.append("as the track heats up")
        
        # Check for high humidity
        if context.humidity is not None and context.humidity > 70:
            phrases.append("in these challenging conditions")
        
        # Return first phrase if any, otherwise generic phrase
        if phrases:
            return phrases[0]
        
        # If weather data exists but nothing notable, return generic phrase
        if context.track_temp is not None or context.air_temp is not None:
            return "in these conditions"
        
        return None
    
    def _resolve_narrative_reference(self, context: ContextData) -> Optional[str]:
        """
        Generate narrative reference phrase.
        
        Creates phrases based on active narratives:
        - "continuing their battle"
        - "on his comeback drive"
        - "with the different tire strategies"
        
        Args:
            context: Context data with active narratives
            
        Returns:
            Narrative phrase if narratives are active, None otherwise
        """
        if not context.active_narratives:
            return None
        
        # Get the first active narrative
        narrative_id = context.active_narratives[0]
        
        # Generate phrase based on narrative type
        if "battle" in narrative_id.lower():
            return "continuing their battle"
        elif "comeback" in narrative_id.lower():
            return "on his comeback drive"
        elif "strategy" in narrative_id.lower():
            return "with the different tire strategies"
        elif "undercut" in narrative_id.lower():
            return "attempting the undercut"
        elif "overcut" in narrative_id.lower():
            return "going for the overcut"
        elif "championship" in narrative_id.lower():
            return "in the championship fight"
        
        # Generic fallback
        return "as the story unfolds"
    
    def _resolve_championship_context(self, context: ContextData) -> Optional[str]:
        """
        Generate championship context phrase.
        
        Creates phrases based on championship position:
        - "the championship leader"
        - "second in the standings"
        - "fighting for third in the championship"
        
        Args:
            context: Context data with championship information
            
        Returns:
            Championship phrase if position is known, None otherwise
        """
        if context.driver_championship_position is None:
            return None
        
        position = context.driver_championship_position
        
        if position == 1:
            return "the championship leader"
        elif position == 2:
            return "second in the standings"
        elif position == 3:
            return "third in the championship"
        elif position <= 5:
            return f"{self._ordinal(position)} in the championship"
        elif position <= 10:
            return f"fighting for {self._ordinal(position)} in the championship"
        else:
            return None
    
    def _resolve_championship_position(self, position: int) -> str:
        """
        Format championship position.
        
        Args:
            position: Championship position
            
        Returns:
            Formatted position (e.g., "1st", "2nd", "3rd")
        """
        return self._ordinal(position)
    
    def _ordinal(self, n: int) -> str:
        """
        Convert number to ordinal string.
        
        Args:
            n: Number
            
        Returns:
            Ordinal string (e.g., "1st", "2nd", "3rd", "4th")
        """
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"
