#!/usr/bin/env python3
"""
Test script to simulate full race commentary without TTS.

This script runs through a complete race replay and generates all commentary,
simulating TTS delays to see the actual event processing order and timing.
"""

import logging
import time
import sys
import os
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Suppress verbose logs from other modules
logging.getLogger('reachy_f1_commentator.src.replay_mode').setLevel(logging.WARNING)
logging.getLogger('reachy_f1_commentator.src.data_ingestion').setLevel(logging.INFO)


def main():
    """Run full race commentary test."""
    # Direct imports to avoid main.py
    from reachy_f1_commentator.src.replay_mode import HistoricalDataLoader, ReplayController
    from reachy_f1_commentator.src.data_ingestion import DataIngestionModule
    from reachy_f1_commentator.src.commentary_generator import CommentaryGenerator
    from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
    from reachy_f1_commentator.src.config import Config
    from reachy_f1_commentator.src.event_queue import PriorityEventQueue
    from reachy_f1_commentator.src.models import EventType
    
    # Configuration
    SESSION_KEY = 9998  # Session with complete data
    PLAYBACK_SPEED = 10  # 10x speed
    SIMULATE_TTS_DELAY = True  # Simulate TTS taking time
    TTS_DELAY_PER_CHAR = 0.015  # ~3.7 seconds for 250 chars
    MAX_EVENTS = 100  # Limit events for testing (set to None for full race)
    
    logger.info("=" * 80)
    logger.info("FULL RACE COMMENTARY TEST")
    logger.info("=" * 80)
    logger.info(f"Session: {SESSION_KEY}")
    logger.info(f"Playback Speed: {PLAYBACK_SPEED}x")
    logger.info(f"Simulate TTS: {SIMULATE_TTS_DELAY}")
    logger.info(f"Max Events: {MAX_EVENTS if MAX_EVENTS else 'unlimited'}")
    logger.info("=" * 80)
    
    # Initialize components
    logger.info("\n📥 Loading race data...")
    
    # Create historical data loader
    data_loader = HistoricalDataLoader(
        api_key="",
        base_url="https://api.openf1.org/v1",
        cache_dir=".test_cache"
    )
    
    # Load race data
    race_data = data_loader.load_race(SESSION_KEY)
    
    if not race_data:
        logger.error("❌ Failed to load race data")
        return
    
    # Get metadata
    total_records = sum(len(v) for v in race_data.values())
    logger.info(f"✅ Race loaded:")
    logger.info(f"   - Total records: {total_records}")
    logger.info(f"   - Drivers: {len(race_data.get('drivers', []))}")
    logger.info(f"   - Position updates: {len(race_data.get('position', []))}")
    logger.info(f"   - Pit stops: {len(race_data.get('pit', []))}")
    logger.info(f"   - Overtakes: {len(race_data.get('overtakes', []))}")
    
    # Initialize config and components
    config = Config()
    config.replay_mode = True
    config.replay_race_id = SESSION_KEY
    config.replay_speed = PLAYBACK_SPEED
    config.enhanced_mode = False
    
    event_queue = PriorityEventQueue(max_size=100)
    state_tracker = RaceStateTracker()
    commentary_generator = CommentaryGenerator(config, state_tracker)
    
    # Create data ingestion module
    data_ingestion = DataIngestionModule(config=config, event_queue=event_queue)
    
    # Statistics tracking
    event_counts = defaultdict(int)
    commentary_counts = defaultdict(int)
    total_events = 0
    total_commentary = 0
    total_tts_time = 0.0
    start_time = time.time()
    
    logger.info("\n🏁 Starting race playback...\n")
    
    # Start data ingestion in background thread
    import threading
    ingestion_thread = threading.Thread(target=data_ingestion.start, daemon=True)
    ingestion_thread.start()
    
    # Give it a moment to start
    time.sleep(0.5)
    
    # Process events from queue
    try:
        no_event_count = 0
        max_no_event_iterations = 50
        
        while True:
            # Get event from queue
            event = event_queue.dequeue()
            
            if event is not None:
                no_event_count = 0
                total_events += 1
                event_counts[event.event_type.value] += 1
                
                # Check max events limit
                if MAX_EVENTS and total_events > MAX_EVENTS:
                    logger.info(f"\n⚠️  Reached max events limit ({MAX_EVENTS}), stopping...")
                    break
                
                # Get lap number
                lap_number = event.data.get('lap_number', 0)
                
                # Generate commentary
                try:
                    commentary = commentary_generator.generate(event)
                    
                    # Skip empty commentary
                    if not commentary or not commentary.strip():
                        continue
                    
                    total_commentary += 1
                    commentary_counts[event.event_type.value] += 1
                    
                    # Calculate TTS delay
                    tts_delay = 0.0
                    if SIMULATE_TTS_DELAY:
                        tts_delay = len(commentary) * TTS_DELAY_PER_CHAR
                        total_tts_time += tts_delay
                    
                    # Log commentary with timing info
                    logger.info(
                        f"[Lap {lap_number:2d}] [{event.event_type.value:15s}] "
                        f"{commentary[:80]}{'...' if len(commentary) > 80 else ''}"
                    )
                    if SIMULATE_TTS_DELAY:
                        logger.info(f"           💬 TTS delay: {tts_delay:.2f}s")
                    
                    # Simulate TTS delay
                    if SIMULATE_TTS_DELAY:
                        time.sleep(tts_delay)
                    
                    # Add pacing delay (same as in main.py)
                    pacing_delay = 1.0 / PLAYBACK_SPEED
                    time.sleep(pacing_delay)
                    
                except Exception as e:
                    logger.error(f"❌ Error generating commentary: {e}", exc_info=True)
            
            else:
                # No event available
                no_event_count += 1
                
                # Check if thread is still alive
                if not ingestion_thread.is_alive():
                    # Thread stopped, check if there are any remaining events
                    remaining_event = event_queue.dequeue()
                    if remaining_event is None:
                        logger.info("\n✅ Ingestion thread stopped and queue is empty")
                        break
                    else:
                        # Process remaining event
                        event = remaining_event
                        no_event_count = 0
                        continue
                elif no_event_count >= max_no_event_iterations:
                    logger.warning(f"\n⚠️  No events for {max_no_event_iterations} iterations, stopping")
                    break
                else:
                    # Wait a bit before checking again
                    time.sleep(0.1)
    
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
    finally:
        # Stop data ingestion
        data_ingestion.stop()
    
    # Print statistics
    elapsed_time = time.time() - start_time
    
    logger.info("\n" + "=" * 80)
    logger.info("RACE COMMENTARY STATISTICS")
    logger.info("=" * 80)
    
    logger.info(f"\n📊 Event Statistics:")
    logger.info(f"   Total events processed: {total_events}")
    for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"   - {event_type:20s}: {count:4d}")
    
    logger.info(f"\n🎙️  Commentary Statistics:")
    logger.info(f"   Total commentary pieces: {total_commentary}")
    for event_type, count in sorted(commentary_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"   - {event_type:20s}: {count:4d}")
    
    logger.info(f"\n⏱️  Timing Statistics:")
    logger.info(f"   Elapsed time: {elapsed_time:.1f}s")
    logger.info(f"   Simulated TTS time: {total_tts_time:.1f}s")
    logger.info(f"   Average TTS per commentary: {total_tts_time/total_commentary if total_commentary > 0 else 0:.2f}s")
    
    # Calculate what percentage of events got commentary
    if total_events > 0:
        commentary_rate = (total_commentary / total_events) * 100
        logger.info(f"\n📈 Commentary Rate: {commentary_rate:.1f}% of events generated commentary")
    
    logger.info("\n" + "=" * 80)
    
    # Identify missing event types
    events_without_commentary = set(event_counts.keys()) - set(commentary_counts.keys())
    if events_without_commentary:
        logger.info("\n⚠️  Event types that generated NO commentary:")
        for event_type in events_without_commentary:
            logger.info(f"   - {event_type} ({event_counts[event_type]} events)")
    
    logger.info("\n✅ Test complete!")


if __name__ == "__main__":
    main()
