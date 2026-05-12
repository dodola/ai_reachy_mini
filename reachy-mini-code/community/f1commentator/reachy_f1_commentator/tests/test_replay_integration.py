"""
Integration tests for replay mode with DataIngestionModule.

Tests the integration of replay mode with the data ingestion module.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from reachy_f1_commentator.src.data_ingestion import DataIngestionModule
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.models import EventType


class TestReplayModeIntegration:
    """Test replay mode integration with DataIngestionModule."""
    
    def create_test_config(self, replay_mode=True):
        """Create test configuration."""
        config = Config()
        config.replay_mode = replay_mode
        config.replay_race_id = "2023_test_race"
        config.replay_speed = 2.0
        config.openf1_api_key = "test_key"
        return config
    
    def create_test_race_data(self):
        """Create test race data."""
        base_time = datetime(2023, 11, 26, 14, 0, 0)
        
        return {
            'position': [
                {"driver_number": "1", "position": 1, "lap_number": 1, "date": base_time.isoformat()},
                {"driver_number": "44", "position": 2, "lap_number": 1, "date": base_time.isoformat()},
            ],
            'pit': [
                {"driver_number": "44", "pit_duration": 2.3, "lap_number": 2, "date": (base_time + timedelta(seconds=100)).isoformat()}
            ],
            'laps': [
                {"driver_number": "1", "lap_duration": 90.5, "lap_number": 1, "date": (base_time + timedelta(seconds=90)).isoformat()}
            ],
            'race_control': [
                {"message": "Green flag", "lap_number": 1, "date": base_time.isoformat()}
            ]
        }
    
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_start_replay_mode(self, mock_loader_class):
        """Test starting data ingestion in replay mode."""
        config = self.create_test_config(replay_mode=True)
        event_queue = PriorityEventQueue(max_size=10)
        
        # Mock the loader
        mock_loader = Mock()
        mock_loader.load_race.return_value = self.create_test_race_data()
        mock_loader_class.return_value = mock_loader
        
        module = DataIngestionModule(config, event_queue)
        result = module.start()
        
        assert result is True
        assert module._running is True
        assert module._replay_controller is not None
        
        # Clean up
        module.stop()
    
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_replay_mode_emits_events(self, mock_loader_class):
        """Test that replay mode emits events to queue."""
        config = self.create_test_config(replay_mode=True)
        config.replay_speed = 10.0  # Fast playback
        event_queue = PriorityEventQueue(max_size=10)
        
        # Mock the loader
        mock_loader = Mock()
        mock_loader.load_race.return_value = self.create_test_race_data()
        mock_loader_class.return_value = mock_loader
        
        module = DataIngestionModule(config, event_queue)
        module.start()
        
        # Wait for events to be processed
        time.sleep(0.5)
        
        # Should have events in queue
        assert event_queue.size() > 0
        
        # Clean up
        module.stop()
    
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_replay_mode_no_race_data(self, mock_loader_class):
        """Test replay mode with no race data."""
        config = self.create_test_config(replay_mode=True)
        event_queue = PriorityEventQueue(max_size=10)
        
        # Mock the loader to return None
        mock_loader = Mock()
        mock_loader.load_race.return_value = None
        mock_loader_class.return_value = mock_loader
        
        module = DataIngestionModule(config, event_queue)
        result = module.start()
        
        assert result is False
        assert module._running is False
    
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_replay_pause_resume(self, mock_loader_class):
        """Test pause and resume in replay mode."""
        config = self.create_test_config(replay_mode=True)
        config.replay_speed = 5.0
        event_queue = PriorityEventQueue(max_size=10)
        
        # Mock the loader
        mock_loader = Mock()
        mock_loader.load_race.return_value = self.create_test_race_data()
        mock_loader_class.return_value = mock_loader
        
        module = DataIngestionModule(config, event_queue)
        module.start()
        
        # Pause
        module.pause_replay()
        assert module.is_replay_paused() is True
        
        # Resume
        module.resume_replay()
        assert module.is_replay_paused() is False
        
        # Clean up
        module.stop()
    
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_replay_seek_to_lap(self, mock_loader_class):
        """Test seeking to specific lap in replay mode."""
        config = self.create_test_config(replay_mode=True)
        event_queue = PriorityEventQueue(max_size=10)
        
        # Mock the loader
        mock_loader = Mock()
        mock_loader.load_race.return_value = self.create_test_race_data()
        mock_loader_class.return_value = mock_loader
        
        module = DataIngestionModule(config, event_queue)
        module.start()
        
        # Seek to lap 2
        module.seek_replay_to_lap(2)
        
        # Should not crash
        assert module._replay_controller is not None
        
        # Clean up
        module.stop()
    
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_replay_set_speed(self, mock_loader_class):
        """Test changing playback speed in replay mode."""
        config = self.create_test_config(replay_mode=True)
        event_queue = PriorityEventQueue(max_size=10)
        
        # Mock the loader
        mock_loader = Mock()
        mock_loader.load_race.return_value = self.create_test_race_data()
        mock_loader_class.return_value = mock_loader
        
        module = DataIngestionModule(config, event_queue)
        module.start()
        
        # Change speed
        module.set_replay_speed(5.0)
        
        # Should not crash
        assert module._replay_controller is not None
        
        # Clean up
        module.stop()
    
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_replay_get_progress(self, mock_loader_class):
        """Test getting replay progress."""
        config = self.create_test_config(replay_mode=True)
        event_queue = PriorityEventQueue(max_size=10)
        
        # Mock the loader
        mock_loader = Mock()
        mock_loader.load_race.return_value = self.create_test_race_data()
        mock_loader_class.return_value = mock_loader
        
        module = DataIngestionModule(config, event_queue)
        module.start()
        
        # Get progress
        progress = module.get_replay_progress()
        
        # Should be between 0 and 1
        assert 0.0 <= progress <= 1.0
        
        # Clean up
        module.stop()
    
    def test_live_mode_no_replay_controls(self):
        """Test that replay controls don't work in live mode."""
        config = self.create_test_config(replay_mode=False)
        event_queue = PriorityEventQueue(max_size=10)
        
        module = DataIngestionModule(config, event_queue)
        
        # These should not crash but should log warnings
        module.pause_replay()
        module.resume_replay()
        module.seek_replay_to_lap(5)
        module.set_replay_speed(2.0)
        
        # Progress should be 0 in live mode
        assert module.get_replay_progress() == 0.0
        assert module.is_replay_paused() is False
    
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_replay_mode_event_parsing(self, mock_loader_class):
        """Test that replay mode uses same event parsing as live mode."""
        config = self.create_test_config(replay_mode=True)
        config.replay_speed = 10.0
        event_queue = PriorityEventQueue(max_size=10)
        
        # Mock the loader
        mock_loader = Mock()
        mock_loader.load_race.return_value = self.create_test_race_data()
        mock_loader_class.return_value = mock_loader
        
        module = DataIngestionModule(config, event_queue)
        module.start()
        
        # Wait for events
        time.sleep(0.5)
        
        # Dequeue and check event types
        events_found = []
        while event_queue.size() > 0:
            event = event_queue.dequeue()
            if event:
                events_found.append(event.event_type)
        
        # Should have position updates at minimum
        assert EventType.POSITION_UPDATE in events_found
        
        # Clean up
        module.stop()
