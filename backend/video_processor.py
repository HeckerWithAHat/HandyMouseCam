"""
Video frame processing using MediaPipe Hands.
Extracts hand landmarks from camera frames.
"""

import logging
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import List, Optional, Tuple

from config import MAX_NUM_HANDS, HAND_DETECTION_CONFIDENCE, HAND_TRACKING_CONFIDENCE

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
        # TODO: Implement palm center calculation
        pass


class VideoProcessor:
    """
    Processes video frames using MediaPipe Hands.
    Extracts hand landmarks for gesture recognition.
    """
    
    def __init__(self):
        """Initialize MediaPipe Hands model."""
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=MAX_NUM_HANDS,
            min_detection_confidence=HAND_DETECTION_CONFIDENCE,
            min_tracking_confidence=HAND_TRACKING_CONFIDENCE
        )
        logger.info(f"VideoProcessor initialized with max_num_hands={MAX_NUM_HANDS}")
    
    def process_frame(self, frame: np.ndarray) -> List[Hand]:
        """
        Process a single video frame and extract hand landmarks.
        
        Args:
            frame: RGB frame as numpy array (H, W, 3)
            
        Returns:
            List[Hand]: List of detected hands with landmarks
        """
        # TODO: Implement frame processing
        # Should:
        # - Convert frame to RGB if needed
        # - Run MediaPipe Hands inference
        # - Extract landmarks
        # - Return Hand objects
        logger.debug(f"Processing frame of shape {frame.shape}")
        pass
    
    def draw_landmarks(self, frame: np.ndarray, hands: List[Hand]) -> np.ndarray:
        """
        Draw hand landmarks and connections on frame (for debugging).
        
        Args:
            frame: RGB frame as numpy array
            hands: List of Hand objects
            
        Returns:
            np.ndarray: Frame with drawn landmarks
        """
        # TODO: Implement landmark drawing
        # Should draw:
        # - Hand landmarks as circles
        # - Hand connections as lines
        logger.debug(f"Drawing {len(hands)} hands on frame")
        return frame
    
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
