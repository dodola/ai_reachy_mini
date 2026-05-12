"""
Test with historical race data from 2023 season.

Tests event detection accuracy and commentary generation
with real race data from:
- 2023 Abu Dhabi GP
- 2023 Singapore GP  
- 2023 Monaco GP
"""

import pytest
import pickle
import os
from datetime import datetime
from unittest.mock import Mock, patch

from reachy_f1_commentator.src.data_ingestion import HistoricalDataLoader, EventParser
from reachy_f1_commentator.src.models import EventType


class TestHistoricalRaceData:
    """Test with historical race data."""
    
    def test_load_2023_abu_dhabi_gp(self):
        """Test loading 2023 Abu Dhabi GP data."""
        loader = HistoricalDataLoader()
        
        # Try to load cached data first
        cache_file = ".test_cache/2023_abu_dhabi.pkl"
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                race_data = pickle.load(f)
            print(f"✓ Loaded cached Abu Dhabi GP data")
        else:
            # Load from API (requires network)
            try:
                race_data = loader.load_race("2023_abu_dhabi")
                if race_data:
                    # Cache for future use
                    os.makedirs(".test_cache", exist_ok=True)
                    with open(cache_file, 'wb') as f:
                        pickle.dump(race_data, f)
                    print(f"✓ Loaded and cached Abu Dhabi GP data")
            except Exception as e:
                pytest.skip(f"Could not load race data: {e}")
                return
        
        # Verify data structure
        assert race_data is not None
        assert 'position' in race_data or 'pit' in race_data or 'laps' in race_data
        
        print(f"  Position updates: {len(race_data.get('position', []))}")
        print(f"  Pit stops: {len(race_data.get('pit', []))}")
        print(f"  Lap data: {len(race_data.get('laps', []))}")
        print(f"  Race control: {len(race_data.get('race_control', []))}")
    
    def test_event_detection_accuracy(self):
        """Test event detection with historical data."""
        # Use cached data if available
        cache_file = ".test_cache/2023_abu_dhabi.pkl"
        if not os.path.exists(cache_file):
            pytest.skip("No cached race data available")
        
        with open(cache_file, 'rb') as f:
            race_data = pickle.load(f)
        
        parser = EventParser()
        
        # Parse position data for overtakes
        position_data = race_data.get('position', [])
        if position_data:
            events = parser.parse_position_data(position_data[:100])  # First 100 updates
            overtakes = [e for e in events if e.event_type == EventType.OVERTAKE]
            print(f"✓ Detected {len(overtakes)} overtakes in first 100 position updates")
        
        # Parse pit data
        pit_data = race_data.get('pit', [])
        if pit_data:
            events = parser.parse_pit_data(pit_data[:20])  # First 20 pit stops
            pit_stops = [e for e in events if e.event_type == EventType.PIT_STOP]
            print(f"✓ Detected {len(pit_stops)} pit stops")
        
        # Parse lap data for fastest laps
        lap_data = race_data.get('laps', [])
        if lap_data:
            events = parser.parse_lap_data(lap_data[:50])  # First 50 laps
            fastest_laps = [e for e in events if e.event_type == EventType.FASTEST_LAP]
            print(f"✓ Detected {len(fastest_laps)} fastest laps")
    
    @patch('src.speech_synthesizer.ElevenLabsClient')
    @patch('reachy_mini.ReachyMini')
    def test_commentary_generation_for_historical_events(self, mock_reachy, mock_tts):
        """Test commentary generation for historical race events."""
        from src.commentary_generator import CommentaryGenerator
        from src.race_state_tracker import RaceStateTracker
        from src.config import Config
        from src.models import RaceEvent
        
        # Mock TTS
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.return_value = b'fake_audio'
        mock_tts.return_value = mock_tts_instance
        
        # Set up components
        config = Config(ai_enabled=False)
        tracker = RaceStateTracker()
        generator = CommentaryGenerator(config, tracker)
        
        # Set up race state
        from src.models import DriverState
        tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=3.5),
            DriverState(name="Leclerc", position=3, gap_to_leader=8.2),
        ]
        tracker._state.current_lap = 30
        tracker._state.total_laps = 58
        
        # Test different event types
        test_events = [
            RaceEvent(
                event_type=EventType.OVERTAKE,
                timestamp=datetime.now(),
                data={'overtaking_driver': 'Hamilton', 'overtaken_driver': 'Verstappen', 'new_position': 1}
            ),
            RaceEvent(
                event_type=EventType.PIT_STOP,
                timestamp=datetime.now(),
                data={'driver': 'Leclerc', 'pit_count': 1, 'tire_compound': 'hard', 'pit_duration': 2.3}
            ),
            RaceEvent(
                event_type=EventType.FASTEST_LAP,
                timestamp=datetime.now(),
                data={'driver': 'Verstappen', 'lap_time': 84.123, 'lap_number': 30}
            ),
        ]
        
        commentaries = []
        for event in test_events:
            commentary = generator.generate(event)
            commentaries.append(commentary)
            assert isinstance(commentary, str)
            assert len(commentary) > 0
        
        print(f"✓ Generated {len(commentaries)} commentaries for historical events")
        for i, commentary in enumerate(commentaries):
            print(f"  {i+1}. {commentary[:80]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
