"""
Performance testing for F1 Commentary Robot.

Tests:
- Event detection latency
- Commentary generation latency
- TTS API latency
- End-to-end latency
- CPU and memory usage
- Memory leak detection
"""

import pytest
import time
import psutil
import os
from datetime import datetime
from unittest.mock import Mock, patch

from reachy_f1_commentator.src.commentary_generator import CommentaryGenerator
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.data_ingestion import EventParser
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.models import RaceEvent, EventType, DriverState
from reachy_f1_commentator.src.resource_monitor import ResourceMonitor


class TestPerformanceMetrics:
    """Test performance metrics."""
    
    def test_event_detection_latency(self):
        """Measure event detection latency (target: <100ms)."""
        parser = EventParser()
        
        # Create test position data
        position_data = [
            {"driver": "VER", "position": 1, "lap_number": 5},
            {"driver": "HAM", "position": 2, "lap_number": 5}
        ]
        
        # Measure parsing time
        start = time.time()
        events = parser.parse_position_data(position_data)
        elapsed_ms = (time.time() - start) * 1000
        
        assert elapsed_ms < 100, f"Event detection took {elapsed_ms:.2f}ms (target: <100ms)"
        print(f"✓ Event detection latency: {elapsed_ms:.2f}ms")
    
    def test_commentary_generation_latency(self):
        """Measure commentary generation latency (target: <2s)."""
        config = Config(ai_enabled=False)
        tracker = RaceStateTracker()
        generator = CommentaryGenerator(config, tracker)
        
        # Set up state
        tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=2.5),
        ]
        tracker._state.current_lap = 25
        tracker._state.total_laps = 58
        
        # Create event
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={'overtaking_driver': 'Hamilton', 'overtaken_driver': 'Verstappen'}
        )
        
        # Measure generation time
        start = time.time()
        commentary = generator.generate(event)
        elapsed = time.time() - start
        
        assert elapsed < 2.0, f"Commentary generation took {elapsed:.2f}s (target: <2s)"
        assert len(commentary) > 0
        print(f"✓ Commentary generation latency: {elapsed*1000:.2f}ms")
    
    @patch('src.speech_synthesizer.ElevenLabsClient')
    def test_tts_api_latency(self, mock_tts):
        """Measure TTS API latency (target: <3s)."""
        from src.speech_synthesizer import SpeechSynthesizer
        from src.config import Config
        
        # Mock TTS with realistic delay
        mock_tts_instance = Mock()
        def mock_tts_call(text):
            time.sleep(0.5)  # Simulate API call
            return b'fake_audio_data'
        mock_tts_instance.text_to_speech.side_effect = mock_tts_call
        mock_tts.return_value = mock_tts_instance
        
        config = Config()
        synthesizer = SpeechSynthesizer(config, None)
        
        # Measure TTS time
        start = time.time()
        audio = synthesizer.synthesize("This is a test commentary")
        elapsed = time.time() - start
        
        assert elapsed < 3.0, f"TTS took {elapsed:.2f}s (target: <3s)"
        assert audio is not None
        print(f"✓ TTS API latency: {elapsed*1000:.2f}ms")
        
        # Cleanup
        synthesizer.stop()

    @patch('src.speech_synthesizer.ElevenLabsClient')
    @patch('reachy_mini.ReachyMini')
    def test_end_to_end_latency(self, mock_reachy, mock_tts):
        """Measure end-to-end latency (target: <5s)."""
        from src.commentary_system import CommentarySystem
        
        # Mock TTS
        mock_tts_instance = Mock()
        mock_tts_instance.text_to_speech.return_value = b'fake_audio'
        mock_tts.return_value = mock_tts_instance
        
        # Create system
        system = CommentarySystem()
        system.config.replay_mode = True
        system.config.enable_movements = False
        system.config.ai_enabled = False
        
        try:
            assert system.initialize() is True
            
            # Set up state
            system.race_state_tracker._state.drivers = [
                DriverState(name="Hamilton", position=1, gap_to_leader=0.0),
                DriverState(name="Verstappen", position=2, gap_to_leader=1.5),
            ]
            system.race_state_tracker._state.current_lap = 25
            system.race_state_tracker._state.total_laps = 58
            
            # Create event
            event = RaceEvent(
                event_type=EventType.OVERTAKE,
                timestamp=datetime.now(),
                data={'overtaking_driver': 'Hamilton', 'overtaken_driver': 'Verstappen'}
            )
            
            # Measure end-to-end time
            start = time.time()
            
            # Enqueue event
            system.event_queue.enqueue(event)
            
            # Dequeue and generate commentary
            queued_event = system.event_queue.dequeue()
            commentary = system.commentary_generator.generate(queued_event)
            
            # Synthesize (mocked)
            audio = system.speech_synthesizer.synthesize(commentary)
            
            elapsed = time.time() - start
            
            assert elapsed < 5.0, f"End-to-end took {elapsed:.2f}s (target: <5s)"
            print(f"✓ End-to-end latency: {elapsed*1000:.2f}ms")
            
        finally:
            if system.resource_monitor:
                system.resource_monitor.stop()
            system.shutdown()
            time.sleep(0.2)
    
    def test_cpu_memory_usage(self):
        """Monitor CPU and memory usage."""
        process = psutil.Process(os.getpid())
        
        # Get initial stats
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create components and do some work
        config = Config(ai_enabled=False)
        tracker = RaceStateTracker()
        generator = CommentaryGenerator(config, tracker)
        queue = PriorityEventQueue()
        
        # Set up state
        tracker._state.drivers = [
            DriverState(name=f"Driver{i}", position=i+1, gap_to_leader=float(i))
            for i in range(20)
        ]
        tracker._state.current_lap = 30
        tracker._state.total_laps = 58
        
        # Generate load
        for i in range(100):
            event = RaceEvent(
                event_type=EventType.POSITION_UPDATE,
                timestamp=datetime.now(),
                data={'lap_number': 30 + i}
            )
            queue.enqueue(event)
            tracker.update(event)
            
            if queue.size() > 0:
                e = queue.dequeue()
                if e:
                    commentary = generator.generate(e)
        
        # Get final stats
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Check memory usage
        assert final_memory < 2048, f"Memory usage {final_memory:.1f}MB exceeds 2GB limit"
        
        print(f"✓ Memory usage: {final_memory:.1f}MB (increase: {memory_increase:.1f}MB)")
        print(f"  Initial: {initial_memory:.1f}MB, Final: {final_memory:.1f}MB")
    
    def test_memory_leak_detection(self):
        """Test for memory leaks over extended operation."""
        process = psutil.Process(os.getpid())
        
        config = Config(ai_enabled=False)
        tracker = RaceStateTracker()
        generator = CommentaryGenerator(config, tracker)
        
        # Set up state
        tracker._state.drivers = [
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
            DriverState(name="Hamilton", position=2, gap_to_leader=2.5),
        ]
        tracker._state.current_lap = 1
        tracker._state.total_laps = 58
        
        # Measure memory at intervals
        memory_samples = []
        
        for iteration in range(5):
            # Do work
            for i in range(50):
                event = RaceEvent(
                    event_type=EventType.POSITION_UPDATE,
                    timestamp=datetime.now(),
                    data={'lap_number': iteration * 50 + i}
                )
                tracker.update(event)
                commentary = generator.generate(event)
            
            # Sample memory
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_samples.append(memory_mb)
            time.sleep(0.1)
        
        # Check for memory growth
        memory_growth = memory_samples[-1] - memory_samples[0]
        avg_growth_per_iteration = memory_growth / len(memory_samples)
        
        # Allow some growth but not excessive
        assert avg_growth_per_iteration < 10, f"Excessive memory growth: {avg_growth_per_iteration:.2f}MB/iteration"
        
        print(f"✓ Memory leak test passed")
        print(f"  Samples: {[f'{m:.1f}MB' for m in memory_samples]}")
        print(f"  Total growth: {memory_growth:.2f}MB over {len(memory_samples)} iterations")
    
    def test_resource_monitor_overhead(self):
        """Test resource monitor overhead."""
        monitor = ResourceMonitor()
        
        # Start monitoring
        monitor.start()
        time.sleep(1.0)
        
        # Get stats (this should be fast)
        start = time.time()
        stats = monitor.get_current_usage()
        stats_time = time.time() - start
        
        # Stop monitoring (this takes ~5s due to thread join timeout)
        monitor.stop()
        
        # Verify stats
        assert 'memory_percent' in stats
        assert 'memory_mb' in stats
        assert 'cpu_percent' in stats
        
        # Getting stats should be fast
        assert stats_time < 0.2, f"Getting stats took {stats_time:.2f}s (should be <0.2s)"
        
        print(f"✓ Resource monitor stats retrieval: {stats_time*1000:.2f}ms")
        print(f"  Memory: {stats['memory_percent']:.1f}% ({stats['memory_mb']:.1f}MB)")
        print(f"  CPU: {stats['cpu_percent']:.1f}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
