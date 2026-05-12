"""
Main Reachy Mini F1 Commentator app.

This module contains the main ReachyMiniApp class and can be run directly:
    python -m reachy_f1_commentator.main
"""

import threading
import logging
import time
from datetime import datetime
from typing import Optional

try:
    from reachy_mini import ReachyMini, ReachyMiniApp
except ImportError:
    # Fallback for development without reachy-mini installed
    class ReachyMiniApp:
        pass
    ReachyMini = None

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from .models import WebUIConfiguration, PlaybackStatus
from .openf1_client import OpenF1APIClient
from .src.enhanced_commentary_generator import EnhancedCommentaryGenerator
from .src.commentary_generator import CommentaryGenerator
from .src.race_state_tracker import RaceStateTracker
from .src.models import RaceEvent, EventType, DriverState, RacePhase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Global app instance for API endpoints
_app_instance = None


class ReachyF1Commentator(ReachyMiniApp):
    """Main Reachy Mini app for F1 commentary generation."""
    
    custom_app_url: str | None = "http://0.0.0.0:8080/"  # URL where the app is served
    dont_start_webserver = False  # Let framework handle the web server
    
    def __init__(self):
        """Initialize the F1 commentator app."""
        super().__init__()
        self.reachy_mini_instance = None
        self.commentary_generator = None
        self.state_tracker = RaceStateTracker()  # Initialize here instead of in run()
        self.playback_status = PlaybackStatus(state='idle')
        self.playback_thread = None
        self.stop_playback_event = threading.Event()
        self.config = None
        self.openf1_client = OpenF1APIClient()
        self.speech_synthesizer = None  # Will be initialized during playback
        
        # Set global instance for API endpoints
        global _app_instance
        _app_instance = self
        
        logger.info("ReachyMiniF1Commentator initialized")
    
    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event) -> None:
        """
        Main entry point called by the Reachy Mini app framework.
        
        Args:
            reachy_mini: Reachy Mini instance for robot control
            stop_event: Event to signal graceful shutdown
        """
        import asyncio
        
        # Create new event loop for this thread (required for Reachy Mini framework)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info("Starting F1 Commentator app")
        
        self.reachy_mini_instance = reachy_mini
        
        # Setup FastAPI routes using the framework-provided settings_app
        self._setup_api_routes()
        
        # Web server is started automatically by framework
        logger.info(f"Web UI available at {self.custom_app_url}")
        
        # Wait for stop_event or user interaction
        try:
            while not stop_event.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self._cleanup()
    
    def _setup_api_routes(self):
        """Setup FastAPI routes and static file serving."""
        import os
        from fastapi import WebSocket, WebSocketDisconnect
        from fastapi.staticfiles import StaticFiles
        
        app = self.settings_app
        
        # Mount static files
        static_path = os.path.join(os.path.dirname(__file__), "static")
        if os.path.exists(static_path):
            app.mount("/static", StaticFiles(directory=static_path, html=True), name="static")
            logger.info(f"Mounted static files from {static_path}")
        
        # Initialize dashboard manager
        global dashboard_manager
        dashboard_manager = ConnectionManager()
        
        # Add all API routes
        self._add_api_routes(app)
        
        logger.info("API routes configured")
    
    def _add_api_routes(self, app: FastAPI):
        """Add all API routes to the FastAPI app."""
        from fastapi import WebSocket, WebSocketDisconnect
        import asyncio
        
        # Configuration endpoints
        @app.get("/api/config")
        async def get_config():
            """Get saved configuration."""
            try:
                config = load_saved_config()
                return {
                    "elevenlabs_api_key": config.get("elevenlabs_api_key", ""),
                    "elevenlabs_voice_id": config.get("elevenlabs_voice_id", "HSSEHuB5EziJgTfCVmC6")
                }
            except Exception as e:
                logger.error(f"Failed to get config: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/config")
        async def save_config_endpoint(request: ConfigSaveRequest):
            """Save configuration."""
            try:
                config = {
                    "elevenlabs_api_key": request.elevenlabs_api_key,
                    "elevenlabs_voice_id": request.elevenlabs_voice_id
                }
                
                if save_config(config):
                    return {"status": "saved", "message": "Configuration saved successfully"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to save configuration")
            except Exception as e:
                logger.error(f"Failed to save config: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Race data endpoints
        @app.get("/api/races/years")
        async def get_years():
            """Get list of available years with race data."""
            try:
                if _app_instance is None:
                    raise HTTPException(status_code=503, detail="App not initialized")
                
                years = _app_instance.openf1_client.get_years()
                return {"years": years}
            except Exception as e:
                logger.error(f"Failed to get years: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/races/{year}")
        async def get_races(year: int):
            """Get all races for a specific year."""
            try:
                if _app_instance is None:
                    raise HTTPException(status_code=503, detail="App not initialized")
                
                logger.info(f"Fetching races for year {year}")
                races = _app_instance.openf1_client.get_races_by_year(year)
                
                if not races:
                    logger.warning(f"No races found for year {year}")
                    return {"races": []}
                
                # Convert to dict format
                races_data = [
                    {
                        "session_key": race.session_key,
                        "date": race.date,
                        "country": race.country,
                        "circuit": race.circuit,
                        "name": race.name
                    }
                    for race in races
                ]
                
                logger.info(f"Returning {len(races_data)} races for year {year}")
                return {"races": races_data}
            except Exception as e:
                logger.error(f"Failed to get races for year {year}: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to load races: {str(e)}")
        
        # Commentary control endpoints
        @app.post("/api/commentary/start")
        async def start_commentary(request: CommentaryStartRequest):
            """Start commentary playback."""
            try:
                if _app_instance is None:
                    raise HTTPException(status_code=503, detail="App not initialized")
                
                # Convert request to WebUIConfiguration
                config = WebUIConfiguration(
                    mode=request.mode,
                    session_key=request.session_key,
                    commentary_mode=request.commentary_mode,
                    playback_speed=request.playback_speed,
                    elevenlabs_api_key=request.elevenlabs_api_key,
                    elevenlabs_voice_id=request.elevenlabs_voice_id
                )
                
                result = _app_instance.start_commentary(config)
                return result
            except Exception as e:
                logger.error(f"Failed to start commentary: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/api/commentary/stop")
        async def stop_commentary():
            """Stop active commentary playback."""
            try:
                if _app_instance is None:
                    raise HTTPException(status_code=503, detail="App not initialized")
                
                result = _app_instance.stop_commentary()
                return result
            except Exception as e:
                logger.error(f"Failed to stop commentary: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/api/commentary/status")
        async def get_status():
            """Get current playback status."""
            try:
                if _app_instance is None:
                    raise HTTPException(status_code=503, detail="App not initialized")
                
                status = _app_instance.get_status()
                return status
            except Exception as e:
                logger.error(f"Failed to get status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Q&A endpoint
        @app.post("/api/qa/ask")
        async def ask_question(request: QuestionRequest):
            """Handle Q&A question from user."""
            try:
                if _app_instance is None:
                    raise HTTPException(status_code=503, detail="App not initialized")
                
                if not request.question or not request.question.strip():
                    raise HTTPException(status_code=400, detail="Question cannot be empty")
                
                # Process question using QA manager
                answer = _app_instance.process_question(request.question)
                
                return {"question": request.question, "answer": answer}
            except Exception as e:
                logger.error(f"Failed to process question: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        # Dashboard endpoints
        @app.websocket("/ws/dashboard")
        async def dashboard_websocket(websocket: WebSocket):
            """WebSocket endpoint for live dashboard updates."""
            await dashboard_manager.connect(websocket)
            try:
                while True:
                    # Process any queued broadcasts
                    while dashboard_manager.broadcast_queue:
                        message = dashboard_manager.broadcast_queue.pop(0)
                        await dashboard_manager.broadcast(message)
                    
                    # Wait a bit before checking queue again
                    await asyncio.sleep(0.1)
                    
                    # Check if client sent any messages (for keep-alive)
                    try:
                        data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                        # Echo back for ping/pong
                        await websocket.send_text(data)
                    except asyncio.TimeoutError:
                        # No message received, continue
                        pass
                        
            except WebSocketDisconnect:
                dashboard_manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                dashboard_manager.disconnect(websocket)
        
        @app.get("/api/dashboard/state")
        async def get_dashboard_state():
            """Get current race state for dashboard."""
            try:
                if _app_instance is None or _app_instance.state_tracker is None:
                    return {
                        "positions": [],
                        "race_info": {
                            "current_lap": 0,
                            "total_laps": 0,
                            "leader": None,
                            "fastest_lap_holder": None,
                            "race_phase": "START"
                        },
                        "recent_events": []
                    }
                
                # Get positions
                positions = _app_instance.state_tracker.get_positions()
                positions_data = [
                    {
                        "position": p.position,
                        "driver": p.name,
                        "gap_to_leader": f"+{p.gap_to_leader:.3f}s" if p.gap_to_leader > 0 else "Leader",
                        "tire_compound": p.current_tire or "Unknown",
                        "pit_stops": p.pit_count,
                        "team": "Unknown"  # Team info not available in DriverState
                    }
                    for p in positions[:20]  # Top 20
                ]
                
                # Get race info
                leader = _app_instance.state_tracker.get_leader()
                state = _app_instance.state_tracker._state  # Access private _state attribute
                
                race_info = {
                    "current_lap": state.current_lap,
                    "total_laps": state.total_laps,
                    "leader": leader.name if leader else None,
                    "fastest_lap_holder": state.fastest_lap_driver,
                    "fastest_lap_time": f"{state.fastest_lap_time:.3f}s" if state.fastest_lap_time else None,
                    "race_phase": state.race_phase.value if state.race_phase else "START",
                    "safety_car": state.safety_car_active
                }
                
                return {
                    "positions": positions_data,
                    "race_info": race_info,
                    "recent_events": []  # TODO: Add event history
                }
            except Exception as e:
                logger.error(f"Failed to get dashboard state: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        # Root and health endpoints
        @app.get("/")
        async def root():
            """Redirect to static UI."""
            return RedirectResponse(url="/static/index.html")
        
        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy", "app": "reachy-f1-commentator"}
    
    def start_commentary(self, config: WebUIConfiguration) -> dict:
        """
        Start commentary playback with given configuration.
        
        Args:
            config: Configuration from web UI
            
        Returns:
            Status dictionary
        """
        # Validate configuration
        is_valid, error_msg = config.validate()
        if not is_valid:
            return {'status': 'error', 'message': error_msg}
        
        # Stop any existing playback
        if self.playback_thread and self.playback_thread.is_alive():
            self.stop_commentary()
        
        self.config = config
        self.stop_playback_event.clear()
        self.playback_status = PlaybackStatus(state='loading')
        
        # Start playback in background thread
        self.playback_thread = threading.Thread(
            target=self._run_playback,
            args=(config,),
            daemon=True
        )
        self.playback_thread.start()
        
        return {'status': 'started'}
    
    def stop_commentary(self) -> dict:
        """
        Stop active commentary playback.
        
        Returns:
            Status dictionary
        """
        logger.info("Stopping commentary playback")
        self.stop_playback_event.set()
        
        if self.playback_thread:
            self.playback_thread.join(timeout=5.0)
        
        self.playback_status = PlaybackStatus(state='stopped')
        return {'status': 'stopped'}
    
    def get_status(self) -> dict:
        """
        Get current playback status.
        
        Returns:
            Status dictionary
        """
        return self.playback_status.to_dict()
    
    def process_question(self, question: str) -> str:
        """
        Process a Q&A question from the user.
        
        Args:
            question: User's question text
            
        Returns:
            Answer string
        """
        try:
            # Initialize QA manager if not already done
            if not hasattr(self, 'qa_manager') or self.qa_manager is None:
                from .src.qa_manager import QAManager
                self.qa_manager = QAManager(
                    state_tracker=self.state_tracker,
                    event_queue=None  # We don't have an event queue in this architecture
                )
            
            # Debug: Log current state
            positions = self.state_tracker.get_positions()
            leader = self.state_tracker.get_leader()
            logger.info(f"Q&A Debug - Question: {question}")
            logger.info(f"Q&A Debug - Drivers count: {len(positions)}")
            logger.info(f"Q&A Debug - Leader: {leader.name if leader else 'None'}")
            if positions:
                logger.info(f"Q&A Debug - Top 3: {[(d.name, d.position) for d in positions[:3]]}")
            
            # Process the question
            answer = self.qa_manager.process_question(question)
            
            logger.info(f"Q&A - Answer: {answer}")
            
            return answer
            
        except Exception as e:
            logger.error(f"Error processing question: {e}", exc_info=True)
            return "I don't have that information right now"
    
    def _run_playback(self, config: WebUIConfiguration):
        """
        Run commentary playback (in background thread).
        
        Args:
            config: Configuration from web UI
        """
        try:
            logger.info(f"Starting playback - Reachy instance available: {self.reachy_mini_instance is not None}")
            self.playback_status.state = 'playing'
            
            # Initialize commentary generator (always use Enhanced mode)
            from .src.config import Config
            gen_config = Config()
            gen_config.elevenlabs_api_key = config.elevenlabs_api_key
            gen_config.elevenlabs_voice_id = config.elevenlabs_voice_id
            gen_config.enhanced_mode = True
            
            self.commentary_generator = EnhancedCommentaryGenerator(gen_config, self.state_tracker)
            
            # Initialize speech synthesizer if API key provided
            speech_synthesizer = None
            if config.elevenlabs_api_key:
                try:
                    from .src.speech_synthesizer import SpeechSynthesizer
                    from .src.motion_controller import MotionController
                    
                    logger.info("Initializing audio synthesis...")
                    
                    # Create motion controller
                    motion_controller = MotionController(gen_config)
                    
                    # Create speech synthesizer with runtime API key
                    speech_synthesizer = SpeechSynthesizer(
                        config=gen_config,
                        motion_controller=motion_controller,
                        api_key=config.elevenlabs_api_key,
                        voice_id=config.elevenlabs_voice_id
                    )
                    
                    # Set Reachy instance if available
                    if self.reachy_mini_instance:
                        speech_synthesizer.set_reachy(self.reachy_mini_instance)
                        logger.info("✅ Audio synthesis enabled with Reachy Mini")
                    else:
                        logger.warning("⚠️  Reachy Mini instance not available - audio will not play")
                        logger.info("This is expected when running in standalone mode without Reachy hardware")
                        logger.info("Audio synthesis will be initialized but playback will be skipped")
                    
                    if not speech_synthesizer.is_initialized():
                        logger.warning("⚠️  Audio synthesis initialization failed")
                        speech_synthesizer = None
                        
                except Exception as e:
                    logger.error(f"Failed to initialize audio synthesis: {e}", exc_info=True)
                    speech_synthesizer = None
            else:
                logger.info("No ElevenLabs API key provided - audio disabled")
            
            # Store speech synthesizer for use in playback methods
            self.speech_synthesizer = speech_synthesizer
            
            if config.mode == 'quick_demo':
                self._run_quick_demo()
            else:
                self._run_full_race(config.session_key, config.playback_speed)
            
        except Exception as e:
            logger.error(f"Error during playback: {e}", exc_info=True)
            self.playback_status.state = 'stopped'
        finally:
            self.playback_status.state = 'idle'
            # Cleanup speech synthesizer
            if hasattr(self, 'speech_synthesizer') and self.speech_synthesizer:
                try:
                    self.speech_synthesizer.stop()
                except:
                    pass
    
    def _run_quick_demo(self):
        """Run quick demo mode with pre-configured events."""
        logger.info("Running enhanced quick demo mode")
        
        # Setup demo race state with more drivers
        drivers = [
            DriverState(name="Max VERSTAPPEN", position=1, gap_to_leader=0.0, pit_count=0, current_tire="soft"),
            DriverState(name="Lewis HAMILTON", position=2, gap_to_leader=0.0, pit_count=0, current_tire="soft"),
            DriverState(name="Charles LECLERC", position=3, gap_to_leader=0.0, pit_count=0, current_tire="medium"),
            DriverState(name="Sergio PEREZ", position=4, gap_to_leader=0.0, pit_count=0, current_tire="medium"),
            DriverState(name="Carlos SAINZ", position=5, gap_to_leader=0.0, pit_count=0, current_tire="soft"),
            DriverState(name="Lando NORRIS", position=6, gap_to_leader=0.0, pit_count=0, current_tire="medium"),
            DriverState(name="Fernando ALONSO", position=7, gap_to_leader=0.0, pit_count=0, current_tire="soft"),
            DriverState(name="George RUSSELL", position=8, gap_to_leader=0.0, pit_count=0, current_tire="medium"),
        ]
        
        self.state_tracker._state.drivers = drivers
        self.state_tracker._state.current_lap = 0
        self.state_tracker._state.total_laps = 15
        self.state_tracker._state.race_phase = RacePhase.START
        
        # Enhanced demo events with a complete race narrative
        demo_events = [
            # Starting grid announcement
            {'type': EventType.POSITION_UPDATE, 'lap': 0, 'data': {
                'is_starting_grid': True,
                'starting_grid': [
                    {'position': 1, 'driver_number': '1', 'full_name': 'Max VERSTAPPEN'},
                    {'position': 2, 'driver_number': '44', 'full_name': 'Lewis HAMILTON'},
                    {'position': 3, 'driver_number': '16', 'full_name': 'Charles LECLERC'},
                    {'position': 4, 'driver_number': '11', 'full_name': 'Sergio PEREZ'},
                    {'position': 5, 'driver_number': '55', 'full_name': 'Carlos SAINZ'},
                    {'position': 6, 'driver_number': '4', 'full_name': 'Lando NORRIS'},
                    {'position': 7, 'driver_number': '14', 'full_name': 'Fernando ALONSO'},
                    {'position': 8, 'driver_number': '63', 'full_name': 'George RUSSELL'},
                ]
            }},
            
            # Race start - lights out!
            {'type': EventType.FLAG, 'lap': 1, 'data': {
                'flag_type': 'green',
                'is_race_start': True,
                'message': 'Race Start'
            }},
            
            # Lap 1 - Hamilton challenges Verstappen
            {'type': EventType.OVERTAKE, 'lap': 1, 'data': {
                'overtaking_driver': 'Lewis HAMILTON',
                'overtaken_driver': 'Max VERSTAPPEN',
                'new_position': 1
            }},
            
            # Lap 2 - Leclerc moves up
            {'type': EventType.OVERTAKE, 'lap': 2, 'data': {
                'overtaking_driver': 'Charles LECLERC',
                'overtaken_driver': 'Sergio PEREZ',
                'new_position': 3
            }},
            
            # Lap 3 - Fastest lap
            {'type': EventType.FASTEST_LAP, 'lap': 3, 'data': {
                'driver': 'Max VERSTAPPEN',
                'driver_number': '1',
                'lap_time': 89.456
            }},
            
            # Lap 4 - First pit stop
            {'type': EventType.PIT_STOP, 'lap': 4, 'data': {
                'driver': 'Sergio PEREZ',
                'driver_number': '11',
                'pit_count': 1,
                'pit_duration': 2.4,
                'tire_compound': 'hard'
            }},
            
            # Lap 5 - Verstappen retakes the lead
            {'type': EventType.OVERTAKE, 'lap': 5, 'data': {
                'overtaking_driver': 'Max VERSTAPPEN',
                'overtaken_driver': 'Lewis HAMILTON',
                'new_position': 1
            }},
            
            # Lap 6 - More pit stops
            {'type': EventType.PIT_STOP, 'lap': 6, 'data': {
                'driver': 'Lewis HAMILTON',
                'driver_number': '44',
                'pit_count': 1,
                'pit_duration': 2.1,
                'tire_compound': 'medium'
            }},
            
            # Lap 7 - Safety car deployed!
            {'type': EventType.SAFETY_CAR, 'lap': 7, 'data': {
                'status': 'deployed',
                'reason': 'Debris on track at Turn 4'
            }},
            
            # Lap 8 - Yellow flag
            {'type': EventType.FLAG, 'lap': 8, 'data': {
                'flag_type': 'yellow',
                'sector': 2,
                'message': 'Yellow flag in sector 2'
            }},
            
            # Lap 9 - Safety car ending
            {'type': EventType.SAFETY_CAR, 'lap': 9, 'data': {
                'status': 'ending',
                'reason': 'Track clear, safety car in this lap'
            }},
            
            # Lap 10 - Racing resumes with overtake
            {'type': EventType.OVERTAKE, 'lap': 10, 'data': {
                'overtaking_driver': 'Charles LECLERC',
                'overtaken_driver': 'Carlos SAINZ',
                'new_position': 3
            }},
            
            # Lap 11 - Another fastest lap
            {'type': EventType.FASTEST_LAP, 'lap': 11, 'data': {
                'driver': 'Lewis HAMILTON',
                'driver_number': '44',
                'lap_time': 88.923
            }},
            
            # Lap 12 - Late pit stop
            {'type': EventType.PIT_STOP, 'lap': 12, 'data': {
                'driver': 'Max VERSTAPPEN',
                'driver_number': '1',
                'pit_count': 1,
                'pit_duration': 2.2,
                'tire_compound': 'soft'
            }},
            
            # Lap 13 - Battle for position
            {'type': EventType.OVERTAKE, 'lap': 13, 'data': {
                'overtaking_driver': 'Fernando ALONSO',
                'overtaken_driver': 'Lando NORRIS',
                'new_position': 5
            }},
            
            # Lap 14 - Final fastest lap
            {'type': EventType.FASTEST_LAP, 'lap': 14, 'data': {
                'driver': 'Max VERSTAPPEN',
                'driver_number': '1',
                'lap_time': 88.234
            }},
            
            # Lap 15 - Checkered flag!
            {'type': EventType.FLAG, 'lap': 15, 'data': {
                'flag_type': 'chequered',
                'message': 'Checkered flag - race finish'
            }},
        ]
        
        for i, event_data in enumerate(demo_events):
            if self.stop_playback_event.is_set():
                break
            
            event = RaceEvent(
                event_type=event_data['type'],
                timestamp=datetime.now(),
                data=event_data['data']
            )
            
            # Update state
            lap = event_data['lap']
            self.state_tracker._state.current_lap = lap
            self.playback_status.current_lap = lap
            self.playback_status.total_laps = 15
            self.playback_status.elapsed_time = i * 5.0  # 5 seconds per event
            
            # Update race phase based on lap
            if lap == 0:
                self.state_tracker._state.race_phase = RacePhase.START
            elif lap >= 12:
                self.state_tracker._state.race_phase = RacePhase.FINISH
            else:
                self.state_tracker._state.race_phase = RacePhase.MID_RACE
            
            # Update race state and broadcast to dashboard
            self._update_race_state(event)
            
            # Generate commentary
            commentary = self.commentary_generator.generate(event)
            
            # Skip empty commentary
            if not commentary or not commentary.strip():
                continue
            
            logger.info(f"[Lap {lap:2d}] {commentary}")
            
            # Trigger gesture based on event type
            if hasattr(self, 'speech_synthesizer') and self.speech_synthesizer:
                if self.speech_synthesizer.motion_controller:
                    try:
                        from .src.motion_controller import GestureLibrary
                        gesture = GestureLibrary.get_gesture_for_event(event.event_type)
                        logger.debug(f"Triggering gesture: {gesture.value} for event: {event.event_type.value}")
                        self.speech_synthesizer.motion_controller.execute_gesture(gesture)
                    except Exception as e:
                        logger.error(f"Gesture execution error: {e}", exc_info=True)
            
            # Synthesize audio if available
            if hasattr(self, 'speech_synthesizer') and self.speech_synthesizer:
                try:
                    self.speech_synthesizer.synthesize_and_play(commentary)
                except Exception as e:
                    logger.error(f"Audio synthesis error: {e}", exc_info=True)
            
            # Simulate time between events (longer for important moments)
            if event.event_type == EventType.FLAG and event.data.get('is_race_start'):
                time.sleep(3.0)  # Pause after race start
            elif event.event_type == EventType.SAFETY_CAR:
                time.sleep(2.5)  # Pause for safety car
            elif event.event_type == EventType.FLAG and event.data.get('flag_type') == 'chequered':
                time.sleep(3.0)  # Pause after checkered flag
            else:
                time.sleep(2.0)  # Normal pause
        
        logger.info("Enhanced quick demo complete")
    
    def _run_full_race(self, session_key: int, playback_speed: int):
        """
        Run full historical race mode.
        
        Args:
            session_key: OpenF1 session key
            playback_speed: Playback speed multiplier
        """
        logger.info(f"Running full race mode: session_key={session_key}, speed={playback_speed}x")
        
        try:
            # Import FullRaceMode
            from .full_race_mode import FullRaceMode
            
            # Create and initialize Full Race Mode
            full_race = FullRaceMode(
                session_key=session_key,
                playback_speed=playback_speed,
                openf1_client=self.openf1_client,
                cache_dir=".test_cache"
            )
            
            # Initialize (fetch race data)
            self.playback_status.state = 'loading'
            logger.info("Loading race data...")
            
            if not full_race.initialize():
                logger.error("Failed to initialize Full Race Mode")
                self.playback_status.state = 'stopped'
                return
            
            # Get race metadata
            metadata = full_race.get_metadata()
            logger.info(f"Race loaded: {metadata}")
            
            # Update status
            self.playback_status.state = 'playing'
            self.playback_status.total_laps = 50  # Estimate, will be updated from events
            
            # Process events
            event_count = 0
            for event in full_race.get_events():
                if self.stop_playback_event.is_set():
                    logger.info("Playback stopped by user")
                    break
                
                # Update lap number if available
                lap_number = event.data.get('lap_number', 0)
                if lap_number > 0:
                    self.playback_status.current_lap = lap_number
                
                # Update race state and broadcast to dashboard
                self._update_race_state(event)
                
                # Generate commentary
                try:
                    commentary = self.commentary_generator.generate(event)
                    
                    # Debug: check what we got back
                    logger.debug(f"Event type: {event.event_type.value}, Commentary: {repr(commentary)[:100]}")
                    
                    # Skip empty or whitespace-only commentary
                    if commentary and isinstance(commentary, str) and commentary.strip():
                        logger.info(f"[Lap {lap_number}] {commentary}")
                        event_count += 1
                        
                        # Trigger gesture based on event type
                        if hasattr(self, 'speech_synthesizer') and self.speech_synthesizer:
                            if self.speech_synthesizer.motion_controller:
                                try:
                                    from .src.motion_controller import GestureLibrary
                                    gesture = GestureLibrary.get_gesture_for_event(event.event_type)
                                    logger.debug(f"Triggering gesture: {gesture.value} for event: {event.event_type.value}")
                                    self.speech_synthesizer.motion_controller.execute_gesture(gesture)
                                except Exception as e:
                                    logger.error(f"Gesture execution error: {e}", exc_info=True)
                        
                        # Synthesize audio if available
                        if hasattr(self, 'speech_synthesizer') and self.speech_synthesizer:
                            try:
                                self.speech_synthesizer.synthesize_and_play(commentary)
                            except Exception as e:
                                logger.error(f"Audio synthesis error: {e}", exc_info=True)
                        
                        # Add a small delay between commentary pieces to prevent queue overflow
                        # and give more natural pacing. At 1x speed, this ensures we don't
                        # generate commentary faster than race events occur.
                        # The delay is scaled by playback speed.
                        delay = 1.0 / playback_speed  # 1 second at 1x, 0.1s at 10x, 0.05s at 20x
                        time.sleep(delay)
                                
                except Exception as e:
                    logger.error(f"Error generating commentary: {e}", exc_info=True)
            
            logger.info(f"Full race complete: {event_count} commentary pieces generated")
            
        except Exception as e:
            logger.error(f"Error in full race mode: {e}", exc_info=True)
        finally:
            self.playback_status.state = 'idle'
    
    def _update_race_state(self, event: RaceEvent):
        """Update race state and broadcast to dashboard clients."""
        self.state_tracker.update(event)
        
        # Broadcast to dashboard if we have connections
        if dashboard_manager.active_connections:
            try:
                # Get current state
                positions = self.state_tracker.get_positions()
                leader = self.state_tracker.get_leader()
                state = self.state_tracker._state  # Access private _state attribute
                
                dashboard_data = {
                    "type": "state_update",
                    "positions": [
                        {
                            "position": p.position,
                            "driver": p.name,
                            "gap_to_leader": f"+{p.gap_to_leader:.3f}s" if p.gap_to_leader > 0 else "Leader",
                            "tire_compound": p.current_tire or "Unknown",
                            "pit_stops": p.pit_count,
                            "team": "Unknown"  # Team info not available in DriverState
                        }
                        for p in positions[:20]
                    ],
                    "race_info": {
                        "current_lap": state.current_lap,
                        "total_laps": state.total_laps,
                        "leader": leader.name if leader else None,
                        "fastest_lap_holder": state.fastest_lap_driver,
                        "fastest_lap_time": f"{state.fastest_lap_time:.3f}s" if state.fastest_lap_time else None,
                        "race_phase": state.race_phase.value if state.race_phase else "START",
                        "safety_car": state.safety_car_active
                    },
                    "last_event": {
                        "type": event.event_type.value,
                        "data": event.data,
                        "lap_number": state.current_lap
                    }
                }
                
                # Schedule broadcast in a thread-safe way
                import asyncio
                # Queue the broadcast to be executed by the event loop
                dashboard_manager.queue_broadcast(dashboard_data)
                
            except Exception as e:
                logger.error(f"Failed to broadcast dashboard update: {e}", exc_info=True)
    
    def _cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up F1 Commentator app")
        self.stop_playback_event.set()
        if self.playback_thread:
            self.playback_thread.join(timeout=2.0)



# ============================================================================
# Helper Classes and Functions for API Routes
# ============================================================================

# WebSocket connections for live dashboard
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json as json_module
import asyncio

class ConnectionManager:
    """Manages WebSocket connections for live dashboard updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.broadcast_queue = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Dashboard client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Dashboard client disconnected. Total connections: {len(self.active_connections)}")
    
    def queue_broadcast(self, message: dict):
        """Queue a message to be broadcast (thread-safe)."""
        self.broadcast_queue.append(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

# Global dashboard manager (initialized in _setup_api_routes)
dashboard_manager = None


# Pydantic models for API
class CommentaryStartRequest(BaseModel):
    mode: str
    session_key: Optional[int] = None
    commentary_mode: str = 'enhanced'
    playback_speed: int = 10
    elevenlabs_api_key: str = ''
    elevenlabs_voice_id: str = 'HSSEHuB5EziJgTfCVmC6'


class ConfigSaveRequest(BaseModel):
    elevenlabs_api_key: str = ''
    elevenlabs_voice_id: str = 'HSSEHuB5EziJgTfCVmC6'


class QuestionRequest(BaseModel):
    question: str


# Configuration file path
import os
CONFIG_DIR = os.path.expanduser("~/.reachy_f1_commentator")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def load_saved_config() -> dict:
    """Load saved configuration from file."""
    try:
        if os.path.exists(CONFIG_FILE):
            import json
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
    return {}


def save_config(config: dict) -> bool:
    """Save configuration to file."""
    try:
        import json
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


# ============================================================================
# Standalone Mode Entry Point
# ============================================================================

if __name__ == "__main__":
    app = ReachyF1Commentator()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        app.stop()
