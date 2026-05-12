"""Motion Controller for F1 Commentary Robot.

This module controls the Reachy Mini robot's physical movements during commentary,
including head gestures synchronized with speech and expressive reactions to race events.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.8, 7.9
"""

import logging
import threading
import time
from typing import Optional, Tuple
from dataclasses import dataclass

import numpy as np

from reachy_f1_commentator.src.models import Gesture, EventType
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.graceful_degradation import degradation_manager


logger = logging.getLogger(__name__)


# ============================================================================
# Reachy SDK Interface Wrapper
# ============================================================================

class ReachyInterface:
    """Wrapper for Reachy Mini SDK providing movement control.
    
    Reachy Mini has rich DOF capabilities:
    - Neck: 6 DOF via Stewart-platform (yaw, pitch, roll + x, y, z translations)
    - Body: 1 DOF continuous 360° base rotation
    - Antennas: 2 DOF (1 per antenna)
    - Total: 9 actuated DOF for full expressivity
    
    For F1 commentary, we focus on neck expressiveness (6 DOF).
    
    Validates: Requirement 7.2
    """
    
    # Movement constraints (in degrees for rotations, mm for translations)
    # These are conservative limits to ensure safe operation
    MAX_ROLL = 30.0
    MIN_ROLL = -30.0
    MAX_PITCH = 20.0
    MIN_PITCH = -20.0
    MAX_YAW = 45.0
    MIN_YAW = -45.0
    MAX_TRANSLATION = 20.0  # mm for x, y, z
    MIN_TRANSLATION = -20.0
    
    def __init__(self):
        """Initialize Reachy SDK connection.
        
        The SDK auto-detects localhost connection when running on the robot.
        """
        self.reachy = None
        self.connected = False
        
        try:
            from reachy_mini import ReachyMini
            from reachy_mini.utils import create_head_pose
            
            self.ReachyMini = ReachyMini
            self.create_head_pose = create_head_pose
            
            # Connect to Reachy (auto-detects localhost)
            self.reachy = ReachyMini()
            self.connected = True
            logger.info("Successfully connected to Reachy Mini SDK")
            
        except ImportError as e:
            logger.error(f"[MotionController] Failed to import Reachy SDK: {e}", exc_info=True)
            logger.warning("Motion control will be disabled")
        except Exception as e:
            logger.error(f"[MotionController] Failed to connect to Reachy Mini: {e}", exc_info=True)
            logger.warning("Motion control will be disabled")
    
    def is_connected(self) -> bool:
        """Check if connected to Reachy SDK."""
        return self.connected
    
    def validate_movement(self, x: float = 0, y: float = 0, z: float = 0,
                         roll: float = 0, pitch: float = 0, yaw: float = 0) -> Tuple[bool, str]:
        """Validate movement parameters against constraints.
        
        Args:
            x, y, z: Translational movements in mm
            roll, pitch, yaw: Rotational movements in degrees
            
        Returns:
            Tuple of (is_valid, error_message)
            
        Validates: Requirement 7.2
        """
        errors = []
        
        # Validate rotations
        if not self.MIN_ROLL <= roll <= self.MAX_ROLL:
            errors.append(f"Roll {roll}° out of range [{self.MIN_ROLL}, {self.MAX_ROLL}]")
        if not self.MIN_PITCH <= pitch <= self.MAX_PITCH:
            errors.append(f"Pitch {pitch}° out of range [{self.MIN_PITCH}, {self.MAX_PITCH}]")
        if not self.MIN_YAW <= yaw <= self.MAX_YAW:
            errors.append(f"Yaw {yaw}° out of range [{self.MIN_YAW}, {self.MAX_YAW}]")
        
        # Validate translations
        if not self.MIN_TRANSLATION <= x <= self.MAX_TRANSLATION:
            errors.append(f"X translation {x}mm out of range [{self.MIN_TRANSLATION}, {self.MAX_TRANSLATION}]")
        if not self.MIN_TRANSLATION <= y <= self.MAX_TRANSLATION:
            errors.append(f"Y translation {y}mm out of range [{self.MIN_TRANSLATION}, {self.MAX_TRANSLATION}]")
        if not self.MIN_TRANSLATION <= z <= self.MAX_TRANSLATION:
            errors.append(f"Z translation {z}mm out of range [{self.MIN_TRANSLATION}, {self.MAX_TRANSLATION}]")
        
        if errors:
            return False, "; ".join(errors)
        return True, ""
    
    def move_head(self, x: float = 0, y: float = 0, z: float = 0,
                  roll: float = 0, pitch: float = 0, yaw: float = 0,
                  antennas: Optional[np.ndarray] = None,
                  body_yaw: Optional[float] = None,
                  duration: float = 1.0,
                  method: str = "minjerk") -> bool:
        """Move head (and optionally body/antennas) using goto_target.
        
        Args:
            x, y, z: Translational movements in mm
            roll, pitch, yaw: Rotational movements in degrees
            antennas: Array of 2 antenna angles in radians (optional)
            body_yaw: Body rotation in radians (optional)
            duration: Movement duration in seconds
            method: Interpolation method ('minjerk', 'linear', 'ease', 'cartoon')
            
        Returns:
            True if movement was executed, False otherwise
            
        Example:
            # Excited gesture: lean forward, look up, antennas up
            move_head(z=10, pitch=15, yaw=5, 
                     antennas=np.deg2rad([30, 30]), 
                     duration=0.5)
        """
        if not self.connected:
            logger.warning("Cannot move head: not connected to Reachy")
            return False
        
        # Validate movement parameters
        is_valid, error_msg = self.validate_movement(x, y, z, roll, pitch, yaw)
        if not is_valid:
            logger.error(f"Invalid movement parameters: {error_msg}")
            return False
        
        try:
            # Create head pose
            head_pose = self.create_head_pose(
                x=x, y=y, z=z,
                roll=roll, pitch=pitch, yaw=yaw,
                mm=True
            )
            
            # Set default antenna and body positions if not provided
            if antennas is None:
                antennas = np.deg2rad([0, 0])
            if body_yaw is None:
                body_yaw = 0
            
            # Execute movement
            self.reachy.goto_target(
                head=head_pose,
                antennas=antennas,
                body_yaw=body_yaw,
                duration=duration,
                method=method
            )
            
            logger.debug(f"Executed head movement: pitch={pitch}°, yaw={yaw}°, roll={roll}°, "
                        f"x={x}mm, y={y}mm, z={z}mm, duration={duration}s")
            return True
            
        except Exception as e:
            logger.error(f"[MotionController] Failed to execute head movement: {e}", exc_info=True)
            return False
    
    def get_current_position(self) -> Optional[dict]:
        """Get current head position.
        
        Returns:
            Dictionary with current position data, or None if unavailable
        """
        if not self.connected:
            return None
        
        try:
            # This would query the actual position from the robot
            # For now, we return None as we don't track position
            return None
        except Exception as e:
            logger.error(f"[MotionController] Failed to get current position: {e}", exc_info=True)
            return None


# ============================================================================
# Gesture Library
# ============================================================================

@dataclass
class GestureSequence:
    """Defines a sequence of movements for a gesture."""
    movements: list[dict]  # List of movement parameters
    total_duration: float  # Total time for gesture
    
    
class GestureLibrary:
    """Library of predefined gestures for F1 commentary.
    
    Each gesture is defined as a sequence of movements using the 6-DOF
    neck capabilities (pitch, yaw, roll, x, y, z) plus 2 antenna DOF.
    
    Validates: Requirements 7.3, 7.4, 7.5, 7.6
    """
    
    # Gesture definitions
    GESTURES = {
        Gesture.NEUTRAL: GestureSequence(
            movements=[
                {"pitch": 0, "yaw": 0, "roll": 0, "x": 0, "y": 0, "z": 0, 
                 "antennas": [0, 0], "duration": 1.0}
            ],
            total_duration=1.0
        ),
        
        Gesture.NOD: GestureSequence(
            movements=[
                {"pitch": 10, "yaw": 0, "roll": 0, "antennas": [10, 10], "duration": 0.3},
                {"pitch": -5, "yaw": 0, "roll": 0, "antennas": [-5, -5], "duration": 0.3},
                {"pitch": 0, "yaw": 0, "roll": 0, "antennas": [0, 0], "duration": 0.3}
            ],
            total_duration=0.9
        ),
        
        Gesture.TURN_LEFT: GestureSequence(
            movements=[
                {"pitch": 0, "yaw": -30, "roll": 0, "antennas": [-15, 5], "duration": 0.5},
                {"pitch": 0, "yaw": 0, "roll": 0, "antennas": [0, 0], "duration": 0.5}
            ],
            total_duration=1.0
        ),
        
        Gesture.TURN_RIGHT: GestureSequence(
            movements=[
                {"pitch": 0, "yaw": 30, "roll": 0, "antennas": [5, -15], "duration": 0.5},
                {"pitch": 0, "yaw": 0, "roll": 0, "antennas": [0, 0], "duration": 0.5}
            ],
            total_duration=1.0
        ),
        
        Gesture.EXCITED: GestureSequence(
            movements=[
                # Quick forward lean with look up and antennas up
                {"pitch": 15, "yaw": 5, "roll": 0, "z": 10, "antennas": [30, 30], "duration": 0.3},
                # Slight turn left with asymmetric antennas
                {"pitch": 10, "yaw": -10, "roll": 0, "z": 10, "antennas": [35, 25], "duration": 0.3},
                # Slight turn right with asymmetric antennas
                {"pitch": 10, "yaw": 10, "roll": 0, "z": 10, "antennas": [25, 35], "duration": 0.3},
                # Return to neutral
                {"pitch": 0, "yaw": 0, "roll": 0, "z": 0, "antennas": [0, 0], "duration": 0.4}
            ],
            total_duration=1.3
        ),
        
        Gesture.CONCERNED: GestureSequence(
            movements=[
                # Slow tilt left with slight down look and drooping antennas
                {"pitch": -5, "yaw": 0, "roll": -15, "antennas": [-20, -20], "duration": 0.6},
                # Hold position
                {"pitch": -5, "yaw": 0, "roll": -15, "antennas": [-20, -20], "duration": 0.4},
                # Return to neutral slowly
                {"pitch": 0, "yaw": 0, "roll": 0, "antennas": [0, 0], "duration": 0.6}
            ],
            total_duration=1.6
        ),
    }
    
    # Map event types to gestures
    EVENT_GESTURE_MAP = {
        EventType.OVERTAKE: Gesture.EXCITED,
        EventType.LEAD_CHANGE: Gesture.EXCITED,
        EventType.INCIDENT: Gesture.CONCERNED,
        EventType.SAFETY_CAR: Gesture.CONCERNED,
        EventType.PIT_STOP: Gesture.NOD,
        EventType.FASTEST_LAP: Gesture.NOD,
        EventType.FLAG: Gesture.TURN_LEFT,
        EventType.POSITION_UPDATE: Gesture.NEUTRAL,
    }
    
    @classmethod
    def get_gesture(cls, gesture: Gesture) -> GestureSequence:
        """Get gesture sequence by gesture type."""
        return cls.GESTURES.get(gesture, cls.GESTURES[Gesture.NEUTRAL])
    
    @classmethod
    def get_gesture_for_event(cls, event_type: EventType) -> Gesture:
        """Get appropriate gesture for an event type.
        
        Validates: Requirements 7.5, 7.6
        """
        return cls.EVENT_GESTURE_MAP.get(event_type, Gesture.NEUTRAL)


# ============================================================================
# Motion Controller
# ============================================================================

class MotionController:
    """Main motion controller orchestrator.
    
    Manages robot movements synchronized with commentary audio,
    executes expressive gestures, and ensures safe operation.
    
    Validates: Requirements 7.1, 7.8, 7.9
    """
    
    def __init__(self, config: Config):
        """Initialize motion controller.
        
        Args:
            config: System configuration
        """
        self.config = config
        self.reachy = ReachyInterface()
        self.gesture_library = GestureLibrary()
        
        # State tracking
        self.is_moving = False
        self.current_gesture: Optional[Gesture] = None
        self.last_movement_time = 0.0
        self.stop_requested = False
        
        # Threading for asynchronous operation
        self.movement_thread: Optional[threading.Thread] = None
        self.movement_lock = threading.Lock()
        
        # Idle timeout (return to neutral after 2 seconds)
        self.idle_timeout = 2.0
        self.idle_check_thread: Optional[threading.Thread] = None
        self.idle_check_running = False
        
        logger.info("Motion Controller initialized")
        
        if not self.reachy.is_connected():
            logger.warning("Reachy SDK not connected - movements will be simulated")
        
        # Start idle check thread
        self._start_idle_check()
    
    def execute_gesture(self, gesture: Gesture) -> None:
        """Execute a predefined gesture.
        
        Args:
            gesture: Gesture to execute
            
        Validates: Requirements 7.3, 7.4
        """
        # Check if motion control is available (graceful degradation)
        if not degradation_manager.is_motion_control_available():
            logger.debug(f"[MotionController] Motion control unavailable, skipping gesture: {gesture.value}")
            return
        
        if not self.config.enable_movements:
            logger.debug(f"Movements disabled, skipping gesture: {gesture.value}")
            return
        
        # Get gesture sequence
        sequence = self.gesture_library.get_gesture(gesture)
        
        # Execute in separate thread for async operation
        self.movement_thread = threading.Thread(
            target=self._execute_gesture_sequence,
            args=(gesture, sequence),
            daemon=True
        )
        self.movement_thread.start()
    
    def _execute_gesture_sequence(self, gesture: Gesture, sequence: GestureSequence) -> None:
        """Execute a gesture sequence (runs in separate thread).
        
        Args:
            gesture: Gesture being executed
            sequence: Gesture sequence to execute
        """
        with self.movement_lock:
            self.is_moving = True
            self.current_gesture = gesture
            self.last_movement_time = time.time()
            
            logger.info(f"Executing gesture: {gesture.value}")
            
            try:
                for movement in sequence.movements:
                    if self.stop_requested:
                        logger.info("Movement stopped by request")
                        break
                    
                    # Extract movement parameters
                    pitch = movement.get("pitch", 0)
                    yaw = movement.get("yaw", 0)
                    roll = movement.get("roll", 0)
                    x = movement.get("x", 0)
                    y = movement.get("y", 0)
                    z = movement.get("z", 0)
                    duration = movement.get("duration", 1.0)
                    
                    # Extract antenna positions (in degrees, will be converted to radians)
                    antenna_angles = movement.get("antennas", [0, 0])
                    antennas = np.deg2rad(antenna_angles)
                    
                    # Apply speed limiting (Requirement 7.8)
                    duration = self._apply_speed_limit(pitch, yaw, roll, duration)
                    
                    # Execute movement with antennas
                    success = self.reachy.move_head(
                        x=x, y=y, z=z,
                        roll=roll, pitch=pitch, yaw=yaw,
                        antennas=antennas,
                        duration=duration,
                        method="minjerk"
                    )
                    
                    if not success:
                        logger.warning(f"Failed to execute movement in gesture {gesture.value}")
                        degradation_manager.record_motion_failure()
                    else:
                        degradation_manager.record_motion_success()
                    
                    # Wait for movement to complete
                    time.sleep(duration)
                
                logger.info(f"Completed gesture: {gesture.value}")
                
            except Exception as e:
                logger.error(f"[MotionController] Error executing gesture {gesture.value}: {e}", exc_info=True)
                degradation_manager.record_motion_failure()
            
            finally:
                self.is_moving = False
                self.current_gesture = None
                self.last_movement_time = time.time()
    
    def _apply_speed_limit(self, pitch: float, yaw: float, roll: float, 
                          duration: float) -> float:
        """Apply speed limiting to ensure safe movement.
        
        Ensures angular velocity doesn't exceed 30°/second.
        
        Args:
            pitch, yaw, roll: Rotation angles in degrees
            duration: Requested duration in seconds
            
        Returns:
            Adjusted duration to respect speed limit
            
        Validates: Requirement 7.8
        """
        max_speed = self.config.movement_speed  # degrees/second
        
        # Calculate maximum angle change
        max_angle = max(abs(pitch), abs(yaw), abs(roll))
        
        # Calculate minimum duration to respect speed limit
        min_duration = max_angle / max_speed
        
        # Return the larger of requested duration or minimum duration
        adjusted_duration = max(duration, min_duration)
        
        if adjusted_duration > duration:
            logger.debug(f"Adjusted movement duration from {duration:.2f}s to "
                        f"{adjusted_duration:.2f}s to respect speed limit")
        
        return adjusted_duration
    
    def sync_with_speech(self, audio_duration: float) -> None:
        """Generate movements synchronized with speech duration.
        
        This method can be called when audio playback starts to coordinate
        movements with the commentary audio.
        
        Args:
            audio_duration: Duration of audio in seconds
            
        Validates: Requirement 7.1
        """
        logger.debug(f"Synchronizing movements with {audio_duration:.2f}s audio")
        
        # For now, we don't generate dynamic movements based on duration
        # The gesture execution is already timed appropriately
        # This method serves as a hook for future enhancements
        
        self.last_movement_time = time.time()
    
    def return_to_neutral(self) -> None:
        """Return head to neutral position.
        
        Validates: Requirement 7.9
        """
        if not self.config.enable_movements:
            return
        
        logger.debug("Returning to neutral position")
        self.execute_gesture(Gesture.NEUTRAL)
    
    def _start_idle_check(self) -> None:
        """Start idle check thread to return to neutral when idle."""
        self.idle_check_running = True
        self.idle_check_thread = threading.Thread(
            target=self._idle_check_loop,
            daemon=True
        )
        self.idle_check_thread.start()
    
    def _idle_check_loop(self) -> None:
        """Check for idle state and return to neutral (runs in separate thread).
        
        Validates: Requirement 7.9
        """
        while self.idle_check_running:
            try:
                time.sleep(0.5)  # Check every 0.5 seconds
                
                # Skip if movements disabled or currently moving
                if not self.config.enable_movements or self.is_moving:
                    continue
                
                # Check if idle timeout exceeded
                time_since_last_movement = time.time() - self.last_movement_time
                
                if time_since_last_movement > self.idle_timeout:
                    # Only return to neutral if not already there
                    if self.current_gesture != Gesture.NEUTRAL:
                        logger.debug(f"Idle for {time_since_last_movement:.1f}s, returning to neutral")
                        self.return_to_neutral()
                        # Reset timer to avoid repeated neutral commands
                        self.last_movement_time = time.time()
                
            except Exception as e:
                logger.error(f"[MotionController] Error in idle check loop: {e}", exc_info=True)
    
    def stop(self) -> None:
        """Stop all movements immediately (emergency halt).
        
        Validates: Requirement 7.9
        """
        logger.info("Emergency stop requested")
        self.stop_requested = True
        
        # Wait for current movement to stop
        if self.movement_thread and self.movement_thread.is_alive():
            self.movement_thread.join(timeout=1.0)
        
        # Return to neutral
        self.return_to_neutral()
        
        # Stop idle check
        self.idle_check_running = False
        if self.idle_check_thread and self.idle_check_thread.is_alive():
            self.idle_check_thread.join(timeout=1.0)
        
        logger.info("Motion controller stopped")
    
    def is_speaking(self) -> bool:
        """Check if robot is currently moving (speaking).
        
        Returns:
            True if movements are in progress
        """
        return self.is_moving
