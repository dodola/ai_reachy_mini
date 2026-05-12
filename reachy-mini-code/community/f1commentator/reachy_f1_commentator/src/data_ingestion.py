"""
Data Ingestion Module for F1 Commentary Robot.

This module connects to the OpenF1 API, polls endpoints for race data,
parses JSON responses into structured events, and emits them to the event queue.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1-2.8
"""

import logging
import time
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from reachy_f1_commentator.src.models import (
    RaceEvent, EventType, OvertakeEvent, PitStopEvent, LeadChangeEvent,
    FastestLapEvent, IncidentEvent, SafetyCarEvent, FlagEvent, PositionUpdateEvent
)
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.replay_mode import HistoricalDataLoader, ReplayController


logger = logging.getLogger(__name__)


class OpenF1Client:
    """
    Client for OpenF1 API with retry logic and connection management.
    
    Note: OpenF1 API does NOT require authentication for historical data.
    Real-time data requires a paid account, but historical data is freely accessible.
    
    Handles HTTP connections, retry with exponential backoff,
    and connection loss detection/reconnection.
    
    Validates: Requirements 1.1, 1.2, 1.4, 1.5
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.openf1.org/v1"):
        """
        Initialize OpenF1 API client.
        
        Args:
            api_key: OpenF1 API authentication key (only needed for real-time data, optional for historical)
            base_url: Base URL for OpenF1 API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = None
        self._authenticated = False
        self._max_retries = 10
        self._retry_delay = 5  # seconds
    
    def authenticate(self) -> bool:
        """
        Set up HTTP session with retry logic.
        
        Note: OpenF1 API does NOT require authentication for historical data.
        This method sets up the session without authentication headers.
        
        Returns:
            True if session setup successful, False otherwise
            
        Validates: Requirements 1.1, 1.2
        """
        try:
            # Create session with retry strategy
            self.session = requests.Session()
            
            # Configure retry strategy with exponential backoff
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],  # Removed 429 - not a rate limit issue
                allowed_methods=["GET", "POST"]
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            # OpenF1 API does NOT require authentication for historical data
            # Only set headers if API key is provided (for real-time data)
            # For historical data, no authentication is needed
            if self.api_key:
                logger.info("API key provided - will be used for real-time data access")
                # Note: Real-time data requires paid account and different access method
                # For now, we only support historical data which needs no auth
            
            # Test connection with a simple request (no auth needed)
            test_url = f"{self.base_url}/sessions"
            response = self.session.get(test_url, timeout=5)  # 5 second timeout per requirement 10.5
            response.raise_for_status()
            
            self._authenticated = True
            logger.info("Successfully connected to OpenF1 API (no authentication required for historical data)")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to OpenF1 API: {e}")
            self._authenticated = False
            return False
    
    def poll_endpoint(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict]]:
        """
        Poll a single OpenF1 API endpoint with retry logic.
        
        Implements exponential backoff retry for failed requests (max 10 attempts).
        
        Args:
            endpoint: API endpoint path (e.g., '/position', '/laps')
            params: Optional query parameters
            
        Returns:
            List of data dictionaries, or None if request fails
            
        Validates: Requirements 1.4, 1.5
        """
        if not self._authenticated or not self.session:
            logger.warning("Not authenticated, attempting to authenticate")
            if not self.authenticate():
                return None
        
        url = f"{self.base_url}{endpoint}"
        attempt = 0
        
        while attempt < self._max_retries:
            try:
                response = self.session.get(url, params=params, timeout=5)  # 5 second timeout per requirement 10.5
                response.raise_for_status()
                
                data = response.json()
                
                # Ensure we return a list
                if isinstance(data, dict):
                    return [data]
                elif isinstance(data, list):
                    return data
                else:
                    logger.warning(f"Unexpected data type from {endpoint}: {type(data)}")
                    return None
                    
            except requests.exceptions.Timeout:
                attempt += 1
                logger.warning(f"Timeout polling {endpoint}, attempt {attempt}/{self._max_retries}")
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay)
                    
            except requests.exceptions.ConnectionError as e:
                attempt += 1
                logger.error(f"Connection error polling {endpoint}: {e}, attempt {attempt}/{self._max_retries}")
                if attempt < self._max_retries:
                    time.sleep(self._retry_delay)
                    # Try to re-authenticate
                    self.authenticate()
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    attempt += 1
                    logger.warning(f"HTTP error {e.response.status_code} polling {endpoint}, attempt {attempt}/{self._max_retries}")
                    if attempt < self._max_retries:
                        time.sleep(self._retry_delay)
                else:
                    logger.error(f"HTTP error polling {endpoint}: {e}")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error polling {endpoint}: {e}")
                return None
        
        logger.error(f"Failed to poll {endpoint} after {self._max_retries} attempts")
        return None
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            self.session.close()
            self._authenticated = False
            logger.info("Closed OpenF1 API connection")


class EventParser:
    """
    Parses OpenF1 API responses into structured race events.
    
    Detects overtakes, pit stops, lead changes, fastest laps, incidents,
    flags, and safety car deployments from raw API data.
    
    Validates: Requirements 2.1-2.8
    """
    
    def __init__(self):
        """Initialize event parser with state tracking."""
        self._last_positions: Dict[str, int] = {}  # driver -> position
        self._last_position_time: Dict[str, datetime] = {}  # driver -> timestamp
        self._last_leader: Optional[str] = None
        self._fastest_lap_time: Optional[float] = None
        self._overtake_threshold = timedelta(seconds=0.5)  # False overtake filter
        self._starting_grid_announced = False  # Track if we've announced the grid
        self._driver_names: Dict[str, str] = {}  # driver_number -> full_name mapping
        self._race_started = False  # Track if race has started
        self._seen_green_flag = False  # Track if we've seen a green flag
        self._initial_positions: Dict[str, int] = {}  # Collect initial positions for grid
        self._position_events_seen = 0  # Count position events before grid announcement
    
    def _get_driver_name(self, driver_number: str) -> str:
        """
        Get driver name from driver number.
        
        Args:
            driver_number: Driver number as string
            
        Returns:
            Driver full name if available, otherwise driver number
        """
        return self._driver_names.get(str(driver_number), str(driver_number))
    
    def parse_position_data(self, data: List[Dict]) -> List[RaceEvent]:
        """
        Parse position data to detect overtakes and lead changes.
        
        Filters out false overtakes (position swaps within 0.5 seconds).
        Also extracts starting grid from first position snapshot if starting_grid endpoint was empty.
        
        Args:
            data: List of position data dictionaries
            
        Returns:
            List of detected events (OvertakeEvent, LeadChangeEvent, PositionUpdateEvent)
            
        Validates: Requirements 2.1, 2.3, 2.8
        """
        events = []
        
        if not data:
            return events
        
        try:
            # If we haven't announced the grid yet, collect initial positions
            if not self._starting_grid_announced:
                self._position_events_seen += 1
                
                for entry in data:
                    driver_number = entry.get('driver_number') or entry.get('driver')
                    position = entry.get('position')
                    
                    if driver_number and position:
                        self._initial_positions[str(driver_number)] = int(position)
                
                # Announce grid when we have 20 drivers, or after 25 position events with at least 18 drivers
                # (to handle cases where some drivers didn't start)
                should_announce = (
                    len(self._initial_positions) >= 20 or  # Full grid
                    (len(self._initial_positions) >= 18 and self._position_events_seen >= 25)  # Partial grid after timeout
                )
                
                if should_announce:
                    grid = []
                    for driver_number, position in self._initial_positions.items():
                        driver_name = self._get_driver_name(driver_number)
                        grid.append({
                            'position': position,
                            'driver_number': str(driver_number),
                            'full_name': driver_name
                        })
                    
                    # Sort by position
                    grid.sort(key=lambda x: x['position'])
                    
                    # Create starting grid announcement event
                    event = RaceEvent(
                        event_type=EventType.POSITION_UPDATE,
                        timestamp=datetime.now(),
                        data={
                            'starting_grid': grid,
                            'is_starting_grid': True
                        }
                    )
                    events.append(event)
                    self._starting_grid_announced = True
                    logger.info(f"Starting grid announced with {len(grid)} drivers from first position snapshot")
            
            # Build current position map
            current_positions: Dict[str, int] = {}
            current_time = datetime.now()
            lap_number = 1
            
            for entry in data:
                driver = entry.get('driver_number') or entry.get('driver')
                position = entry.get('position')
                
                if driver and position:
                    current_positions[str(driver)] = int(position)
                    
                # Extract lap number if available
                if 'lap_number' in entry:
                    lap_number = entry['lap_number']
            
            # Detect overtakes and lead changes
            if self._last_positions:
                for driver, new_pos in current_positions.items():
                    old_pos = self._last_positions.get(driver)
                    
                    if old_pos is not None and old_pos > new_pos:
                        # Driver moved up in position
                        
                        # Check for false overtake (rapid position swap)
                        last_time = self._last_position_time.get(driver, current_time)
                        time_diff = current_time - last_time
                        
                        if time_diff > self._overtake_threshold:
                            # Find who was overtaken
                            overtaken_driver = None
                            for other_driver, other_new_pos in current_positions.items():
                                if other_driver != driver:
                                    other_old_pos = self._last_positions.get(other_driver)
                                    if other_old_pos == new_pos and other_new_pos == old_pos:
                                        overtaken_driver = other_driver
                                        break
                            
                            if overtaken_driver:
                                event = RaceEvent(
                                    event_type=EventType.OVERTAKE,
                                    timestamp=current_time,
                                    data={
                                        'overtaking_driver': driver,
                                        'overtaken_driver': overtaken_driver,
                                        'new_position': new_pos,
                                        'lap_number': lap_number
                                    }
                                )
                                events.append(event)
                                logger.info(f"Detected overtake: {driver} overtakes {overtaken_driver} for P{new_pos}")
                
                # Check for lead change
                current_leader = None
                for driver, pos in current_positions.items():
                    if pos == 1:
                        current_leader = driver
                        break
                
                if current_leader and self._last_leader and current_leader != self._last_leader:
                    event = RaceEvent(
                        event_type=EventType.LEAD_CHANGE,
                        timestamp=current_time,
                        data={
                            'new_leader': current_leader,
                            'old_leader': self._last_leader,
                            'lap_number': lap_number
                        }
                    )
                    events.append(event)
                    logger.info(f"Detected lead change: {current_leader} takes lead from {self._last_leader}")
                
                self._last_leader = current_leader
            
            # Update state
            self._last_positions = current_positions
            for driver in current_positions:
                self._last_position_time[driver] = current_time
            
            # Always emit position update (unless we're still collecting initial grid)
            if current_positions and self._starting_grid_announced:
                event = RaceEvent(
                    event_type=EventType.POSITION_UPDATE,
                    timestamp=current_time,
                    data={
                        'positions': current_positions,
                        'lap_number': lap_number
                    }
                )
                events.append(event)
                
        except Exception as e:
            logger.error(f"[DataIngestion] Error parsing position data: {e}", exc_info=True)
        
        return events
    
    def parse_pit_data(self, data: List[Dict]) -> List[RaceEvent]:
        """
        Parse pit stop data to detect pit stops.
        
        Args:
            data: List of pit stop data dictionaries
            
        Returns:
            List of PitStopEvent events
            
        Validates: Requirement 2.2
        """
        events = []
        
        if not data:
            return events
        
        try:
            for entry in data:
                driver_number = entry.get('driver_number') or entry.get('driver')
                pit_duration = entry.get('pit_duration', 0.0)
                lap_number = entry.get('lap_number', 1)
                
                if driver_number:
                    # Get driver name
                    driver_name = self._get_driver_name(driver_number)
                    
                    event = RaceEvent(
                        event_type=EventType.PIT_STOP,
                        timestamp=datetime.now(),
                        data={
                            'driver': driver_name,
                            'driver_number': str(driver_number),
                            'pit_duration': float(pit_duration),
                            'lap_number': lap_number,
                            'tire_compound': entry.get('tire_compound', 'unknown')
                        }
                    )
                    events.append(event)
                    logger.info(f"Detected pit stop: {driver_name} (duration: {pit_duration}s)")
                    
        except Exception as e:
            logger.error(f"[DataIngestion] Error parsing pit data: {e}", exc_info=True)
        
        return events
    
    def parse_lap_data(self, data: List[Dict]) -> List[RaceEvent]:
        """
        Parse lap data to detect fastest laps and race start.
        
        Args:
            data: List of lap data dictionaries
            
        Returns:
            List of FastestLapEvent events and race start event
            
        Validates: Requirement 2.4
        """
        events = []
        
        if not data:
            return events
        
        try:
            for entry in data:
                driver_number = entry.get('driver_number') or entry.get('driver')
                lap_time = entry.get('lap_duration') or entry.get('lap_time')
                lap_number = entry.get('lap_number', 1)
                
                # Detect race start from first lap 1 event
                if lap_number == 1 and not self._race_started and self._starting_grid_announced:
                    self._race_started = True
                    race_start_event = RaceEvent(
                        event_type=EventType.FLAG,
                        timestamp=datetime.now(),
                        data={
                            'flag_type': 'green',
                            'sector': None,
                            'lap_number': 1,
                            'message': 'Race Start',
                            'is_race_start': True
                        }
                    )
                    events.append(race_start_event)
                    logger.info("Detected race start from first lap data!")
                
                if driver_number and lap_time:
                    lap_time = float(lap_time)
                    
                    # Only track fastest lap after race has started
                    if self._race_started:
                        # Check if this is a new fastest lap
                        if self._fastest_lap_time is None or lap_time < self._fastest_lap_time:
                            self._fastest_lap_time = lap_time
                            
                            # Get driver name
                            driver_name = self._get_driver_name(driver_number)
                            
                            event = RaceEvent(
                                event_type=EventType.FASTEST_LAP,
                                timestamp=datetime.now(),
                                data={
                                    'driver': driver_name,
                                    'driver_number': str(driver_number),
                                    'lap_time': lap_time,
                                    'lap_number': lap_number
                                }
                            )
                            events.append(event)
                            logger.info(f"Detected fastest lap: {driver_name} ({lap_time}s)")
                        
        except Exception as e:
            logger.error(f"[DataIngestion] Error parsing lap data: {e}", exc_info=True)
        
        return events
    
    def parse_race_control_data(self, data: List[Dict]) -> List[RaceEvent]:
        """
        Parse race control data to detect flags, safety car, and incidents.
        
        Filters out boring race control messages and only keeps important ones like:
        - Race start
        - Safety car deployment/withdrawal
        - Red flags
        - Chequered flag
        - Major incidents
        
        Args:
            data: List of race control message dictionaries
            
        Returns:
            List of events (FlagEvent, SafetyCarEvent, IncidentEvent)
            
        Validates: Requirements 2.5, 2.6, 2.7
        """
        events = []
        
        if not data:
            return events
        
        try:
            for entry in data:
                message = entry.get('message', '').lower()
                category = entry.get('category', '').lower()
                lap_number = entry.get('lap_number', 1)
                
                # Filter out boring messages - only keep important race control events
                boring_keywords = [
                    'track limits',
                    'deleted',
                    'time',
                    'under investigation',
                    'noted',
                    'reported',
                    'car stopped',
                    'drs enabled',
                    'drs disabled',
                    'permission',
                    'allowed',
                    'document',
                    'stewards',
                    'penalty'
                ]
                
                # Skip boring messages unless they're about important events
                is_boring = any(keyword in message for keyword in boring_keywords)
                is_important = (
                    'safety car' in message or
                    'red flag' in message or
                    'chequered' in message or 'checkered' in message or
                    'session started' in message or
                    'green flag' in message or
                    'incident' in message or
                    'crash' in message or
                    'collision' in message
                )
                
                if is_boring and not is_important:
                    continue  # Skip this boring message
                
                # Detect flags (only important ones)
                if 'flag' in message or 'flag' in category:
                    flag_type = 'yellow'
                    if 'red' in message:
                        flag_type = 'red'
                    elif 'green' in message:
                        flag_type = 'green'
                    elif 'blue' in message:
                        continue  # Skip blue flags (not interesting for commentary)
                    elif 'chequered' in message or 'checkered' in message:
                        flag_type = 'chequered'
                    elif 'yellow' not in message:
                        continue  # Skip other flag types
                    
                    # Check if this is the race start (first green flag after grid)
                    is_race_start = False
                    if flag_type == 'green' and not self._race_started and self._starting_grid_announced:
                        # This is the race start!
                        self._race_started = True
                        is_race_start = True
                        logger.info("Detected race start!")
                    
                    event = RaceEvent(
                        event_type=EventType.FLAG,
                        timestamp=datetime.now(),
                        data={
                            'flag_type': flag_type,
                            'sector': entry.get('sector'),
                            'lap_number': lap_number,
                            'message': entry.get('message', ''),
                            'is_race_start': is_race_start
                        }
                    )
                    events.append(event)
                    logger.info(f"Detected flag: {flag_type}")
                
                # Detect race start from "SESSION STARTED" message
                elif 'session started' in message and not self._race_started and self._starting_grid_announced:
                    self._race_started = True
                    event = RaceEvent(
                        event_type=EventType.FLAG,
                        timestamp=datetime.now(),
                        data={
                            'flag_type': 'green',
                            'sector': None,
                            'lap_number': lap_number,
                            'message': entry.get('message', ''),
                            'is_race_start': True
                        }
                    )
                    events.append(event)
                    logger.info("Detected race start from SESSION STARTED message!")
                
                # Detect safety car
                elif 'safety car' in message or 'sc' in category:
                    status = 'deployed'
                    if 'in' in message:
                        status = 'in'
                    elif 'ending' in message or 'end' in message:
                        status = 'ending'
                    
                    event = RaceEvent(
                        event_type=EventType.SAFETY_CAR,
                        timestamp=datetime.now(),
                        data={
                            'status': status,
                            'reason': entry.get('message', ''),
                            'lap_number': lap_number
                        }
                    )
                    events.append(event)
                    logger.info(f"Detected safety car: {status}")
                
                # Skip incidents for now - they flood the queue at race start
                # TODO: Re-enable incidents with better filtering later
                # elif 'incident' in message or 'crash' in message or 'collision' in message:
                #     event = RaceEvent(
                #         event_type=EventType.INCIDENT,
                #         timestamp=datetime.now(),
                #         data={
                #             'description': entry.get('message', ''),
                #             'drivers_involved': [],  # Would need more parsing
                #             'lap_number': lap_number
                #         }
                #     )
                #     events.append(event)
                #     logger.info(f"Detected incident: {entry.get('message', '')}")
                    
        except Exception as e:
            logger.error(f"[DataIngestion] Error parsing race control data: {e}", exc_info=True)
        
        return events
    
    def parse_drivers_data(self, data: List[Dict]) -> List[RaceEvent]:
        """
        Parse drivers data to populate driver name lookup table.
        
        This endpoint provides driver information (names, teams, etc.) but NOT grid positions.
        Grid positions come from starting_grid or position endpoints.
        
        Args:
            data: List of driver data dictionaries
            
        Returns:
            Empty list (no events generated, just populates lookup table)
        """
        events = []
        
        if not data:
            return events
        
        try:
            # Populate driver name lookup table
            for entry in data:
                driver_number = entry.get('driver_number')
                full_name = entry.get('full_name', 'Unknown')
                
                if driver_number:
                    # Store driver name for lookup
                    self._driver_names[str(driver_number)] = full_name
            
            logger.info(f"Loaded {len(self._driver_names)} driver names for lookup")
                    
        except Exception as e:
            logger.error(f"[DataIngestion] Error parsing drivers data: {e}", exc_info=True)
        
        return events
    
    def parse_overtakes_data(self, data: List[Dict]) -> List[RaceEvent]:
        """
        Parse overtakes data from OpenF1 API.
        
        Uses the official overtakes endpoint instead of detecting from position changes.
        This is more accurate as it's based on official timing data.
        
        Args:
            data: List of overtake data dictionaries
            
        Returns:
            List of OvertakeEvent events
        """
        events = []
        
        logger.debug(f"[EventParser] parse_overtakes_data called with {len(data) if data else 0} records")
        
        if not data:
            logger.debug("[EventParser] No overtake data to parse")
            return events
        
        logger.info(f"[EventParser] Parsing {len(data)} overtake records")
        
        try:
            for entry in data:
                overtaking_driver_num = entry.get('overtaking_driver_number')
                overtaken_driver_num = entry.get('overtaken_driver_number')
                lap_number = entry.get('lap_number', 1)
                position = entry.get('position')  # New position after overtake
                
                logger.debug(f"[EventParser] Processing overtake: {overtaking_driver_num} -> {overtaken_driver_num}")
                
                if overtaking_driver_num and overtaken_driver_num:
                    # Get driver names
                    overtaking_driver = self._get_driver_name(overtaking_driver_num)
                    overtaken_driver = self._get_driver_name(overtaken_driver_num)
                    
                    event = RaceEvent(
                        event_type=EventType.OVERTAKE,
                        timestamp=datetime.now(),
                        data={
                            'overtaking_driver': overtaking_driver,
                            'overtaken_driver': overtaken_driver,
                            'overtaking_driver_number': str(overtaking_driver_num),
                            'overtaken_driver_number': str(overtaken_driver_num),
                            'new_position': position,  # Add the position
                            'lap_number': lap_number
                        }
                    )
                    events.append(event)
                    logger.debug(f"Parsed overtake: {overtaking_driver} overtakes {overtaken_driver} for P{position} on lap {lap_number}")
                else:
                    logger.warning(f"[EventParser] Skipping overtake with missing driver numbers: {entry}")
                    
        except Exception as e:
            logger.error(f"[DataIngestion] Error parsing overtakes data: {e}", exc_info=True)
        
        logger.info(f"[EventParser] Created {len(events)} overtake events")
        return events
    
    def parse_starting_grid_data(self, data: List[Dict]) -> List[RaceEvent]:
        """
        Parse starting_grid data to get the actual grid positions.
        
        This endpoint provides the official starting grid with correct positions.
        Note: If this endpoint is empty, the starting grid will be extracted from
        the first position data snapshot instead.
        
        Args:
            data: List of starting grid data dictionaries
            
        Returns:
            List of events (one STARTING_GRID event with properly ordered drivers)
        """
        events = []
        
        if not data or self._starting_grid_announced:
            return events
        
        try:
            # Sort by position to ensure correct order
            sorted_grid = sorted(data, key=lambda x: x.get('position', 999))
            
            # Build grid with driver names
            grid = []
            for entry in sorted_grid:
                driver_number = entry.get('driver_number')
                position = entry.get('position')
                
                if driver_number and position:
                    # Get driver name from lookup
                    driver_name = self._get_driver_name(driver_number)
                    
                    grid.append({
                        'position': position,
                        'driver_number': str(driver_number),
                        'full_name': driver_name
                    })
            
            if grid:
                # Create starting grid announcement event
                event = RaceEvent(
                    event_type=EventType.POSITION_UPDATE,
                    timestamp=datetime.now(),
                    data={
                        'starting_grid': grid,
                        'is_starting_grid': True
                    }
                )
                events.append(event)
                self._starting_grid_announced = True
                logger.info(f"Starting grid announced with {len(grid)} drivers from starting_grid endpoint")
                
        except Exception as e:
            logger.error(f"[DataIngestion] Error parsing starting_grid data: {e}", exc_info=True)
        
        return events


class DataIngestionModule:
    """
    Main orchestrator for data ingestion from OpenF1 API.
    
    Manages polling threads for multiple endpoints, coordinates event parsing,
    and emits events to the event queue. Supports both live mode and replay mode.
    
    Validates: Requirements 1.6, 9.3
    """
    
    def __init__(self, config: Config, event_queue: PriorityEventQueue):
        """
        Initialize data ingestion module.
        
        Args:
            config: System configuration
            event_queue: Event queue for emitting parsed events
        """
        self.config = config
        self.event_queue = event_queue
        self.client = OpenF1Client(config.openf1_api_key, config.openf1_base_url)
        self.parser = EventParser()
        
        self._running = False
        self._threads: List[threading.Thread] = []
        
        # Replay mode components
        self._replay_controller: Optional[ReplayController] = None
        self._historical_loader: Optional[HistoricalDataLoader] = None
    
    def start(self) -> bool:
        """
        Start polling all configured endpoints (live mode) or replay (replay mode).
        
        Launches separate threads for each endpoint with configured intervals in live mode,
        or starts replay controller in replay mode.
        
        Returns:
            True if started successfully, False otherwise
            
        Validates: Requirements 1.6, 9.3
        """
        if self._running:
            logger.warning("Data ingestion already running")
            return False
        
        # Check if we're in replay mode
        if self.config.replay_mode:
            return self._start_replay_mode()
        else:
            return self._start_live_mode()
    
    def _start_live_mode(self) -> bool:
        """
        Start live mode data ingestion.
        
        Returns:
            True if started successfully, False otherwise
        """
        # Authenticate first
        if not self.client.authenticate():
            logger.error("Failed to authenticate with OpenF1 API")
            return False
        
        self._running = True
        
        # Start polling threads for each endpoint
        endpoints = [
            ('/position', self.config.position_poll_interval, self.parser.parse_position_data),
            ('/pit', self.config.pit_poll_interval, self.parser.parse_pit_data),
            ('/laps', self.config.laps_poll_interval, self.parser.parse_lap_data),
            ('/race_control', self.config.race_control_poll_interval, self.parser.parse_race_control_data),
        ]
        
        for endpoint, interval, parser_func in endpoints:
            thread = threading.Thread(
                target=self._poll_loop,
                args=(endpoint, interval, parser_func),
                daemon=True
            )
            thread.start()
            self._threads.append(thread)
            logger.info(f"Started polling thread for {endpoint} (interval: {interval}s)")
        
        logger.info("Data ingestion module started in LIVE mode")
        return True
    
    def _start_replay_mode(self) -> bool:
        """
        Start replay mode data ingestion.
        
        Returns:
            True if started successfully, False otherwise
            
        Validates: Requirement 9.3
        """
        if not self.config.replay_race_id:
            logger.error("replay_race_id not configured for replay mode")
            return False
        
        logger.info(f"Starting replay mode for race: {self.config.replay_race_id}")
        
        # Initialize historical data loader
        self._historical_loader = HistoricalDataLoader(
            api_key=self.config.openf1_api_key,
            base_url=self.config.openf1_base_url
        )
        
        # Load race data
        race_data = self._historical_loader.load_race(self.config.replay_race_id)
        
        if not race_data:
            logger.error(f"Failed to load race data for {self.config.replay_race_id}")
            return False
        
        # Initialize replay controller
        self._replay_controller = ReplayController(
            race_data=race_data,
            playback_speed=self.config.replay_speed,
            skip_large_gaps=self.config.replay_skip_large_gaps
        )
        
        # Start replay with callback to process events
        self._replay_controller.start(self._replay_event_callback)
        
        self._running = True
        logger.info(f"Data ingestion module started in REPLAY mode at {self.config.replay_speed}x speed")
        
        # Wait for replay to complete (keep thread alive)
        # The replay controller runs in its own thread, so we need to wait for it
        while self._running and self._replay_controller and not self._replay_controller.is_stopped():
            time.sleep(0.1)
        
        logger.info("Replay mode completed")
        return True
    
    def _replay_event_callback(self, endpoint: str, data: Dict) -> None:
        """
        Callback for replay controller to process historical events.
        
        Parses the event using the same parser as live mode and emits to queue.
        
        Args:
            endpoint: Endpoint name ('position', 'pit', 'laps', 'race_control')
            data: Event data dictionary
            
        Validates: Requirement 9.3
        """
        try:
            # Map endpoint to parser function
            parser_map = {
                'drivers': self.parser.parse_drivers_data,
                'starting_grid': self.parser.parse_starting_grid_data,
                'position': self.parser.parse_position_data,
                'pit': self.parser.parse_pit_data,
                'laps': self.parser.parse_lap_data,
                'race_control': self.parser.parse_race_control_data,
                'overtakes': self.parser.parse_overtakes_data
            }
            
            parser_func = parser_map.get(endpoint)
            if not parser_func:
                logger.warning(f"Unknown endpoint in replay: {endpoint}")
                return
            
            # Debug: log endpoint being processed
            logger.debug(f"[DataIngestion] Processing {endpoint} event")
            
            # Parse events (parser expects a list)
            events = parser_func([data])
            
            # Debug: log how many events were generated
            if events:
                logger.debug(f"[DataIngestion] Generated {len(events)} events from {endpoint}")
            
            # Emit events to queue
            for event in events:
                self.event_queue.enqueue(event)
                
        except Exception as e:
            logger.error(f"[DataIngestion] Error processing replay event from {endpoint}: {e}", exc_info=True)
    
    def stop(self) -> None:
        """
        Stop polling and gracefully shutdown all threads (live mode) or replay (replay mode).
        
        Validates: Requirements 1.6, 9.3
        """
        if not self._running:
            return
        
        logger.info("Stopping data ingestion module...")
        self._running = False
        
        # Stop replay controller if in replay mode
        if self._replay_controller:
            self._replay_controller.stop()
            self._replay_controller = None
        
        # Wait for threads to finish (with timeout)
        for thread in self._threads:
            thread.join(timeout=5.0)
        
        self._threads.clear()
        self.client.close()
        
        logger.info("Data ingestion module stopped")
    
    def _poll_loop(self, endpoint: str, interval: float, parser_func) -> None:
        """
        Polling loop for a single endpoint.
        
        Args:
            endpoint: API endpoint path
            interval: Polling interval in seconds
            parser_func: Function to parse endpoint data
        """
        while self._running:
            try:
                start_time = time.time()
                
                # Poll endpoint
                data = self.client.poll_endpoint(endpoint)
                
                if data:
                    # Parse events
                    parse_start = time.time()
                    events = parser_func(data)
                    parse_duration = time.time() - parse_start
                    
                    # Log parsing latency (Requirement 1.3)
                    if parse_duration > 0.5:
                        logger.warning(f"Parsing {endpoint} took {parse_duration:.3f}s (exceeds 500ms target)")
                    
                    # Emit events to queue
                    for event in events:
                        self.event_queue.enqueue(event)
                
                # Sleep for remaining interval time
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"[DataIngestion] Error in polling loop for {endpoint}: {e}", exc_info=True)
                time.sleep(interval)

    def pause_replay(self) -> None:
        """
        Pause replay playback (replay mode only).
        
        Validates: Requirement 9.4
        """
        if self._replay_controller:
            self._replay_controller.pause()
        else:
            logger.warning("Not in replay mode, cannot pause")
    
    def resume_replay(self) -> None:
        """
        Resume replay playback (replay mode only).
        
        Validates: Requirement 9.4
        """
        if self._replay_controller:
            self._replay_controller.resume()
        else:
            logger.warning("Not in replay mode, cannot resume")
    
    def seek_replay_to_lap(self, lap_number: int) -> None:
        """
        Seek to specific lap in replay (replay mode only).
        
        Args:
            lap_number: Lap number to seek to
            
        Validates: Requirement 9.5
        """
        if self._replay_controller:
            self._replay_controller.seek_to_lap(lap_number)
        else:
            logger.warning("Not in replay mode, cannot seek")
    
    def set_replay_speed(self, speed: float) -> None:
        """
        Set replay playback speed (replay mode only).
        
        Args:
            speed: Playback speed multiplier (1.0 = real-time)
            
        Validates: Requirement 9.2
        """
        if self._replay_controller:
            self._replay_controller.set_playback_speed(speed)
        else:
            logger.warning("Not in replay mode, cannot set speed")
    
    def get_replay_progress(self) -> float:
        """
        Get replay progress (replay mode only).
        
        Returns:
            Progress from 0.0 to 1.0, or 0.0 if not in replay mode
        """
        if self._replay_controller:
            return self._replay_controller.get_progress()
        return 0.0
    
    def is_replay_paused(self) -> bool:
        """
        Check if replay is paused (replay mode only).
        
        Returns:
            True if paused, False otherwise
        """
        if self._replay_controller:
            return self._replay_controller.is_paused()
        return False
