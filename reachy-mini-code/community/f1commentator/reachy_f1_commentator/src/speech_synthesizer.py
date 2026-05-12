"""Speech synthesis module for F1 Commentary Robot.

This module provides text-to-speech functionality using ElevenLabs streaming API,
audio playback queue management, and integration with the Motion Controller.

Validates: Requirements 6.1, 6.2, 6.4, 6.5, 6.6, 6.7
"""

import logging
import time
import asyncio
import numpy as np
from typing import Optional, Dict, Any
from io import BytesIO
import queue
import threading

from elevenlabs import AsyncElevenLabs
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.graceful_degradation import degradation_manager


logger = logging.getLogger(__name__)


class ElevenLabsStreamingClient:
    """Client for ElevenLabs Text-to-Speech Streaming API.
    
    Uses async streaming for lower latency and real-time audio delivery.
    
    Validates: Requirements 6.1, 6.2, 6.5
    """
    
    def __init__(self, api_key: str, voice_id: str):
        """Initialize ElevenLabs streaming client with API credentials.
        
        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use for synthesis
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.client = AsyncElevenLabs(api_key=api_key)
        
        logger.info(f"ElevenLabs streaming client initialized with voice_id: {voice_id}")
    
    async def text_to_speech_stream(
        self,
        text: str,
        reachy_media,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, float]:
        """Convert text to speech using ElevenLabs streaming API and play directly on Reachy.
        
        Args:
            text: Text to convert to speech
            reachy_media: Reachy Mini media interface for audio output
            voice_settings: Optional voice configuration settings
        
        Returns:
            Tuple of (success: bool, audio_duration: float in seconds)
            
        Validates: Requirements 6.1, 6.2, 6.5
        """
        try:
            start_time = time.time()
            logger.info(f"Starting streaming TTS: '{text[:50]}...'")
            
            # Get Reachy audio configuration
            out_sr = reachy_media.get_output_audio_samplerate()  # Should be 16000
            out_ch = reachy_media.get_output_channels()  # 1 or 2
            
            logger.debug(f"Reachy audio config: {out_sr}Hz, {out_ch} channels")
            
            # Start audio playback
            reachy_media.start_playing()
            
            first_chunk_time = None
            total_chunks = 0
            total_samples = 0
            
            # Stream audio from ElevenLabs (returns async generator directly)
            # Using eleven_v3 for emotion tag support (audio tags)
            # Note: v3 is required for emotion tags like [excited], [serious], [surprised]
            stream = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                model_id="eleven_v3",  # Required for emotion tag support
                text=text,
                output_format="pcm_16000"  # Request 16kHz PCM to match Reachy
            )
            
            async for chunk in stream:
                if first_chunk_time is None:
                    first_chunk_time = time.time()
                    ttfb = first_chunk_time - start_time
                    logger.info(f"First audio chunk received in {ttfb:.3f}s (TTFB)")
                
                # Convert bytes to int16 -> float32 in [-1, 1]
                audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                total_samples += len(audio)
                
                # Handle channel configuration
                if out_ch == 2:
                    # Reachy expects stereo, duplicate mono to stereo
                    audio = np.stack([audio, audio], axis=1)
                else:
                    # Reachy expects mono
                    audio = audio.reshape(-1, 1)
                
                # Push audio sample to Reachy (non-blocking)
                reachy_media.push_audio_sample(audio)
                total_chunks += 1
            
            # Calculate audio duration
            audio_duration = total_samples / out_sr
            
            elapsed = time.time() - start_time
            logger.info(f"Streaming TTS completed: {total_chunks} chunks, {audio_duration:.2f}s audio in {elapsed:.2f}s")
            
            # Wait for audio to finish playing before stopping
            # Add a small buffer (0.5s) to ensure all audio is played
            logger.debug(f"Waiting {audio_duration + 0.5:.2f}s for audio playback to complete")
            await asyncio.sleep(audio_duration + 0.5)
            
            # Now stop audio playback
            reachy_media.stop_playing()
            
            degradation_manager.record_tts_success()
            return True, audio_duration
            
        except Exception as e:
            logger.error(f"[SpeechSynthesizer] Streaming TTS error: {e}", exc_info=True)
            degradation_manager.record_tts_failure()
            
            # Try to stop playback on error
            try:
                reachy_media.stop_playing()
            except:
                pass
            
            return False, 0.0



class SpeechSynthesizer:
    """Main speech synthesis orchestrator with streaming support.
    
    Coordinates TTS streaming API calls and motion controller integration.
    Uses async streaming for lower latency.
    
    Validates: Requirements 6.1, 6.7
    """
    
    def __init__(
        self,
        config: Config,
        motion_controller=None,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None
    ):
        """Initialize speech synthesizer.
        
        Args:
            config: System configuration
            motion_controller: Optional MotionController instance for synchronization
            api_key: Optional ElevenLabs API key (overrides config)
            voice_id: Optional voice ID (overrides config)
        """
        self.config = config
        self.motion_controller = motion_controller
        self._reachy = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self._initialized = False
        self.elevenlabs_client = None
        
        # Use provided API key or fall back to config
        self.api_key = api_key or getattr(config, 'elevenlabs_api_key', '')
        self.voice_id = voice_id or getattr(config, 'elevenlabs_voice_id', 'HSSEHuB5EziJgTfCVmC6')
        
        # Create a dedicated event loop for async operations
        self._loop = None
        self._loop_thread = None
        self._start_event_loop()
        
        # Initialize if API key is provided
        if self.api_key:
            self._initialized = self.initialize()
        else:
            logger.warning("SpeechSynthesizer initialized without API key - audio will be disabled")
            logger.info("SpeechSynthesizer initialized (no API key)")
    
    def _start_event_loop(self):
        """Start a dedicated event loop in a background thread."""
        def run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
        
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=run_loop, args=(self._loop,), daemon=True)
        self._loop_thread.start()
        logger.debug("Event loop started in background thread")
    
    def initialize(self) -> bool:
        """Initialize the ElevenLabs client with API credentials.
        
        Returns:
            True if initialization successful, False otherwise
            
        Validates: Requirements 8.8, 8.9, 9.1
        """
        if not self.api_key:
            logger.warning("Cannot initialize SpeechSynthesizer: No API key provided")
            return False
        
        try:
            # Initialize streaming client
            self.elevenlabs_client = ElevenLabsStreamingClient(
                api_key=self.api_key,
                voice_id=self.voice_id
            )
            self._initialized = True
            logger.info(f"SpeechSynthesizer initialized successfully with voice_id: {self.voice_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize SpeechSynthesizer: {e}", exc_info=True)
            self._initialized = False
            return False
    
    def is_initialized(self) -> bool:
        """Check if the synthesizer is initialized and ready to use.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized
    
    def set_reachy(self, reachy) -> None:
        """Set Reachy Mini SDK instance for audio output.
        
        Args:
            reachy: ReachyMini instance
        """
        self._reachy = reachy
        logger.info("Reachy SDK instance set for audio output")
    
    def _run_async_synthesis(self, text: str) -> tuple[bool, float]:
        """Run async synthesis using the dedicated event loop.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Tuple of (success: bool, audio_duration: float in seconds)
        """
        try:
            # Schedule the coroutine on the dedicated event loop
            future = asyncio.run_coroutine_threadsafe(
                self.elevenlabs_client.text_to_speech_stream(
                    text=text,
                    reachy_media=self._reachy.media
                ),
                self._loop
            )
            
            # Wait for completion (with timeout)
            result = future.result(timeout=60)  # 60 second timeout
            return result
                
        except Exception as e:
            logger.error(f"[SpeechSynthesizer] Error in async synthesis: {e}", exc_info=True)
            return False, 0.0
    
    def synthesize_and_play(self, text: str) -> bool:
        """Synthesize text and stream audio directly to Reachy (convenience method).
        
        Args:
            text: Text to synthesize and play
            
        Returns:
            True if successful, False otherwise
            
        Validates: Requirement 6.7 (end-to-end latency tracking)
        """
        start_time = time.time()
        
        # Check if synthesizer is initialized
        if not self._initialized or self.elevenlabs_client is None:
            logger.warning("[SpeechSynthesizer] Not initialized, cannot synthesize audio")
            logger.info(f"[TEXT_ONLY] Commentary (not initialized): {text}")
            return False
        
        # Check if TTS is available (graceful degradation)
        if not degradation_manager.is_tts_available():
            logger.warning("[SpeechSynthesizer] TTS unavailable, operating in TEXT_ONLY mode")
            logger.info(f"[TEXT_ONLY] Commentary: {text}")
            return False
        
        # Check if Reachy is connected
        if self._reachy is None:
            logger.warning("[SpeechSynthesizer] Reachy not connected, cannot play audio")
            logger.info(f"[TEXT_ONLY] Commentary (no Reachy): {text}")
            return False
        
        # Mark as speaking
        with self._speaking_lock:
            self._is_speaking = True
        
        try:
            # Notify motion controller before speech starts
            if self.motion_controller is not None:
                try:
                    # Estimate duration (rough: ~150 words per minute, ~2.5 chars per word)
                    estimated_duration = len(text) / (150 * 2.5 / 60)
                    logger.debug(f"Notifying motion controller: estimated duration {estimated_duration:.2f}s")
                    self.motion_controller.sync_with_speech(estimated_duration)
                except Exception as e:
                    logger.error(f"[SpeechSynthesizer] Failed to notify motion controller: {e}", exc_info=True)
            
            # Run streaming synthesis (this now waits for audio to complete internally)
            success, audio_duration = self._run_async_synthesis(text)
            
            if not success:
                logger.info(f"[TEXT_ONLY] Commentary (TTS failed): {text}")
            
            elapsed = time.time() - start_time
            logger.info(f"End-to-end TTS latency: {elapsed:.2f}s")
            
            return success
            
        finally:
            # Mark as not speaking
            with self._speaking_lock:
                self._is_speaking = False
    
    def is_speaking(self) -> bool:
        """Check if audio is currently playing.
        
        Returns:
            True if speaking, False otherwise
        """
        with self._speaking_lock:
            return self._is_speaking
    
    def stop(self) -> None:
        """Stop speech synthesis and clean up resources."""
        logger.info("Stopping speech synthesizer")
        with self._speaking_lock:
            self._is_speaking = False
        
        # Stop the event loop
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._loop_thread is not None:
                self._loop_thread.join(timeout=2)
            logger.debug("Event loop stopped")
