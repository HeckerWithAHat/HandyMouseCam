"""
OS control module for cursor and window manipulation.
Handles mouse movements, clicks, and window management on Windows.
"""

import logging
from dataclasses import dataclass
from typing import Tuple, Optional
import pydirectinput
import win32gui
import win32con
import win32api

from gesture_recognizer import GestureEvent, GestureType, PinchType
from config import (
    CURSOR_SENSITIVITY,
    CURSOR_SMOOTHING_FACTOR,
    CURSOR_MOVEMENT_DEADZONE_PIXELS,
    TITLE_BAR_HEIGHT_PIXELS,
)

logger = logging.getLogger(__name__)


@dataclass
class WindowRect:
    """Represents a window's rectangle."""
    left: int
    top: int
    right: int
    bottom: int
    
    @property
    def width(self) -> int:
        return self.right - self.left
    
    @property
    def height(self) -> int:
        return self.bottom - self.top
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is within window rectangle."""
        return (self.left <= x <= self.right and 
                self.top <= y <= self.bottom)


class OSController:
    """
    Controls OS-level actions: cursor movement, clicks, window manipulation.
    Translates gesture events into OS actions.
    """
    
    def __init__(self):
        """Initialize OS controller."""
        self.current_cursor_pos = self._get_cursor_pos()
        self.dragging_window = False
        self.dragging_window_hwnd = None
        self.last_hand_position = None
        self._smoothed_delta = (0.0, 0.0)
        self._cursor_remainder = (0.0, 0.0)
        logger.info("OSController initialized")
    
    def  handle_gesture(self, event: GestureEvent):
        """
        Process a gesture event and perform corresponding OS action.
        
        Args:
            event: GestureEvent to handle
        """
        try:
            if event.gesture_type == GestureType.OPEN_HAND_MOVE:
                self._handle_hand_movement(event)
            elif event.gesture_type == GestureType.PINCH_INDEX:
                self._handle_index_pinch(event)
            elif event.gesture_type == GestureType.PINCH_MIDDLE:
                self._handle_middle_pinch(event)
            elif event.gesture_type == GestureType.CLUTCH:
                self._handle_clutch(event)
        except Exception as e:
            logger.error(f"Error handling gesture: {e}")
    
    def _handle_hand_movement(self, event: GestureEvent):
        """
        Move cursor based on hand position (relative/trackpad mode).
        
        Args:
            event: Hand movement gesture event
        """
        if event.hand != 'Right':
            return

        if event.phase == 'end':
            self.last_hand_position = None
            self._smoothed_delta = (0.0, 0.0)
            self._cursor_remainder = (0.0, 0.0)
            return

        position = event.hand_position
        if position is None or len(position) < 2:
            logger.warning("Ignoring movement event without a valid hand position")
            return

        if self.last_hand_position is None or event.phase == 'start':
            self.last_hand_position = (float(position[0]), float(position[1]))
            self._smoothed_delta = (0.0, 0.0)
            self._cursor_remainder = (0.0, 0.0)
            return

        screen_width = win32api.GetSystemMetrics(0)
        screen_height = win32api.GetSystemMetrics(1)
        delta = (
            (self.last_hand_position[0] - float(position[0]))
            * screen_width
            * CURSOR_SENSITIVITY,
            (float(position[1]) - self.last_hand_position[1])
            * screen_height
            * CURSOR_SENSITIVITY,
        )
        smoothing = min(max(CURSOR_SMOOTHING_FACTOR, 0.0), 1.0)
        self._smoothed_delta = tuple(
            smoothing * current + (1.0 - smoothing) * previous
            for current, previous in zip(delta, self._smoothed_delta)
        )
        self.last_hand_position = (float(position[0]), float(position[1]))

        delta = tuple(
            value if abs(value) >= CURSOR_MOVEMENT_DEADZONE_PIXELS else 0.0
            for value in self._smoothed_delta
        )

        self._cursor_remainder = tuple(
            remainder + value
            for remainder, value in zip(self._cursor_remainder, delta)
        )
        dx, dy = (int(round(value)) for value in self._cursor_remainder)
        self._cursor_remainder = tuple(
            value - emitted
            for value, emitted in zip(self._cursor_remainder, (dx, dy))
        )
        if dx or dy:
            logger.debug("Moving cursor by (%d, %d) from hand position %s", dx, dy, position)
            self.move_cursor_relative(dx, dy)
    
    def _handle_index_pinch(self, event: GestureEvent):
        """
        Handle index finger pinch (left click or drag).
        
        Args:
            event: Index pinch gesture event
        """
        # TODO: Implement index pinch handling
        # Differentiate between:
        # - Pinch start: left click or start of drag
        # - Pinch move: drag operation
        # - Pinch end: release
        logger.debug(f"Index pinch event from {event.hand}")
        if event.phase == 'start':
            pydirectinput.mouseDown()
        elif event.phase == 'move':
            self._handle_hand_movement(event)  # Continue moving cursor while pinched
            pass
        elif event.phase == 'end':
            pydirectinput.mouseUp()

    
    def _handle_middle_pinch(self, event: GestureEvent):
        """
        Handle middle finger pinch (right click).
        
        Args:
            event: Middle pinch gesture event
        """
        # TODO: Implement middle pinch handling
        logger.debug(f"Middle pinch event from {event.hand}")
    
    def _handle_clutch(self, event: GestureEvent):
        """
        Handle clutch gesture (pause cursor tracking).
        
        Args:
            event: Clutch gesture event
        """
        if event.hand == 'Right':
            self.last_hand_position = None
            self._smoothed_delta = (0.0, 0.0)
            self._cursor_remainder = (0.0, 0.0)
        logger.debug(f"Clutch gesture from {event.hand}")
    
    def move_cursor(self, x: int, y: int):
        """
        Move cursor to absolute position.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        try:
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
            bounded_x = max(0, min(int(x), screen_width - 1))
            bounded_y = max(0, min(int(y), screen_height - 1))
            pydirectinput.moveTo(bounded_x, bounded_y)
            self.current_cursor_pos = (bounded_x, bounded_y)
        except Exception as e:
            logger.error(f"Error moving cursor: {e}")
    
    def move_cursor_relative(self, dx: int, dy: int):
        """
        Move cursor by relative offset.
        
        Args:
            dx: X offset in pixels
            dy: Y offset in pixels
        """
        try:
            current_x, current_y = self._get_cursor_pos()
            new_x = int(current_x + dx)
            new_y = int(current_y + dy)
            self.move_cursor(new_x, new_y)
        except Exception as e:
            logger.error(f"Error moving cursor relatively: {e}")
    
    def left_click(self):
        """Perform left mouse click."""
        try:
            pydirectinput.click()
            pydirectinput.mouseUp()
            logger.debug("Left click performed")
        except Exception as e:
            logger.error(f"Error performing left click: {e}")
    
    def right_click(self):
        """Perform right mouse click."""
        try:
            pydirectinput.rightClick()
            logger.debug("Right click performed")
        except Exception as e:
            logger.error(f"Error performing right click: {e}")
    
    def drag_to(self, x: int, y: int, duration: float = 0.1):
        """
        Perform click-drag to target position.
        
        Args:
            x: Target X coordinate
            y: Target Y coordinate
            duration: Duration of drag in seconds
        """
        try:
            current_x, current_y = self._get_cursor_pos()
            pydirectinput.drag(x - current_x, y - current_y, duration=duration)
            logger.debug(f"Drag performed to ({x}, {y})")
        except Exception as e:
            logger.error(f"Error performing drag: {e}")
    
    def drag_window(self, hwnd: int, x: int, y: int):
        """
        Drag a window by updating its position.
        
        Args:
            hwnd: Window handle
            x: New X position
            y: New Y position
        """
        # TODO: Implement window dragging
        # Use win32gui.SetWindowPos
        logger.debug(f"Dragging window {hwnd} to ({x}, {y})")
    
    def resize_window(self, hwnd: int, width: int, height: int):
        """
        Resize a window.
        
        Args:
            hwnd: Window handle
            width: New width in pixels
            height: New height in pixels
        """
        # TODO: Implement window resizing
        # Use win32gui.SetWindowPos
        logger.debug(f"Resizing window {hwnd} to {width}x{height}")
    
    def get_window_at_cursor(self) -> Optional[int]:
        """
        Get window handle at current cursor position.
        
        Returns:
            int: Window handle or None
        """
        # TODO: Implement window lookup
        # Use win32gui.WindowFromPoint
        x, y = self._get_cursor_pos()
        logger.debug(f"Getting window at cursor ({x}, {y})")
        return None
    
    def get_window_rect(self, hwnd: int) -> Optional[WindowRect]:
        """
        Get rectangle of window.
        
        Args:
            hwnd: Window handle
            
        Returns:
            WindowRect or None
        """
        # TODO: Implement rect retrieval
        # Use win32gui.GetWindowRect
        logger.debug(f"Getting rect for window {hwnd}")
        return None
    
    def is_point_in_title_bar(self, hwnd: int, x: int, y: int) -> bool:
        """
        Check if point is in window's title bar.
        
        Args:
            hwnd: Window handle
            x: X coordinate
            y: Y coordinate
            
        Returns:
            bool: True if point is in title bar
        """
        # TODO: Implement title bar detection
        rect = self.get_window_rect(hwnd)
        if rect:
            # Title bar is at top of window, height TITLE_BAR_HEIGHT_PIXELS
            return (rect.left <= x <= rect.right and
                    rect.top <= y <= rect.top + TITLE_BAR_HEIGHT_PIXELS)
        return False
    
    def _get_cursor_pos(self) -> Tuple[int, int]:
        """
        Get current cursor position.
        
        Returns:
            Tuple[int, int]: (x, y) coordinates
        """
        position = pydirectinput.position()
        return int(position[0]), int(position[1])
