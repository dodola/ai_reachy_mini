"""
Replay Mode functionality for F1 Commentary Robot.

This module provides historical race data loading, replay control with variable
playback speeds, and integration with the data ingestion module.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
"""

import logging
import time
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import requests
from pathlib import Path
import json
import pickle


logger = logging.getLogger(__name__)


class HistoricalDataLoader:
    """
    Loads and caches historical race data from OpenF1 API.
    
    Fetches complete race data for a given session_key and caches it locally
    to avoid repeated API calls.
    
    Note: OpenF1 uses numeric session_key values (e.g., 9197 for 2023 Abu Dhabi GP Race).
    Use find_session_key() to look up session keys by year, country, and session name.
    
    Validates: Requirement 9.1
    """
    
    def __init__(self, api_key: str = "", base_url: str = "https://api.openf1.org/v1", cache_dir: str = ".test_cache"):
        """
        Initialize historical data loader.
        
        Args:
            api_key: OpenF1 API authentication key (optional for historical data)
            base_url: Base URL for OpenF1 API
            cache_dir: Directory for caching historical data
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup session (no auth needed for historical data)
        self.session = requests.Session()
        
        # Rate limiting: track last request time
        self._last_request_time = 0
        self._min_request_interval = 0.5  # Minimum 0.5 seconds between requests
    
    def find_session_key(self, year: int, country_name: str, session_name: str = "Race") -> Optional[int]:
        """
        Find session_key for a specific race.
        
        Args:
            year: Year of the race (e.g., 2023)
            country_name: Country name (e.g., "United Arab Emirates", "Singapore")
            session_name: Session name (e.g., "Race", "Qualifying", "Practice 1")
            
        Returns:
            Numeric session_key, or None if not found
            
        Example:
            >>> loader = HistoricalDataLoader()
            >>> session_key = loader.find_session_key(2023, "United Arab Emirates", "Race")
            >>> print(session_key)  # 9197
        """
        try:
            url = f"{self.base_url}/sessions"
            params = {
                'year': year,
                'country_name': country_name,
                'session_name': session_name
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            sessions = response.json()
            
            if sessions and len(sessions) > 0:
                session_key = sessions[0]['session_key']
                logger.info(f"Found session_key {session_key} for {year} {country_name} {session_name}")
                return session_key
            else:
                logger.warning(f"No session found for {year} {country_name} {session_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to find session_key: {e}")
            return None
    
    def load_race(self, session_key: int) -> Optional[Dict[str, List[Dict]]]:
        """
        Load historical race data for a given session_key.
        
        First checks local cache, then fetches from OpenF1 API if not cached.
        Caches the result for future use.
        
        Args:
            session_key: Numeric session identifier (e.g., 9197 for 2023 Abu Dhabi GP Race)
                        Use find_session_key() to look up session keys by race details.
            
        Returns:
            Dictionary with keys: 'drivers', 'starting_grid', 'position', 'pit', 'laps', 'race_control', 'overtakes'
            Each value is a list of data dictionaries with timestamps.
            Returns None if loading fails.
            
        Validates: Requirement 9.1
        """
        # Convert to string for cache filename
        session_key_str = str(session_key)
        
        # Check cache first
        cache_file = self.cache_dir / f"{session_key_str}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                logger.info(f"Loaded session {session_key} from cache")
                return data
            except Exception as e:
                logger.warning(f"[ReplayMode] Failed to load cache for session {session_key}: {e}", exc_info=True)
        
        # Fetch from API
        logger.info(f"Fetching historical data for session {session_key} from OpenF1 API")
        
        try:
            race_data = {
                'drivers': self._fetch_endpoint('/drivers', session_key),
                'starting_grid': self._fetch_endpoint('/starting_grid', session_key),
                'position': self._fetch_endpoint('/position', session_key),
                'pit': self._fetch_endpoint('/pit', session_key),
                'laps': self._fetch_endpoint('/laps', session_key),
                'race_control': self._fetch_endpoint('/race_control', session_key),
                'overtakes': self._fetch_endpoint('/overtakes', session_key)
            }
            
            # Validate we got some data
            total_records = sum(len(v) for v in race_data.values())
            if total_records == 0:
                logger.error(f"No data found for session {session_key}")
                logger.info(f"Tip: Use find_session_key() to verify the session_key is correct")
                return None
            
            logger.info(f"Fetched {total_records} total records for session {session_key}")
            
            # Sort all data by timestamp
            for endpoint, data in race_data.items():
                if data:
                    race_data[endpoint] = self._sort_by_timestamp(data)
            
            # Cache the data
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(race_data, f)
                logger.info(f"Cached race data for session {session_key}")
            except Exception as e:
                logger.warning(f"[ReplayMode] Failed to cache data for session {session_key}: {e}", exc_info=True)
            
            return race_data
            
        except Exception as e:
            logger.error(f"[ReplayMode] Failed to load session {session_key}: {e}", exc_info=True)
            return None
    
    def _fetch_endpoint(self, endpoint: str, session_key: int) -> List[Dict]:
        """
        Fetch data from a specific endpoint for a session.
        Includes rate limiting to avoid 429 errors.
        
        Args:
            endpoint: API endpoint path (e.g., '/position')
            session_key: Numeric session identifier
            
        Returns:
            List of data dictionaries
        """
        # Rate limiting: ensure minimum interval between requests
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s before request")
            time.sleep(sleep_time)
        
        url = f"{self.base_url}{endpoint}"
        params = {'session_key': session_key}
        
        try:
            response = self.session.get(url, params=params, timeout=10)  # Increased timeout for large datasets
            self._last_request_time = time.time()  # Update last request time
            response.raise_for_status()
            
            data = response.json()
            
            # Ensure we return a list
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
            else:
                logger.warning(f"Unexpected data type from {endpoint}: {type(data)}")
                return []
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Rate limit hit for {endpoint}, waiting 2 seconds and retrying...")
                time.sleep(2)
                # Retry once
                try:
                    response = self.session.get(url, params=params, timeout=10)
                    self._last_request_time = time.time()
                    response.raise_for_status()
                    data = response.json()
                    return data if isinstance(data, list) else [data] if isinstance(data, dict) else []
                except Exception as retry_error:
                    logger.error(f"[ReplayMode] Retry failed for {endpoint}: {retry_error}")
                    return []
            else:
                logger.error(f"[ReplayMode] Failed to fetch {endpoint} for session {session_key}: {e}", exc_info=True)
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"[ReplayMode] Failed to fetch {endpoint} for session {session_key}: {e}", exc_info=True)
            return []
    
    def _sort_by_timestamp(self, data: List[Dict]) -> List[Dict]:
        """
        Sort data by timestamp field.
        
        Args:
            data: List of data dictionaries
            
        Returns:
            Sorted list
        """
        def get_timestamp(item: Dict) -> datetime:
            """Extract timezone-aware timestamp from item."""
            from datetime import timezone
            
            # Try different timestamp field names
            for field in ['date', 'timestamp', 'time', 'date_start']:
                if field in item:
                    try:
                        # Parse ISO format timestamp
                        dt = datetime.fromisoformat(item[field].replace('Z', '+00:00'))
                        # Ensure timezone-aware (UTC)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt
                    except:
                        pass
            
            # If no timestamp found, use epoch with UTC timezone
            return datetime.fromtimestamp(0, tz=timezone.utc)
        
        try:
            return sorted(data, key=get_timestamp)
        except Exception as e:
            logger.warning(f"[ReplayMode] Failed to sort data by timestamp: {e}", exc_info=True)
            return data
    
    def clear_cache(self, session_key: Optional[int] = None) -> None:
        """
        Clear cached race data.
        
        Args:
            session_key: Specific session to clear, or None to clear all
        """
        if session_key:
            cache_file = self.cache_dir / f"{session_key}.pkl"
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Cleared cache for session {session_key}")
        else:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            logger.info("Cleared all cached race data")



class ReplayController:
    """
    Controls playback of historical race data with variable speed.
    
    Manages playback speed (1x, 2x, 5x, 10x), pause/resume functionality,
    seeking to specific laps, and emits events at scaled time intervals.
    
    Validates: Requirements 9.2, 9.4, 9.5
    """
    
    def __init__(self, race_data: Dict[str, List[Dict]], playback_speed: float = 1.0, skip_large_gaps: bool = True):
        """
        Initialize replay controller with race data.
        
        Args:
            race_data: Historical race data from HistoricalDataLoader
            playback_speed: Playback speed multiplier (1.0 = real-time)
            skip_large_gaps: If True, skip time gaps > 60 seconds (default: True)
                           Note: Gaps > 600 seconds (10 minutes) are ALWAYS skipped as they're data artifacts
        """
        self.race_data = race_data
        self.playback_speed = playback_speed
        self.skip_large_gaps = skip_large_gaps
        
        # Merge all data into a single timeline
        self._timeline = self._build_timeline()
        
        # Playback state
        self._current_index = 0
        self._paused = False
        self._stopped = False
        self._playback_thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None
        self._pause_time: Optional[float] = None
        self._total_paused_duration = 0.0
        
        # Callbacks
        self._event_callback = None
    
    def _build_timeline(self) -> List[Dict]:
        """
        Build a unified timeline from all endpoints.
        
        Merges position, pit, laps, and race_control data into a single
        chronologically sorted list with endpoint tags.
        
        Returns:
            List of events with 'endpoint', 'data', and 'timestamp' fields
        """
        timeline = []
        endpoint_counts = {}
        
        for endpoint, data_list in self.race_data.items():
            count = len(data_list)
            endpoint_counts[endpoint] = count
            
            for data in data_list:
                # Extract timestamp
                timestamp = self._extract_timestamp(data)
                
                timeline.append({
                    'endpoint': endpoint,
                    'data': data,
                    'timestamp': timestamp
                })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'])
        
        logger.info(f"Built timeline with {len(timeline)} events")
        logger.info(f"Endpoint breakdown: {endpoint_counts}")
        return timeline
    
    def _extract_timestamp(self, data: Dict) -> datetime:
        """
        Extract timestamp from data dictionary.
        
        Args:
            data: Data dictionary
            
        Returns:
            Timezone-aware datetime object (UTC)
        """
        for field in ['date', 'timestamp', 'time', 'date_start']:
            if field in data:
                try:
                    dt = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                    # Ensure timezone-aware (UTC)
                    if dt.tzinfo is None:
                        from datetime import timezone
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except:
                    pass
        
        # Default to epoch with UTC timezone if no timestamp
        from datetime import timezone
        return datetime.fromtimestamp(0, tz=timezone.utc)
    
    def set_playback_speed(self, speed: float) -> None:
        """
        Set playback speed.
        
        Args:
            speed: Playback speed multiplier (1.0 = real-time, 2.0 = 2x speed, etc.)
            
        Validates: Requirement 9.2
        """
        if speed <= 0:
            logger.warning(f"Invalid playback speed {speed}, must be positive")
            return
        
        self.playback_speed = speed
        logger.info(f"Playback speed set to {speed}x")
    
    def start(self, event_callback) -> None:
        """
        Start replay playback.
        
        Args:
            event_callback: Function to call for each event (endpoint, data)
            
        Validates: Requirements 9.2, 9.4
        """
        if self._playback_thread and self._playback_thread.is_alive():
            logger.warning("Replay already running")
            return
        
        self._event_callback = event_callback
        self._stopped = False
        self._paused = False
        self._start_time = time.time()
        self._total_paused_duration = 0.0
        
        self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._playback_thread.start()
        
        logger.info(f"Started replay at {self.playback_speed}x speed")
    
    def pause(self) -> None:
        """
        Pause replay playback.
        
        Validates: Requirement 9.4
        """
        if not self._paused:
            self._paused = True
            self._pause_time = time.time()
            logger.info("Replay paused")
    
    def resume(self) -> None:
        """
        Resume replay playback.
        
        Validates: Requirement 9.4
        """
        if self._paused:
            self._paused = False
            if self._pause_time:
                self._total_paused_duration += time.time() - self._pause_time
                self._pause_time = None
            logger.info("Replay resumed")
    
    def stop(self) -> None:
        """
        Stop replay playback.
        
        Validates: Requirement 9.4
        """
        logger.info(f"[ReplayMode] stop() called at event {self._current_index}, stopped was {self._stopped}")
        
        self._stopped = True
        self._paused = False
        
        if self._playback_thread:
            self._playback_thread.join(timeout=5.0)
        
        logger.info("Replay stopped")
    
    def seek_to_lap(self, lap_number: int) -> None:
        """
        Seek to a specific lap in the replay.
        
        Args:
            lap_number: Lap number to seek to
            
        Validates: Requirement 9.5
        """
        # Find the first event at or after the target lap
        for i, event in enumerate(self._timeline):
            data = event['data']
            event_lap = data.get('lap_number', 0)
            
            if event_lap >= lap_number:
                self._current_index = i
                logger.info(f"Seeked to lap {lap_number} (index {i})")
                
                # Reset timing
                if self._start_time:
                    self._start_time = time.time()
                    self._total_paused_duration = 0.0
                
                return
        
        logger.warning(f"Lap {lap_number} not found in timeline")
    
    def get_current_lap(self) -> int:
        """
        Get the current lap number in replay.
        
        Returns:
            Current lap number
        """
        if self._current_index < len(self._timeline):
            event = self._timeline[self._current_index]
            return event['data'].get('lap_number', 0)
        return 0
    
    def is_paused(self) -> bool:
        """Check if replay is paused."""
        return self._paused
    
    def is_stopped(self) -> bool:
        """Check if replay is stopped."""
        return self._stopped
    
    def get_progress(self) -> float:
        """
        Get replay progress as a percentage.
        
        Returns:
            Progress from 0.0 to 1.0
        """
        if not self._timeline:
            return 0.0
        return self._current_index / len(self._timeline)
    
    def _playback_loop(self) -> None:
        """
        Main playback loop that emits events at scaled time intervals.
        
        Skips large time gaps (>60 seconds) to avoid long waits during replay,
        unless skip_large_gaps is disabled.
        
        Validates: Requirements 9.2, 9.4
        """
        try:
            if not self._timeline:
                logger.warning("No events in timeline to replay")
                return
            
            logger.info(f"[ReplayMode] Starting playback loop with {len(self._timeline)} events")
            
            # Get the first event's timestamp as reference
            first_timestamp = self._timeline[0]['timestamp']
            last_event_timestamp = first_timestamp
            
            # Track cumulative race time (excluding large gaps if enabled)
            cumulative_race_time = 0.0
            
            while self._current_index < len(self._timeline) and not self._stopped:
                # Debug: log loop condition
                if self._current_index == 42:
                    logger.info(f"[ReplayMode] At event 42: current_index={self._current_index}, timeline_len={len(self._timeline)}, stopped={self._stopped}")
                
                # Handle pause
                while self._paused and not self._stopped:
                    time.sleep(0.1)
                
                if self._stopped:
                    logger.info(f"[ReplayMode] Stopped at event {self._current_index}/{len(self._timeline)}")
                    break
                
                # Get current event
                event = self._timeline[self._current_index]
                event_timestamp = event['timestamp']
                
                # Calculate time since last event
                time_since_last = (event_timestamp - last_event_timestamp).total_seconds()
                
                # ALWAYS skip absurdly large gaps (> 600 seconds = 10 minutes)
                # These are data artifacts, not actual race time
                if time_since_last > 600.0:
                    logger.info(f"Skipping absurd time gap of {time_since_last:.1f}s at event {self._current_index} (data artifact)")
                    time_since_last = 0.0
                # Handle pre-race to race transition (starting grid -> race start)
                # Skip ALL gaps > 10 seconds in the first 100 events (pre-race phase)
                # This handles the gap from grid formation to lights out without long waits
                elif time_since_last > 10.0 and self._current_index < 100:
                    logger.info(f"Skipping pre-race time gap of {time_since_last:.1f}s at event {self._current_index} (grid -> race start)")
                    time_since_last = 0.0
                # Skip moderate gaps (> 60 seconds) if skip_large_gaps is enabled (after first 100 events)
                elif self.skip_large_gaps and time_since_last > 60.0 and self._current_index >= 100:
                    logger.info(f"Skipping large time gap of {time_since_last:.1f}s at event {self._current_index}")
                    time_since_last = 0.0
                
                # Add to cumulative race time
                cumulative_race_time += time_since_last
                
                # Time since playback started (adjusted for speed and pauses)
                playback_time_elapsed = (time.time() - self._start_time - self._total_paused_duration) * self.playback_speed
                
                # Wait if we're ahead of schedule
                wait_time = cumulative_race_time - playback_time_elapsed
                if wait_time > 0:
                    # Log long waits
                    if wait_time > 10.0:
                        logger.info(f"[ReplayMode] Long wait: {wait_time:.1f}s at event {self._current_index}")
                    time.sleep(wait_time / self.playback_speed)
                elif wait_time < -60.0:
                    # We're way behind schedule - log it
                    logger.warning(f"[ReplayMode] Behind schedule by {-wait_time:.1f}s at event {self._current_index}")
                
                # Emit event
                if self._event_callback and not self._stopped:
                    try:
                        self._event_callback(event['endpoint'], event['data'])
                    except Exception as e:
                        logger.error(f"[ReplayMode] Error in event callback: {e}", exc_info=True)
                
                last_event_timestamp = event_timestamp
                self._current_index += 1
                
                # Log progress every 100 events
                if self._current_index % 100 == 0:
                    logger.info(f"[ReplayMode] Progress: {self._current_index}/{len(self._timeline)} events processed")
            
            # Loop exited - log why
            logger.info(f"[ReplayMode] Loop exited: current_index={self._current_index}, timeline_len={len(self._timeline)}, stopped={self._stopped}")
        
            logger.info(f"[ReplayMode] Playback loop completed: {self._current_index}/{len(self._timeline)} events processed")
            logger.info("Replay playback completed")
            
        except Exception as e:
            logger.error(f"[ReplayMode] Exception in playback loop at event {self._current_index}: {e}", exc_info=True)
