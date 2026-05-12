#!/usr/bin/env python3
"""
Simple test to see what events are being generated from a race replay.
"""

import sys
import os
import logging
import time
import threading
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see more details
    format='%(message)s'
)

logger = logging.getLogger(__name__)

# Suppress verbose logs
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('reachy_f1_commentator.src.replay_mode').setLevel(logging.INFO)  # Show replay logs

# Direct imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reachy_f1_commentator.src.replay_mode import HistoricalDataLoader
from reachy_f1_commentator.src.data_ingestion import DataIngestionModule
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.event_queue import PriorityEventQueue

# Configuration
SESSION_KEY = 9998
PLAYBACK_SPEED = 10
MAX_EVENTS = 500  # Increased to see more events

logger.info("=" * 80)
logger.info(f"RACE EVENT ANALYSIS - Session {SESSION_KEY} at {PLAYBACK_SPEED}x speed")
logger.info("=" * 80)

# Load race data
logger.info("\nLoading race data...")
data_loader = HistoricalDataLoader(
    api_key="",
    base_url="https://api.openf1.org/v1",
    cache_dir=".test_cache"
)

race_data = data_loader.load_race(SESSION_KEY)

if not race_data:
    logger.error("Failed to load race data")
    sys.exit(1)

# Print data summary
logger.info(f"\nRace Data Summary:")
logger.info(f"  Drivers: {len(race_data.get('drivers', []))}")
logger.info(f"  Starting Grid: {len(race_data.get('starting_grid', []))}")
logger.info(f"  Position Updates: {len(race_data.get('position', []))}")
logger.info(f"  Pit Stops: {len(race_data.get('pit', []))}")
logger.info(f"  Overtakes: {len(race_data.get('overtakes', []))}")
logger.info(f"  Laps: {len(race_data.get('laps', []))}")
logger.info(f"  Race Control: {len(race_data.get('race_control', []))}")

# Setup replay
config = Config()
config.replay_mode = True
config.replay_race_id = SESSION_KEY
config.replay_speed = PLAYBACK_SPEED

event_queue = PriorityEventQueue(max_size=100)
data_ingestion = DataIngestionModule(config=config, event_queue=event_queue)

# Start ingestion
logger.info(f"\nStarting replay at {PLAYBACK_SPEED}x speed...")
logger.info("=" * 80)

ingestion_thread = threading.Thread(target=data_ingestion.start, daemon=True)
ingestion_thread.start()

time.sleep(0.5)

# Track events
event_counts = defaultdict(int)
event_samples = defaultdict(list)
total_events = 0

try:
    no_event_count = 0
    
    while total_events < MAX_EVENTS:
        event = event_queue.dequeue()
        
        if event is not None:
            no_event_count = 0
            total_events += 1
            event_type = event.event_type.value
            event_counts[event_type] += 1
            
            # Store first 3 samples of each type
            if len(event_samples[event_type]) < 3:
                event_samples[event_type].append(event.data)
            
            # Print event
            lap = event.data.get('lap_number', 0)
            logger.info(f"[{total_events:3d}] [Lap {lap:2d}] {event_type:20s} - {str(event.data)[:80]}")
            
        else:
            no_event_count += 1
            if not ingestion_thread.is_alive() and event_queue.size() == 0:
                logger.info("\nIngestion complete, queue empty")
                break
            elif no_event_count >= 50:
                logger.info(f"\nNo events for 5 seconds, stopping")
                break
            time.sleep(0.1)

except KeyboardInterrupt:
    logger.info("\nInterrupted by user")

# Stop ingestion
data_ingestion.stop()

# Print summary
logger.info("\n" + "=" * 80)
logger.info("EVENT SUMMARY")
logger.info("=" * 80)
logger.info(f"\nTotal events processed: {total_events}")
logger.info(f"\nEvent counts:")
for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
    logger.info(f"  {event_type:20s}: {count:4d}")

logger.info(f"\nEvent samples (first 3 of each type):")
for event_type, samples in sorted(event_samples.items()):
    logger.info(f"\n  {event_type}:")
    for i, sample in enumerate(samples, 1):
        logger.info(f"    {i}. {sample}")

logger.info("\n" + "=" * 80)
