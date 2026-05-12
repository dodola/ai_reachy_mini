"""Simon game for Reachy Mini robot with difficulty modes.

The robot displays a sequence using head movements and sounds.
Player repeats the sequence by tilting the robot's head in 4 directions.

Difficulty modes:
- Difficulty 1: Head tilts only (UP, DOWN, LEFT, RIGHT)
- Difficulty 2: Head tilts + body yaw rotation (BODY_LEFT, BODY_RIGHT)
- Difficulty 3: Head tilts + body yaw + antenna movements (4 antenna directions)
"""
import threading
import time
import random
from enum import Enum
from pathlib import Path
from typing import Optional, List

import numpy as np
from scipy.spatial.transform import Rotation as R
from reachy_mini import ReachyMini, ReachyMiniApp
from reachy_mini.utils import create_head_pose
from reachy_mini.motion.recorded_move import RecordedMoves

# ===== CONSTANTS =====
ASSETS_DIR = Path(__file__).parent / "assets"

TILT_THRESHOLD = 12.0  # degrees (very sensitive for easier detection)
NEUTRAL_THRESHOLD = 8.0  # degrees (very sensitive for easier detection)
BODY_YAW_THRESHOLD = 20.0  # degrees for body yaw detection
ANTENNA_THRESHOLD = 0.3  # radians for antenna detection


# ===== ENUMS =====
class Direction(Enum):
    """All possible directions across all difficulties."""
    # Difficulty 1: Head tilts
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

    # Difficulty 2: Body yaw
    BODY_LEFT = "body_left"
    BODY_RIGHT = "body_right"

    # Difficulty 3: Antennas
    LEFT_ANTENNA_LEFT = "left_antenna_left"
    LEFT_ANTENNA_RIGHT = "left_antenna_right"
    RIGHT_ANTENNA_LEFT = "right_antenna_left"
    RIGHT_ANTENNA_RIGHT = "right_antenna_right"


class GameState(Enum):
    """Game state machine states."""
    IDLE = "idle"
    SELECTING_DIFFICULTY = "selecting_difficulty"
    SHOWING_SEQUENCE = "showing_sequence"
    WAITING_FOR_INPUT = "waiting_for_input"
    CELEBRATING = "celebrating"
    GAME_OVER = "game_over"


# ===== DIFFICULTY CONFIGURATION =====
DIFFICULTY_DIRECTIONS = {
    1: [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT],
    2: [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT,
        Direction.BODY_LEFT, Direction.BODY_RIGHT],
    3: [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT,
        Direction.BODY_LEFT, Direction.BODY_RIGHT,
        Direction.LEFT_ANTENNA_LEFT, Direction.LEFT_ANTENNA_RIGHT,
        Direction.RIGHT_ANTENNA_LEFT, Direction.RIGHT_ANTENNA_RIGHT],
}

# ===== HEAD POSES =====
DIRECTION_POSES = {
    Direction.UP: create_head_pose(pitch=-20, degrees=True),
    Direction.DOWN: create_head_pose(pitch=20, degrees=True),
    Direction.LEFT: create_head_pose(roll=20, degrees=True),
    Direction.RIGHT: create_head_pose(roll=-20, degrees=True),
}

NEUTRAL_POSE = np.eye(4)

# Body yaw angles (degrees)
BODY_YAW_ANGLES = {
    Direction.BODY_LEFT: 30.0,
    Direction.BODY_RIGHT: -30.0,
}

# Antenna positions (radians)
ANTENNA_POSITIONS = {
    Direction.LEFT_ANTENNA_LEFT: ([0, 0.6], "left antenna left"),
    Direction.LEFT_ANTENNA_RIGHT: ([0, -0.6], "left antenna right"),
    Direction.RIGHT_ANTENNA_LEFT: ([0.6, 0], "right antenna left"),
    Direction.RIGHT_ANTENNA_RIGHT: ([-0.6, 0], "right antenna right"),
}

# ===== SOUND FILES =====
DIRECTION_SOUNDS = {
    Direction.UP: ASSETS_DIR / "up.wav",
    Direction.DOWN: ASSETS_DIR / "down.wav",
    Direction.LEFT: ASSETS_DIR / "left.wav",
    Direction.RIGHT: ASSETS_DIR / "right.wav",
    Direction.BODY_LEFT: ASSETS_DIR / "body_left.wav",
    Direction.BODY_RIGHT: ASSETS_DIR / "body_right.wav",
    Direction.LEFT_ANTENNA_LEFT: ASSETS_DIR / "left_antenna_left.wav",
    Direction.LEFT_ANTENNA_RIGHT: ASSETS_DIR / "left_antenna_right.wav",
    Direction.RIGHT_ANTENNA_LEFT: ASSETS_DIR / "right_antenna_left.wav",
    Direction.RIGHT_ANTENNA_RIGHT: ASSETS_DIR / "right_antenna_right.wav",
}

SUCCESS_SOUND = ASSETS_DIR / "success.wav"
GAME_OVER_SOUND = ASSETS_DIR / "game_over.wav"
START_GAME_SOUND = ASSETS_DIR / "start_game.wav"
DIFFICULTY_SOUNDS = {
    1: ASSETS_DIR / "difficulty1.wav",
    2: ASSETS_DIR / "difficulty2.wav",
    3: ASSETS_DIR / "difficulty3.wav",
}


# ===== DIFFICULTY SELECTION =====
class DifficultySelector:
    """Manages difficulty selection via left antenna position."""

    def __init__(self):
        self.current_difficulty = 1
        self.last_announced_difficulty = None

    def get_difficulty_from_antenna(self, left_antenna_pos: float) -> int:
        """
        Determine difficulty based on left antenna position.
        - Straight up (0 to 0.3 rad): Difficulty 1
        - ~45° (0.5 to 1.2 rad): Difficulty 2
        - ~90° (1.3+ rad): Difficulty 3
        """
        if left_antenna_pos < 0.3:
            return 1
        elif left_antenna_pos < 1.3:
            return 2
        else:
            return 3

    def update(self, left_antenna_pos: float) -> Optional[int]:
        """
        Update difficulty based on antenna position.
        Returns difficulty number if it changed, None otherwise.
        """
        new_difficulty = self.get_difficulty_from_antenna(left_antenna_pos)

        if new_difficulty != self.last_announced_difficulty:
            self.current_difficulty = new_difficulty
            self.last_announced_difficulty = new_difficulty
            return new_difficulty

        return None

    def reset(self):
        """Reset to allow re-announcement."""
        self.last_announced_difficulty = None


# ===== GAME CLASSES =====
class SimonGame:
    """Core game logic: sequence generation, validation, scoring."""

    def __init__(self, difficulty: int = 1):
        self.difficulty = difficulty
        self.sequence: List[Direction] = []
        self.current_round = 0
        self.best_round = 0

    def set_difficulty(self, difficulty: int):
        """Change difficulty level."""
        self.difficulty = difficulty

    def add_to_sequence(self):
        """Add a random direction to the sequence based on difficulty."""
        available_directions = DIFFICULTY_DIRECTIONS[self.difficulty]
        new_dir = random.choice(available_directions)
        self.sequence.append(new_dir)
        self.current_round += 1

    def validate_input(self, player_input: List[Direction]) -> bool:
        """Check if player input matches the sequence."""
        return player_input == self.sequence

    def is_new_record(self) -> bool:
        """Check if current round is a new personal best."""
        return self.current_round > self.best_round

    def update_best_score(self):
        """Update best score if current is better."""
        if self.current_round > self.best_round:
            self.best_round = self.current_round

    def reset(self):
        """Reset game for a new round."""
        self.sequence = []
        self.current_round = 0


class InputDetector:
    """Detects player inputs: head tilts, body yaw, and antenna positions."""

    def __init__(self, difficulty: int = 1):
        self.difficulty = difficulty
        self.state = "NEUTRAL"
        self.current_direction: Optional[Direction] = None
        self.tilt_start_time: Optional[float] = None
        self.last_input_time = 0.0

        # Configuration
        self.HOLD_DURATION = 0.1  # seconds to hold tilt (very fast)
        self.COOLDOWN = 0.1  # seconds between inputs
        self.debug = False  # Set to True to see orientation values

    def set_difficulty(self, difficulty: int):
        """Update difficulty level."""
        self.difficulty = difficulty

    def update(self, reachy_mini: ReachyMini) -> Optional[Direction]:
        """Check for player input.

        Returns Direction if valid input detected, None otherwise.
        """
        # Get head orientation
        head_pose = reachy_mini.get_current_head_pose()
        rotation_matrix = head_pose[:3, :3]
        r = R.from_matrix(rotation_matrix)
        roll, pitch, yaw = r.as_euler("xyz", degrees=True)

        # Get body yaw if difficulty >= 2
        body_yaw = 0.0
        if self.difficulty >= 2:
            joint_positions = reachy_mini.get_current_joint_positions()
            body_yaw = np.rad2deg(joint_positions[0][0])  # First joint is body yaw

        # Get antenna positions if difficulty >= 3
        antennas = [0.0, 0.0]
        if self.difficulty >= 3:
            antennas = reachy_mini.get_present_antenna_joint_positions()

        # Debug output
        if self.debug:
            print(f"Roll: {roll:6.1f}°  Pitch: {pitch:6.1f}°  Yaw: {yaw:6.1f}°  Body: {body_yaw:6.1f}°  State: {self.state}", end="\r")

        detected = self._detect_direction(roll, pitch, body_yaw, antennas)
        current_time = time.time()

        # State machine: NEUTRAL → TILTED → REGISTERED
        if self.state == "NEUTRAL":
            if detected is not None:
                self.state = "TILTED"
                self.current_direction = detected
                self.tilt_start_time = current_time

        elif self.state == "TILTED":
            if detected != self.current_direction:
                # Lost tilt, reset
                self.state = "NEUTRAL"
                self.current_direction = None
                self.tilt_start_time = None
            elif current_time - self.tilt_start_time >= self.HOLD_DURATION:
                # Held long enough
                if current_time - self.last_input_time >= self.COOLDOWN:
                    self.state = "REGISTERED"
                    self.last_input_time = current_time
                    if self.debug:
                        print(f"\n>>> Registered: {self.current_direction.value.upper()}")
                    return self.current_direction

        elif self.state == "REGISTERED":
            if detected is None:
                # Returned to neutral
                self.state = "NEUTRAL"
                self.current_direction = None

        return None

    def _detect_direction(self, roll: float, pitch: float, body_yaw: float,
                         antennas: List[float]) -> Optional[Direction]:
        """Detect direction from all sensor inputs based on difficulty."""

        # Check antennas first (Difficulty 3)
        if self.difficulty >= 3:
            # Left antenna (index 1)
            if antennas[1] > ANTENNA_THRESHOLD:
                return Direction.LEFT_ANTENNA_LEFT
            elif antennas[1] < -ANTENNA_THRESHOLD:
                return Direction.LEFT_ANTENNA_RIGHT

            # Right antenna (index 0)
            if antennas[0] > ANTENNA_THRESHOLD:
                return Direction.RIGHT_ANTENNA_LEFT
            elif antennas[0] < -ANTENNA_THRESHOLD:
                return Direction.RIGHT_ANTENNA_RIGHT

        # Check body yaw (Difficulty 2+)
        if self.difficulty >= 2:
            if body_yaw > BODY_YAW_THRESHOLD:
                return Direction.BODY_LEFT
            elif body_yaw < -BODY_YAW_THRESHOLD:
                return Direction.BODY_RIGHT

        # Check head tilts (All difficulties)
        # Neutral zone
        if abs(roll) < NEUTRAL_THRESHOLD and abs(pitch) < NEUTRAL_THRESHOLD:
            return None

        # Dominant axis
        if abs(pitch) > abs(roll):
            if pitch < -TILT_THRESHOLD:  # Forward tilt (negative pitch) is UP
                return Direction.UP
            elif pitch > TILT_THRESHOLD:  # Backward tilt (positive pitch) is DOWN
                return Direction.DOWN
        else:
            if roll > TILT_THRESHOLD:
                return Direction.LEFT
            elif roll < -TILT_THRESHOLD:
                return Direction.RIGHT

        return None

    def reset(self):
        """Reset detector for new round."""
        self.state = "NEUTRAL"
        self.current_direction = None
        self.tilt_start_time = None


class SequenceDisplay:
    """Displays sequence with head movements, body yaw, antennas, and sounds."""

    def __init__(self):
        self.MOVE_DURATION = 0.3
        self.HOLD_DURATION = 0.2
        self.RETURN_DURATION = 0.3
        self.PAUSE_DURATION = 0.15

    def show_direction(self, direction: Direction, reachy_mini: ReachyMini):
        """Display a single direction with animation and sound."""
        sound = DIRECTION_SOUNDS[direction]

        # Determine what to move based on direction type
        if direction in DIRECTION_POSES:
            # Head movement
            pose = DIRECTION_POSES[direction]
            reachy_mini.goto_target(head=pose, duration=self.MOVE_DURATION)
            reachy_mini.media.play_sound(str(sound))
            time.sleep(self.HOLD_DURATION)
            reachy_mini.goto_target(head=NEUTRAL_POSE, duration=self.RETURN_DURATION)
            time.sleep(self.PAUSE_DURATION)

        elif direction in BODY_YAW_ANGLES:
            # Body yaw movement
            yaw_angle = BODY_YAW_ANGLES[direction]
            reachy_mini.goto_target(body_yaw=np.deg2rad(yaw_angle), duration=self.MOVE_DURATION)
            reachy_mini.media.play_sound(str(sound))
            time.sleep(self.HOLD_DURATION)
            reachy_mini.goto_target(body_yaw=0, duration=self.RETURN_DURATION)
            time.sleep(self.PAUSE_DURATION)

        elif direction in ANTENNA_POSITIONS:
            # Antenna movement
            antenna_pos, desc = ANTENNA_POSITIONS[direction]
            reachy_mini.goto_target(antennas=antenna_pos, duration=self.MOVE_DURATION)
            reachy_mini.media.play_sound(str(sound))
            time.sleep(self.HOLD_DURATION)
            reachy_mini.goto_target(antennas=[0, 0], duration=self.RETURN_DURATION)
            time.sleep(self.PAUSE_DURATION)

    def show_sequence(
        self, sequence: List[Direction], reachy_mini: ReachyMini, stop_event: threading.Event
    ):
        """Display entire sequence."""
        print(f"Watch carefully! Sequence of {len(sequence)} moves:")

        for i, direction in enumerate(sequence):
            if stop_event.is_set():
                break

            print(f"  {i+1}. {direction.value.upper()}")
            self.show_direction(direction, reachy_mini)

        print("Your turn!\n")


# ===== MAIN APP =====
class ReachyMiniSimon(ReachyMiniApp):
    """Simon game for Reachy Mini with difficulty modes."""

    custom_app_url: str | None = None  # No web UI

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event):
        """Main game loop."""
        # Initialize game components
        difficulty_selector = DifficultySelector()
        game = SimonGame(difficulty=1)
        detector = InputDetector(difficulty=1)
        display = SequenceDisplay()

        # Load emotions library for celebrations
        try:
            emotions = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
            emotions_available = True
        except Exception as e:
            print(f"Warning: Could not load emotions library: {e}")
            emotions_available = False

        # Game state
        state = GameState.SELECTING_DIFFICULTY
        player_input: List[Direction] = []
        last_antenna_twitch = 0.0

        # Welcome message
        print("=" * 50)
        print("           SIMON - Reachy Mini Edition")
        print("=" * 50)
        print("\nDifficulty Selection:")
        print("  Move the LEFT antenna to select difficulty:")
        print("    - Straight up (0°): Difficulty 1 (Head only)")
        print("    - ~45°: Difficulty 2 (Head + Body Yaw)")
        print("    - ~90°: Difficulty 3 (Head + Body + Antennas)")
        print("\n  Pull the RIGHT antenna to start!")
        print("=" * 50 + "\n")

        # Move to neutral position and disable left antenna for selection
        print("Initializing...")
        reachy_mini.goto_target(head=NEUTRAL_POSE, antennas=[0, 0], body_yaw=0, duration=1.0)
        time.sleep(1.0)
        reachy_mini.disable_motors(["left_antenna"])  # Allow manual positioning
        print("Ready! Move left antenna to select difficulty, pull right to start.\n")
        difficulty_selector.reset()
        last_antenna_twitch = time.time()  # Initialize timer for twitching

        # Main game loop
        while not stop_event.is_set():
            if state == GameState.SELECTING_DIFFICULTY:
                # Twitch right antenna every 3 seconds to show ready state
                current_time = time.time()
                if current_time - last_antenna_twitch >= 3.0:
                    # Quick antenna twitch to indicate readiness (keep head at neutral)
                    reachy_mini.goto_target(head=NEUTRAL_POSE, antennas=[0.3, 0], body_yaw=0, duration=0.15)
                    reachy_mini.goto_target(head=NEUTRAL_POSE, antennas=[0, 0], body_yaw=0, duration=0.15)
                    last_antenna_twitch = current_time

                # Check difficulty selection via left antenna
                antennas = reachy_mini.get_present_antenna_joint_positions()
                left_antenna = antennas[1]

                new_difficulty = difficulty_selector.update(left_antenna)
                if new_difficulty is not None:
                    print(f"Difficulty {new_difficulty} selected!")
                    reachy_mini.media.play_sound(str(DIFFICULTY_SOUNDS[new_difficulty]))
                    game.set_difficulty(new_difficulty)
                    detector.set_difficulty(new_difficulty)

                # Check if right antenna pulled to start
                if abs(antennas[0]) > 0.4:
                    print(f"\n" + "=" * 50)
                    print(f"Starting game at Difficulty {game.difficulty}!")
                    print("=" * 50 + "\n")

                    # Re-enable left antenna and prepare for game
                    reachy_mini.enable_motors(["left_antenna"])
                    reachy_mini.goto_target(head=NEUTRAL_POSE, antennas=[0, 0], body_yaw=0, duration=0.5)
                    time.sleep(0.5)

                    reachy_mini.media.play_sound(str(START_GAME_SOUND))
                    time.sleep(0.5)

                    game.reset()
                    game.add_to_sequence()
                    state = GameState.SHOWING_SEQUENCE

            elif state == GameState.SHOWING_SEQUENCE:
                # Display sequence to player
                display.show_sequence(game.sequence, reachy_mini, stop_event)

                # Reset to neutral and prepare for input
                reachy_mini.goto_target(head=NEUTRAL_POSE, antennas=[0, 0], body_yaw=0, duration=0.2)

                # Reset for player input
                player_input = []
                detector.reset()

                print(f"Repeat the sequence ({len(game.sequence)} moves):")

                state = GameState.WAITING_FOR_INPUT

            elif state == GameState.WAITING_FOR_INPUT:
                # Detect player input
                direction = detector.update(reachy_mini)

                # Show feedback when tilting (before full hold)
                if detector.state == "TILTED" and detector.current_direction is not None:
                    hold_time = time.time() - detector.tilt_start_time
                    remaining = detector.HOLD_DURATION - hold_time
                    if remaining > 0:
                        print(f"  Holding {detector.current_direction.value.upper()}... {remaining:.1f}s   ", end="\r")

                if direction is not None:
                    player_input.append(direction)

                    # Play sound feedback for the direction
                    sound = DIRECTION_SOUNDS[direction]
                    reachy_mini.media.play_sound(str(sound))

                    # Check immediately if this input is correct
                    current_index = len(player_input) - 1
                    expected_direction = game.sequence[current_index]

                    if direction != expected_direction:
                        # Wrong input! Lose immediately
                        print(
                            f"  Input {len(player_input)}: {direction.value.upper()} "
                            f"({len(player_input)}/{len(game.sequence)})"
                        )
                        print(f"\n✗ Wrong! Expected {expected_direction.value.upper()}\n")
                        state = GameState.GAME_OVER
                    else:
                        # Correct so far
                        print(
                            f"  Input {len(player_input)}: {direction.value.upper()} "
                            f"({len(player_input)}/{len(game.sequence)})"
                        )

                        # Check if sequence is complete
                        if len(player_input) == len(game.sequence):
                            print("\n✓ Complete sequence correct!\n")
                            reachy_mini.media.play_sound(str(SUCCESS_SOUND))

                            # Add to sequence and continue
                            game.add_to_sequence()
                            time.sleep(0.5)
                            state = GameState.SHOWING_SEQUENCE

            elif state == GameState.CELEBRATING:
                # Play celebration emotion
                celebration_emotions = ["enthusiastic1", "enthusiastic2", "success2"]
                try:
                    emotion_name = random.choice(celebration_emotions)
                    celebration = emotions.get(emotion_name)
                    print(f"Playing {emotion_name} celebration!")
                    reachy_mini.play_move(celebration, initial_goto_duration=0.5)
                except Exception as e:
                    print(f"Could not play celebration: {e}")
                    time.sleep(1.0)

                # After celebration, show game over screen
                print("=" * 50)
                print(f"Game Over! Final Score: Round {game.current_round}")
                print(f"Best Score: Round {game.best_round}")
                print(f"Difficulty: {game.difficulty}")
                print("=" * 50)
                print("\nReturning to difficulty selection...")

                # Reset to neutral position
                reachy_mini.goto_target(head=NEUTRAL_POSE, antennas=[0, 0], body_yaw=0, duration=1.0)
                time.sleep(0.5)
                reachy_mini.disable_motors(["left_antenna"])  # Re-enable selection

                print("Move left antenna to select difficulty, pull right to start!\n")
                difficulty_selector.reset()
                last_antenna_twitch = time.time()
                state = GameState.SELECTING_DIFFICULTY

            elif state == GameState.GAME_OVER:
                # Always play game over sound first
                reachy_mini.media.play_sound(str(GAME_OVER_SOUND))
                time.sleep(0.5)

                # Check if new record
                is_new_record = game.is_new_record()

                if is_new_record and emotions_available:
                    # Celebrate new record after game over sound!
                    print("\n🎉 NEW RECORD! 🎉\n")
                    game.update_best_score()
                    state = GameState.CELEBRATING
                else:
                    # Regular game over
                    print("=" * 50)
                    print(f"Game Over! Final Score: Round {game.current_round}")
                    print(f"Best Score: Round {game.best_round}")
                    print(f"Difficulty: {game.difficulty}")
                    print("=" * 50)
                    print("\nReturning to difficulty selection...")

                    # Reset to neutral position
                    reachy_mini.goto_target(head=NEUTRAL_POSE, antennas=[0, 0], body_yaw=0, duration=1.0)
                    time.sleep(0.5)
                    reachy_mini.disable_motors(["left_antenna"])  # Re-enable selection

                    print("Move left antenna to select difficulty, pull right to start!\n")
                    difficulty_selector.reset()
                    last_antenna_twitch = time.time()
                    state = GameState.SELECTING_DIFFICULTY

            time.sleep(0.02)


if __name__ == "__main__":
    app = ReachyMiniSimon()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        print("\nGame interrupted. Goodbye!")
        app.stop()
