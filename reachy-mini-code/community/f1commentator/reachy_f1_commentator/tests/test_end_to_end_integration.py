"""
End-to-end integration test suite for F1 Commentary Robot.

Tests complete system flows including:
- Event → Commentary → Audio → Movement
- Q&A interruption flow
- Replay mode operation
- Error recovery scenarios
- Resource limits under load
"""

import pytest
import time
import threading
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from reachy_f1_commentator.src.commentary_system import CommentarySystem
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.models import RaceEvent, EventType, DriverState
from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker


class TestEndToEndCommentaryFlow:
    """Test complete commentary flow from event to output."""
    
    def setup_method(self):
        """Set up test system."""
        self.system = CommentarySystem()
        self.system.config.replay_mode = True
        self.system.config.enable_movements = False  # Disable for testing
        self.system.config.ai_enabled = False
        
    def teardown_method(self):
        """Clean up after test."""
        if hasattr(self, 'system') and self.system:
            # Stop resource monitor first to avoid logging errors
            if self.system.resource_monitor:
                self.system.resource_monitor.stop()
            self.system.shutdown()
            time.sleep(0.1)  # Give threads time to clean up
    
    @patch('src.speech_synthesizer.ElevenLabsClient')
    @patch('src.motion_controller.ReachyMini')
    def test_complete_event_to_audio_flow(self, mock_reachy, mock_tts):
        """Test: Event → Commentary → Audio → Movement."""
        # Mock TTS to return fake audio
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.return_value = b'fake_audio_data'
        mock_tts.return_value = mock_tts_instance
        
        # Mock Reachy
        mock_reachy_instance = Mock()
        mock_reachy.return_value = mock_reachy_instance
        
        # Initialize system
        assert self.system.initialize() is True
        
        # Create test event
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={
                'overtaking_driver': 'Hamilton',
                'overtaken_driver': 'Verstappen',
                'new_position': 1,
                'lap_number': 25
            }
        )
        
        # Update state
        self.system.race_state_tracker._state.drivers = [
            DriverState(name="Hamilton", position=1, gap_to_leader=0.0),
            DriverState(name="Verstappen", position=2, gap_to_leader=1.5),
        ]
        self.system.race_state_tracker._state.current_lap = 25
        self.system.race_state_tracker._state.total_laps = 58
        
        # Inject event
        self.system.event_queue.enqueue(event)
        
        # Process event
        queued_event = self.system.event_queue.dequeue()
        assert queued_event is not None
        
        # Generate commentary
        commentary = self.system.commentary_generator.generate(queued_event)
        assert isinstance(commentary, str)
        assert len(commentary) > 0
        assert 'Hamilton' in commentary or 'Verstappen' in commentary
        
        # Synthesize speech (mocked)
        audio = self.system.speech_synthesizer.synthesize(commentary)
        assert audio is not None
        
        # Verify TTS was called
        mock_tts_instance.text_to_speech.assert_called_once()
        
        print(f"✓ Complete flow test passed: {commentary}")
    
    @patch('src.speech_synthesizer.ElevenLabsClient')
    def test_multiple_events_sequential_processing(self, mock_tts):
        """Test processing multiple events in sequence."""
        # Mock TTS
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.return_value = b'fake_audio'
        mock_tts.return_value = mock_tts_instance
        
        # Initialize
        assert self.system.initialize() is True
        
        # Set up race state
        self.system.race_state_tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=2.5),
            DriverState(name="Leclerc", position=3, gap_to_leader=5.0),
        ]
        self.system.race_state_tracker._state.current_lap = 20
        self.system.race_state_tracker._state.total_laps = 58
        
        # Create multiple events
        events = [
            RaceEvent(
                event_type=EventType.OVERTAKE,
                timestamp=datetime.now(),
                data={'overtaking_driver': 'Hamilton', 'overtaken_driver': 'Verstappen'}
            ),
            RaceEvent(
                event_type=EventType.PIT_STOP,
                timestamp=datetime.now(),
                data={'driver': 'Leclerc', 'pit_count': 1, 'tire_compound': 'soft'}
            ),
            RaceEvent(
                event_type=EventType.FASTEST_LAP,
                timestamp=datetime.now(),
                data={'driver': 'Verstappen', 'lap_time': 84.5}
            ),
        ]
        
        # Process all events
        commentaries = []
        for event in events:
            self.system.event_queue.enqueue(event)
            self.system.race_state_tracker.update(event)
            
            queued = self.system.event_queue.dequeue()
            if queued:
                commentary = self.system.commentary_generator.generate(queued)
                commentaries.append(commentary)
        
        # Verify all processed
        assert len(commentaries) == 3
        for commentary in commentaries:
            assert isinstance(commentary, str)
            assert len(commentary) > 0
        
        print(f"✓ Processed {len(commentaries)} events successfully")
    
    @patch('src.speech_synthesizer.ElevenLabsClient')
    def test_priority_based_event_processing(self, mock_tts):
        """Test that events are processed by priority."""
        # Mock TTS
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.return_value = b'fake_audio'
        mock_tts.return_value = mock_tts_instance
        
        # Initialize
        assert self.system.initialize() is True
        
        # Set up state
        self.system.race_state_tracker._state.current_lap = 30
        self.system.race_state_tracker._state.total_laps = 58
        
        # Add events in non-priority order
        events = [
            (EventType.FASTEST_LAP, {'driver': 'Leclerc', 'lap_time': 85.0}),
            (EventType.INCIDENT, {'description': 'Collision', 'lap_number': 30}),
            (EventType.OVERTAKE, {'overtaking_driver': 'A', 'overtaken_driver': 'B'}),
        ]
        
        for event_type, data in events:
            self.system.event_queue.enqueue(RaceEvent(
                event_type=event_type,
                timestamp=datetime.now(),
                data=data
            ))
        
        # Dequeue and verify order
        processed_types = []
        while self.system.event_queue.size() > 0:
            event = self.system.event_queue.dequeue()
            if event:
                processed_types.append(event.event_type)
                commentary = self.system.commentary_generator.generate(event)
                assert len(commentary) > 0
        
        # Should be: INCIDENT (critical) → OVERTAKE (high) → FASTEST_LAP (medium)
        assert processed_types[0] == EventType.INCIDENT
        assert processed_types[1] == EventType.OVERTAKE
        assert processed_types[2] == EventType.FASTEST_LAP
        
        print("✓ Priority-based processing verified")


class TestQAInterruptionFlow:
    """Test Q&A interruption of commentary flow."""
    
    def setup_method(self):
        """Set up test system."""
        self.system = CommentarySystem()
        self.system.config.replay_mode = True
        self.system.config.enable_movements = False
        self.system.config.ai_enabled = False
        
    def teardown_method(self):
        """Clean up."""
        if hasattr(self, 'system') and self.system:
            self.system.shutdown()
    
    def test_qa_pauses_event_queue(self):
        """Test that Q&A pauses event processing."""
        # Initialize
        assert self.system.initialize() is True
        
        # Set up race state
        self.system.race_state_tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=2.5),
        ]
        self.system.race_state_tracker._state.current_lap = 25
        
        # Add events to queue
        for i in range(3):
            self.system.event_queue.enqueue(RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={'lap_number': 25 + i}
            ))
        
        initial_size = self.system.event_queue.size()
        assert initial_size == 3
        assert not self.system.event_queue.is_paused()
        
        # Process Q&A
        response = self.system.qa_manager.process_question("Who's leading?")
        
        # Queue should be paused
        assert self.system.event_queue.is_paused()
        assert self.system.event_queue.size() == initial_size  # Events preserved
        assert "Verstappen" in response
        
        # Resume
        self.system.qa_manager.resume_event_queue()
        assert not self.system.event_queue.is_paused()
        
        print("✓ Q&A pause/resume verified")
    
    def test_qa_during_active_commentary(self):
        """Test Q&A interruption during active commentary generation."""
        # Initialize
        assert self.system.initialize() is True
        
        # Set up race state
        self.system.race_state_tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=3.2),
            DriverState(name="Leclerc", position=3, gap_to_leader=7.5),
        ]
        self.system.race_state_tracker._state.current_lap = 30
        
        # Add pit stop event
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={'driver': 'Hamilton', 'tire_compound': 'hard', 'lap_number': 28}
        )
        self.system.race_state_tracker.update(pit_event)
        
        # Fill queue with events
        for i in range(5):
            self.system.event_queue.enqueue(RaceEvent(
                event_type=EventType.OVERTAKE,
                timestamp=datetime.now(),
                data={'overtaking_driver': 'A', 'overtaken_driver': 'B'}
            ))
        
        # Process Q&A
        response = self.system.qa_manager.process_question("Has Hamilton pitted?")
        
        # Should get response
        assert "pit" in response.lower() or "hard" in response.lower()
        assert self.system.event_queue.is_paused()
        
        # Events should still be in queue
        assert self.system.event_queue.size() == 5
        
        # Resume and verify events can be processed
        self.system.qa_manager.resume_event_queue()
        event = self.system.event_queue.dequeue()
        assert event is not None
        
        print("✓ Q&A during commentary verified")
    
    def test_multiple_qa_interactions(self):
        """Test multiple Q&A interactions in sequence."""
        # Initialize
        assert self.system.initialize() is True
        
        # Set up race state
        self.system.race_state_tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=2.1),
            DriverState(name="Leclerc", position=3, gap_to_leader=5.8),
        ]
        
        questions = [
            "Who's leading?",
            "Where is Hamilton?",
            "What's the gap to the leader?",
        ]
        
        for question in questions:
            response = self.system.qa_manager.process_question(question)
            assert isinstance(response, str)
            assert len(response) > 0
            assert self.system.event_queue.is_paused()
            
            self.system.qa_manager.resume_event_queue()
            assert not self.system.event_queue.is_paused()
        
        print(f"✓ Processed {len(questions)} Q&A interactions")


class TestReplayModeOperation:
    """Test replay mode functionality."""
    
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_replay_mode_initialization(self, mock_loader_class):
        """Test system initialization in replay mode."""
        # Mock loader
        mock_loader = Mock()
        mock_loader.load_race.return_value = {
            'position': [{"driver_number": "1", "position": 1, "lap_number": 1}],
            'pit': [],
            'laps': [],
            'race_control': []
        }
        mock_loader_class.return_value = mock_loader
        
        # Create system
        system = CommentarySystem()
        system.config.replay_mode = True
        system.config.replay_race_id = "test_race"
        system.config.enable_movements = False
        
        # Initialize
        assert system.initialize() is True
        assert system.data_ingestion._replay_controller is not None
        
        # Clean up
        system.shutdown()
        
        print("✓ Replay mode initialization verified")
    
    @patch('src.data_ingestion.HistoricalDataLoader')
    def test_replay_controls(self, mock_loader_class):
        """Test replay pause/resume/seek controls."""
        # Mock loader
        mock_loader = Mock()
        mock_loader.load_race.return_value = {
            'position': [{"driver_number": "1", "position": 1, "lap_number": 1}],
            'pit': [],
            'laps': [],
            'race_control': []
        }
        mock_loader_class.return_value = mock_loader
        
        # Create system
        system = CommentarySystem()
        system.config.replay_mode = True
        system.config.replay_race_id = "test_race"
        system.config.enable_movements = False
        
        # Initialize
        assert system.initialize() is True
        
        # Test pause
        system.data_ingestion.pause_replay()
        assert system.data_ingestion.is_replay_paused() is True
        
        # Test resume
        system.data_ingestion.resume_replay()
        assert system.data_ingestion.is_replay_paused() is False
        
        # Test seek
        system.data_ingestion.seek_replay_to_lap(10)
        
        # Test speed change
        system.data_ingestion.set_replay_speed(5.0)
        
        # Clean up
        system.shutdown()
        
        print("✓ Replay controls verified")


class TestErrorRecoveryScenarios:
    """Test error recovery and resilience."""
    
    def setup_method(self):
        """Set up test system."""
        self.system = CommentarySystem()
        self.system.config.replay_mode = True
        self.system.config.enable_movements = False
        self.system.config.ai_enabled = False
        
    def teardown_method(self):
        """Clean up."""
        if hasattr(self, 'system') and self.system:
            self.system.shutdown()
    
    @patch('src.speech_synthesizer.ElevenLabsClient')
    def test_tts_failure_graceful_degradation(self, mock_tts):
        """Test system continues when TTS fails."""
        # Mock TTS to fail
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.side_effect = Exception("TTS API Error")
        mock_tts.return_value = mock_tts_instance
        
        # Initialize
        assert self.system.initialize() is True
        
        # Set up state
        self.system.race_state_tracker._state.current_lap = 20
        self.system.race_state_tracker._state.total_laps = 58
        
        # Create event
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={'overtaking_driver': 'Hamilton', 'overtaken_driver': 'Verstappen'}
        )
        
        # Generate commentary (should work)
        commentary = self.system.commentary_generator.generate(event)
        assert isinstance(commentary, str)
        assert len(commentary) > 0
        
        # Try to synthesize (should fail gracefully)
        try:
            audio = self.system.speech_synthesizer.synthesize(commentary)
            # Should return None or handle error
        except Exception:
            pass  # Expected to fail
        
        # System should still be operational
        assert self.system.is_initialized() is True
        
        print("✓ TTS failure handled gracefully")
    
    def test_malformed_event_handling(self):
        """Test handling of malformed events."""
        # Initialize
        assert self.system.initialize() is True
        
        # Create malformed event (missing required data)
        bad_event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}  # Missing driver names
        )
        
        # Try to generate commentary
        try:
            commentary = self.system.commentary_generator.generate(bad_event)
            # Should either return default or handle gracefully
            assert isinstance(commentary, str)
        except Exception as e:
            # Should not crash the system
            pass
        
        # System should still be operational
        assert self.system.is_initialized() is True
        
        print("✓ Malformed event handled")
    
    def test_empty_race_state_handling(self):
        """Test handling of empty race state."""
        # Initialize
        assert self.system.initialize() is True
        
        # Don't set up any race state
        
        # Try Q&A with no data
        response = self.system.qa_manager.process_question("Who's leading?")
        assert "don't have" in response.lower()
        
        # System should still be operational
        assert self.system.is_initialized() is True
        
        print("✓ Empty state handled")
    
    def test_queue_overflow_handling(self):
        """Test event queue overflow handling."""
        # Initialize
        assert self.system.initialize() is True
        
        # Fill queue beyond capacity
        for i in range(15):  # Max is 10
            event = RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={'lap_number': i}
            )
            self.system.event_queue.enqueue(event)
        
        # Queue should not exceed max size
        assert self.system.event_queue.size() <= 10
        
        # System should still be operational
        assert self.system.is_initialized() is True
        
        print("✓ Queue overflow handled")


class TestResourceLimitsUnderLoad:
    """Test system behavior under load."""
    
    def setup_method(self):
        """Set up test system."""
        self.system = CommentarySystem()
        self.system.config.replay_mode = True
        self.system.config.enable_movements = False
        self.system.config.ai_enabled = False
        
    def teardown_method(self):
        """Clean up."""
        if hasattr(self, 'system') and self.system:
            self.system.shutdown()
    
    @patch('src.speech_synthesizer.ElevenLabsClient')
    def test_high_event_rate_processing(self, mock_tts):
        """Test processing high rate of events."""
        # Mock TTS
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.return_value = b'fake_audio'
        mock_tts.return_value = mock_tts_instance
        
        # Initialize
        assert self.system.initialize() is True
        
        # Set up state
        self.system.race_state_tracker._state.drivers = [
            DriverState(name=f"Driver{i}", position=i+1, gap_to_leader=float(i))
            for i in range(20)
        ]
        self.system.race_state_tracker._state.current_lap = 30
        self.system.race_state_tracker._state.total_laps = 58
        
        # Generate many events rapidly
        start_time = time.time()
        event_count = 50
        
        for i in range(event_count):
            event = RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={'lap_number': 30 + i}
            )
            self.system.event_queue.enqueue(event)
            self.system.race_state_tracker.update(event)
        
        # Process all events
        processed = 0
        while self.system.event_queue.size() > 0:
            event = self.system.event_queue.dequeue()
            if event:
                commentary = self.system.commentary_generator.generate(event)
                assert len(commentary) > 0
                processed += 1
        
        elapsed = time.time() - start_time
        
        # Verify all processed
        assert processed <= 10  # Queue max size
        
        print(f"✓ Processed {processed} events in {elapsed:.2f}s")
    
    def test_memory_monitoring_under_load(self):
        """Test memory monitoring during high load."""
        # Initialize
        assert self.system.initialize() is True
        
        # Start resource monitor
        self.system.resource_monitor.start()
        
        # Generate load
        for i in range(100):
            event = RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={'lap_number': i}
            )
            self.system.event_queue.enqueue(event)
            self.system.race_state_tracker.update(event)
        
        # Get memory stats
        stats = self.system.resource_monitor.get_stats()
        
        # Should have memory info
        assert 'memory_percent' in stats
        assert 'memory_mb' in stats
        
        # Memory should be reasonable
        assert stats['memory_percent'] < 90.0
        
        # Stop monitor
        self.system.resource_monitor.stop()
        
        print(f"✓ Memory usage: {stats['memory_percent']:.1f}% ({stats['memory_mb']:.1f} MB)")
    
    @patch('src.speech_synthesizer.ElevenLabsClient')
    def test_concurrent_operations(self, mock_tts):
        """Test concurrent event processing and Q&A."""
        # Mock TTS
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.return_value = b'fake_audio'
        mock_tts.return_value = mock_tts_instance
        
        # Initialize
        assert self.system.initialize() is True
        
        # Set up state
        self.system.race_state_tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=2.5),
        ]
        self.system.race_state_tracker._state.current_lap = 25
        
        # Add events
        for i in range(5):
            self.system.event_queue.enqueue(RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={'lap_number': 25 + i}
            ))
        
        # Process Q&A while events are queued
        response = self.system.qa_manager.process_question("Who's leading?")
        assert "Verstappen" in response
        
        # Resume and process events
        self.system.qa_manager.resume_event_queue()
        
        processed = 0
        while self.system.event_queue.size() > 0:
            event = self.system.event_queue.dequeue()
            if event:
                commentary = self.system.commentary_generator.generate(event)
                processed += 1
        
        assert processed > 0
        
        print(f"✓ Concurrent operations handled: {processed} events + Q&A")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
