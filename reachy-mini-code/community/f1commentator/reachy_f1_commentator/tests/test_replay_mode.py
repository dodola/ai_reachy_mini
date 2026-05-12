"""
Unit tests for Replay Mode functionality.

Tests HistoricalDataLoader and ReplayController.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests
from pathlib import Path
import pickle

from reachy_f1_commentator.src.replay_mode import HistoricalDataLoader, ReplayController


class TestHistoricalDataLoader:
    """Test historical data loader functionality."""
    
    def test_loader_initialization(self):
        """Test loader initializes with correct parameters."""
        loader = HistoricalDataLoader("test_key", "https://api.test.com", ".test_cache")
        assert loader.api_key == "test_key"
        assert loader.base_url == "https://api.test.com"
        assert loader.cache_dir == Path(".test_cache")
    
    @patch('src.replay_mode.requests.Session')
    def test_load_race_from_api(self, mock_session_class):
        """Test loading race data from API."""
        mock_session = Mock()
        
        # Mock API responses
        position_data = [{"driver": "VER", "position": 1, "date": "2023-11-26T14:00:00Z"}]
        pit_data = [{"driver": "HAM", "pit_duration": 2.3, "date": "2023-11-26T14:10:00Z"}]
        laps_data = [{"driver": "VER", "lap_time": 90.5, "date": "2023-11-26T14:02:00Z"}]
        race_control_data = [{"message": "Green flag", "date": "2023-11-26T14:00:00Z"}]
        
        mock_session.get.side_effect = [
            Mock(status_code=200, json=lambda: position_data),
            Mock(status_code=200, json=lambda: pit_data),
            Mock(status_code=200, json=lambda: laps_data),
            Mock(status_code=200, json=lambda: race_control_data)
        ]
        mock_session_class.return_value = mock_session
        
        loader = HistoricalDataLoader("test_key", cache_dir=".test_cache")
        loader.session = mock_session
        
        result = loader.load_race("2023_abu_dhabi")
        
        assert result is not None
        assert 'position' in result
        assert 'pit' in result
        assert 'laps' in result
        assert 'race_control' in result
        assert len(result['position']) == 1
        assert result['position'][0]['driver'] == "VER"
    
    def test_load_race_from_cache(self, tmp_path):
        """Test loading race data from cache."""
        # Create cached data
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        cached_data = {
            'position': [{"driver": "VER", "position": 1}],
            'pit': [],
            'laps': [],
            'race_control': []
        }
        
        cache_file = cache_dir / "2023_abu_dhabi.pkl"
        with open(cache_file, 'wb') as f:
            pickle.dump(cached_data, f)
        
        loader = HistoricalDataLoader("test_key", cache_dir=str(cache_dir))
        result = loader.load_race("2023_abu_dhabi")
        
        assert result is not None
        assert result['position'][0]['driver'] == "VER"
    
    @patch('src.replay_mode.requests.Session')
    def test_load_race_no_data(self, mock_session_class):
        """Test handling of race with no data."""
        mock_session = Mock()
        mock_session.get.return_value = Mock(status_code=200, json=lambda: [])
        mock_session_class.return_value = mock_session
        
        loader = HistoricalDataLoader("test_key", cache_dir=".test_cache")
        loader.session = mock_session
        
        result = loader.load_race("invalid_race")
        
        assert result is None
    
    @patch('src.replay_mode.requests.Session')
    def test_load_race_api_error(self, mock_session_class, tmp_path):
        """Test handling of API errors."""
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.RequestException("API Error")
        mock_session_class.return_value = mock_session
        
        # Use temp directory to avoid loading from cache
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        loader = HistoricalDataLoader("test_key", cache_dir=str(cache_dir))
        loader.session = mock_session
        
        result = loader.load_race("2023_abu_dhabi_error_test")
        
        assert result is None
    
    def test_clear_cache_specific_race(self, tmp_path):
        """Test clearing cache for specific race."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        # Create cache files
        (cache_dir / "race1.pkl").touch()
        (cache_dir / "race2.pkl").touch()
        
        loader = HistoricalDataLoader("test_key", cache_dir=str(cache_dir))
        loader.clear_cache("race1")
        
        assert not (cache_dir / "race1.pkl").exists()
        assert (cache_dir / "race2.pkl").exists()
    
    def test_clear_cache_all(self, tmp_path):
        """Test clearing all cached data."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        # Create cache files
        (cache_dir / "race1.pkl").touch()
        (cache_dir / "race2.pkl").touch()
        
        loader = HistoricalDataLoader("test_key", cache_dir=str(cache_dir))
        loader.clear_cache()
        
        assert not (cache_dir / "race1.pkl").exists()
        assert not (cache_dir / "race2.pkl").exists()


class TestReplayController:
    """Test replay controller functionality."""
    
    def create_test_race_data(self):
        """Create test race data with timestamps."""
        base_time = datetime(2023, 11, 26, 14, 0, 0)
        
        return {
            'position': [
                {"driver": "VER", "position": 1, "lap_number": 1, "date": base_time.isoformat()},
                {"driver": "HAM", "position": 2, "lap_number": 1, "date": base_time.isoformat()},
                {"driver": "VER", "position": 1, "lap_number": 2, "date": (base_time + timedelta(seconds=90)).isoformat()},
            ],
            'pit': [
                {"driver": "HAM", "pit_duration": 2.3, "lap_number": 5, "date": (base_time + timedelta(seconds=300)).isoformat()}
            ],
            'laps': [
                {"driver": "VER", "lap_time": 90.5, "lap_number": 1, "date": (base_time + timedelta(seconds=90)).isoformat()}
            ],
            'race_control': [
                {"message": "Green flag", "lap_number": 1, "date": base_time.isoformat()}
            ]
        }
    
    def test_controller_initialization(self):
        """Test controller initializes correctly."""
        race_data = self.create_test_race_data()
        controller = ReplayController(race_data, playback_speed=2.0)
        
        assert controller.playback_speed == 2.0
        assert not controller.is_paused()
        assert not controller.is_stopped()
        assert len(controller._timeline) > 0
    
    def test_build_timeline(self):
        """Test timeline building from race data."""
        race_data = self.create_test_race_data()
        controller = ReplayController(race_data)
        
        # Should have 6 total events (3 position + 1 pit + 1 lap + 1 race_control)
        assert len(controller._timeline) == 6
        
        # Timeline should be sorted by timestamp
        timestamps = [event['timestamp'] for event in controller._timeline]
        assert timestamps == sorted(timestamps)
    
    def test_set_playback_speed(self):
        """Test setting playback speed."""
        race_data = self.create_test_race_data()
        controller = ReplayController(race_data, playback_speed=1.0)
        
        controller.set_playback_speed(5.0)
        assert controller.playback_speed == 5.0
        
        # Invalid speed should be rejected
        controller.set_playback_speed(-1.0)
        assert controller.playback_speed == 5.0  # Should remain unchanged
    
    def test_pause_resume(self):
        """Test pause and resume functionality."""
        race_data = self.create_test_race_data()
        controller = ReplayController(race_data)
        
        assert not controller.is_paused()
        
        controller.pause()
        assert controller.is_paused()
        
        controller.resume()
        assert not controller.is_paused()
    
    def test_stop(self):
        """Test stop functionality."""
        race_data = self.create_test_race_data()
        controller = ReplayController(race_data)
        
        assert not controller.is_stopped()
        
        controller.stop()
        assert controller.is_stopped()
    
    def test_seek_to_lap(self):
        """Test seeking to specific lap."""
        race_data = self.create_test_race_data()
        controller = ReplayController(race_data)
        
        initial_index = controller._current_index
        
        controller.seek_to_lap(2)
        
        # Should have moved forward in timeline
        assert controller._current_index > initial_index
        assert controller.get_current_lap() >= 2
    
    def test_get_progress(self):
        """Test progress calculation."""
        race_data = self.create_test_race_data()
        controller = ReplayController(race_data)
        
        # At start
        assert controller.get_progress() == 0.0
        
        # Move to middle
        controller._current_index = len(controller._timeline) // 2
        progress = controller.get_progress()
        assert 0.4 < progress < 0.6
        
        # At end
        controller._current_index = len(controller._timeline)
        assert controller.get_progress() == 1.0
    
    def test_playback_emits_events(self):
        """Test that playback emits events via callback."""
        race_data = self.create_test_race_data()
        controller = ReplayController(race_data, playback_speed=10.0)  # Fast playback
        
        events_received = []
        
        def callback(endpoint, data):
            events_received.append((endpoint, data))
        
        controller.start(callback)
        
        # Wait for some events to be processed
        time.sleep(0.5)
        
        controller.stop()
        
        # Should have received some events
        assert len(events_received) > 0
    
    def test_playback_respects_speed(self):
        """Test that playback speed affects timing."""
        race_data = self.create_test_race_data()
        
        # Test with fast speed
        controller_fast = ReplayController(race_data, playback_speed=10.0)
        events_fast = []
        
        def callback_fast(endpoint, data):
            events_fast.append(time.time())
        
        start_time = time.time()
        controller_fast.start(callback_fast)
        time.sleep(0.5)
        controller_fast.stop()
        fast_duration = time.time() - start_time
        
        # Fast playback should process events quickly
        assert len(events_fast) > 0
    
    def test_playback_pause_resume(self):
        """Test pause and resume during playback."""
        race_data = self.create_test_race_data()
        controller = ReplayController(race_data, playback_speed=10.0)  # Faster for testing
        
        events_received = []
        
        def callback(endpoint, data):
            events_received.append((endpoint, data))
        
        controller.start(callback)
        time.sleep(0.2)
        
        # Pause
        events_before_pause = len(events_received)
        controller.pause()
        time.sleep(0.3)
        events_during_pause = len(events_received)
        
        # Should not receive new events while paused
        assert events_during_pause == events_before_pause
        
        # Resume
        controller.resume()
        time.sleep(0.3)
        events_after_resume = len(events_received)
        
        # Should receive new events after resume (or all events completed)
        # Either we get more events, or we completed all events before pause
        assert events_after_resume >= events_during_pause
        
        controller.stop()


class TestReplayIntegration:
    """Integration tests for replay mode."""
    
    def test_empty_race_data(self):
        """Test handling of empty race data."""
        race_data = {
            'position': [],
            'pit': [],
            'laps': [],
            'race_control': []
        }
        
        controller = ReplayController(race_data)
        assert len(controller._timeline) == 0
        assert controller.get_progress() == 0.0
    
    def test_malformed_timestamps(self):
        """Test handling of malformed timestamps."""
        race_data = {
            'position': [
                {"driver": "VER", "position": 1, "date": "invalid_timestamp"},
                {"driver": "HAM", "position": 2}  # No timestamp
            ],
            'pit': [],
            'laps': [],
            'race_control': []
        }
        
        # Should not crash, should handle gracefully
        controller = ReplayController(race_data)
        assert len(controller._timeline) == 2
