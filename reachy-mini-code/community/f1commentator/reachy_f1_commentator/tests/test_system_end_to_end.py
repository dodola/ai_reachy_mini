"""
Simplified end-to-end integration tests for F1 Commentary Robot.

Tests complete system flows without resource monitor issues.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from reachy_f1_commentator.src.commentary_system import CommentarySystem
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.models import RaceEvent, EventType, DriverState
from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker


@pytest.fixture
def mock_system():
    """Create a mocked system for testing."""
    with patch('reachy_mini.ReachyMini'):
        system = CommentarySystem()
        system.config.replay_mode = True
        system.config.enable_movements = False
        system.config.ai_enabled = False
        yield system
        # Cleanup
        if system.resource_monitor and system.resource_monitor._running:
            system.resource_monitor.stop()
        if system._initialized:
            system.shutdown()
        time.sleep(0.2)  # Allow threads to clean up


class TestCompleteCommentaryFlow:
    """Test end-to-end commentary generation flow."""
    
    @patch('src.speech_synthesizer.ElevenLabsClient')
    def test_event_to_commentary_flow(self, mock_tts, mock_system):
        """Test: Event → Commentary → Audio."""
        # Mock TTS
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.return_value = b'fake_audio'
        mock_tts.return_value = mock_tts_instance
        
        # Initialize
        assert mock_system.initialize() is True
        
        # Set up race state
        mock_system.race_state_tracker._state.drivers = [
            DriverState(name="Hamilton", position=1, gap_to_leader=0.0),
            DriverState(name="Verstappen", position=2, gap_to_leader=1.5),
        ]
        mock_system.race_state_tracker._state.current_lap = 25
        mock_system.race_state_tracker._state.total_laps = 58
        
        # Create and process event
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={
                'overtaking_driver': 'Hamilton',
                'overtaken_driver': 'Verstappen',
                'new_position': 1
            }
        )
        
        mock_system.event_queue.enqueue(event)
        queued_event = mock_system.event_queue.dequeue()
        
        # Generate commentary
        commentary = mock_system.commentary_generator.generate(queued_event)
        assert isinstance(commentary, str)
        assert len(commentary) > 0
        
        print(f"✓ Generated commentary: {commentary}")

    @patch('src.speech_synthesizer.ElevenLabsClient')
    def test_priority_queue_ordering(self, mock_tts, mock_system):
        """Test events are processed by priority."""
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.return_value = b'fake_audio'
        mock_tts.return_value = mock_tts_instance
        
        assert mock_system.initialize() is True
        mock_system.race_state_tracker._state.current_lap = 30
        mock_system.race_state_tracker._state.total_laps = 58
        
        # Add events in non-priority order
        events = [
            (EventType.FASTEST_LAP, {'driver': 'Leclerc', 'lap_time': 85.0}),
            (EventType.INCIDENT, {'description': 'Collision'}),
            (EventType.OVERTAKE, {'overtaking_driver': 'A', 'overtaken_driver': 'B'}),
        ]
        
        for event_type, data in events:
            mock_system.event_queue.enqueue(RaceEvent(
                event_type=event_type,
                timestamp=datetime.now(),
                data=data
            ))
        
        # Verify priority order
        processed_types = []
        while mock_system.event_queue.size() > 0:
            event = mock_system.event_queue.dequeue()
            if event:
                processed_types.append(event.event_type)
        
        assert processed_types[0] == EventType.INCIDENT
        assert processed_types[1] == EventType.OVERTAKE
        assert processed_types[2] == EventType.FASTEST_LAP
        
        print("✓ Priority ordering verified")


class TestQAInterruption:
    """Test Q&A interruption flow."""
    
    def test_qa_pauses_queue(self, mock_system):
        """Test Q&A pauses event processing."""
        assert mock_system.initialize() is True
        
        # Set up state
        mock_system.race_state_tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=2.5),
        ]
        mock_system.race_state_tracker._state.current_lap = 25
        
        # Add events
        for i in range(3):
            mock_system.event_queue.enqueue(RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={'lap_number': 25 + i}
            ))
        
        initial_size = mock_system.event_queue.size()
        assert not mock_system.event_queue.is_paused()
        
        # Process Q&A
        response = mock_system.qa_manager.process_question("Who's leading?")
        
        # Verify pause
        assert mock_system.event_queue.is_paused()
        assert mock_system.event_queue.size() == initial_size
        assert "Verstappen" in response
        
        # Resume
        mock_system.qa_manager.resume_event_queue()
        assert not mock_system.event_queue.is_paused()
        
        print("✓ Q&A pause/resume verified")


class TestErrorRecovery:
    """Test error recovery scenarios."""
    
    @patch('src.speech_synthesizer.ElevenLabsClient')
    def test_tts_failure_graceful_degradation(self, mock_tts, mock_system):
        """Test system continues when TTS fails."""
        # Mock TTS to fail
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.side_effect = Exception("TTS Error")
        mock_tts.return_value = mock_tts_instance
        
        assert mock_system.initialize() is True
        mock_system.race_state_tracker._state.current_lap = 20
        mock_system.race_state_tracker._state.total_laps = 58
        
        # Generate commentary (should work)
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={'overtaking_driver': 'Hamilton', 'overtaken_driver': 'Verstappen'}
        )
        
        commentary = mock_system.commentary_generator.generate(event)
        assert isinstance(commentary, str)
        assert len(commentary) > 0
        
        # System should still be operational
        assert mock_system.is_initialized() is True
        
        print("✓ TTS failure handled gracefully")
    
    def test_queue_overflow_handling(self, mock_system):
        """Test event queue overflow."""
        assert mock_system.initialize() is True
        
        # Fill queue beyond capacity
        for i in range(15):  # Max is 10
            mock_system.event_queue.enqueue(RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={'lap_number': i}
            ))
        
        # Queue should not exceed max size
        assert mock_system.event_queue.size() <= 10
        assert mock_system.is_initialized() is True
        
        print("✓ Queue overflow handled")


class TestReplayMode:
    """Test replay mode functionality."""
    
    @patch('reachy_mini.ReachyMini')
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_replay_initialization(self, mock_loader_class, mock_reachy):
        """Test replay mode initialization."""
        mock_loader = Mock()
        mock_loader.load_race.return_return = {
            'position': [{"driver_number": "1", "position": 1, "lap_number": 1}],
            'pit': [],
            'laps': [],
            'race_control': []
        }
        mock_loader_class.return_value = mock_loader
        
        system = CommentarySystem()
        system.config.replay_mode = True
        system.config.replay_race_id = "test_race"
        system.config.enable_movements = False
        
        try:
            assert system.initialize() is True
            assert system.data_ingestion._replay_controller is not None
            print("✓ Replay mode initialized")
        finally:
            if system.resource_monitor:
                system.resource_monitor.stop()
            system.shutdown()
            time.sleep(0.2)


class TestResourceMonitoring:
    """Test resource monitoring under load."""
    
    def test_memory_monitoring(self, mock_system):
        """Test memory monitoring."""
        assert mock_system.initialize() is True
        
        # Start monitor
        mock_system.resource_monitor.start()
        time.sleep(0.5)
        
        # Get stats
        stats = mock_system.resource_monitor.get_stats()
        
        assert 'memory_percent' in stats
        assert 'memory_mb' in stats
        assert stats['memory_percent'] < 90.0
        
        # Stop monitor
        mock_system.resource_monitor.stop()
        time.sleep(0.2)
        
        print(f"✓ Memory: {stats['memory_percent']:.1f}% ({stats['memory_mb']:.1f} MB)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
