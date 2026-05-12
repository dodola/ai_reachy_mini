"""Hand Tracker using MediaPipe to detect hand positions in images."""

import cv2
import mediapipe as mp
import numpy as np

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

class HandTracker:
    """Hand Tracker using MediaPipe Hands to detect hand positions."""

    def __init__(self, nb_hands=2, model_complexity=1):
        """Initialize the Hand Tracker."""
        self.hands = mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=nb_hands,
            min_detection_confidence=0.5,
            model_complexity=model_complexity,
        )

    def _norm(self, xy):
        """Normalize coordinates from [0,1] -> [-1,1] and flip x like you did for palm."""
        return np.array([-(xy[0] - 0.5) * 2, (xy[1] - 0.5) * 2])

    def get_hands_positions(self, img):
        """Get the positions of the hands in the image."""

        img = cv2.flip(img, 1)

        results = self.hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if results.multi_hand_landmarks is not None:
            hand_positions = []
            for landmarks in results.multi_hand_landmarks:
                middle_finger_pip_landmark = landmarks.landmark[
                    mp_hands.HandLandmark.MIDDLE_FINGER_PIP
                ]
                palm_center = np.array(
                    [middle_finger_pip_landmark.x, middle_finger_pip_landmark.y]
                )
                palm_center = self._norm(palm_center)

                index_finger_tip = np.array([
                    landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].x,
                    landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y
                ])
                index_finger_tip = self._norm(index_finger_tip)

                index_finger_mcp = np.array([
                    landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].x,
                    landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].y
                ])
                index_finger_mcp = self._norm(index_finger_mcp)

                middle_finger_tip = np.array([
                    landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].x,
                    landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
                ])
                middle_finger_tip = self._norm(middle_finger_tip)
                
                hand_positions.append({
                    'palm': palm_center,
                    'index_tip': index_finger_tip,
                    'index_mcp': index_finger_mcp,
                    'middle': middle_finger_tip
                })

            return hand_positions
        return None