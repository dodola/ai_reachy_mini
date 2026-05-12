#!/usr/bin/env python3
"""Autonomous Dance Move Tester and Choreography Player for Reachy Mini.

---------------------------------------------
This script cycles through moves automatically for quick previews and can also
play pre-defined choreographies from JSON files.

Preview Mode (default):
    python dance_demo.py
    - Cycles through all available moves automatically.

Player Mode:
    python dance_demo.py --choreography choreographies/my_choreo.json
    - Plays a specific, ordered sequence of moves from a file.
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from reachy_mini import ReachyMini, utils
from reachy_mini_dances_library.collection.dance import AVAILABLE_MOVES


# Moves that are too dynamic for the default preview cycle.
DEFAULT_SKIPPED_MOVES: List[str] = ["headbanger_combo"]


# --- Configuration ---
@dataclass
class Config:
    """Store configuration for the dance tester."""

    bpm: float = 120.0
    control_ts: float = 0.01  # 100 Hz control loop
    beats_per_sequence: int = 8  # Switch move every 8 beats
    start_move: str = "simple_nod"
    amplitude_scale: float = 1.0
    neutral_pos: np.ndarray = field(default_factory=lambda: np.array([0, 0, 0.0]))
    neutral_eul: np.ndarray = field(default_factory=lambda: np.zeros(3))
    choreography_path: Optional[str] = None


# --- Logic updated to only handle the new, standardized format ---
def load_choreography(
    file_path: str,
) -> Optional[Tuple[List[Dict[str, Any]], Optional[float]]]:
    """Load a choreography from a JSON file.

    The file must be a JSON object with a 'bpm' key and a 'sequence' key.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"Error: Choreography file not found at '{file_path}'")
        return None
    try:
        with open(path) as f:
            data = json.load(f)

        if not isinstance(data, dict):
            print(
                f"Error: Choreography file '{file_path}' has an invalid format. It must be a JSON object containing 'bpm' and 'sequence' keys."
            )
            return None

        sequence = data.get("sequence")
        bpm_from_file = data.get("bpm")

        if not isinstance(sequence, list):
            print(
                f"Error: Choreography file '{file_path}' is missing a 'sequence' list."
            )
            return None

        for step in sequence:
            if step.get("move") not in AVAILABLE_MOVES:
                print(
                    f"Error: Move '{step.get('move')}' in choreography is not a valid move."
                )
                return None

        return sequence, bpm_from_file

    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file_path}'")
        return None


# --- Main Application Logic ---
def main(config: Config) -> None:
    """Run the main application loop for the dance tester."""
    choreography = None
    choreography_mode = False
    if config.choreography_path:
        result = load_choreography(config.choreography_path)
        if result:
            choreography, _ = result
            choreography_mode = True
        else:
            return

    skip_moves = set(DEFAULT_SKIPPED_MOVES)
    move_names: List[str] = [
        name for name in AVAILABLE_MOVES.keys() if name not in skip_moves
    ]
    if not move_names:
        move_names = list(AVAILABLE_MOVES.keys())

    try:
        current_move_idx = move_names.index(config.start_move)
    except ValueError:
        print(
            f"Warning: Start move '{config.start_move}' not found. Starting with the first move."
        )
        current_move_idx = 0

    t_beats, sequence_beat_counter = 0.0, 0.0
    choreography_step_idx, step_beat_counter = 0, 0.0
    last_status_print_time = 0.0
    bpm, amplitude_scale = config.bpm, config.amplitude_scale

    with ReachyMini(media_backend="no_media") as mini:
        try:
            print("Connecting to Reachy Mini...")

            mode_text = (
                "Choreography Player" if choreography_mode else "Interactive Tester"
            )
            print(
                f"Robot connected. Starting {mode_text} (no keyboard controls). Press Ctrl+C to exit."
            )
            mini.wake_up()

            last_loop_time = time.time()

            while True:
                loop_start_time = time.time()
                dt = loop_start_time - last_loop_time
                last_loop_time = loop_start_time

                beats_this_frame = dt * (bpm / 60.0)

                if choreography_mode:
                    current_step = choreography[choreography_step_idx]
                    move_name = current_step["move"]
                    _, params, _ = AVAILABLE_MOVES[move_name]

                    target_cycles = current_step["cycles"]
                    subcycles_per_beat = params.get("subcycles_per_beat", 1.0)
                    target_beats = (
                        target_cycles / subcycles_per_beat
                        if subcycles_per_beat > 0
                        else target_cycles
                    )

                    step_beat_counter += beats_this_frame
                    if step_beat_counter >= target_beats:
                        step_beat_counter = 0.0
                        choreography_step_idx = (choreography_step_idx + 1) % len(
                            choreography
                        )

                    step_amplitude_modifier = current_step.get("amplitude", 1.0)
                    t_motion = step_beat_counter
                else:
                    sequence_beat_counter += beats_this_frame
                    if sequence_beat_counter >= config.beats_per_sequence:
                        current_move_idx = (current_move_idx + 1) % len(move_names)
                        sequence_beat_counter = 0.0

                    move_name = move_names[current_move_idx]
                    step_amplitude_modifier = 1.0
                    t_beats += beats_this_frame
                    t_motion = t_beats

                move_fn, base_params, _ = AVAILABLE_MOVES[move_name]
                current_params = base_params.copy()

                final_amplitude_scale = amplitude_scale * step_amplitude_modifier
                for key in current_params:
                    if "amplitude" in key or "_amp" in key:
                        current_params[key] *= final_amplitude_scale

                offsets = move_fn(t_motion, **current_params)

                final_pos = config.neutral_pos + offsets.position_offset
                final_eul = config.neutral_eul + offsets.orientation_offset
                final_ant = offsets.antennas_offset
                mini.set_target(
                    utils.create_head_pose(*final_pos, *final_eul, degrees=False),
                    antennas=final_ant,
                )

                if loop_start_time - last_status_print_time > 1.0:
                    sys.stdout.write("\r" + " " * 80 + "\r")
                    if choreography_mode:
                        _, params_for_ui, _ = AVAILABLE_MOVES[move_name]
                        subcycles_for_ui = params_for_ui.get("subcycles_per_beat", 1.0)
                        target_beats_display = (
                            choreography[choreography_step_idx]["cycles"]
                            / subcycles_for_ui
                            if subcycles_for_ui > 0
                            else 0
                        )
                        progress_pct = (
                            f"{(step_beat_counter / target_beats_display * 100):.0f}%"
                            if target_beats_display > 0
                            else "N/A"
                        )
                        status_line = (
                            f"[RUNNING] Step {choreography_step_idx + 1}/{len(choreography)}: {move_name:<20} ({progress_pct:>4}) | "
                            f"BPM: {bpm:<5.1f} | Amp: {final_amplitude_scale:.1f}x"
                        )
                    else:
                        status_line = f"[RUNNING] Move: {move_name:<35} | BPM: {bpm:<5.1f} | Amp: {amplitude_scale:.1f}x"
                    print(status_line, end="")
                    sys.stdout.flush()
                    last_status_print_time = loop_start_time

                time.sleep(max(0, config.control_ts - (time.time() - loop_start_time)))

        except KeyboardInterrupt:
            print("\nCtrl-C received. Shutting down...")
        finally:
            print("\nPutting robot to sleep and cleaning up...")
            if mini is not None:
                mini.goto_sleep()
            print("Shutdown complete.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Autonomous Dance Move Tester and Choreography Player for Reachy Mini.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--bpm",
        type=float,
        default=None,
        help="Starting BPM. Overrides file BPM. Default is 120.",
    )
    parser.add_argument(
        "--start-move",
        default="simple_nod",
        choices=list(AVAILABLE_MOVES.keys()),
        help="Which dance move to start with in preview mode.",
    )
    parser.add_argument(
        "--beats-per-sequence",
        type=int,
        default=8,
        help="In preview mode, automatically change move after this many beats.",
    )
    parser.add_argument(
        "--choreography",
        type=str,
        default=None,
        help="Path to a JSON choreography file to play. Overrides preview mode.",
    )
    cli_args = parser.parse_args()

    bpm_from_file = None
    if cli_args.choreography:
        result = load_choreography(cli_args.choreography)
        if result:
            _, bpm_from_file = result

    # Priority: CLI > File > Script Default (120)
    if cli_args.bpm is not None:
        bpm_to_use = cli_args.bpm
    elif bpm_from_file is not None:
        bpm_to_use = bpm_from_file
    else:
        bpm_to_use = 120.0

    app_config = Config(
        bpm=bpm_to_use,
        start_move=cli_args.start_move,
        beats_per_sequence=cli_args.beats_per_sequence,
        choreography_path=cli_args.choreography,
    )

    main(app_config)
