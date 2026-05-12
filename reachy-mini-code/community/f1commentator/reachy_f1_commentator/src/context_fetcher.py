"""
Context Fetcher for Enhanced Commentary System.

This module provides async methods for fetching context data from multiple
OpenF1 endpoints concurrently. Each method handles timeouts and errors gracefully
to ensure commentary generation continues even with partial data.

Validates: Requirements 1.1, 1.2
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any

import aiohttp

from reachy_f1_commentator.src.data_ingestion import OpenF1Client


logger = logging.getLogger(__name__)


class ContextFetcher:
    """
    Async context fetcher for OpenF1 data.
    
    Provides async methods to fetch data from multiple OpenF1 endpoints
    concurrently with timeout handling and error recovery.
    
    Validates: Requirements 1.1, 1.2
    """
    
    def __init__(self, openf1_client: OpenF1Client, timeout_ms: int = 500):
        """
        Initialize context fetcher.
        
        Args:
            openf1_client: OpenF1 API client for base URL and session
            timeout_ms: Timeout in milliseconds for each fetch (default 500ms)
        """
        self.base_url = openf1_client.base_url
        self.timeout_seconds = timeout_ms / 1000.0
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"ContextFetcher initialized with {timeout_ms}ms timeout")
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """
        Ensure aiohttp session exists.
        
        Returns:
            Active aiohttp ClientSession
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("ContextFetcher session closed")
    
    async def fetch_telemetry(
        self,
        driver_number: int,
        session_key: int,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Fetch telemetry data from car_data endpoint.
        
        Retrieves: speed, DRS status, throttle, brake, RPM, gear
        
        Args:
            driver_number: Driver number (e.g., 44 for Hamilton)
            session_key: OpenF1 session key
            timestamp: Optional timestamp to fetch data near (uses latest if None)
            
        Returns:
            Dictionary with telemetry data, or empty dict on failure
            
        Validates: Requirements 1.1, 1.2
        """
        try:
            session = await self._ensure_session()
            
            # Build query parameters
            params = {
                "session_key": session_key,
                "driver_number": driver_number
            }
            
            # Add timestamp filter if provided (get data near this time)
            if timestamp:
                # OpenF1 API uses ISO format timestamps
                params["date"] = timestamp.isoformat()
            
            url = f"{self.base_url}/car_data"
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch telemetry for driver {driver_number}: "
                        f"HTTP {response.status}"
                    )
                    return {}
                
                data = await response.json()
                
                # OpenF1 returns a list, get the most recent entry
                if isinstance(data, list) and len(data) > 0:
                    latest = data[-1]  # Most recent entry
                    
                    return {
                        "speed": latest.get("speed"),
                        "throttle": latest.get("throttle"),
                        "brake": latest.get("brake"),
                        "drs_active": latest.get("drs") in [10, 12, 14],  # DRS open values
                        "rpm": latest.get("rpm"),
                        "gear": latest.get("n_gear")
                    }
                
                logger.debug(f"No telemetry data found for driver {driver_number}")
                return {}
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching telemetry for driver {driver_number}")
            return {}
        except Exception as e:
            logger.warning(f"Error fetching telemetry for driver {driver_number}: {e}")
            return {}
    
    async def fetch_gaps(
        self,
        driver_number: int,
        session_key: int
    ) -> Dict[str, Any]:
        """
        Fetch gap data from intervals endpoint.
        
        Retrieves: gap_to_leader, gap_to_ahead, gap_to_behind
        
        Args:
            driver_number: Driver number
            session_key: OpenF1 session key
            
        Returns:
            Dictionary with gap data, or empty dict on failure
            
        Validates: Requirements 1.1, 1.2
        """
        try:
            session = await self._ensure_session()
            
            params = {
                "session_key": session_key,
                "driver_number": driver_number
            }
            
            url = f"{self.base_url}/intervals"
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch gaps for driver {driver_number}: "
                        f"HTTP {response.status}"
                    )
                    return {}
                
                data = await response.json()
                
                # Get the most recent interval data
                if isinstance(data, list) and len(data) > 0:
                    latest = data[-1]
                    
                    # Parse gap values (can be strings like "+1.234" or None)
                    def parse_gap(gap_str: Optional[str]) -> Optional[float]:
                        if gap_str is None:
                            return None
                        if isinstance(gap_str, (int, float)):
                            return float(gap_str)
                        # Remove '+' prefix and convert to float
                        try:
                            return float(str(gap_str).replace('+', ''))
                        except (ValueError, AttributeError):
                            return None
                    
                    return {
                        "gap_to_leader": parse_gap(latest.get("gap_to_leader")),
                        "gap_to_ahead": parse_gap(latest.get("interval")),
                        # gap_to_behind not directly available, would need to query next driver
                        "gap_to_behind": None
                    }
                
                logger.debug(f"No gap data found for driver {driver_number}")
                return {}
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching gaps for driver {driver_number}")
            return {}
        except Exception as e:
            logger.warning(f"Error fetching gaps for driver {driver_number}: {e}")
            return {}
    
    async def fetch_lap_data(
        self,
        driver_number: int,
        session_key: int,
        lap_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch lap data from laps endpoint.
        
        Retrieves: sector times, sector status (purple/green/yellow), speed trap
        
        Args:
            driver_number: Driver number
            session_key: OpenF1 session key
            lap_number: Optional specific lap number (uses latest if None)
            
        Returns:
            Dictionary with lap data, or empty dict on failure
            
        Validates: Requirements 1.1, 1.2
        """
        try:
            session = await self._ensure_session()
            
            params = {
                "session_key": session_key,
                "driver_number": driver_number
            }
            
            if lap_number is not None:
                params["lap_number"] = lap_number
            
            url = f"{self.base_url}/laps"
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch lap data for driver {driver_number}: "
                        f"HTTP {response.status}"
                    )
                    return {}
                
                data = await response.json()
                
                # Get the most recent lap data
                if isinstance(data, list) and len(data) > 0:
                    latest = data[-1]
                    
                    # Determine sector status based on segment values
                    # 0 = no time, 2048 = yellow, 2049 = green, 2051 = purple, 2064 = white
                    def get_sector_status(segment_value: Optional[int]) -> Optional[str]:
                        if segment_value is None:
                            return None
                        status_map = {
                            2048: "yellow",
                            2049: "green",
                            2051: "purple",
                            2064: "white"
                        }
                        return status_map.get(segment_value)
                    
                    return {
                        "sector_1_time": latest.get("duration_sector_1"),
                        "sector_2_time": latest.get("duration_sector_2"),
                        "sector_3_time": latest.get("duration_sector_3"),
                        "sector_1_status": get_sector_status(latest.get("segments_sector_1")),
                        "sector_2_status": get_sector_status(latest.get("segments_sector_2")),
                        "sector_3_status": get_sector_status(latest.get("segments_sector_3")),
                        "speed_trap": latest.get("st_speed")
                    }
                
                logger.debug(f"No lap data found for driver {driver_number}")
                return {}
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching lap data for driver {driver_number}")
            return {}
        except Exception as e:
            logger.warning(f"Error fetching lap data for driver {driver_number}: {e}")
            return {}
    
    async def fetch_tire_data(
        self,
        driver_number: int,
        session_key: int
    ) -> Dict[str, Any]:
        """
        Fetch tire data from stints endpoint.
        
        Retrieves: current compound, current age, previous compound, previous age
        
        Args:
            driver_number: Driver number
            session_key: OpenF1 session key
            
        Returns:
            Dictionary with tire data, or empty dict on failure
            
        Validates: Requirements 1.1, 1.2
        """
        try:
            session = await self._ensure_session()
            
            params = {
                "session_key": session_key,
                "driver_number": driver_number
            }
            
            url = f"{self.base_url}/stints"
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch tire data for driver {driver_number}: "
                        f"HTTP {response.status}"
                    )
                    return {}
                
                data = await response.json()
                
                # Get current and previous stints
                if isinstance(data, list) and len(data) > 0:
                    # Sort by stint number to get most recent
                    stints = sorted(data, key=lambda x: x.get("stint_number", 0))
                    
                    current_stint = stints[-1]
                    previous_stint = stints[-2] if len(stints) > 1 else None
                    
                    result = {
                        "current_tire_compound": current_stint.get("compound"),
                        "current_tire_age": current_stint.get("tyre_age_at_start"),
                    }
                    
                    if previous_stint:
                        result["previous_tire_compound"] = previous_stint.get("compound")
                        result["previous_tire_age"] = previous_stint.get("tyre_age_at_start")
                    
                    return result
                
                logger.debug(f"No tire data found for driver {driver_number}")
                return {}
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching tire data for driver {driver_number}")
            return {}
        except Exception as e:
            logger.warning(f"Error fetching tire data for driver {driver_number}: {e}")
            return {}
    
    async def fetch_weather(
        self,
        session_key: int
    ) -> Dict[str, Any]:
        """
        Fetch weather data from weather endpoint.
        
        Retrieves: air temp, track temp, humidity, rainfall, wind speed, wind direction
        
        Args:
            session_key: OpenF1 session key
            
        Returns:
            Dictionary with weather data, or empty dict on failure
            
        Validates: Requirements 1.1, 1.2
        """
        try:
            session = await self._ensure_session()
            
            params = {
                "session_key": session_key
            }
            
            url = f"{self.base_url}/weather"
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch weather data: HTTP {response.status}"
                    )
                    return {}
                
                data = await response.json()
                
                # Get the most recent weather data
                if isinstance(data, list) and len(data) > 0:
                    latest = data[-1]
                    
                    return {
                        "air_temp": latest.get("air_temperature"),
                        "track_temp": latest.get("track_temperature"),
                        "humidity": latest.get("humidity"),
                        "rainfall": latest.get("rainfall"),
                        "wind_speed": latest.get("wind_speed"),
                        "wind_direction": latest.get("wind_direction")
                    }
                
                logger.debug("No weather data found")
                return {}
                
        except asyncio.TimeoutError:
            logger.warning("Timeout fetching weather data")
            return {}
        except Exception as e:
            logger.warning(f"Error fetching weather data: {e}")
            return {}
    
    async def fetch_pit_data(
        self,
        driver_number: int,
        session_key: int,
        lap_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch pit stop data from pit endpoint.
        
        Retrieves: pit duration, pit lane time
        
        Args:
            driver_number: Driver number
            session_key: OpenF1 session key
            lap_number: Optional lap number to get specific pit stop
            
        Returns:
            Dictionary with pit data, or empty dict on failure
            
        Validates: Requirements 1.1, 1.2
        """
        try:
            session = await self._ensure_session()
            
            params = {
                "session_key": session_key,
                "driver_number": driver_number
            }
            
            if lap_number is not None:
                params["lap_number"] = lap_number
            
            url = f"{self.base_url}/pit"
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch pit data for driver {driver_number}: "
                        f"HTTP {response.status}"
                    )
                    return {}
                
                data = await response.json()
                
                # Get the most recent pit stop
                if isinstance(data, list) and len(data) > 0:
                    latest = data[-1]
                    
                    return {
                        "pit_duration": latest.get("pit_duration"),
                        "pit_lane_time": latest.get("lap_time"),  # Total time in pit lane
                        "pit_count": len(data)  # Total number of pit stops
                    }
                
                logger.debug(f"No pit data found for driver {driver_number}")
                return {}
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching pit data for driver {driver_number}")
            return {}
        except Exception as e:
            logger.warning(f"Error fetching pit data for driver {driver_number}: {e}")
            return {}
