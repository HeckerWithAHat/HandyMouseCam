"""
Video frame processing using MediaPipe Hands.
Extracts hand landmarks from camera frames.
"""

import logging
import time
from pathlib import Path
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFont
from aiortc import MediaStreamTrack
from av import VideoFrame
from dataclasses import dataclass
from typing import List, Optional, Tuple

from config import (
    HAND_DETECTION_CONFIDENCE,
    HAND_LANDMARKER_MODEL_PATH,
    HAND_TRACKING_CONFIDENCE,
    MAX_NUM_HANDS,
    PINCH_DISTANCE_THRESHOLD_MM,
)

logger = logging.getLogger(__name__)


@dataclass
class Hand:
    """Represents detected hand and its landmarks."""
    landmarks: np.ndarray  # Shape: (21, 3) - x, y, z coordinates
    handedness: str  # 'Left' or 'Right'
    confidence: float  # Detection confidence (0.0-1.0)
    
    def get_wrist(self) -> Tuple[float, float, float]:
        """Get wrist landmark (index 0)."""
        return tuple(self.landmarks[0])
    
    def get_index_tip(self) -> Tuple[float, float, float]:
        """Get index finger tip (index 8)."""
        return tuple(self.landmarks[8])
    
    def get_middle_tip(self) -> Tuple[float, float, float]:
        """Get middle finger tip (index 12)."""
        return tuple(self.landmarks[12])
    
    def get_thumb_tip(self) -> Tuple[float, float, float]:
        """Get thumb tip (index 4)."""
        return tuple(self.landmarks[4])
    
    def get_palm_center(self) -> Tuple[float, float, float]:
        """
        Calculate palm center as average of wrist and MCP landmarks.
        Returns: (x, y, z) coordinates
        """
        return (self.landmarks[0] + ((self.landmarks[9] + self.landmarks[13]) / 2)) / 2

        
        


class VideoProcessor:
    """
    Processes video frames using MediaPipe Hands.
    Extracts hand landmarks for gesture recognition.
    """
    
    def __init__(self):
        """Initialize MediaPipe Hands model."""
        model_path = Path(__file__).resolve().parent.parent / HAND_LANDMARKER_MODEL_PATH
        if not model_path.is_file():
            raise FileNotFoundError(f"Hand landmarker model not found: {model_path}")

        base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=MAX_NUM_HANDS,
            min_hand_detection_confidence=HAND_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=HAND_TRACKING_CONFIDENCE,
            min_tracking_confidence=HAND_TRACKING_CONFIDENCE,
        )
        self.hands = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self._last_timestamp_ms = 0
        self._last_gesture_events = []
        logger.info(f"VideoProcessor initialized with max_num_hands={MAX_NUM_HANDS}")
    
    def process_frame(self, frame: np.ndarray) -> List[Hand]:
        """
        Process a single video frame and extract hand landmarks.
        
        Args:
            frame: RGB frame as numpy array (H, W, 3)
            
        Returns:
            List[Hand]: List of detected hands with landmarks
        """
        logger.debug(f"Processing frame of shape {frame.shape}")
        rgb_frame = np.asarray(frame)
        if rgb_frame.ndim != 3 or rgb_frame.shape[2] != 3:
            raise ValueError("frame must have shape (height, width, 3)")
        last_timestamp_ms = getattr(self, "_last_timestamp_ms", 0)
        timestamp_ms = max(time.monotonic_ns() // 1_000_000, last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self.hands.detect_for_video(mp_image, timestamp_ms)
        hands = []
        detected_handedness = result.handedness or []
        detected_landmarks = result.hand_landmarks or []
        for index, hand_landmarks in enumerate(detected_landmarks):
            classification = detected_handedness[index][0]
            landmarks = np.array(
                [[point.x, point.y, point.z] for point in hand_landmarks],
                dtype=float,
            )
            hands.append(Hand(
                landmarks=landmarks,
                handedness=classification.category_name,
                confidence=float(classification.score),
            ))
        logger.debug("Detected %d hands", len(hands))
        return hands

    def draw_landmarks(
        self,
        frame: np.ndarray,
        hands: List[Hand],
        gesture_events: Optional[List[object]] = None,
    ) -> np.ndarray:
        """
        Draw hand landmarks and connections on frame (for debugging).
        
        Args:
            frame: RGB frame as numpy array
            hands: List of Hand objects
            
        Returns:
            np.ndarray: Frame with drawn landmarks
        """
        logger.debug(f"Drawing {len(hands)} hands on frame")
        mp_hands = mp.tasks.vision.HandLandmarksConnections
        mp_drawing = mp.tasks.vision.drawing_utils
        mp_drawing_styles = mp.tasks.vision.drawing_styles
        annotated_image = np.copy(frame)
        for hand in hands:
            landmark_list = [
                mp.tasks.components.containers.NormalizedLandmark(
                    x=float(point[0]), y=float(point[1]), z=float(point[2])
                )
                for point in hand.landmarks
            ]
            mp_drawing.draw_landmarks(
                annotated_image,
                landmark_list,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style())

        events = gesture_events if gesture_events is not None else self._last_gesture_events
        return self._draw_debug_overlay(annotated_image, hands, events)

    def _draw_debug_overlay(
        self,
        frame: np.ndarray,
        hands: List[Hand],
        gesture_events: List[object],
    ) -> np.ndarray:
        """Draw the current gesture and raw pinch measurements for debugging."""
        image = Image.fromarray(frame)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=24)
        frame_height, frame_width = frame.shape[:2]
        latest_gestures = {}
        for event in gesture_events or []:
            latest_gestures[event.hand.lower()] = event

        for hand in hands:
            side = hand.handedness.lower()
            event = latest_gestures.get(side)
            gesture_text = event.gesture_type.value if event else "detecting"
            label = f"{hand.handedness}: {gesture_text}"
            text_width = draw.textbbox((0, 0), label, font=font)[2]
            text_x = 8 if side == "left" else max(8, frame_width - text_width - 8)
            text_y = 8 + (22 if side == "right" else 0)
            draw.rectangle(
                (text_x - 3, text_y - 2, text_x + text_width + 3, text_y + 12),
                fill=(0, 0, 0),
            )
            draw.text((text_x, text_y), label, fill=(255, 255, 255), font=font)

            palm_center = self._pixel_point(
                hand.get_palm_center(), frame_width, frame_height
            )
            palm_radius = 5
            draw.ellipse(
                (
                    palm_center[0] - palm_radius,
                    palm_center[1] - palm_radius,
                    palm_center[0] + palm_radius,
                    palm_center[1] + palm_radius,
                ),
                fill=(40, 180, 255),
                outline=(0, 0, 0),
            )

            thumb = self._pixel_point(hand.get_thumb_tip(), frame_width, frame_height)
            for finger_name, finger in (
                ("index", hand.get_index_tip()),
                ("middle", hand.get_middle_tip()),
            ):
                finger_point = self._pixel_point(finger, frame_width, frame_height)
                distance_mm = self._calculate_debug_distance(hand.get_thumb_tip(), finger)
                is_pinched = distance_mm <= PINCH_DISTANCE_THRESHOLD_MM
                color = (40, 220, 80) if is_pinched else (255, 190, 40)
                self._draw_dashed_line(draw, thumb, finger_point, color)
                midpoint = (
                    (thumb[0] + finger_point[0]) // 2,
                    (thumb[1] + finger_point[1]) // 2,
                )
                distance_text = f"{finger_name[0].upper()}: {distance_mm:.1f}mm"
                bounds = draw.textbbox(midpoint, distance_text, font=font)
                draw.rectangle(
                    (bounds[0] - 2, bounds[1] - 1, bounds[2] + 2, bounds[3] + 1),
                    fill=(0, 0, 0),
                )
                draw.text(midpoint, distance_text, fill=color, font=font)

        return np.asarray(image)

    @staticmethod
    def _pixel_point(point: Tuple[float, float, float], width: int, height: int):
        return (round(point[0] * width), round(point[1] * height))

    @staticmethod
    def _calculate_debug_distance(thumb, finger) -> float:
        return float(np.linalg.norm(np.asarray(thumb) - np.asarray(finger)) * 170.0)

    @staticmethod
    def _draw_dashed_line(draw, start, end, color, dash_length=6):
        start_point = np.asarray(start, dtype=float)
        end_point = np.asarray(end, dtype=float)
        vector = end_point - start_point
        length = float(np.linalg.norm(vector))
        if length == 0:
            return
        direction = vector / length
        for offset in np.arange(0, length, dash_length * 2):
            dash_start = start_point + direction * offset
            dash_end = start_point + direction * min(offset + dash_length, length)
            draw.line((*dash_start, *dash_end), fill=color, width=2)
    
    def get_frame_dimensions(self, frame: np.ndarray) -> Tuple[int, int]:
        """
        Get normalized frame dimensions.
        
        Args:
            frame: Input frame
            
        Returns:
            Tuple[int, int]: (width, height)
        """
        h, w = frame.shape[:2]
        return w, h
    
    def close(self):
        """Clean up resources."""
        if self.hands:
            self.hands.close()
            logger.info("VideoProcessor closed")


class AnnotatedVideoTrack(MediaStreamTrack):
    """Return landmark-annotated frames while recognizing their hands."""

    kind = "video"

    def __init__(self, source, processor, recognizer):
        super().__init__()
        self.source = source
        self.processor = processor
        self.recognizer = recognizer
        self.frame_count = 0

    async def recv(self):
        frame = await self.source.recv()
        image = frame.to_ndarray(format="rgb24")
        hands = self.processor.process_frame(image)
        timestamp = frame.time
        if timestamp is None:
            timestamp = time.monotonic()
        gesture_events = self.recognizer.process_hands(hands, timestamp)
        self.processor._last_gesture_events = gesture_events or []
        annotated = self.processor.draw_landmarks(image, hands)
        self.frame_count += 1
        if self.frame_count == 1 or self.frame_count % 30 == 0:
            logger.info(
                "Annotated video frame %d; detected %d hands",
                self.frame_count,
                len(hands),
            )

        output = VideoFrame.from_ndarray(annotated, format="rgb24")
        frame_pts = getattr(frame, "pts", None)
        frame_time_base = getattr(frame, "time_base", None)
        if frame_pts is not None:
            output.pts = frame_pts
        if frame_time_base is not None:
            output.time_base = frame_time_base
        return output
