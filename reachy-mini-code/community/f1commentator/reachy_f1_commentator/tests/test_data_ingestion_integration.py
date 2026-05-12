"""
Integration tests for Data Ingestion Module.

Tests end-to-end functionality with mocked API responses.
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime

from reachy_f1_commentator.src.data_ingestion import DataIngestionModule
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.models import EventType


class TestDataIngestionIntegration:
    """Integration tests for complete data ingestion flow."""
    
    @patch('src.data_ingestion.requests.Session')
    def test_end_to_end_position_data_flow(self, mock_session_class):
        """Test complete flow from API poll to event queue."""
        # Setup mock responses
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        
        # First call: authentication
        mock_response.json.return_value = []
        
        # Subsequent calls: position data
        position_data = [
            {"driver": "VER", "position": 1, "lap_number": 5},
            {"driver": "HAM", "position": 2, "lap_number": 5}
        ]
        
        mock_session.get.side_effect = [
            mock_response,  # Auth call
            Mock(status_code=200, json=lambda: position_data),  # Position poll
            Mock(status_code=200, json=lambda: []),  # Pit poll
            Mock(status_code=200, json=lambda: []),  # Laps poll
            Mock(status_code=200, json=lambda: []),  # Race control poll
        ]
        
        mock_session_class.return_value = mock_session
        
        # Setup module
        config = Config()
        config.position_poll_interval = 0.1
        config.pit_poll_interval = 0.1
        config.laps_poll_interval = 0.1
        config.race_control_poll_interval = 0.1
        
        event_queue = PriorityEventQueue()
        module = DataIngestionModule(config, event_queue)
        
        # Start and let it run briefly
        module.start()
        time.sleep(0.3)
        module.stop()
        
        # Verify events were queued
        assert event_queue.size() > 0
        
        # Dequeue and verify event
        event = event_queue.dequeue()
        assert event is not None
        assert event.event_type == EventType.POSITION_UPDATE
    
    def test_overtake_detection_integration(self):
        """Test overtake detection from position changes using parser directly."""
        from src.data_ingestion import EventParser
        
        parser = EventParser()
        
        # First position update
        initial_positions = [
            {"driver": "VER", "position": 2, "lap_number": 5},
            {"driver": "HAM", "position": 1, "lap_number": 5}
        ]
        
        events1 = parser.parse_position_data(initial_positions)
        # Should just be position update, no overtake yet
        overtake_events1 = [e for e in events1 if e.event_type == EventType.OVERTAKE]
        assert len(overtake_events1) == 0
        
        # Wait to avoid false overtake filter
        time.sleep(0.6)
        
        # Second position update - VER overtakes HAM
        new_positions = [
            {"driver": "VER", "position": 1, "lap_number": 6},
            {"driver": "HAM", "position": 2, "lap_number": 6}
        ]
        
        events2 = parser.parse_position_data(new_positions)
        
        # Should detect overtake
        overtake_events2 = [e for e in events2 if e.event_type == EventType.OVERTAKE]
        assert len(overtake_events2) == 1
        assert overtake_events2[0].data['overtaking_driver'] == "VER"
        assert overtake_events2[0].data['overtaken_driver'] == "HAM"
    
    @patch('src.data_ingestion.requests.Session')
    def test_multiple_event_types_integration(self, mock_session_class):
        """Test detection of multiple event types simultaneously."""
        mock_session = Mock()
        
        # Setup various event data
        position_data = [{"driver": "VER", "position": 1, "lap_number": 10}]
        pit_data = [{"driver": "HAM", "pit_duration": 2.5, "lap_number": 10}]
        lap_data = [{"driver": "VER", "lap_duration": 89.5, "lap_number": 10}]
        race_control_data = [{"message": "YELLOW FLAG in sector 2", "lap_number": 10}]
        
        call_count = [0]
        
        def get_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return Mock(status_code=200, json=lambda: [])  # Auth
            elif '/position' in args[0]:
                return Mock(status_code=200, json=lambda: position_data)
            elif '/pit' in args[0]:
                return Mock(status_code=200, json=lambda: pit_data)
            elif '/laps' in args[0]:
                return Mock(status_code=200, json=lambda: lap_data)
            elif '/race_control' in args[0]:
                return Mock(status_code=200, json=lambda: race_control_data)
            else:
                return Mock(status_code=200, json=lambda: [])
        
        mock_session.get.side_effect = get_side_effect
        mock_session_class.return_value = mock_session
        
        # Setup module
        config = Config()
        config.position_poll_interval = 0.1
        config.pit_poll_interval = 0.1
        config.laps_poll_interval = 0.1
        config.race_control_poll_interval = 0.1
        
        event_queue = PriorityEventQueue()
        module = DataIngestionModule(config, event_queue)
        
        # Start and let it run
        module.start()
        time.sleep(0.5)
        module.stop()
        
        # Collect all event types
        event_types = set()
        while event_queue.size() > 0:
            event = event_queue.dequeue()
            if event:
                event_types.add(event.event_type)
        
        # Should have detected multiple event types
        assert EventType.POSITION_UPDATE in event_types
        assert EventType.PIT_STOP in event_types
        assert EventType.FASTEST_LAP in event_types
        assert EventType.FLAG in event_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
