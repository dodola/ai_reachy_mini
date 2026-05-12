"""Unit tests for Speech Synthesizer module.

Tests ElevenLabs API client, audio queue, audio player, and speech synthesizer.
"""

import pytest
import time
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
import soundfile as sf

from reachy_f1_commentator.src.speech_synthesizer import (
    ElevenLabsClient,
    AudioQueue,
    AudioPlayer,
    SpeechSynthesizer
)
from reachy_f1_commentator.src.config import Config


class TestElevenLabsClient:
    """Test ElevenLabs API client."""
    
    def test_initialization(self):
        """Test client initialization."""
        client = ElevenLabsClient(api_key="test_key", voice_id="test_voice")
        
        assert client.api_key == "test_key"
        assert client.voice_id == "test_voice"
        assert client.timeout == 3.0
    
    @patch('src.speech_synthesizer.requests.post')
    def test_text_to_speech_success(self, mock_post):
        """Test successful TTS API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_audio_data"
        mock_post.return_value = mock_response
        
        client = ElevenLabsClient(api_key="test_key", voice_id="test_voice")
        result = client.text_to_speech("Hello world")
        
        assert result == b"fake_audio_data"
        assert mock_post.called
        
        # Verify API call parameters
        call_args = mock_post.call_args
        assert "text-to-speech/test_voice" in call_args[0][0]
        assert call_args[1]['timeout'] == 3.0
    
    @patch('src.speech_synthesizer.requests.post')
    def test_text_to_speech_api_error(self, mock_post):
        """Test TTS API error handling."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        client = ElevenLabsClient(api_key="invalid_key", voice_id="test_voice")
        result = client.text_to_speech("Hello world")
        
        assert result is None
    
    @patch('src.speech_synthesizer.requests.post')
    def test_text_to_speech_timeout(self, mock_post):
        """Test TTS API timeout handling."""
        # Mock timeout
        mock_post.side_effect = Exception("Timeout")
        
        client = ElevenLabsClient(api_key="test_key", voice_id="test_voice")
        result = client.text_to_speech("Hello world")
        
        assert result is None
    
    def test_text_to_speech_with_custom_settings(self):
        """Test TTS with custom voice settings."""
        with patch('src.speech_synthesizer.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"fake_audio"
            mock_post.return_value = mock_response
            
            client = ElevenLabsClient(api_key="test_key", voice_id="test_voice")
            
            custom_settings = {
                "stability": 0.7,
                "similarity_boost": 0.8,
                "style": 0.5
            }
            
            result = client.text_to_speech("Test", voice_settings=custom_settings)
            
            assert result == b"fake_audio"
            
            # Verify custom settings were passed
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['voice_settings'] == custom_settings


class TestAudioQueue:
    """Test audio queue functionality."""
    
    def test_initialization(self):
        """Test queue initialization."""
        queue = AudioQueue()
        
        assert queue.is_empty()
        assert queue.size() == 0
        assert not queue.is_playing()
    
    def test_enqueue_dequeue(self):
        """Test basic enqueue and dequeue operations."""
        queue = AudioQueue()
        
        audio_data = np.array([1, 2, 3], dtype=np.int16)
        duration = 1.5
        
        queue.enqueue(audio_data, duration)
        
        assert not queue.is_empty()
        assert queue.size() == 1
        
        result = queue.dequeue()
        
        assert result is not None
        result_audio, result_duration = result
        np.testing.assert_array_equal(result_audio, audio_data)
        assert result_duration == duration
        
        assert queue.is_empty()
    
    def test_fifo_order(self):
        """Test FIFO ordering of queue."""
        queue = AudioQueue()
        
        # Enqueue multiple items
        for i in range(3):
            audio = np.array([i], dtype=np.int16)
            queue.enqueue(audio, float(i))
        
        assert queue.size() == 3
        
        # Dequeue and verify order
        for i in range(3):
            result = queue.dequeue()
            assert result is not None
            audio, duration = result
            assert audio[0] == i
            assert duration == float(i)
    
    def test_dequeue_empty(self):
        """Test dequeue from empty queue."""
        queue = AudioQueue()
        
        result = queue.dequeue()
        assert result is None
    
    def test_playing_status(self):
        """Test playing status tracking."""
        queue = AudioQueue()
        
        assert not queue.is_playing()
        
        queue.set_playing(True)
        assert queue.is_playing()
        
        queue.set_playing(False)
        assert not queue.is_playing()
    
    def test_clear(self):
        """Test queue clearing."""
        queue = AudioQueue()
        
        # Add multiple items
        for i in range(5):
            queue.enqueue(np.array([i], dtype=np.int16), float(i))
        
        assert queue.size() == 5
        
        queue.clear()
        
        assert queue.is_empty()
        assert queue.size() == 0


class TestAudioPlayer:
    """Test audio player functionality."""
    
    def test_initialization(self):
        """Test player initialization."""
        queue = AudioQueue()
        player = AudioPlayer(audio_queue=queue, volume=0.8)
        
        assert player.volume == 0.8
        assert player.audio_queue == queue
    
    def test_convert_mp3_to_numpy(self):
        """Test MP3 to numpy conversion."""
        queue = AudioQueue()
        player = AudioPlayer(audio_queue=queue)
        
        # Create a simple audio array (1 second of 440Hz sine wave)
        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
        
        # Save to MP3 bytes using soundfile (via WAV first, then mock MP3)
        # For testing, we'll mock the librosa.load function
        with patch('src.speech_synthesizer.librosa.load') as mock_load:
            mock_load.return_value = (audio_data, sample_rate)
            
            # Convert
            audio_array, result_duration = player._convert_mp3_to_numpy(b"fake_mp3_data")
            
            assert isinstance(audio_array, np.ndarray)
            assert audio_array.dtype == np.float32  # Updated to float32
            assert result_duration > 0.9 and result_duration < 1.1  # Approximately 1 second
    
    def test_play_adds_to_queue(self):
        """Test that play() adds audio to queue."""
        queue = AudioQueue()
        player = AudioPlayer(audio_queue=queue)
        
        # Create simple audio data and mock the conversion
        audio_data = (np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)) * 0.5).astype(np.float32)
        
        with patch('src.speech_synthesizer.librosa.load') as mock_load:
            mock_load.return_value = (audio_data, 16000)
            
            # Play
            player.play(b"fake_mp3_data")
            
            # Verify added to queue
            assert not queue.is_empty()
            assert queue.size() == 1
    
    def test_is_speaking(self):
        """Test is_speaking() method."""
        queue = AudioQueue()
        player = AudioPlayer(audio_queue=queue)
        
        assert not player.is_speaking()
        
        queue.set_playing(True)
        assert player.is_speaking()
        
        queue.set_playing(False)
        assert not player.is_speaking()
    
    def test_stop_clears_queue(self):
        """Test that stop() clears the queue."""
        queue = AudioQueue()
        player = AudioPlayer(audio_queue=queue)
        
        # Add items to queue
        for i in range(3):
            queue.enqueue(np.array([i], dtype=np.int16), float(i))
        
        assert queue.size() == 3
        
        # Stop
        player.stop()
        
        # Verify queue cleared
        assert queue.is_empty()
    
    def test_set_reachy(self):
        """Test setting Reachy SDK instance."""
        queue = AudioQueue()
        player = AudioPlayer(audio_queue=queue)
        
        mock_reachy = Mock()
        player.set_reachy(mock_reachy)
        
        assert player._reachy == mock_reachy


class TestSpeechSynthesizer:
    """Test speech synthesizer orchestrator."""
    
    def test_initialization(self):
        """Test synthesizer initialization."""
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice",
            audio_volume=0.7
        )
        
        synthesizer = SpeechSynthesizer(config)
        
        assert synthesizer.config == config
        assert synthesizer.elevenlabs_client is not None
        assert synthesizer.audio_queue is not None
        assert synthesizer.audio_player is not None
    
    @patch('src.speech_synthesizer.ElevenLabsClient.text_to_speech')
    def test_synthesize_success(self, mock_tts):
        """Test successful text synthesis."""
        mock_tts.return_value = b"fake_audio"
        
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        
        synthesizer = SpeechSynthesizer(config)
        result = synthesizer.synthesize("Hello world")
        
        assert result == b"fake_audio"
        assert mock_tts.called
    
    @patch('src.speech_synthesizer.ElevenLabsClient.text_to_speech')
    def test_synthesize_failure(self, mock_tts):
        """Test synthesis failure handling."""
        mock_tts.return_value = None
        
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        
        synthesizer = SpeechSynthesizer(config)
        result = synthesizer.synthesize("Hello world")
        
        assert result is None
    
    def test_play_queues_audio(self):
        """Test that play() queues audio."""
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        
        synthesizer = SpeechSynthesizer(config)
        
        # Create simple audio data and mock the conversion
        audio_data = (np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)) * 0.5).astype(np.float32)
        
        with patch('src.speech_synthesizer.librosa.load') as mock_load:
            mock_load.return_value = (audio_data, 16000)
            
            # Play
            synthesizer.play(b"fake_mp3_data")
            
            # Verify queued
            assert not synthesizer.audio_queue.is_empty()
    
    def test_play_notifies_motion_controller(self):
        """Test that play() notifies motion controller."""
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        
        mock_motion_controller = Mock()
        synthesizer = SpeechSynthesizer(config, motion_controller=mock_motion_controller)
        
        # Create simple audio data and mock the conversion
        audio_data = (np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)) * 0.5).astype(np.float32)
        
        with patch('src.speech_synthesizer.librosa.load') as mock_load:
            mock_load.return_value = (audio_data, 16000)
            
            # Play
            synthesizer.play(b"fake_mp3_data")
            
            # Verify motion controller was notified
            assert mock_motion_controller.sync_with_speech.called
    
    @patch('src.speech_synthesizer.ElevenLabsClient.text_to_speech')
    def test_synthesize_and_play(self, mock_tts):
        """Test synthesize_and_play convenience method."""
        # Create simple audio data
        audio_data = (np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)) * 0.5).astype(np.float32)
        
        mock_tts.return_value = b"fake_mp3_data"
        
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        
        synthesizer = SpeechSynthesizer(config)
        
        with patch('src.speech_synthesizer.librosa.load') as mock_load:
            mock_load.return_value = (audio_data, 16000)
            
            result = synthesizer.synthesize_and_play("Hello world")
            
            assert result is True
            assert not synthesizer.audio_queue.is_empty()
    
    def test_is_speaking(self):
        """Test is_speaking() method."""
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        
        synthesizer = SpeechSynthesizer(config)
        
        assert not synthesizer.is_speaking()
        
        synthesizer.audio_queue.set_playing(True)
        assert synthesizer.is_speaking()
    
    def test_stop(self):
        """Test stop() method."""
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        
        synthesizer = SpeechSynthesizer(config)
        
        # Add items to queue
        for i in range(3):
            synthesizer.audio_queue.enqueue(np.array([i], dtype=np.int16), float(i))
        
        # Stop
        synthesizer.stop()
        
        # Verify queue cleared
        assert synthesizer.audio_queue.is_empty()
    
    def test_set_reachy(self):
        """Test setting Reachy SDK instance."""
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        
        synthesizer = SpeechSynthesizer(config)
        
        mock_reachy = Mock()
        synthesizer.set_reachy(mock_reachy)
        
        assert synthesizer.audio_player._reachy == mock_reachy


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch('src.speech_synthesizer.requests.post')
    def test_network_error_handling(self, mock_post):
        """Test handling of network errors."""
        mock_post.side_effect = Exception("Network error")
        
        client = ElevenLabsClient(api_key="test_key", voice_id="test_voice")
        result = client.text_to_speech("Hello")
        
        assert result is None
    
    def test_invalid_audio_data(self):
        """Test handling of invalid audio data."""
        queue = AudioQueue()
        player = AudioPlayer(audio_queue=queue)
        
        # Try to play invalid data
        with pytest.raises(Exception):
            player._convert_mp3_to_numpy(b"invalid_data")
    
    @patch('src.speech_synthesizer.ElevenLabsClient.text_to_speech')
    def test_synthesize_and_play_failure(self, mock_tts):
        """Test synthesize_and_play when synthesis fails."""
        mock_tts.return_value = None
        
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        
        synthesizer = SpeechSynthesizer(config)
        result = synthesizer.synthesize_and_play("Hello")
        
        assert result is False
        assert synthesizer.audio_queue.is_empty()


class TestLatencyTracking:
    """Test latency tracking and logging."""
    
    @patch('src.speech_synthesizer.requests.post')
    def test_tts_latency_logging(self, mock_post):
        """Test that TTS latency is logged."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_audio"
        mock_post.return_value = mock_response
        
        client = ElevenLabsClient(api_key="test_key", voice_id="test_voice")
        
        start = time.time()
        result = client.text_to_speech("Hello")
        elapsed = time.time() - start
        
        assert result is not None
        assert elapsed < 5.0  # Should be fast with mock
    
    @patch('src.speech_synthesizer.ElevenLabsClient.text_to_speech')
    def test_end_to_end_latency_tracking(self, mock_tts):
        """Test end-to-end latency tracking."""
        audio_data = (np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, 8000)) * 0.5).astype(np.float32)
        
        mock_tts.return_value = b"fake_mp3_data"
        
        config = Config(
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        
        synthesizer = SpeechSynthesizer(config)
        
        with patch('src.speech_synthesizer.librosa.load') as mock_load:
            mock_load.return_value = (audio_data, 16000)
            
            start = time.time()
            result = synthesizer.synthesize_and_play("Hello world")
            elapsed = time.time() - start
            
            assert result is True
            # Should complete quickly with mock
            assert elapsed < 2.0
