import threading
import time

import cv2
import numpy as np
from reachy_mini import ReachyMini, ReachyMiniApp
from hand_tracker_v2.hand_tracker import HandTracker
from scipy.spatial.transform import Rotation as R
from hand_tracker_v2.utils import finger_orientation_deg, allow_multiturn
# from hand_tracker_v2.recorded_moves import RecordedMoves
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reachy_mini.motion.recorded_move import RecordedMove, RecordedMoves


DEBUG = True
FREQUENCY = 50  # Hz


class HandTrackerV2(ReachyMiniApp):
    custom_app_url: str | None = "http://0.0.0.0:8042"

    def __init__(self):
        super().__init__()

        # Tracking state
        self.hand_pos = None
        self.hands = None
        self.width = None
        self.height = None
        self.hand_tracker = None

        # Antennas
        self.left_antenna_angle = 0.0
        self.right_antenna_angle = 0.0
        self.previous_antenna_angles = [0.0, 0.0]
        self.previous_head_pose = np.eye(4)

        # Hand count + sound triggers
        self.number_hands = 0
        self.previous_number_hands = 0
        self.hand_count_history = []
        self.hand_count_buffer_size = 3

        self.last_hand_seen = time.time()
        self.idle_timeout = 1.0
        self.is_idle = False
        self.last_play_sound = 0.0
        self.last_emotion_sound = {
            "success2": time.time(),
            "irritated1": time.time(),
        }

        self.show_img = False
        self.track_mode = True
        self.antenna_tracking = True
        self.preferred_side = "Left"
        self.antenna_mode = "Same Movement"

        self.app_ready = False

        self.last_frame = None

        @self.settings_app.get("/video_feed")
        def video_feed():
            return StreamingResponse(self.frame_generator(),
                                     media_type="multipart/x-mixed-replace; boundary=frame")
    
        @self.settings_app.get("/ready")
        async def ready():
            print("[READY ENDPOINT] called, app_ready =", self.app_ready)
            return {"ready": self.app_ready}
                
        class UIState(BaseModel):
            video: bool | None = None
            tracking: bool | None = None
            antenna: bool | None = None
            preferred_side: str | None = None
            antenna_mode: str | None = None
        
        @self.settings_app.post("/set_toggles")
        async def set_toggles(state: UIState):
            if state.video is not None:
                self.show_img = state.video
            if state.tracking is not None:
                self.track_mode = state.tracking
            if state.antenna is not None:
                self.antenna_tracking = state.antenna
            if state.preferred_side is not None:
                print("Preferred side set to:", state.preferred_side)
                self.preferred_side = state.preferred_side
            if state.antenna_mode is not None:
                print("Index mode set to:", state.antenna_mode)
                self.antenna_mode = state.antenna_mode
            return {"status": "ok"}

    def frame_generator(self):
        while True:
            if self.last_frame is None:
                time.sleep(0.01)
                continue
            ret, jpeg = cv2.imencode(".jpg", self.last_frame)
            frame = jpeg.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
            time.sleep(0.05)


    def draw(self, im):
        if self.hand_pos is None:
            return im
        if self.hands is None:
            return im
        for hand in self.hands:
            if "palm" in hand:
                palm_pos = hand["palm"]
                draw_palm = [
                    (-palm_pos[0] + 1) / 2,
                    (palm_pos[1] + 1) / 2,
                ]
                im = cv2.circle(
                    im,
                    (
                    int(self.width - draw_palm[0] * self.width),
                    int(draw_palm[1] * self.height),
                    ),
                    radius=5,
                    color=(0, 0, 255),
                    thickness=-1,
                )
            if "index_tip" in hand:
                index_pos = hand["index_tip"]
                draw_index = [
                    (-index_pos[0] + 1) / 2,
                    (index_pos[1] + 1) / 2,
                ]
                im = cv2.circle(
                    im,
                    (
                    int(self.width - draw_index[0] * self.width),
                    int(draw_index[1] * self.height),
                    ),
                    radius=5,
                    color=(0, 255, 0),
                    thickness=-1,
                )
            if 'index_mcp' in hand:
                index_mcp_pos = hand['index_mcp']
                draw_index_mcp = [
                    (-index_mcp_pos[0] + 1) / 2,
                    (index_mcp_pos[1] + 1) / 2,
                ]
                im = cv2.circle(
                    im,
                    (
                    int(self.width - draw_index_mcp[0] * self.width),
                    int(draw_index_mcp[1] * self.height),
                    ),
                    radius=5,
                    color=(255, 0, 0),
                    thickness=-1,
                )
        return im

    def update_hand_pos(self, im):
        if self.hand_tracker is None:
            self.hand_tracker = HandTracker(model_complexity=0)
        hands = self.hand_tracker.get_hands_positions(im)
        self.hands = hands
        if hands == None:
            self.number_hands = 0
        else:
            self.number_hands = len(hands)
        if hands:
            # Reset IDLE TIMER
            self.last_hand_seen = time.time()
            self.is_idle = False
            rightmost_hand = min(hands, key=lambda h: h["palm"][0])
            leftmost_hand = max(hands, key=lambda h: h["palm"][0])

            if self.preferred_side == "Left":
                self.hand_pos = np.array(leftmost_hand["palm"])
            else:
                self.hand_pos = np.array(rightmost_hand["palm"])

            self.left_antenna_angle = - finger_orientation_deg(
                rightmost_hand["index_mcp"], rightmost_hand["index_tip"]
            )
            self.right_antenna_angle = - finger_orientation_deg(
                leftmost_hand["index_mcp"], leftmost_hand["index_tip"]
            )
            if self.antenna_mode == "Symmetric" and len(hands) == 1:
                self.left_antenna_angle = - self.right_antenna_angle
        elif self.hand_pos is not None:
            self.hand_pos *= 0.9  # Slowly go back to center

    def play_sound(self,reachy_mini, sound_name: str):
        if time.time() - self.last_play_sound < 2.0:
            return
        if time.time() - self.last_emotion_sound[sound_name] < 5.0:
            return
        sound_path = self.recorded_moves.sounds[sound_name]
        reachy_mini.media.play_sound(sound_path)
        self.last_play_sound = time.time()
        self.last_emotion_sound[sound_name] = time.time()


    def track(self, reachy_mini: ReachyMini, stop_event: threading.Event):
        target = np.array([0, 0])
        pitch_kp = 0.024
        yaw_kp = 0.028
        max_delta = 0.6
        max_antenna_delta = np.radians(5)
        head_pose = np.eye(4)
        euler_rot = np.array([0.0, 0.0, 0.0])
        dead_zone = 0.05


        while not stop_event.is_set():
            t0 = time.time()

            self.hand_count_history.append(self.number_hands)
            if len(self.hand_count_history) > self.hand_count_buffer_size:
                self.hand_count_history.pop(0)

            if len(self.hand_count_history) == self.hand_count_buffer_size:
                stable_hand_count = self.hand_count_history[0]
                if all(count == stable_hand_count for count in self.hand_count_history):
                    if stable_hand_count > self.previous_number_hands:
                        self.play_sound(reachy_mini, "success2")
                    elif stable_hand_count < self.previous_number_hands and stable_hand_count == 0:
                        self.play_sound(reachy_mini, "irritated1")

                    self.previous_number_hands = stable_hand_count

            time_since_last_hand = time.time() - self.last_hand_seen

            if time_since_last_hand > self.idle_timeout or (not self.track_mode and not self.antenna_tracking):
                if not self.is_idle:
                    print("Entering IDLE mode")
                    self.previous_antenna_angles = reachy_mini.get_present_antenna_joint_positions()
                    self.is_idle = True

                # Head return to neutral (xyz=euler)
                idle_rot = np.array([0.0, 0.0, 0.0]) - euler_rot
                idle_rot = np.clip(idle_rot, -max_delta, max_delta)

                euler_rot += idle_rot * 0.05  # slow return factor

                # Bound rotation like normal tracking
                euler_rot = np.clip(
                    euler_rot,
                    [0.0, -np.deg2rad(30), -np.deg2rad(170)],
                    [0.0, np.deg2rad(20),  np.deg2rad(170)],
                )

                # Compute head matrix
                head_pose[:3, :3] = R.from_euler("xyz", euler_rot).as_matrix()
                head_pose[:3, 3][2] = 0.0  # neutral height


                # Antennas back to 0
                antennas = np.array([0.0, 0.0])
                antennas = allow_multiturn(
                    antennas,
                    self.previous_antenna_angles,
                    max_antenna_delta
                )

            else:
                self.is_idle = False

                if not self.track_mode:
                    head_pose = self.previous_head_pose.copy()
                else:
                    if self.hand_pos is None:
                        time.sleep(max(0, (1.0 / FREQUENCY) - (time.time() - t0)))
                        continue

                    # Tracking error
                    error = target - self.hand_pos
                    error[np.abs(error) < dead_zone] = 0.0
                    error = np.clip(error, -max_delta, max_delta)

                    # Update head orientation
                    euler_rot += np.array([
                        0.0,
                        -pitch_kp * error[1],
                        yaw_kp * error[0]
                    ])

                    euler_rot = np.clip(
                        euler_rot,
                        [0.0, -np.deg2rad(30), -np.deg2rad(170)],
                        [0.0, np.deg2rad(20),  np.deg2rad(170)],
                    )

                    # Compute new head pose
                    head_pose[:3, :3] = R.from_euler("xyz", euler_rot).as_matrix()
                    # head_pose[:3, 3][2] = error[1] * kz

                if not self.antenna_tracking:
                    antennas = self.previous_antenna_angles.copy()
                else:
                    # Antennas
                    antennas = np.radians([
                        self.right_antenna_angle,
                        self.left_antenna_angle,
                    ])

                    antennas = allow_multiturn(
                        antennas,
                        self.previous_antenna_angles,
                        max_antenna_delta
                    )

            reachy_mini.set_target(head=head_pose, antennas=antennas)
            self.previous_head_pose = head_pose.copy()
            self.previous_antenna_angles = antennas.copy()

            time.sleep(max(0, (1.0 / FREQUENCY) - (time.time() - t0)))

    def play_recorded_move(self, reachy_mini: ReachyMini, move_name: str):
        move: RecordedMove = self.recorded_moves.get(move_name)
        reachy_mini.play_move(move, initial_goto_duration=1.0)



    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event):
        self.recorded_moves = RecordedMoves(
            "pollen-robotics/reachy-mini-emotions-library"
        )
        self.play_recorded_move(reachy_mini, "success2")
        reachy_mini.goto_target(np.eye(4), [0.0, 0.0], body_yaw=0.0, duration=1.0)


        self.app_ready = True

        tracking_thread = threading.Thread(
            target=self.track, args=(reachy_mini, stop_event)
        )
        tracking_thread.start()



        while not stop_event.is_set():
            t0 = time.time()
            im = reachy_mini.media.get_frame()
            if im is None:
                continue
            im = cv2.resize(im, (1280, 720))
            if self.width is None or self.height is None:
                self.height, self.width = im.shape[:2]

            self.update_hand_pos(im)

            if not self.show_img:
                continue
            im = self.draw(im)
            self.last_frame = im.copy()
            time.sleep(max(0, (1.0 / FREQUENCY) - (time.time() - t0)))

        if DEBUG:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass

        tracking_thread.join()


if __name__ == "__main__":
    app = HandTrackerV2()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        pass
