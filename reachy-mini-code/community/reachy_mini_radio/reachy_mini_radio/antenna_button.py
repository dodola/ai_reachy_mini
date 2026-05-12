from reachy_mini import ReachyMini
import threading
import time


class AntennaButton:
    def __init__(
        self,
        reachy_mini: ReachyMini,
        stop_event: threading.Event,
        antenna="right",
        zero_target=0,
    ):
        assert antenna in ["right", "left"]
        self.reachy_mini = reachy_mini
        self.zero_target = zero_target
        self.antenna_index = 0 if antenna == "right" else 1
        self.stop_event = stop_event
        self.reachy_mini.set_target_antenna_joint_positions([0, 0])
        self.current_antenna_pos = 0
        self.triggered = False
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while not self.stop_event.is_set():
            self.current_antenna_pos = (
                self.reachy_mini.get_present_antenna_joint_positions()[
                    self.antenna_index
                ]
            )
            time.sleep(0.05)

    def close_to_target(self):
        return abs(self.current_antenna_pos - self.zero_target) < 0.05

    def is_triggered(self):
        was_triggered = self.triggered
        over_threshold = abs(self.current_antenna_pos - self.zero_target) > 0.2
        direction = None
        if over_threshold and not self.triggered:
            self.triggered = True
            direction = (
                "left" if self.current_antenna_pos > self.zero_target else "right"
            )

        if self.triggered and self.close_to_target():
            self.triggered = False
        return not was_triggered and self.triggered, direction


def between_angles(angle, angles):
    """
    Given an angle (float) and a list of angles (floats, in radians),
    return the previous and next angles in circular order.
    """

    # Sort angles
    sorted_angles = sorted(angles)

    # Insert angle into sorted list to find position
    import bisect

    idx = bisect.bisect_left(sorted_angles, angle)

    # Previous angle (circular)
    prev_angle = sorted_angles[idx - 1]  # works even if idx = 0 (wraps)

    # Next angle (circular)
    if idx == len(sorted_angles):
        next_angle = sorted_angles[0]  # wrap
    else:
        next_angle = sorted_angles[idx]  # next in sorted list

    return prev_angle, next_angle


if __name__ == "__main__":
    rm = ReachyMini()
    stop_event = threading.Event()
    right_antenna_button = AntennaButton(
        reachy_mini=rm, stop_event=stop_event, antenna="right", zero_target=0
    )
    import numpy as np

    angles = np.random.uniform(0, 2 * np.pi, size=np.random.randint(3, 10))
    try:
        while True:
            right_antenna_position = rm.get_present_antenna_joint_positions()[1]
            triggered, direction = right_antenna_button.is_triggered()
            if triggered:
                prev_angle, next_angle = between_angles(right_antenna_position, angles)
                print(f"Antenna button triggered! Direction: {direction}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_event.set()
