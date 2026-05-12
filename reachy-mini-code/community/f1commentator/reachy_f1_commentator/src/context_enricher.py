"""
Context Enricher Orchestrator for Enhanced Commentary System.

This module orchestrates the OpenF1DataCache and ContextFetcher to provide
a unified interface for context enrichment. It fetches data concurrently from
multiple endpoints, calculates derived metrics (gap trends, tire differentials),
and handles timeouts gracefully.

Validates: Requirements 1.1, 1.2, 15.1, 15.4
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Any

from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.context_fetcher import ContextFetcher
from reachy_f1_commentator.src.data_ingestion import OpenF1Client
from reachy_f1_commentator.src.enhanced_models import ContextData
from reachy_f1_commentator.src.models import RaceEvent, RaceState, OvertakeEvent
from reachy_f1_commentator.src.openf1_data_cache import OpenF1DataCache


logger = logging.getLogger(__name__)


class ContextEnricher:
    """
    Context enrichment orchestrator.
    
    Coordinates OpenF1DataCache and ContextFetcher to gather enriched context
    data from multiple sources concurrently. Calculates derived metrics like
    gap trends and tire age differentials.
    
    Validates: Requirements 1.1, 1.2, 15.1, 15.4
    """
    
    def __init__(
        self,
        config: Config,
        openf1_client: OpenF1Client,
        race_state_tracker: Any
    ):
        """
        Initialize context enricher.
        
        Args:
            config: System configuration
            openf1_client: OpenF1 API client
            race_state_tracker: Race state tracker for current race state
        """
        self.config = config
        self.openf1_client = openf1_client
        self.race_state_tracker = race_state_tracker
        
        # Initialize cache and fetcher
        self.cache = OpenF1DataCache(openf1_client, config)
        self.fetcher = ContextFetcher(openf1_client, config.context_enrichment_timeout_ms)
        
        # Timeout for context enrichment (milliseconds)
        self.timeout_ms = config.context_enrichment_timeout_ms
        self.timeout_seconds = self.timeout_ms / 1000.0
        
        # Gap history for trend calculation (driver -> deque of (lap, gap) tuples)
        self._gap_history: Dict[str, deque] = {}
        self._gap_history_window = 3  # Track last 3 laps for trend
        
        # Session key for API calls
        self._session_key: Optional[int] = None
        
        logger.info(f"ContextEnricher initialized with {self.timeout_ms}ms timeout")
    
    def set_session_key(self, session_key: int) -> None:
        """
        Set the session key for data fetching.
        
        Args:
            session_key: OpenF1 session key (e.g., 9197 for 2023 Abu Dhabi GP)
        """
        self._session_key = session_key
        self.cache.set_session_key(session_key)
        logger.info(f"ContextEnricher session key set to: {session_key}")
    
    def load_static_data(self, session_key: Optional[int] = None) -> bool:
        """
        Load static data (driver info, championship standings) at session start.
        
        Args:
            session_key: OpenF1 session key (optional, uses stored session_key if not provided)
            
        Returns:
            True if data loaded successfully, False otherwise
        """
        if session_key:
            self.set_session_key(session_key)
        
        # Load driver info and team colors
        driver_success = self.cache.load_static_data()
        
        # Load championship standings (optional, may not be available)
        championship_success = self.cache.load_championship_standings()
        
        if not driver_success:
            logger.error("Failed to load driver info - context enrichment may be limited")
            return False
        
        if not championship_success:
            logger.warning("Championship standings not available - championship context will be omitted")
        
        return True
    
    async def enrich_context(self, event: RaceEvent) -> ContextData:
        """
        Gather enriched context data for an event from multiple sources.
        
        Fetches data concurrently from multiple OpenF1 endpoints with timeout
        handling. Calculates derived metrics like gap trends and tire differentials.
        
        Args:
            event: Race event to enrich with context
            
        Returns:
            ContextData object with all available enriched data
            
        Validates: Requirements 1.1, 1.2, 15.1, 15.4
        """
        start_time = time.time()
        missing_sources = []
        
        # Get current race state
        race_state = self.race_state_tracker.get_state()
        
        # Initialize context data with event and race state
        context = ContextData(
            event=event,
            race_state=race_state
        )
        
        # Check if session key is set
        if not self._session_key:
            logger.error("Cannot enrich context: session_key not set")
            context.enrichment_time_ms = (time.time() - start_time) * 1000
            context.missing_data_sources = ["all - no session key"]
            return context
        
        # Get driver number from event
        driver_number = self._get_driver_number_from_event(event)
        if not driver_number:
            logger.warning(f"Cannot determine driver number from event: {event}")
            context.enrichment_time_ms = (time.time() - start_time) * 1000
            context.missing_data_sources = ["all - no driver number"]
            return context
        
        # Fetch data concurrently from multiple endpoints
        try:
            # Create tasks for concurrent fetching
            tasks = []
            
            # Telemetry (if enabled)
            if self.config.enable_telemetry:
                tasks.append(self._fetch_telemetry_safe(driver_number))
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Dummy task
            
            # Gaps
            tasks.append(self._fetch_gaps_safe(driver_number))
            
            # Lap data
            lap_number = getattr(event, 'lap_number', None)
            tasks.append(self._fetch_lap_data_safe(driver_number, lap_number))
            
            # Tire data
            tasks.append(self._fetch_tire_data_safe(driver_number))
            
            # Weather (if enabled)
            if self.config.enable_weather:
                tasks.append(self._fetch_weather_safe())
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Dummy task
            
            # Pit data
            tasks.append(self._fetch_pit_data_safe(driver_number, lap_number))
            
            # Fetch all concurrently with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.timeout_seconds
            )
            
            # Unpack results
            telemetry_data = results[0] if self.config.enable_telemetry else {}
            gaps_data = results[1]
            lap_data = results[2]
            tire_data = results[3]
            weather_data = results[4] if self.config.enable_weather else {}
            pit_data = results[5]
            
            # Populate context with fetched data
            self._populate_telemetry(context, telemetry_data, missing_sources)
            self._populate_gaps(context, gaps_data, missing_sources, driver_number)
            self._populate_lap_data(context, lap_data, missing_sources)
            self._populate_tire_data(context, tire_data, missing_sources)
            self._populate_weather(context, weather_data, missing_sources)
            self._populate_pit_data(context, pit_data, missing_sources)
            
        except asyncio.TimeoutError:
            logger.warning(f"Context enrichment timeout after {self.timeout_ms}ms")
            missing_sources.append("timeout - partial data only")
        except Exception as e:
            logger.error(f"Error during context enrichment: {e}")
            missing_sources.append(f"error - {str(e)}")
        
        # Get championship data from cache (if enabled)
        if self.config.enable_championship:
            self._populate_championship(context, driver_number, missing_sources)
        
        # Calculate derived metrics
        self._calculate_gap_trend(context, driver_number)
        self._calculate_tire_age_differential(context, event)
        
        # Calculate enrichment time
        enrichment_time_ms = (time.time() - start_time) * 1000
        context.enrichment_time_ms = enrichment_time_ms
        context.missing_data_sources = missing_sources
        
        logger.debug(
            f"Context enrichment completed in {enrichment_time_ms:.1f}ms "
            f"({len(missing_sources)} missing sources)"
        )
        
        return context
    
    async def _fetch_telemetry_safe(self, driver_number: int) -> Dict[str, Any]:
        """Safely fetch telemetry data with error handling."""
        try:
            return await self.fetcher.fetch_telemetry(driver_number, self._session_key)
        except Exception as e:
            logger.debug(f"Failed to fetch telemetry: {e}")
            return {}
    
    async def _fetch_gaps_safe(self, driver_number: int) -> Dict[str, Any]:
        """Safely fetch gap data with error handling."""
        try:
            return await self.fetcher.fetch_gaps(driver_number, self._session_key)
        except Exception as e:
            logger.debug(f"Failed to fetch gaps: {e}")
            return {}
    
    async def _fetch_lap_data_safe(
        self,
        driver_number: int,
        lap_number: Optional[int]
    ) -> Dict[str, Any]:
        """Safely fetch lap data with error handling."""
        try:
            return await self.fetcher.fetch_lap_data(
                driver_number,
                self._session_key,
                lap_number
            )
        except Exception as e:
            logger.debug(f"Failed to fetch lap data: {e}")
            return {}
    
    async def _fetch_tire_data_safe(self, driver_number: int) -> Dict[str, Any]:
        """Safely fetch tire data with error handling."""
        try:
            return await self.fetcher.fetch_tire_data(driver_number, self._session_key)
        except Exception as e:
            logger.debug(f"Failed to fetch tire data: {e}")
            return {}
    
    async def _fetch_weather_safe(self) -> Dict[str, Any]:
        """Safely fetch weather data with error handling."""
        try:
            return await self.fetcher.fetch_weather(self._session_key)
        except Exception as e:
            logger.debug(f"Failed to fetch weather: {e}")
            return {}
    
    async def _fetch_pit_data_safe(
        self,
        driver_number: int,
        lap_number: Optional[int]
    ) -> Dict[str, Any]:
        """Safely fetch pit data with error handling."""
        try:
            return await self.fetcher.fetch_pit_data(
                driver_number,
                self._session_key,
                lap_number
            )
        except Exception as e:
            logger.debug(f"Failed to fetch pit data: {e}")
            return {}
    
    def _get_driver_number_from_event(self, event: RaceEvent) -> Optional[int]:
        """
        Extract driver number from event.
        
        Args:
            event: Race event
            
        Returns:
            Driver number if found, None otherwise
        """
        # Try to get driver name from event
        driver_name = None
        if hasattr(event, 'driver'):
            driver_name = event.driver
        elif hasattr(event, 'overtaking_driver'):
            driver_name = event.overtaking_driver
        
        if not driver_name:
            return None
        
        # Look up driver number from cache
        driver_info = self.cache.get_driver_info(driver_name)
        if driver_info:
            return driver_info.driver_number
        
        return None
    
    def _populate_telemetry(
        self,
        context: ContextData,
        data: Dict[str, Any],
        missing_sources: List[str]
    ) -> None:
        """Populate context with telemetry data."""
        if not data:
            missing_sources.append("telemetry")
            return
        
        context.speed = data.get("speed")
        context.throttle = data.get("throttle")
        context.brake = data.get("brake")
        context.drs_active = data.get("drs_active")
        context.rpm = data.get("rpm")
        context.gear = data.get("gear")
    
    def _populate_gaps(
        self,
        context: ContextData,
        data: Dict[str, Any],
        missing_sources: List[str],
        driver_number: int
    ) -> None:
        """Populate context with gap data."""
        if not data:
            missing_sources.append("gaps")
            return
        
        context.gap_to_leader = data.get("gap_to_leader")
        context.gap_to_ahead = data.get("gap_to_ahead")
        context.gap_to_behind = data.get("gap_to_behind")
        
        # Store gap for trend calculation
        if context.gap_to_leader is not None:
            lap_number = getattr(context.event, 'lap_number', 0)
            if driver_number not in self._gap_history:
                self._gap_history[driver_number] = deque(maxlen=self._gap_history_window)
            self._gap_history[driver_number].append((lap_number, context.gap_to_leader))
    
    def _populate_lap_data(
        self,
        context: ContextData,
        data: Dict[str, Any],
        missing_sources: List[str]
    ) -> None:
        """Populate context with lap data."""
        if not data:
            missing_sources.append("lap_data")
            return
        
        context.sector_1_time = data.get("sector_1_time")
        context.sector_2_time = data.get("sector_2_time")
        context.sector_3_time = data.get("sector_3_time")
        context.sector_1_status = data.get("sector_1_status")
        context.sector_2_status = data.get("sector_2_status")
        context.sector_3_status = data.get("sector_3_status")
        context.speed_trap = data.get("speed_trap")
    
    def _populate_tire_data(
        self,
        context: ContextData,
        data: Dict[str, Any],
        missing_sources: List[str]
    ) -> None:
        """Populate context with tire data."""
        if not data:
            missing_sources.append("tire_data")
            return
        
        context.current_tire_compound = data.get("current_tire_compound")
        context.current_tire_age = data.get("current_tire_age")
        context.previous_tire_compound = data.get("previous_tire_compound")
        context.previous_tire_age = data.get("previous_tire_age")
    
    def _populate_weather(
        self,
        context: ContextData,
        data: Dict[str, Any],
        missing_sources: List[str]
    ) -> None:
        """Populate context with weather data."""
        if not data:
            missing_sources.append("weather")
            return
        
        context.air_temp = data.get("air_temp")
        context.track_temp = data.get("track_temp")
        context.humidity = data.get("humidity")
        context.rainfall = data.get("rainfall")
        context.wind_speed = data.get("wind_speed")
        context.wind_direction = data.get("wind_direction")
    
    def _populate_pit_data(
        self,
        context: ContextData,
        data: Dict[str, Any],
        missing_sources: List[str]
    ) -> None:
        """Populate context with pit data."""
        if not data:
            missing_sources.append("pit_data")
            return
        
        context.pit_duration = data.get("pit_duration")
        context.pit_lane_time = data.get("pit_lane_time")
        context.pit_count = data.get("pit_count", 0)
    
    def _populate_championship(
        self,
        context: ContextData,
        driver_number: int,
        missing_sources: List[str]
    ) -> None:
        """Populate context with championship data from cache."""
        position = self.cache.get_championship_position(driver_number)
        points = self.cache.get_championship_points(driver_number)
        
        if position is None or points is None:
            missing_sources.append("championship")
            return
        
        context.driver_championship_position = position
        context.driver_championship_points = points
        context.is_championship_contender = self.cache.is_championship_contender(driver_number)
        
        # Calculate gap to leader
        if position > 1:
            leader_points = self.cache.get_championship_points(
                self.cache.championship_standings[0].driver_number
            )
            if leader_points is not None:
                context.championship_gap_to_leader = int(leader_points - points)
    
    def _calculate_gap_trend(self, context: ContextData, driver_number: int) -> None:
        """
        Calculate gap trend (closing, stable, increasing) from recent history.
        
        Args:
            context: Context data to populate with gap trend
            driver_number: Driver number
        """
        if driver_number not in self._gap_history:
            return
        
        history = list(self._gap_history[driver_number])
        if len(history) < 2:
            return
        
        # Calculate average gap change per lap
        gap_changes = []
        for i in range(1, len(history)):
            prev_lap, prev_gap = history[i-1]
            curr_lap, curr_gap = history[i]
            
            # Calculate gap change per lap
            lap_diff = curr_lap - prev_lap
            if lap_diff > 0:
                gap_change = (curr_gap - prev_gap) / lap_diff
                gap_changes.append(gap_change)
        
        if not gap_changes:
            return
        
        # Average gap change per lap
        avg_change = sum(gap_changes) / len(gap_changes)
        
        # Determine trend
        if avg_change < -0.5:
            context.gap_trend = "closing"
        elif avg_change > 0.5:
            context.gap_trend = "increasing"
        else:
            context.gap_trend = "stable"
    
    def _calculate_tire_age_differential(
        self,
        context: ContextData,
        event: RaceEvent
    ) -> None:
        """
        Calculate tire age differential for overtake events.
        
        Args:
            context: Context data to populate with tire age differential
            event: Race event (must be OvertakeEvent)
        """
        # Only calculate for overtake events
        if not isinstance(event, OvertakeEvent):
            return
        
        # Get tire age for overtaking driver (already in context)
        overtaking_tire_age = context.current_tire_age
        if overtaking_tire_age is None:
            return
        
        # Get tire age for overtaken driver
        overtaken_driver = event.overtaken_driver
        overtaken_driver_info = self.cache.get_driver_info(overtaken_driver)
        if not overtaken_driver_info:
            return
        
        # Fetch tire data for overtaken driver
        # Note: This is a synchronous call, but we're already in async context
        # We'll need to make this async or use cached data
        # For now, we'll skip this calculation if we don't have cached tire data
        # TODO: Consider caching tire data for all drivers periodically
        
        logger.debug("Tire age differential calculation requires cached tire data for all drivers")
    
    async def close(self) -> None:
        """Close the context fetcher session."""
        await self.fetcher.close()
        logger.info("ContextEnricher closed")
    
    def clear_gap_history(self) -> None:
        """Clear gap history (called at session start)."""
        self._gap_history.clear()
        logger.debug("Gap history cleared")
