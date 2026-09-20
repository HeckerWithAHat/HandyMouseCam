"""
Configuration constants for HandyMouseCam backend.
"""

# Flask Configuration
FLASK_PORT = 5000
FLASK_HOST = "0.0.0.0"
DEBUG_MODE = True

# WebRTC Configuration
STUN_SERVERS = []  # Not needed on local LAN
TURN_SERVERS = []

# Hand Tracking Configuration
MAX_NUM_HANDS = 2
HAND_DETECTION_CONFIDENCE = 0.7
HAND_TRACKING_CONFIDENCE = 0.5
HAND_LANDMARKER_MODEL_PATH = "models/hand_landmarker.task"

# Gesture Recognition Configuration
PINCH_DISTANCE_THRESHOLD_MM = 10  # Distance between thumb and finger to trigger pinch
PINCH_STABILITY_FRAMES = 3  # Number of frames to confirm a pinch
MIN_HAND_VISIBILITY = 0.5  # Minimum confidence to consider hand visible
FIST_DISTANCE_THRESHOLD_MM = 20  # Distance between all fingertips and palm center to consider a fist

# Cursor Control Configuration
CURSOR_SENSITIVITY = 1.5  # Pixels per mm of hand movement
CURSOR_SMOOTHING_FACTOR = 0.7  # Apply exponential smoothing to cursor movement (0.0-1.0)

# Window Control Configuration
TITLE_BAR_HEIGHT_PIXELS = 30
WINDOW_RESIZE_MIN_WIDTH = 100
WINDOW_RESIZE_MIN_HEIGHT = 100

# Logging Configuration
LOG_LEVEL = "WARNING"
LOG_FILE = "handy_mouse_cam.log"

# Network Configuration
QR_CODE_OUTPUT_PATH = "qr_code.bmp"
