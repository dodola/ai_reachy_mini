"""Tests for CommentarySystem orchestrator.

This module tests the main system orchestrator including initialization,
startup, shutdown, and signal handling.
"""

import pytest
import time
import signal
import os
from unittest.mock import Mock, patch, MagicMock

from reachy_f1_commentator.src.commentary_system import CommentarySystem
from reachy_f1_commentator.src.config import Config


class TestCommentarySystemInitialization:
    """Test system initialization."""
    
    def test_init_loads_config(self, tmp_path):
        """Test that __init__ loads configuration."""
        # Create a temporary config file
        config_file = tmp_path / "test_config.json"
        config_file.write_text('{"log_level": "DEBUG"}')
        
        system = CommentarySystem(config_path=str(config_file))
        
        assert system.config is not None
        assert system.config.log_level == "DEBUG"
        assert not system._initialized
        assert not system._running
    
    def test_init_registers_signal_handlers(self):
        """Test that signal handlers are registered."""
        with patch('signal.signal') as mock_signal:
            system = CommentarySystem()
            
            # Verify SIGTERM and SIGINT handlers were registered
            assert mock_signal.call_count >= 2
            calls = [call[0] for call in mock_signal.call_args_list]
            assert (signal.SIGTERM,) in [call[:1] for call in calls]
            assert (signal.SIGINT,) in [call[:1] for call in calls]
    
    @patch('src.commentary_system.RaceStateTracker')
    @patch('src.commentary_system.PriorityEventQueue')
    @patch('src.commentary_system.MotionController')
    @patch('src.commentary_system.SpeechSynthesizer')
    @patch('src.commentary_system.EnhancedCommentaryGenerator')
    @patch('src.commentary_system.DataIngestionModule')
    @patch('src.commentary_system.QAManager')
    @patch('src.commentary_system.ResourceMonitor')
    def test_initialize_creates_all_components(
        self, mock_resource_monitor, mock_qa, mock_data_ingestion,
        mock_commentary_gen, mock_speech_synth, mock_motion_ctrl,
        mock_event_queue, mock_race_state
    ):
        """Test that initialize() creates all system components."""
        # Setup mocks
        mock_motion_ctrl.return_value.reachy.is_connected.return_value = False
        mock_resource_monitor.return_value.start.return_value = None
        mock_commentary_gen.return_value.is_enhanced_mode.return_value = True
        mock_commentary_gen.return_value.load_static_data.return_value = True
        
        system = CommentarySystem()
        system.config.replay_mode = True  # Skip API verification
        
        result = system.initialize()
        
        assert result is True
        assert system._initialized is True
        assert system.race_state_tracker is not None
        assert system.event_queue is not None
        assert system.motion_controller is not None
        assert system.speech_synthesizer is not None
        assert system.commentary_generator is not None
        assert system.data_ingestion is not None
        assert system.qa_manager is not None
        assert system.resource_monitor is not None
    
    @patch('src.commentary_system.RaceStateTracker')
    @patch('src.commentary_system.PriorityEventQueue')
    @patch('src.commentary_system.MotionController')
    @patch('src.commentary_system.SpeechSynthesizer')
    @patch('src.commentary_system.EnhancedCommentaryGenerator')
    @patch('src.commentary_system.DataIngestionModule')
    @patch('src.commentary_system.QAManager')
    @patch('src.commentary_system.ResourceMonitor')
    def test_initialize_moves_head_to_neutral(
        self, mock_resource_monitor, mock_qa, mock_data_ingestion,
        mock_commentary_gen, mock_speech_synth, mock_motion_ctrl,
        mock_event_queue, mock_race_state
    ):
        """Test that initialize() moves robot head to neutral position."""
        # Setup mocks
        mock_motion = Mock()
        mock_motion_ctrl.return_value = mock_motion
        mock_motion.reachy.is_connected.return_value = False
        mock_resource_monitor.return_value.start.return_value = None
        mock_commentary_gen.return_value.is_enhanced_mode.return_value = True
        mock_commentary_gen.return_value.load_static_data.return_value = True
        
        system = CommentarySystem()
        system.config.replay_mode = True
        system.config.enable_movements = True
        
        with patch('time.sleep'):  # Skip sleep
            system.initialize()
        
        # Verify return_to_neutral was called
        mock_motion.return_to_neutral.assert_called_once()
    
    def test_initialize_returns_false_on_error(self):
        """Test that initialize() returns False on error."""
        with patch('src.commentary_system.RaceStateTracker', side_effect=Exception("Test error")):
            system = CommentarySystem()
            
            result = system.initialize()
            
            assert result is False
            assert system._initialized is False


class TestCommentarySystemStartStop:
    """Test system start and stop."""
    
    @patch('src.commentary_system.RaceStateTracker')
    @patch('src.commentary_system.PriorityEventQueue')
    @patch('src.commentary_system.MotionController')
    @patch('src.commentary_system.SpeechSynthesizer')
    @patch('src.commentary_system.EnhancedCommentaryGenerator')
    @patch('src.commentary_system.DataIngestionModule')
    @patch('src.commentary_system.QAManager')
    @patch('src.commentary_system.ResourceMonitor')
    def test_start_requires_initialization(
        self, mock_resource_monitor, mock_qa, mock_data_ingestion,
        mock_commentary_gen, mock_speech_synth, mock_motion_ctrl,
        mock_event_queue, mock_race_state
    ):
        """Test that start() requires system to be initialized."""
        system = CommentarySystem()
        
        result = system.start()
        
        assert result is False
        assert not system._running
    
    @patch('src.commentary_system.RaceStateTracker')
    @patch('src.commentary_system.PriorityEventQueue')
    @patch('src.commentary_system.MotionController')
    @patch('src.commentary_system.SpeechSynthesizer')
    @patch('src.commentary_system.EnhancedCommentaryGenerator')
    @patch('src.commentary_system.DataIngestionModule')
    @patch('src.commentary_system.QAManager')
    @patch('src.commentary_system.ResourceMonitor')
    def test_start_starts_data_ingestion(
        self, mock_resource_monitor, mock_qa, mock_data_ingestion_cls,
        mock_commentary_gen, mock_speech_synth, mock_motion_ctrl,
        mock_event_queue, mock_race_state
    ):
        """Test that start() starts data ingestion."""
        # Setup mocks
        mock_data_ingestion = Mock()
        mock_data_ingestion.start.return_value = True
        mock_data_ingestion_cls.return_value = mock_data_ingestion
        mock_motion_ctrl.return_value.reachy.is_connected.return_value = False
        mock_resource_monitor.return_value.start.return_value = None
        mock_commentary_gen.return_value.is_enhanced_mode.return_value = True
        mock_commentary_gen.return_value.load_static_data.return_value = True
        
        system = CommentarySystem()
        system.config.replay_mode = True
        
        with patch('time.sleep'):
            system.initialize()
        
        result = system.start()
        
        assert result is True
        assert system._running is True
        mock_data_ingestion.start.assert_called_once()


class TestCommentarySystemShutdown:
    """Test system shutdown."""
    
    @patch('src.commentary_system.RaceStateTracker')
    @patch('src.commentary_system.PriorityEventQueue')
    @patch('src.commentary_system.MotionController')
    @patch('src.commentary_system.SpeechSynthesizer')
    @patch('src.commentary_system.EnhancedCommentaryGenerator')
    @patch('src.commentary_system.DataIngestionModule')
    @patch('src.commentary_system.QAManager')
    @patch('src.commentary_system.ResourceMonitor')
    def test_shutdown_waits_for_current_commentary(
        self, mock_resource_monitor, mock_qa, mock_data_ingestion,
        mock_commentary_gen, mock_speech_synth_cls, mock_motion_ctrl,
        mock_event_queue, mock_race_state
    ):
        """Test that shutdown() waits for current commentary to complete."""
        # Setup mocks
        mock_speech_synth = Mock()
        mock_speech_synth.is_speaking.side_effect = [True, True, False]  # Speaking, then done
        mock_speech_synth_cls.return_value = mock_speech_synth
        mock_motion_ctrl.return_value.reachy.is_connected.return_value = False
        mock_resource_monitor.return_value.start.return_value = None
        mock_commentary_gen.return_value.is_enhanced_mode.return_value = True
        mock_commentary_gen.return_value.load_static_data.return_value = True
        
        system = CommentarySystem()
        system.config.replay_mode = True
        
        with patch('time.sleep'):
            system.initialize()
        
        system.shutdown()
        
        # Verify is_speaking was called to check status
        assert mock_speech_synth.is_speaking.call_count >= 1
    
    @patch('src.commentary_system.RaceStateTracker')
    @patch('src.commentary_system.PriorityEventQueue')
    @patch('src.commentary_system.MotionController')
    @patch('src.commentary_system.SpeechSynthesizer')
    @patch('src.commentary_system.EnhancedCommentaryGenerator')
    @patch('src.commentary_system.DataIngestionModule')
    @patch('src.commentary_system.QAManager')
    @patch('src.commentary_system.ResourceMonitor')
    def test_shutdown_returns_head_to_neutral(
        self, mock_resource_monitor, mock_qa, mock_data_ingestion,
        mock_commentary_gen, mock_speech_synth, mock_motion_ctrl_cls,
        mock_event_queue, mock_race_state
    ):
        """Test that shutdown() returns robot head to neutral position."""
        # Setup mocks
        mock_motion_ctrl = Mock()
        mock_motion_ctrl_cls.return_value = mock_motion_ctrl
        mock_motion_ctrl.reachy.is_connected.return_value = False
        mock_resource_monitor.return_value.start.return_value = None
        mock_commentary_gen.return_value.is_enhanced_mode.return_value = True
        mock_commentary_gen.return_value.load_static_data.return_value = True
        
        system = CommentarySystem()
        system.config.replay_mode = True
        system.config.enable_movements = True
        
        with patch('time.sleep'):
            system.initialize()
            system.shutdown()
        
        # Verify return_to_neutral was called during shutdown
        assert mock_motion_ctrl.return_to_neutral.call_count >= 1
    
    @patch('src.commentary_system.RaceStateTracker')
    @patch('src.commentary_system.PriorityEventQueue')
    @patch('src.commentary_system.MotionController')
    @patch('src.commentary_system.SpeechSynthesizer')
    @patch('src.commentary_system.EnhancedCommentaryGenerator')
    @patch('src.commentary_system.DataIngestionModule')
    @patch('src.commentary_system.QAManager')
    @patch('src.commentary_system.ResourceMonitor')
    def test_shutdown_closes_api_connections(
        self, mock_resource_monitor, mock_qa, mock_data_ingestion_cls,
        mock_commentary_gen, mock_speech_synth, mock_motion_ctrl,
        mock_event_queue, mock_race_state
    ):
        """Test that shutdown() closes API connections."""
        # Setup mocks
        mock_data_ingestion = Mock()
        mock_client = Mock()
        mock_data_ingestion.client = mock_client
        mock_data_ingestion_cls.return_value = mock_data_ingestion
        mock_motion_ctrl.return_value.reachy.is_connected.return_value = False
        mock_resource_monitor.return_value.start.return_value = None
        mock_commentary_gen.return_value.is_enhanced_mode.return_value = True
        mock_commentary_gen.return_value.load_static_data.return_value = True
        
        system = CommentarySystem()
        system.config.replay_mode = True
        
        with patch('time.sleep'):
            system.initialize()
            system.shutdown()
        
        # Verify client.close() was called
        mock_client.close.assert_called_once()
    
    @patch('src.commentary_system.RaceStateTracker')
    @patch('src.commentary_system.PriorityEventQueue')
    @patch('src.commentary_system.MotionController')
    @patch('src.commentary_system.SpeechSynthesizer')
    @patch('src.commentary_system.EnhancedCommentaryGenerator')
    @patch('src.commentary_system.DataIngestionModule')
    @patch('src.commentary_system.QAManager')
    @patch('src.commentary_system.ResourceMonitor')
    def test_signal_handler_triggers_shutdown(
        self, mock_resource_monitor, mock_qa, mock_data_ingestion,
        mock_commentary_gen, mock_speech_synth, mock_motion_ctrl,
        mock_event_queue, mock_race_state
    ):
        """Test that signal handler triggers graceful shutdown."""
        # Setup mocks
        mock_motion_ctrl.return_value.reachy.is_connected.return_value = False
        mock_resource_monitor.return_value.start.return_value = None
        mock_commentary_gen.return_value.is_enhanced_mode.return_value = True
        mock_commentary_gen.return_value.load_static_data.return_value = True
        
        system = CommentarySystem()
        system.config.replay_mode = True
        
        with patch('time.sleep'):
            system.initialize()
        
        # Mock sys.exit to prevent actual exit
        with patch('sys.exit'):
            system._signal_handler(signal.SIGTERM, None)
        
        # Verify shutdown was triggered
        assert system._shutdown_requested is True


class TestCommentarySystemQuestionProcessing:
    """Test Q&A question processing."""
    
    @patch('src.commentary_system.RaceStateTracker')
    @patch('src.commentary_system.PriorityEventQueue')
    @patch('src.commentary_system.MotionController')
    @patch('src.commentary_system.SpeechSynthesizer')
    @patch('src.commentary_system.EnhancedCommentaryGenerator')
    @patch('src.commentary_system.DataIngestionModule')
    @patch('src.commentary_system.QAManager')
    @patch('src.commentary_system.ResourceMonitor')
    def test_process_question_requires_running_system(
        self, mock_resource_monitor, mock_qa_cls, mock_data_ingestion,
        mock_commentary_gen, mock_speech_synth, mock_motion_ctrl,
        mock_event_queue, mock_race_state
    ):
        """Test that process_question() requires system to be running."""
        system = CommentarySystem()
        
        # Should not process if not initialized
        system.process_question("Who is leading?")
        
        # No assertions needed - just verify it doesn't crash
    
    @patch('src.commentary_system.RaceStateTracker')
    @patch('src.commentary_system.PriorityEventQueue')
    @patch('src.commentary_system.MotionController')
    @patch('src.commentary_system.SpeechSynthesizer')
    @patch('src.commentary_system.EnhancedCommentaryGenerator')
    @patch('src.commentary_system.DataIngestionModule')
    @patch('src.commentary_system.QAManager')
    @patch('src.commentary_system.ResourceMonitor')
    def test_process_question_resumes_queue_on_error(
        self, mock_resource_monitor, mock_qa_cls, mock_data_ingestion,
        mock_commentary_gen, mock_speech_synth, mock_motion_ctrl,
        mock_event_queue, mock_race_state
    ):
        """Test that process_question() resumes queue even on error."""
        # Setup mocks
        mock_qa = Mock()
        mock_qa.process_question.side_effect = Exception("Test error")
        mock_qa_cls.return_value = mock_qa
        mock_motion_ctrl.return_value.reachy.is_connected.return_value = False
        mock_resource_monitor.return_value.start.return_value = None
        mock_data_ingestion.return_value.start.return_value = True
        mock_commentary_gen.return_value.is_enhanced_mode.return_value = True
        mock_commentary_gen.return_value.load_static_data.return_value = True
        
        system = CommentarySystem()
        system.config.replay_mode = True
        
        with patch('time.sleep'):
            system.initialize()
            system.start()
        
        # Process question (should handle error gracefully)
        system.process_question("Who is leading?")
        
        # Verify resume was called even though error occurred
        mock_qa.resume_event_queue.assert_called()


class TestCommentarySystemStatus:
    """Test system status methods."""
    
    def test_is_running_returns_false_initially(self):
        """Test that is_running() returns False initially."""
        system = CommentarySystem()
        
        assert system.is_running() is False
    
    def test_is_initialized_returns_false_initially(self):
        """Test that is_initialized() returns False initially."""
        system = CommentarySystem()
        
        assert system.is_initialized() is False
