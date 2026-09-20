"""
Gesture recognition logic.
Transforms raw hand landmarks into semantic gesture events.
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
import numpy as np

from video_processor import Hand
from config import (
    MIN_HAND_VISIBILITY,
    PINCH_DISTANCE_THRESHOLD_MM,
    PINCH_STABILITY_FRAMES,
    FIST_DISTANCE_THRESHOLD_MM,
)

logger = logging.getLogger(__name__)


class GestureType(Enum):
    """Enumeration of recognized gesture types."""
    NO_GESTURE = "none"
    OPEN_HAND_MOVE = "open_hand_move"
    PINCH_INDEX = "pinch_index"
    PINCH_MIDDLE = "pinch_middle"
    CLUTCH = "clutch"  # Fist or hand out of frame


class PinchType(Enum):
    """Types of pinches (by finger paired with thumb)."""
    INDEX = "index"
    MIDDLE = "middle"


@dataclass
class GestureEvent:
    """Represents a detected gesture event."""
    gesture_type: GestureType
    hand: str  # 'Left' or 'Right'
    timestamp: float
    hand_position: tuple  # (x, y) screen coordinates
    pinch_type: Optional[PinchType] = None
    pinch_distance_mm: Optional[float] = None
    phase: str = "move"
    
    def __repr__(self) -> str:
        return f"GestureEvent({self.gesture_type.value}, {self.hand}, pos={self.hand_position})"


class GestureRecognizer:
    """Recognize gestures from hand landmarks and emit state changes."""

    def __init__(self):
        self.pinch_state = {'left': None, 'right': None}
        self.pinch_frame_count = {'left': 0, 'right': 0}
        self._pinch_candidates = {'left': None, 'right': None}
        self._active_gestures = {'left': None, 'right': None}
        self._last_positions = {'left': None, 'right': None}
        self.previous_hands = None
        self.gesture_callbacks = []
        logger.info("GestureRecognizer initialized")

    def register_gesture_callback(self, callback: Callable[[GestureEvent], None]):
        if not callable(callback):
            raise TypeError("gesture callback must be callable")
        self.gesture_callbacks.append(callback)
        logger.debug("Registered gesture callback: %s", getattr(callback, '__name__', callback))

    def process_hands(self, hands: List[Hand], timestamp: float) -> List[GestureEvent]:
        hands_by_side = {
            hand.handedness.lower(): hand for hand in hands
            if hand.handedness.lower() in ('left', 'right')
            and hand.confidence >= MIN_HAND_VISIBILITY
        }
        logger.debug("Processing %d visible hands", len(hands_by_side))
        events = []
        for side in ('left', 'right'):
            hand = hands_by_side.get(side)
            if hand is None:
                end_event = self._finish_active_gesture(side, timestamp)
                if end_event:
                    events.append(end_event)
                self._pinch_candidates[side] = None
                self.pinch_frame_count[side] = 0
                self.pinch_state[side] = None
                if self._active_gestures[side] != GestureType.CLUTCH:
                    events.append(self._make_event(
                        GestureType.CLUTCH, side, timestamp, (0.0, 0.0), 'start'
                    ))
                    self._active_gestures[side] = GestureType.CLUTCH
                continue

            position = tuple(np.asarray(hand.get_palm_center())[:2])
            self._last_positions[side] = position
            if self._is_hand_closed(hand):
                end_event = self._finish_active_gesture(side, timestamp, position)
                if end_event:
                    events.append(end_event)
                self._pinch_candidates[side] = None
                self.pinch_frame_count[side] = 0
                self.pinch_state[side] = None
                phase = 'move' if self._active_gestures[side] == GestureType.CLUTCH else 'start'
                events.append(self._make_event(
                    GestureType.CLUTCH, side, timestamp, position, phase
                ))
                self._active_gestures[side] = GestureType.CLUTCH
                continue

            pinch_type, pinch_distance = self._detect_pinch(hand)
            if pinch_type == self._pinch_candidates[side]:
                self.pinch_frame_count[side] += 1
            else:
                self._pinch_candidates[side] = pinch_type
                self.pinch_frame_count[side] = 1 if pinch_type else 0

            if pinch_type and self.pinch_frame_count[side] >= PINCH_STABILITY_FRAMES:
                gesture_type = (GestureType.PINCH_INDEX
                                if pinch_type == PinchType.INDEX
                                else GestureType.PINCH_MIDDLE)
                if self._active_gestures[side] not in (None, gesture_type):
                    end_event = self._finish_active_gesture(side, timestamp, position)
                    if end_event:
                        events.append(end_event)
                phase = 'start' if self._active_gestures[side] != gesture_type else 'move'
                events.append(self._make_event(
                    gesture_type, side, timestamp, position, phase,
                    pinch_type, pinch_distance
                ))
                self._active_gestures[side] = gesture_type
                self.pinch_state[side] = pinch_type
            elif self._active_gestures[side] == GestureType.CLUTCH:
                self._active_gestures[side] = None
                events.append(self._make_event(
                    GestureType.CLUTCH, side, timestamp, position, 'end'
                ))
            elif pinch_type is None and self._active_gestures[side] is None:
                events.append(self._make_event(
                    GestureType.OPEN_HAND_MOVE, side, timestamp, position, 'move'
                ))
            elif pinch_type is None:
                end_event = self._finish_active_gesture(side, timestamp, position)
                if end_event:
                    events.append(end_event)

        self.previous_hands = hands_by_side
        for event in events:
            self._emit_gesture(event)
        return events

    def _detect_pinch(self, hand: Hand):
        distances = {
            PinchType.INDEX: self._calculate_pinch_distance(hand.get_thumb_tip(), hand.get_index_tip()),
            PinchType.MIDDLE: self._calculate_pinch_distance(hand.get_thumb_tip(), hand.get_middle_tip()),
        }
        pinched = [item for item in distances.items()
                   if item[1] <= PINCH_DISTANCE_THRESHOLD_MM]
        return min(pinched, key=lambda item: item[1], default=(None, None))

    def _make_event(self, gesture_type, side, timestamp, position, phase,
                    pinch_type=None, pinch_distance=None):
        return GestureEvent(gesture_type, side.title(), timestamp, position,
                            pinch_type, pinch_distance, phase)

    def _finish_active_gesture(self, side, timestamp, position=None):
        active = self._active_gestures[side]
        if active is None or active == GestureType.CLUTCH:
            return None
        position = position or self._last_positions[side] or (0.0, 0.0)
        event = self._make_event(active, side, timestamp, position, 'end',
                                 self.pinch_state[side])
        self._active_gestures[side] = None
        self.pinch_state[side] = None
        self.pinch_frame_count[side] = 0
        return event

    def _calculate_pinch_distance(self, thumb: tuple, finger: tuple) -> float:
        thumb_point = np.asarray(thumb, dtype=float)
        finger_point = np.asarray(finger, dtype=float)
        if thumb_point.shape != (3,) or finger_point.shape != (3,):
            raise ValueError("thumb and finger must be 3D points")
        return float(np.linalg.norm(thumb_point - finger_point) * 170.0)

    def _is_pinched(self, hand: Hand, finger_idx: int) -> bool:
        if not 0 <= finger_idx < len(hand.landmarks):
            raise IndexError(finger_idx)
        distance = self._calculate_pinch_distance(
            hand.get_thumb_tip(), tuple(hand.landmarks[finger_idx])
        )
        return distance <= PINCH_DISTANCE_THRESHOLD_MM

    def _is_hand_closed(self, hand: Hand) -> bool:

        print("4", np.asarray(tuple(hand.landmarks[4])))
        print("8", np.asarray(tuple(hand.landmarks[8])))
        print("12", np.asarray(tuple(hand.landmarks[12])))
        print("16", np.asarray(tuple(hand.landmarks[16])))
        print("20", np.asarray(tuple(hand.landmarks[20])))
        print("palm", np.asarray(hand.get_palm_center()))
        print("result", [np.linalg.norm(np.asarray(tuple(hand.landmarks[index])) - np.asarray(hand.get_palm_center())) * 170.0 <= FIST_DISTANCE_THRESHOLD_MM for index in (4, 8, 12, 16, 20)])

        return all(
            
            [np.linalg.norm(np.asarray(tuple(hand.landmarks[index])) - np.asarray(hand.get_palm_center())) * 170.0 <= FIST_DISTANCE_THRESHOLD_MM for index in (4, 8, 12, 16, 20)]
        )

    def _emit_gesture(self, event: GestureEvent):
        message = (f"[gesture] {event.hand} {event.gesture_type.value} "
                   f"{event.phase} pos={event.hand_position}")
        if event.pinch_distance_mm is not None:
            message += f" distance={event.pinch_distance_mm:.1f}mm"
        print(message)
        logger.info(message)
        for callback in self.gesture_callbacks:
            try:
                callback(event)
            except Exception:
                logger.exception("Error in gesture callback")
