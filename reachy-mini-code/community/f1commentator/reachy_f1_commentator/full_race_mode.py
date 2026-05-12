"""
Full Race Mode for Reachy F1 Commentator.

This module provides historical race playback with variable speed control,
integrating with the OpenF1 API and DataIngestionModule.
"""

import logging
import time
import threading
from typing import Optional, Iterator, Dict, Any
from datetime import datetime

from .openf1_client import OpenF1APIClient
from .src.data_ingestion import OpenF1Client, DataIngestionModule
from .src.replay_mode import HistoricalDataLoader, ReplayController
from .src.models import RaceEvent

logger = logging.getLogger(__name__)


class FullRaceMode:
    """
    Full historical race playback mode.
    
    Fetches race data from OpenF1 API and plays it back at configurable speeds.
    Integrates with DataIngestionModule for event generation.
    
    Validates: Requirements 6.1, 6.2, 6.3
    """
    
    def __init__(
        self,
        session_key: int,
        playback_speed: int,
        openf1_client: OpenF1APIClient,
        cache_dir: str = ".test_cache"
    ):
        """
        Initialize Full Race Mode.
        
        Args:
            session_key: OpenF1 session key for the race
            playback_speed: Playback speed multiplier (1, 5, 10, or 20)
            openf1_client: OpenF1 API client for fetching race data
            cache_dir: Directory for caching race data
            
        Validates: Requirements 6.1, 6.2
        """
        self.session_key = session_key
        self.playback_speed = playback_speed
        self.openf1_client = openf1_client
        self.cache_dir = cache_dir
        
        # Components
        self.data_loader = None
        self.replay_controller = None
        self.data_ingestion = None
        self._initialized = False
        self._race_data = None
        
        logger.info(
            f"FullRaceMode created: session_key={session_key}, "
            f"speed={playback_speed}x"
        )
    
    def initialize(self) -> bool:
        """
        Initialize the race mode by fetching race data.
        
        Returns:
            True if initialization successful, False otherwise
            
        Validates: Requirement 6.1
        """
        try:
            logger.info(f"Initializing Full Race Mode for session {self.session_key}")
            
            # Create historical data loader
            self.data_loader = HistoricalDataLoader(
                api_key="",  # Not needed for historical data
                base_url="https://api.openf1.org/v1",
                cache_dir=self.cache_dir
            )
            
            # Load race data
            logger.info(f"Loading race data for session {self.session_key}...")
            self._race_data = self.data_loader.load_race(self.session_key)
            
            if not self._race_data:
                logger.error(f"Failed to load race data for session {self.session_key}")
                return False
            
            # Log data summary
            total_records = sum(len(v) for v in self._race_data.values())
            logger.info(f"Loaded {total_records} records for session {self.session_key}")
            
            # Create replay controller
            self.replay_controller = ReplayController(
                race_data=self._race_data,
                playback_speed=self.playback_speed
            )
            
            # Create data ingestion module in replay mode
            from .src.config import Config
            from .src.event_queue import PriorityEventQueue
            
            config = Config()
            config.replay_mode = True  # Enable replay mode
            config.replay_race_id = self.session_key  # Set the session key
            config.replay_speed = self.playback_speed  # Set playback speed
            # skip_large_gaps defaults to True, which is fine now that we handle starting grid -> race start
            event_queue = PriorityEventQueue(max_size=100)  # Larger queue for replay mode
            
            self.data_ingestion = DataIngestionModule(
                config=config,
                event_queue=event_queue
            )
            
            # The replay controller will be created by DataIngestionModule
            # when it starts in replay mode
            
            self._initialized = True
            logger.info("Full Race Mode initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Full Race Mode: {e}", exc_info=True)
            self._initialized = False
            return False
    
    def is_initialized(self) -> bool:
        """Check if the race mode is initialized."""
        return self._initialized
    
    def get_events(self) -> Iterator[RaceEvent]:
        """
        Get race events as an iterator.
        
        Yields events with timing adjusted for playback speed.
        
        Yields:
            RaceEvent objects
            
        Validates: Requirements 6.2, 6.3
        """
        if not self._initialized:
            logger.error("FullRaceMode not initialized")
            return
        
        try:
            # Start data ingestion in replay mode
            logger.info(f"Starting race playback at {self.playback_speed}x speed")
            
            # The replay controller handles timing adjustments
            # Events are yielded through the event queue
            event_queue = self.data_ingestion.event_queue
            
            # Start ingestion thread
            ingestion_thread = threading.Thread(
                target=self.data_ingestion.start,
                daemon=True
            )
            ingestion_thread.start()
            
            # Give the thread a moment to start
            time.sleep(0.1)
            
            # Yield events from queue
            no_event_count = 0
            max_no_event_iterations = 600  # Increased to 60 seconds to handle long waits during replay
            
            while True:
                try:
                    # Get event from queue using dequeue()
                    event = event_queue.dequeue()
                    
                    if event is not None:
                        no_event_count = 0  # Reset counter when we get an event
                        yield event
                    else:
                        # No event available
                        no_event_count += 1
                        
                        # Check if thread is still alive
                        if not ingestion_thread.is_alive():
                            # Thread stopped, check if there are any remaining events
                            remaining_event = event_queue.dequeue()
                            if remaining_event is None:
                                logger.info("Ingestion thread stopped and queue is empty")
                                break
                            else:
                                # Still have events, yield them
                                yield remaining_event
                                no_event_count = 0
                        elif no_event_count >= max_no_event_iterations:
                            logger.warning(f"No events received for {max_no_event_iterations} iterations, stopping")
                            logger.warning("This may indicate the replay is stuck or has very long gaps between events")
                            break
                        else:
                            # Wait a bit before checking again
                            time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error getting event from queue: {e}", exc_info=True)
                    break
            
            # Stop ingestion
            self.data_ingestion.stop()
            
        except Exception as e:
            logger.error(f"Error during race playback: {e}", exc_info=True)
    
    def get_duration(self) -> float:
        """
        Get estimated race duration in seconds (at current playback speed).
        
        Returns:
            Estimated duration in seconds
        """
        if not self._race_data:
            return 0.0
        
        # Estimate based on typical race duration (2 hours)
        # Adjusted for playback speed
        typical_race_duration = 2 * 3600  # 2 hours in seconds
        return typical_race_duration / self.playback_speed
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get race metadata.
        
        Returns:
            Dictionary with race information
        """
        if not self._race_data:
            return {}
        
        metadata = {
            'session_key': self.session_key,
            'playback_speed': self.playback_speed,
            'total_records': sum(len(v) for v in self._race_data.values()),
            'drivers': len(self._race_data.get('drivers', [])),
            'position_updates': len(self._race_data.get('position', [])),
            'pit_stops': len(self._race_data.get('pit', [])),
            'overtakes': len(self._race_data.get('overtakes', [])),
        }
        
        return metadata
    
    def stop(self):
        """Stop the race playback."""
        if self.data_ingestion:
            self.data_ingestion.stop()
            logger.info("Full Race Mode stopped")
