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
from config import CURSOR_SENSITIVITY, TITLE_BAR_HEIGHT_PIXELS

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
        # TODO: Implement relative cursor movement
        # Should:
        # - Calculate delta from previous position
        # - Apply sensitivity scaling
        # - Apply smoothing
        # - Update OS cursor position
        if event.hand == 'Right':
            logger.debug(f"Moving cursor to hand position {event.hand_position}")
    
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
        # TODO: Implement clutch handling
        logger.debug(f"Clutch gesture from {event.hand}")
    
    def move_cursor(self, x: int, y: int):
        """
        Move cursor to absolute position.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        try:
            pydirectinput.moveTo(x, y)
            self.current_cursor_pos = (x, y)
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
            new_x = current_x + dx
            new_y = current_y + dy
            self.move_cursor(new_x, new_y)
        except Exception as e:
            logger.error(f"Error moving cursor relatively: {e}")
    
    def left_click(self):
        """Perform left mouse click."""
        try:
            pydirectinput.click()
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
        return pydirectinput.position()
