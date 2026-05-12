"""Main application orchestrator for F1 Commentary Robot.

This module provides the CommentarySystem class that coordinates all system
components, handles initialization, manages the main event processing loop,
and ensures graceful shutdown.

Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7
"""

import logging
import signal
import sys
import time
import threading
from typing import Optional

from reachy_f1_commentator.src.config import Config, load_config
from reachy_f1_commentator.src.logging_config import setup_logging
from reachy_f1_commentator.src.models import EventType
from reachy_f1_commentator.src.data_ingestion import DataIngestionModule
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.commentary_generator import CommentaryGenerator
from reachy_f1_commentator.src.enhanced_commentary_generator import EnhancedCommentaryGenerator
from reachy_f1_commentator.src.speech_synthesizer import SpeechSynthesizer
from reachy_f1_commentator.src.motion_controller import MotionController
from reachy_f1_commentator.src.qa_manager import QAManager
from reachy_f1_commentator.src.resource_monitor import ResourceMonitor


logger = logging.getLogger(__name__)


class CommentarySystem:
    """Main orchestrator for the F1 Commentary Robot system.
    
    Coordinates all system components, manages initialization in dependency
    order, verifies API connectivity, and handles graceful shutdown.
    
    Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7
    """
    
    def __init__(self, config_path: str = "config/config.json"):
        """Initialize commentary system with configuration.
        
        Args:
            config_path: Path to configuration file
            
        Validates: Requirement 17.1
        """
        # Load configuration
        self.config = load_config(config_path)
        
        # Setup logging
        setup_logging(self.config.log_level, self.config.log_file)
        
        logger.info("=" * 80)
        logger.info("F1 Commentary Robot - System Initialization")
        logger.info("=" * 80)
        
        # Initialize components (will be set during initialize())
        self.race_state_tracker: Optional[RaceStateTracker] = None
        self.event_queue: Optional[PriorityEventQueue] = None
        self.motion_controller: Optional[MotionController] = None
        self.speech_synthesizer: Optional[SpeechSynthesizer] = None
        self.commentary_generator: Optional[EnhancedCommentaryGenerator] = None
        self.data_ingestion: Optional[DataIngestionModule] = None
        self.qa_manager: Optional[QAManager] = None
        self.resource_monitor: Optional[ResourceMonitor] = None
        
        # System state
        self._initialized = False
        self._running = False
        self._shutdown_requested = False
        self._event_processing_thread: Optional[threading.Thread] = None
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info(f"Configuration loaded: replay_mode={self.config.replay_mode}")
    
    def initialize(self) -> bool:
        """Initialize all system modules in dependency order.
        
        Initialization order:
        1. Race State Tracker (no dependencies)
        2. Event Queue (no dependencies)
        3. Motion Controller (no dependencies)
        4. Speech Synthesizer (depends on Motion Controller)
        5. Commentary Generator (depends on Race State Tracker)
        6. Data Ingestion Module (depends on Event Queue)
        7. Q&A Manager (depends on Race State Tracker, Event Queue)
        8. Resource Monitor (no dependencies)
        
        Returns:
            True if initialization successful, False otherwise
            
        Validates: Requirements 17.1, 17.2, 17.3
        """
        if self._initialized:
            logger.warning("System already initialized")
            return True
        
        try:
            logger.info("Starting system initialization...")
            
            # 1. Initialize Race State Tracker
            logger.info("Initializing Race State Tracker...")
            self.race_state_tracker = RaceStateTracker()
            logger.info("✓ Race State Tracker initialized")
            
            # 2. Initialize Event Queue
            logger.info("Initializing Event Queue...")
            self.event_queue = PriorityEventQueue(max_size=self.config.max_queue_size)
            logger.info("✓ Event Queue initialized")
            
            # 3. Initialize Motion Controller
            logger.info("Initializing Motion Controller...")
            self.motion_controller = MotionController(self.config)
            
            # Move robot head to neutral position during initialization
            if self.config.enable_movements:
                logger.info("Moving robot head to neutral position...")
                self.motion_controller.return_to_neutral()
                time.sleep(1.0)  # Wait for movement to complete
            
            logger.info("✓ Motion Controller initialized")
            
            # 4. Initialize Speech Synthesizer
            logger.info("Initializing Speech Synthesizer...")
            self.speech_synthesizer = SpeechSynthesizer(
                config=self.config,
                motion_controller=self.motion_controller
            )
            
            # Connect Reachy SDK to speech synthesizer if motion controller has it
            if self.motion_controller.reachy.is_connected():
                self.speech_synthesizer.set_reachy(self.motion_controller.reachy.reachy)
            
            logger.info("✓ Speech Synthesizer initialized")
            
            # 5. Initialize Commentary Generator
            logger.info("Initializing Commentary Generator...")
            
            # Use EnhancedCommentaryGenerator which maintains backward compatibility
            # and supports both enhanced and basic modes (Requirement 19.1, 19.8)
            # Note: OpenF1 client will be set after data ingestion module is initialized
            self.commentary_generator = EnhancedCommentaryGenerator(
                config=self.config,
                state_tracker=self.race_state_tracker,
                openf1_client=None  # Will be set after data ingestion initialization
            )
            
            # Log which mode is active at startup (Requirement 19.8)
            if self.commentary_generator.is_enhanced_mode():
                logger.info("✓ Commentary Generator initialized in ENHANCED mode")
            else:
                logger.info("✓ Commentary Generator initialized in BASIC mode")
            
            # Load static data if in enhanced mode
            if self.commentary_generator.is_enhanced_mode():
                logger.info("Loading static data for enhanced commentary...")
                session_key = self.config.replay_race_id if self.config.replay_mode else None
                if self.commentary_generator.load_static_data(session_key):
                    logger.info("✓ Static data loaded successfully")
                else:
                    logger.warning("⚠ Failed to load static data - enhanced features may be limited")
            
            # 6. Initialize Data Ingestion Module
            logger.info("Initializing Data Ingestion Module...")
            self.data_ingestion = DataIngestionModule(
                config=self.config,
                event_queue=self.event_queue
            )
            logger.info("✓ Data Ingestion Module initialized")
            
            # Connect OpenF1 client to enhanced commentary generator (Requirement 19.4)
            if self.commentary_generator.is_enhanced_mode():
                logger.info("Connecting OpenF1 client to enhanced commentary generator...")
                self.commentary_generator.openf1_client = self.data_ingestion.client
                # Re-initialize enhanced components now that we have the client
                self.commentary_generator._initialize_enhanced_components()
                logger.info("✓ OpenF1 client connected to commentary generator")
            
            # 7. Initialize Q&A Manager
            logger.info("Initializing Q&A Manager...")
            self.qa_manager = QAManager(
                state_tracker=self.race_state_tracker,
                event_queue=self.event_queue
            )
            logger.info("✓ Q&A Manager initialized")
            
            # 8. Initialize Resource Monitor
            logger.info("Initializing Resource Monitor...")
            self.resource_monitor = ResourceMonitor()
            self.resource_monitor.start()
            logger.info("✓ Resource Monitor initialized")
            
            # Verify API connectivity before entering active mode
            if not self.config.replay_mode:
                logger.info("Verifying API connectivity...")
                
                # Test OpenF1 API connection
                if not self._verify_openf1_connectivity():
                    logger.error("Failed to verify OpenF1 API connectivity")
                    return False
                
                # Test ElevenLabs API connection
                if not self._verify_elevenlabs_connectivity():
                    logger.error("Failed to verify ElevenLabs API connectivity")
                    logger.warning("System will continue in TEXT_ONLY mode")
                
                logger.info("✓ API connectivity verified")
            else:
                logger.info("Replay mode enabled - skipping API connectivity checks")
            
            self._initialized = True
            logger.info("=" * 80)
            logger.info("System initialization complete!")
            logger.info("=" * 80)
            return True
            
        except Exception as e:
            logger.error(f"[CommentarySystem] System initialization failed: {e}", exc_info=True)
            return False
    
    def _verify_openf1_connectivity(self) -> bool:
        """Verify connectivity to OpenF1 API.
        
        Returns:
            True if connection successful, False otherwise
            
        Validates: Requirement 17.3
        """
        try:
            # Try to authenticate with OpenF1 API
            if self.data_ingestion.client.authenticate():
                logger.info("✓ OpenF1 API connection verified")
                return True
            else:
                logger.error("✗ OpenF1 API authentication failed")
                return False
        except Exception as e:
            logger.error(f"[CommentarySystem] OpenF1 API verification failed: {e}", exc_info=True)
            return False
    
    def _verify_elevenlabs_connectivity(self) -> bool:
        """Verify connectivity to ElevenLabs API.
        
        Returns:
            True if connection successful, False otherwise
            
        Validates: Requirement 17.3
        """
        try:
            # Try a simple TTS request
            test_text = "System check"
            audio_bytes = self.speech_synthesizer.elevenlabs_client.text_to_speech(test_text)
            
            if audio_bytes:
                logger.info("✓ ElevenLabs API connection verified")
                return True
            else:
                logger.error("✗ ElevenLabs API test request failed")
                return False
        except Exception as e:
            logger.error(f"[CommentarySystem] ElevenLabs API verification failed: {e}", exc_info=True)
            return False
    
    def start(self) -> bool:
        """Start the commentary system.
        
        Starts data ingestion and event processing loop.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self._initialized:
            logger.error("Cannot start system: not initialized")
            return False
        
        if self._running:
            logger.warning("System already running")
            return True
        
        try:
            logger.info("Starting commentary system...")
            
            # Start data ingestion
            if not self.data_ingestion.start():
                logger.error("Failed to start data ingestion")
                return False
            
            # Start event processing loop
            self._running = True
            self._event_processing_thread = threading.Thread(
                target=self._event_processing_loop,
                daemon=True,
                name="EventProcessingThread"
            )
            self._event_processing_thread.start()
            
            logger.info("=" * 80)
            logger.info("F1 Commentary Robot is now ACTIVE!")
            logger.info("=" * 80)
            
            return True
            
        except Exception as e:
            logger.error(f"[CommentarySystem] Failed to start system: {e}", exc_info=True)
            return False
    
    def _event_processing_loop(self) -> None:
        """Main event processing loop.
        
        Continuously dequeues events, generates commentary, and plays audio.
        """
        logger.info("Event processing loop started")
        
        while self._running and not self._shutdown_requested:
            try:
                # Dequeue next event
                event = self.event_queue.dequeue()
                
                if event is None:
                    # No events available, sleep briefly
                    time.sleep(0.1)
                    continue
                
                # Update race state
                self.race_state_tracker.update(event)
                
                # Skip position updates for commentary (too frequent)
                if event.event_type == EventType.POSITION_UPDATE:
                    continue
                
                # Generate commentary
                logger.info(f"Processing event: {event.event_type.value}")
                commentary_text = self.commentary_generator.generate(event)
                
                # Synthesize and play audio
                self.speech_synthesizer.synthesize_and_play(commentary_text)
                
                # Execute gesture based on event type
                if self.config.enable_movements:
                    gesture = self.motion_controller.gesture_library.get_gesture_for_event(event.event_type)
                    self.motion_controller.execute_gesture(gesture)
                
            except Exception as e:
                logger.error(f"[CommentarySystem] Error in event processing loop: {e}", exc_info=True)
                time.sleep(0.5)  # Brief pause before continuing
        
        logger.info("Event processing loop stopped")
    
    def shutdown(self) -> None:
        """Gracefully shutdown the commentary system.
        
        Completes current commentary, closes API connections, and returns
        robot to neutral position.
        
        Validates: Requirements 17.4, 17.5, 17.6, 17.7
        """
        if self._shutdown_requested:
            logger.warning("Shutdown already in progress")
            return
        
        self._shutdown_requested = True
        
        logger.info("=" * 80)
        logger.info("Initiating graceful shutdown...")
        logger.info("=" * 80)
        
        try:
            # Complete current commentary before stopping
            if self.speech_synthesizer and self.speech_synthesizer.is_speaking():
                logger.info("Waiting for current commentary to complete...")
                timeout = 10.0  # Maximum 10 seconds to wait
                start_time = time.time()
                
                while self.speech_synthesizer.is_speaking() and (time.time() - start_time) < timeout:
                    time.sleep(0.5)
                
                if self.speech_synthesizer.is_speaking():
                    logger.warning("Commentary did not complete within timeout, proceeding with shutdown")
            
            # Stop event processing loop
            logger.info("Stopping event processing...")
            self._running = False
            if self._event_processing_thread and self._event_processing_thread.is_alive():
                self._event_processing_thread.join(timeout=5.0)
            
            # Stop data ingestion
            if self.data_ingestion:
                logger.info("Stopping data ingestion...")
                self.data_ingestion.stop()
            
            # Stop speech synthesizer
            if self.speech_synthesizer:
                logger.info("Stopping speech synthesizer...")
                self.speech_synthesizer.stop()
            
            # Return robot head to neutral position
            if self.motion_controller and self.config.enable_movements:
                logger.info("Returning robot head to neutral position...")
                self.motion_controller.return_to_neutral()
                time.sleep(1.0)  # Wait for movement to complete
            
            # Stop motion controller
            if self.motion_controller:
                logger.info("Stopping motion controller...")
                self.motion_controller.stop()
            
            # Stop resource monitor
            if self.resource_monitor:
                logger.info("Stopping resource monitor...")
                self.resource_monitor.stop()
            
            # Close all API connections gracefully
            logger.info("Closing API connections...")
            if self.data_ingestion and self.data_ingestion.client:
                self.data_ingestion.client.close()
            
            logger.info("=" * 80)
            logger.info("Shutdown complete. Goodbye!")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"[CommentarySystem] Error during shutdown: {e}", exc_info=True)
    
    def _signal_handler(self, signum, frame):
        """Handle SIGTERM and SIGINT signals for graceful shutdown.
        
        Args:
            signum: Signal number
            frame: Current stack frame
            
        Validates: Requirement 17.7
        """
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
        self.shutdown()
        sys.exit(0)
    
    def process_question(self, question: str) -> None:
        """Process a user question (Q&A functionality).
        
        Args:
            question: User's question text
        """
        if not self._initialized or not self._running:
            logger.warning("Cannot process question: system not running")
            return
        
        try:
            logger.info(f"Processing question: {question}")
            
            # Process question and get response
            response = self.qa_manager.process_question(question)
            
            # Synthesize and play response
            self.speech_synthesizer.synthesize_and_play(response)
            
            # Wait for response to complete
            while self.speech_synthesizer.is_speaking():
                time.sleep(0.5)
            
            # Resume event queue
            self.qa_manager.resume_event_queue()
            
            logger.info("Question processed successfully")
            
        except Exception as e:
            logger.error(f"[CommentarySystem] Error processing question: {e}", exc_info=True)
            # Ensure event queue is resumed even on error
            if self.qa_manager:
                self.qa_manager.resume_event_queue()
    
    def is_running(self) -> bool:
        """Check if system is running.
        
        Returns:
            True if system is running, False otherwise
        """
        return self._running
    
    def is_initialized(self) -> bool:
        """Check if system is initialized.
        
        Returns:
            True if system is initialized, False otherwise
        """
        return self._initialized
