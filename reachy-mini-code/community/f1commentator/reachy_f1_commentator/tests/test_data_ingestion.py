"""
Unit tests for Data Ingestion Module.

Tests OpenF1 API client, event parsers, and data ingestion orchestrator.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests

from reachy_f1_commentator.src.data_ingestion import OpenF1Client, EventParser, DataIngestionModule
from reachy_f1_commentator.src.models import EventType, RaceEvent
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.event_queue import PriorityEventQueue


class TestOpenF1Client:
    """Test OpenF1 API client functionality."""
    
    def test_client_initialization(self):
        """Test client initializes with correct parameters."""
        client = OpenF1Client("test_key", "https://api.test.com")
        assert client.api_key == "test_key"
        assert client.base_url == "https://api.test.com"
        assert not client._authenticated
    
    @patch('src.data_ingestion.requests.Session')
    def test_authenticate_success(self, mock_session_class):
        """Test successful authentication."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = OpenF1Client("test_key")
        result = client.authenticate()
        
        assert result is True
        assert client._authenticated is True
        assert mock_session.get.called
    
    @patch('src.data_ingestion.requests.Session')
    def test_authenticate_failure(self, mock_session_class):
        """Test authentication failure handling."""
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        mock_session_class.return_value = mock_session
        
        client = OpenF1Client("test_key")
        result = client.authenticate()
        
        assert result is False
        assert client._authenticated is False
    
    @patch('src.data_ingestion.requests.Session')
    def test_poll_endpoint_success(self, mock_session_class):
        """Test successful endpoint polling."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"driver": "VER", "position": 1}]
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = OpenF1Client("test_key")
        client._authenticated = True
        client.session = mock_session
        
        result = client.poll_endpoint("/position")
        
        assert result is not None
        assert len(result) == 1
        assert result[0]["driver"] == "VER"
    
    @patch('src.data_ingestion.requests.Session')
    def test_poll_endpoint_retry_on_timeout(self, mock_session_class):
        """Test retry logic on timeout."""
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.Timeout("Timeout")
        mock_session_class.return_value = mock_session
        
        client = OpenF1Client("test_key")
        client._authenticated = True
        client.session = mock_session
        client._max_retries = 2
        client._retry_delay = 0.1
        
        result = client.poll_endpoint("/position")
        
        assert result is None
        assert mock_session.get.call_count == 2
    
    @patch('src.data_ingestion.requests.Session')
    def test_poll_endpoint_returns_dict_as_list(self, mock_session_class):
        """Test that single dict response is converted to list."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"driver": "VER", "position": 1}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        client = OpenF1Client("test_key")
        client._authenticated = True
        client.session = mock_session
        
        result = client.poll_endpoint("/position")
        
        assert isinstance(result, list)
        assert len(result) == 1


class TestEventParser:
    """Test event parsing functionality."""
    
    def test_parse_position_data_overtake(self):
        """Test overtake detection from position data."""
        parser = EventParser()
        
        # Set initial positions
        parser._last_positions = {"VER": 2, "HAM": 1}
        parser._last_position_time = {
            "VER": datetime.now() - timedelta(seconds=2),
            "HAM": datetime.now() - timedelta(seconds=2)
        }
        
        # New positions: VER overtakes HAM
        data = [
            {"driver": "VER", "position": 1, "lap_number": 5},
            {"driver": "HAM", "position": 2, "lap_number": 5}
        ]
        
        events = parser.parse_position_data(data)
        
        # Should detect overtake and position update
        overtake_events = [e for e in events if e.event_type == EventType.OVERTAKE]
        assert len(overtake_events) == 1
        assert overtake_events[0].data['overtaking_driver'] == "VER"
        assert overtake_events[0].data['overtaken_driver'] == "HAM"
    
    def test_parse_position_data_lead_change(self):
        """Test lead change detection."""
        parser = EventParser()
        
        # Set initial leader
        parser._last_positions = {"VER": 1, "HAM": 2}
        parser._last_leader = "VER"
        parser._last_position_time = {
            "VER": datetime.now() - timedelta(seconds=2),
            "HAM": datetime.now() - timedelta(seconds=2)
        }
        
        # New positions: HAM takes lead
        data = [
            {"driver": "HAM", "position": 1, "lap_number": 10},
            {"driver": "VER", "position": 2, "lap_number": 10}
        ]
        
        events = parser.parse_position_data(data)
        
        # Should detect lead change
        lead_change_events = [e for e in events if e.event_type == EventType.LEAD_CHANGE]
        assert len(lead_change_events) == 1
        assert lead_change_events[0].data['new_leader'] == "HAM"
        assert lead_change_events[0].data['old_leader'] == "VER"
    
    def test_parse_position_data_false_overtake_filter(self):
        """Test that rapid position swaps are filtered out."""
        parser = EventParser()
        
        # Set initial positions with very recent timestamp
        parser._last_positions = {"VER": 2, "HAM": 1}
        parser._last_position_time = {
            "VER": datetime.now() - timedelta(milliseconds=100),
            "HAM": datetime.now() - timedelta(milliseconds=100)
        }
        
        # New positions: VER overtakes HAM (but too soon)
        data = [
            {"driver": "VER", "position": 1, "lap_number": 5},
            {"driver": "HAM", "position": 2, "lap_number": 5}
        ]
        
        events = parser.parse_position_data(data)
        
        # Should NOT detect overtake due to false overtake filter
        overtake_events = [e for e in events if e.event_type == EventType.OVERTAKE]
        assert len(overtake_events) == 0
    
    def test_parse_pit_data(self):
        """Test pit stop detection."""
        parser = EventParser()
        
        data = [
            {
                "driver": "VER",
                "pit_duration": 2.3,
                "lap_number": 15,
                "tire_compound": "soft"
            }
        ]
        
        events = parser.parse_pit_data(data)
        
        assert len(events) == 1
        assert events[0].event_type == EventType.PIT_STOP
        assert events[0].data['driver'] == "VER"
        assert events[0].data['pit_duration'] == 2.3
        assert events[0].data['tire_compound'] == "soft"
    
    def test_parse_lap_data_fastest_lap(self):
        """Test fastest lap detection."""
        parser = EventParser()
        
        # First lap
        data1 = [{"driver": "VER", "lap_duration": 90.5, "lap_number": 1}]
        events1 = parser.parse_lap_data(data1)
        
        assert len(events1) == 1
        assert events1[0].event_type == EventType.FASTEST_LAP
        assert events1[0].data['driver'] == "VER"
        
        # Slower lap (should not trigger)
        data2 = [{"driver": "HAM", "lap_duration": 91.0, "lap_number": 2}]
        events2 = parser.parse_lap_data(data2)
        
        assert len(events2) == 0
        
        # Faster lap (should trigger)
        data3 = [{"driver": "HAM", "lap_duration": 89.8, "lap_number": 3}]
        events3 = parser.parse_lap_data(data3)
        
        assert len(events3) == 1
        assert events3[0].data['driver'] == "HAM"
        assert events3[0].data['lap_time'] == 89.8
    
    def test_parse_race_control_flag(self):
        """Test flag detection from race control."""
        parser = EventParser()
        
        data = [
            {
                "message": "YELLOW FLAG in sector 2",
                "category": "Flag",
                "lap_number": 20,
                "sector": "2"
            }
        ]
        
        events = parser.parse_race_control_data(data)
        
        flag_events = [e for e in events if e.event_type == EventType.FLAG]
        assert len(flag_events) == 1
        assert flag_events[0].data['flag_type'] == "yellow"
    
    def test_parse_race_control_safety_car(self):
        """Test safety car detection."""
        parser = EventParser()
        
        data = [
            {
                "message": "SAFETY CAR deployed",
                "category": "SafetyCar",
                "lap_number": 25
            }
        ]
        
        events = parser.parse_race_control_data(data)
        
        sc_events = [e for e in events if e.event_type == EventType.SAFETY_CAR]
        assert len(sc_events) == 1
        assert sc_events[0].data['status'] == "deployed"
    
    def test_parse_race_control_incident(self):
        """Test incident detection."""
        parser = EventParser()
        
        data = [
            {
                "message": "Incident involving car 44",
                "category": "Incident",
                "lap_number": 30
            }
        ]
        
        events = parser.parse_race_control_data(data)
        
        incident_events = [e for e in events if e.event_type == EventType.INCIDENT]
        assert len(incident_events) == 1
        assert "Incident" in incident_events[0].data['description']
    
    def test_parse_empty_data(self):
        """Test handling of empty data."""
        parser = EventParser()
        
        assert parser.parse_position_data([]) == []
        assert parser.parse_pit_data([]) == []
        assert parser.parse_lap_data([]) == []
        assert parser.parse_race_control_data([]) == []
    
    def test_parse_malformed_data(self):
        """Test handling of malformed data."""
        parser = EventParser()
        
        # Missing required fields
        data = [{"invalid": "data"}]
        
        # Should not crash, just return empty or skip
        events = parser.parse_position_data(data)
        # Position update might still be created with empty positions
        assert isinstance(events, list)


class TestDataIngestionModule:
    """Test data ingestion module orchestrator."""
    
    @patch('src.data_ingestion.OpenF1Client')
    def test_module_initialization(self, mock_client_class):
        """Test module initializes correctly."""
        config = Config()
        event_queue = PriorityEventQueue()
        
        module = DataIngestionModule(config, event_queue)
        
        assert module.config == config
        assert module.event_queue == event_queue
        assert not module._running
    
    @patch('src.data_ingestion.OpenF1Client')
    def test_start_success(self, mock_client_class):
        """Test successful module start."""
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        config = Config()
        event_queue = PriorityEventQueue()
        module = DataIngestionModule(config, event_queue)
        
        result = module.start()
        
        assert result is True
        assert module._running is True
        assert len(module._threads) == 4  # 4 endpoints
        
        # Cleanup
        module.stop()
    
    @patch('src.data_ingestion.OpenF1Client')
    def test_start_authentication_failure(self, mock_client_class):
        """Test module start fails if authentication fails."""
        mock_client = Mock()
        mock_client.authenticate.return_value = False
        mock_client_class.return_value = mock_client
        
        config = Config()
        event_queue = PriorityEventQueue()
        module = DataIngestionModule(config, event_queue)
        
        result = module.start()
        
        assert result is False
        assert module._running is False
    
    @patch('src.data_ingestion.OpenF1Client')
    def test_stop(self, mock_client_class):
        """Test module stop."""
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        config = Config()
        event_queue = PriorityEventQueue()
        module = DataIngestionModule(config, event_queue)
        
        module.start()
        time.sleep(0.1)  # Let threads start
        module.stop()
        
        assert module._running is False
        assert len(module._threads) == 0
    
    @patch('src.data_ingestion.OpenF1Client')
    def test_poll_loop_emits_events(self, mock_client_class):
        """Test that polling loop emits events to queue."""
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client.poll_endpoint.return_value = [
            {"driver": "VER", "position": 1, "lap_number": 1}
        ]
        mock_client_class.return_value = mock_client
        
        config = Config()
        config.position_poll_interval = 0.1
        event_queue = PriorityEventQueue()
        module = DataIngestionModule(config, event_queue)
        module.client = mock_client
        
        module.start()
        time.sleep(0.3)  # Let it poll a few times
        module.stop()
        
        # Should have some events in queue
        assert event_queue.size() > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
