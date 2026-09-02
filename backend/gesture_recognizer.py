"""
Gesture recognition logic.
Transforms raw hand landmarks into semantic gesture events.
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Callable
import numpy as np

from video_processor import Hand
from config import PINCH_DISTANCE_THRESHOLD_MM, PINCH_STABILITY_FRAMES

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
    
    def __repr__(self) -> str:
        return f"GestureEvent({self.gesture_type.value}, {self.hand}, pos={self.hand_position})"


class GestureRecognizer:
    """
    Recognizes gestures from hand landmarks.
    Maintains state machine for pinch detection and produces gesture events.
    """
    
    def __init__(self):
        """Initialize gesture recognizer."""
        self.pinch_state = {
            'left': None,   # Current pinch type or None
            'right': None
        }
        self.pinch_frame_count = {
            'left': 0,
            'right': 0
        }
        self.previous_hands = None
        self.gesture_callbacks = []
        logger.info("GestureRecognizer initialized")
    
    def register_gesture_callback(self, callback: Callable[[GestureEvent], None]):
        """
        Register callback function for gesture events.
        
        Args:
            callback: Function that receives GestureEvent
        """
        self.gesture_callbacks.append(callback)
        logger.debug(f"Registered gesture callback: {callback.__name__}")
    
    def process_hands(self, hands: List[Hand], timestamp: float) -> List[GestureEvent]:
        """
        Process detected hands and generate gesture events.
        
        Args:
            hands: List of Hand objects from VideoProcessor
            timestamp: Current frame timestamp
            
        Returns:
            List[GestureEvent]: Detected gestures in this frame
        """
        # TODO: Implement gesture recognition logic
        # Should:
        # - Map hands by handedness (left/right)
        # - Detect pinches (thumb to index, thumb to middle)
        # - Detect open hand movement
        # - Detect clutch gestures
        # - Track state transitions (start, move, end)
        # - Generate GestureEvent objects
        # - Maintain frame count for stability
        logger.debug(f"Processing {len(hands)} hands")
        events = []
        return events
    
    def _calculate_pinch_distance(self, thumb: tuple, finger: tuple) -> float:
        """
        Calculate distance between thumb and finger in mm.
        Assumes input coordinates are normalized (0-1).
        Assumes ~170mm hand width for calibration.
        
        Args:
            thumb: Thumb tip coordinates (x, y, z)
            finger: Finger tip coordinates (x, y, z)
            
        Returns:
            float: Distance in mm
        """
        # TODO: Implement distance calculation
        # Account for z-depth if using 3D coordinates
        pass
    
    def _is_pinched(self, hand: Hand, finger_idx: int) -> bool:
        """
        Check if hand is performing a pinch with given finger.
        
        Args:
            hand: Hand object
            finger_idx: Finger index (8 for index, 12 for middle)
            
        Returns:
            bool: True if pinch detected
        """
        # TODO: Implement pinch detection
        # Should check if thumb and finger are close enough
        pass
    
    def _is_hand_closed(self, hand: Hand) -> bool:
        """
        Detect if hand is closed into a fist.
        
        Args:
            hand: Hand object
            
        Returns:
            bool: True if hand is closed
        """
        # TODO: Implement fist detection
        # Check if all fingertips are close to palm
        pass
    
    def _emit_gesture(self, event: GestureEvent):
        """Emit gesture event to registered callbacks."""
        for callback in self.gesture_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in gesture callback: {e}")
