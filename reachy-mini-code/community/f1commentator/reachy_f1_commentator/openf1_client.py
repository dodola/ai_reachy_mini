"""
OpenF1 API client for fetching historical race data.
"""

import time
import logging
import requests
from typing import List, Dict, Optional
from .models import RaceMetadata

logger = logging.getLogger(__name__)


class OpenF1APIClient:
    """Client for OpenF1 API with caching."""
    
    BASE_URL = "https://api.openf1.org/v1"
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    def get_sessions(self) -> List[Dict]:
        """
        Fetch all sessions from OpenF1 API.
        
        Returns:
            List of session dictionaries
        """
        cache_key = 'sessions'
        if cache_key in self.cache:
            cached_time, data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                logger.debug("Returning cached sessions")
                return data
        
        try:
            logger.info("Fetching sessions from OpenF1 API")
            response = requests.get(f"{self.BASE_URL}/sessions", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            self.cache[cache_key] = (time.time(), data)
            logger.info(f"Fetched {len(data)} sessions")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch sessions: {e}")
            # Return cached data if available, even if expired
            if cache_key in self.cache:
                _, data = self.cache[cache_key]
                logger.warning("Returning expired cached data due to API error")
                return data
            raise
    
    def get_race_sessions(self) -> List[Dict]:
        """
        Filter sessions to only include Race sessions.
        
        Returns:
            List of race session dictionaries
        """
        all_sessions = self.get_sessions()
        races = [s for s in all_sessions if s.get('session_name') == 'Race']
        logger.info(f"Filtered to {len(races)} race sessions")
        return races
    
    def get_years(self) -> List[int]:
        """
        Get list of available years with race data.
        Only returns years with completed races (excludes current/future years).
        
        Returns:
            List of years in descending order
        """
        try:
            from datetime import datetime
            
            races = self.get_race_sessions()
            current_year = datetime.now().year
            
            # Filter to only include years before current year
            # (current year races may not have telemetry data yet)
            years = sorted(
                set(r.get('year', 0) for r in races if r.get('year') and r.get('year') < current_year),
                reverse=True
            )
            logger.info(f"Found {len(years)} years with race data: {years}")
            return years
        except Exception as e:
            logger.error(f"Failed to get years: {e}")
            return []
    
    def get_races_by_year(self, year: int) -> List[RaceMetadata]:
        """
        Get all races for a specific year.
        
        Args:
            year: Year to filter by
            
        Returns:
            List of RaceMetadata objects
        """
        try:
            races = self.get_race_sessions()
            year_races = [r for r in races if r.get('year') == year]
            
            # Convert to RaceMetadata objects
            race_metadata = []
            for race in year_races:
                try:
                    metadata = RaceMetadata.from_openf1_session(race)
                    race_metadata.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to parse race metadata: {e}")
                    continue
            
            # Sort by date
            race_metadata.sort(key=lambda r: r.date)
            
            logger.info(f"Found {len(race_metadata)} races for year {year}")
            return race_metadata
        except Exception as e:
            logger.error(f"Failed to get races for year {year}: {e}")
            return []
    
    def get_session_data(self, session_key: int) -> Optional[Dict]:
        """
        Get detailed data for a specific session.
        
        Args:
            session_key: Session key to fetch
            
        Returns:
            Session data dictionary or None if not found
        """
        try:
            logger.info(f"Fetching session data for session_key={session_key}")
            response = requests.get(
                f"{self.BASE_URL}/sessions",
                params={'session_key': session_key},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                return data[0]
            return None
        except requests.RequestException as e:
            logger.error(f"Failed to fetch session data: {e}")
            return None
