"""
OpenF1 Data Cache for Enhanced Commentary System.

This module provides caching for static and semi-static data from OpenF1 API
to minimize API calls and improve performance. Caches driver info, team colors,
championship standings, and tracks session-specific records.

Validates: Requirements 1.8, 8.1
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from reachy_f1_commentator.src.data_ingestion import OpenF1Client


logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class DriverInfo:
    """Driver information from OpenF1 drivers endpoint."""
    driver_number: int
    broadcast_name: str  # e.g., "L HAMILTON"
    full_name: str  # e.g., "Lewis HAMILTON"
    name_acronym: str  # e.g., "HAM"
    team_name: str
    team_colour: str  # Hex color code
    first_name: str
    last_name: str
    headshot_url: Optional[str] = None
    country_code: Optional[str] = None


@dataclass
class ChampionshipEntry:
    """Championship standings entry."""
    driver_number: int
    position: int
    points: float
    driver_name: str  # Derived from driver info


@dataclass
class SessionRecords:
    """Session-specific records tracked during a race."""
    # Fastest lap
    fastest_lap_driver: Optional[str] = None
    fastest_lap_time: Optional[float] = None
    
    # Most overtakes
    overtake_counts: Dict[str, int] = field(default_factory=dict)
    most_overtakes_driver: Optional[str] = None
    most_overtakes_count: int = 0
    
    # Longest stint
    stint_lengths: Dict[str, int] = field(default_factory=dict)  # driver -> laps on current tires
    longest_stint_driver: Optional[str] = None
    longest_stint_laps: int = 0
    
    # Fastest pit stop
    fastest_pit_driver: Optional[str] = None
    fastest_pit_duration: Optional[float] = None
    
    def update_fastest_lap(self, driver: str, lap_time: float) -> bool:
        """
        Update fastest lap record if new time is faster.
        
        Args:
            driver: Driver name
            lap_time: Lap time in seconds
            
        Returns:
            True if this is a new record, False otherwise
        """
        if self.fastest_lap_time is None or lap_time < self.fastest_lap_time:
            self.fastest_lap_driver = driver
            self.fastest_lap_time = lap_time
            logger.debug(f"New fastest lap: {driver} - {lap_time:.3f}s")
            return True
        return False
    
    def increment_overtake_count(self, driver: str) -> int:
        """
        Increment overtake count for a driver.
        
        Args:
            driver: Driver name
            
        Returns:
            New overtake count for the driver
        """
        current_count = self.overtake_counts.get(driver, 0) + 1
        self.overtake_counts[driver] = current_count
        
        # Update most overtakes record
        if current_count > self.most_overtakes_count:
            self.most_overtakes_driver = driver
            self.most_overtakes_count = current_count
            logger.debug(f"New most overtakes: {driver} - {current_count}")
        
        return current_count
    
    def update_stint_length(self, driver: str, laps: int) -> bool:
        """
        Update stint length for a driver.
        
        Args:
            driver: Driver name
            laps: Number of laps on current tires
            
        Returns:
            True if this is a new longest stint record, False otherwise
        """
        self.stint_lengths[driver] = laps
        
        if laps > self.longest_stint_laps:
            self.longest_stint_driver = driver
            self.longest_stint_laps = laps
            logger.debug(f"New longest stint: {driver} - {laps} laps")
            return True
        return False
    
    def reset_stint_length(self, driver: str) -> None:
        """
        Reset stint length for a driver (called after pit stop).
        
        Args:
            driver: Driver name
        """
        self.stint_lengths[driver] = 0
    
    def update_fastest_pit(self, driver: str, duration: float) -> bool:
        """
        Update fastest pit stop record if new duration is faster.
        
        Args:
            driver: Driver name
            duration: Pit stop duration in seconds
            
        Returns:
            True if this is a new record, False otherwise
        """
        if self.fastest_pit_duration is None or duration < self.fastest_pit_duration:
            self.fastest_pit_driver = driver
            self.fastest_pit_duration = duration
            logger.debug(f"New fastest pit: {driver} - {duration:.3f}s")
            return True
        return False


# ============================================================================
# Cache Entry with Expiration
# ============================================================================

@dataclass
class CacheEntry:
    """Cache entry with expiration tracking."""
    data: Any
    timestamp: datetime
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl_seconds


# ============================================================================
# OpenF1 Data Cache
# ============================================================================

class OpenF1DataCache:
    """
    Cache for static and semi-static OpenF1 data.
    
    Caches:
    - Driver info (names, teams, colors) - 1 hour TTL
    - Championship standings - 1 hour TTL
    - Session records (fastest lap, most overtakes, etc.) - session lifetime
    
    Validates: Requirements 1.8, 8.1
    """
    
    def __init__(self, openf1_client: OpenF1Client, config: Any):
        """
        Initialize data cache.
        
        Args:
            openf1_client: OpenF1 API client for fetching data
            config: Configuration object with cache duration settings
        """
        self.client = openf1_client
        self.config = config
        
        # Static data caches
        self.driver_info: Dict[int, DriverInfo] = {}  # driver_number -> DriverInfo
        self.driver_info_by_name: Dict[str, DriverInfo] = {}  # name -> DriverInfo
        self.team_colors: Dict[str, str] = {}  # team_name -> hex color
        self.championship_standings: List[ChampionshipEntry] = []
        
        # Cache entries with expiration
        self._driver_info_cache: Optional[CacheEntry] = None
        self._championship_cache: Optional[CacheEntry] = None
        
        # Session records (no expiration, cleared at session start)
        self.session_records = SessionRecords()
        
        # Session key for data fetching
        self._session_key: Optional[int] = None
        
        logger.info("OpenF1DataCache initialized")
    
    def set_session_key(self, session_key: int) -> None:
        """
        Set the session key for data fetching.
        
        Args:
            session_key: OpenF1 session key (e.g., 9197 for 2023 Abu Dhabi GP)
        """
        self._session_key = session_key
        logger.info(f"Session key set to: {session_key}")
    
    def load_static_data(self, session_key: Optional[int] = None) -> bool:
        """
        Load static data (driver info, team colors) at session start.
        
        Fetches from OpenF1 drivers endpoint and caches for the configured duration.
        
        Args:
            session_key: OpenF1 session key (optional, uses stored session_key if not provided)
            
        Returns:
            True if data loaded successfully, False otherwise
            
        Validates: Requirements 1.8
        """
        if session_key:
            self._session_key = session_key
        
        if not self._session_key:
            logger.error("Cannot load static data: session_key not set")
            return False
        
        # Check if cache is still valid
        if self._driver_info_cache and not self._driver_info_cache.is_expired():
            logger.debug("Driver info cache still valid, skipping reload")
            return True
        
        try:
            logger.info(f"Loading driver info for session {self._session_key}")
            
            # Fetch drivers endpoint
            params = {"session_key": self._session_key}
            drivers_data = self.client.poll_endpoint("/drivers", params)
            
            if not drivers_data:
                logger.error("Failed to fetch driver info from OpenF1 API")
                return False
            
            # Clear existing caches
            self.driver_info.clear()
            self.driver_info_by_name.clear()
            self.team_colors.clear()
            
            # Parse driver data
            for driver_data in drivers_data:
                try:
                    driver_number = driver_data.get("driver_number")
                    if not driver_number:
                        continue
                    
                    # Create DriverInfo object
                    driver = DriverInfo(
                        driver_number=driver_number,
                        broadcast_name=driver_data.get("broadcast_name", ""),
                        full_name=driver_data.get("full_name", ""),
                        name_acronym=driver_data.get("name_acronym", ""),
                        team_name=driver_data.get("team_name", ""),
                        team_colour=driver_data.get("team_colour", ""),
                        first_name=driver_data.get("first_name", ""),
                        last_name=driver_data.get("last_name", ""),
                        headshot_url=driver_data.get("headshot_url"),
                        country_code=driver_data.get("country_code")
                    )
                    
                    # Store in caches
                    self.driver_info[driver_number] = driver
                    
                    # Store by various name formats for flexible lookup
                    if driver.last_name:
                        self.driver_info_by_name[driver.last_name.upper()] = driver
                    if driver.name_acronym:
                        self.driver_info_by_name[driver.name_acronym.upper()] = driver
                    if driver.full_name:
                        self.driver_info_by_name[driver.full_name.upper()] = driver
                    
                    # Store team color
                    if driver.team_name and driver.team_colour:
                        self.team_colors[driver.team_name] = driver.team_colour
                    
                except Exception as e:
                    logger.warning(f"Failed to parse driver data: {e}")
                    continue
            
            # Create cache entry
            ttl = getattr(self.config, 'cache_duration_driver_info', 3600)
            self._driver_info_cache = CacheEntry(
                data=True,
                timestamp=datetime.now(),
                ttl_seconds=ttl
            )
            
            logger.info(f"Loaded {len(self.driver_info)} drivers, {len(self.team_colors)} teams")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load static data: {e}")
            return False
    
    def load_championship_standings(self, session_key: Optional[int] = None) -> bool:
        """
        Load championship standings at session start.
        
        Fetches from OpenF1 championship_drivers endpoint (if available).
        Note: This endpoint may not be available for all sessions.
        
        Args:
            session_key: OpenF1 session key (optional, uses stored session_key if not provided)
            
        Returns:
            True if data loaded successfully, False otherwise
            
        Validates: Requirements 1.8
        """
        if session_key:
            self._session_key = session_key
        
        if not self._session_key:
            logger.error("Cannot load championship standings: session_key not set")
            return False
        
        # Check if cache is still valid
        if self._championship_cache and not self._championship_cache.is_expired():
            logger.debug("Championship standings cache still valid, skipping reload")
            return True
        
        try:
            logger.info(f"Loading championship standings for session {self._session_key}")
            
            # Note: championship_drivers endpoint may not exist in OpenF1 API
            # This is a placeholder for when/if it becomes available
            # For now, we'll try to fetch it but gracefully handle failure
            
            params = {"session_key": self._session_key}
            standings_data = self.client.poll_endpoint("/championship_drivers", params)
            
            if not standings_data:
                logger.warning("Championship standings not available (endpoint may not exist)")
                # This is not a critical failure - championship context is optional
                return False
            
            # Clear existing standings
            self.championship_standings.clear()
            
            # Parse standings data
            for entry_data in standings_data:
                try:
                    driver_number = entry_data.get("driver_number")
                    if not driver_number:
                        continue
                    
                    # Get driver name from driver info cache
                    driver_name = ""
                    if driver_number in self.driver_info:
                        driver_name = self.driver_info[driver_number].last_name
                    
                    entry = ChampionshipEntry(
                        driver_number=driver_number,
                        position=entry_data.get("position", 0),
                        points=entry_data.get("points", 0.0),
                        driver_name=driver_name
                    )
                    
                    self.championship_standings.append(entry)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse championship entry: {e}")
                    continue
            
            # Sort by position
            self.championship_standings.sort(key=lambda x: x.position)
            
            # Create cache entry
            ttl = getattr(self.config, 'cache_duration_championship', 3600)
            self._championship_cache = CacheEntry(
                data=True,
                timestamp=datetime.now(),
                ttl_seconds=ttl
            )
            
            logger.info(f"Loaded championship standings: {len(self.championship_standings)} drivers")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load championship standings: {e}")
            # This is not a critical failure - championship context is optional
            return False
    
    def get_driver_info(self, identifier: Any) -> Optional[DriverInfo]:
        """
        Get driver info by number or name.
        
        Args:
            identifier: Driver number (int) or name (str)
            
        Returns:
            DriverInfo object if found, None otherwise
        """
        if isinstance(identifier, int):
            return self.driver_info.get(identifier)
        elif isinstance(identifier, str):
            return self.driver_info_by_name.get(identifier.upper())
        return None
    
    def get_team_color(self, team_name: str) -> Optional[str]:
        """
        Get team color hex code.
        
        Args:
            team_name: Team name
            
        Returns:
            Hex color code if found, None otherwise
        """
        return self.team_colors.get(team_name)
    
    def get_championship_position(self, driver_number: int) -> Optional[int]:
        """
        Get driver's championship position.
        
        Args:
            driver_number: Driver number
            
        Returns:
            Championship position if found, None otherwise
        """
        for entry in self.championship_standings:
            if entry.driver_number == driver_number:
                return entry.position
        return None
    
    def get_championship_points(self, driver_number: int) -> Optional[float]:
        """
        Get driver's championship points.
        
        Args:
            driver_number: Driver number
            
        Returns:
            Championship points if found, None otherwise
        """
        for entry in self.championship_standings:
            if entry.driver_number == driver_number:
                return entry.points
        return None
    
    def is_championship_contender(self, driver_number: int) -> bool:
        """
        Check if driver is a championship contender (top 5).
        
        Args:
            driver_number: Driver number
            
        Returns:
            True if driver is in top 5 of championship, False otherwise
        """
        position = self.get_championship_position(driver_number)
        return position is not None and position <= 5
    
    def update_session_records(self, event: Any) -> None:
        """
        Update session-specific records as events occur.
        
        Args:
            event: Race event (OvertakeEvent, PitStopEvent, FastestLapEvent, etc.)
            
        Validates: Requirements 8.1
        """
        from src.models import OvertakeEvent, PitStopEvent, FastestLapEvent
        
        try:
            if isinstance(event, FastestLapEvent):
                # Update fastest lap
                self.session_records.update_fastest_lap(event.driver, event.lap_time)
                
            elif isinstance(event, OvertakeEvent):
                # Increment overtake count
                self.session_records.increment_overtake_count(event.overtaking_driver)
                
            elif isinstance(event, PitStopEvent):
                # Update fastest pit stop
                if event.pit_duration:
                    self.session_records.update_fastest_pit(event.driver, event.pit_duration)
                
                # Reset stint length for driver
                self.session_records.reset_stint_length(event.driver)
                
        except Exception as e:
            logger.warning(f"Failed to update session records: {e}")
    
    def update_stint_lengths(self, driver_tire_ages: Dict[str, int]) -> None:
        """
        Update stint lengths for all drivers.
        
        Should be called periodically (e.g., every lap) with current tire ages.
        
        Args:
            driver_tire_ages: Dictionary mapping driver names to tire ages in laps
        """
        for driver, laps in driver_tire_ages.items():
            self.session_records.update_stint_length(driver, laps)
    
    def clear_session_records(self) -> None:
        """Clear all session records (called at session start)."""
        self.session_records = SessionRecords()
        logger.info("Session records cleared")
    
    def invalidate_cache(self, cache_type: str = "all") -> None:
        """
        Invalidate cached data to force reload.
        
        Args:
            cache_type: Type of cache to invalidate ("driver_info", "championship", or "all")
        """
        if cache_type in ["driver_info", "all"]:
            self._driver_info_cache = None
            logger.info("Driver info cache invalidated")
        
        if cache_type in ["championship", "all"]:
            self._championship_cache = None
            logger.info("Championship cache invalidated")
