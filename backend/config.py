"""Configuration constants for HandyMouseCam backend."""

import os


def _env_bool(name: str, default: bool) -> bool:
	value = os.getenv(name)
	if value is None:
		return default
	return value.strip().lower() in {"1", "true", "yes", "on"}

# Flask Configuration
FLASK_PORT = 5000
FLASK_HOST = "0.0.0.0"
DEBUG_MODE = True

# Set USE_WEBRTC=false to use the laptop webcam instead of a phone camera.
USE_WEBRTC = _env_bool("USE_WEBRTC", False)
LOCAL_CAMERA_INDEX = int(os.getenv("LOCAL_CAMERA_INDEX", "0"))
LOCAL_CAMERA_WIDTH = int(os.getenv("LOCAL_CAMERA_WIDTH", "640"))
LOCAL_CAMERA_HEIGHT = int(os.getenv("LOCAL_CAMERA_HEIGHT", "480"))
LOCAL_CAMERA_FPS = int(os.getenv("LOCAL_CAMERA_FPS", "30"))
RETURN_ANNOTATED_VIDEO = _env_bool("RETURN_ANNOTATED_VIDEO", False)

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
CURSOR_SMOOTHING_FACTOR = 0.35  # Current-delta weight; lower is smoother but slower
CURSOR_MOVEMENT_DEADZONE_PIXELS = 1.0

# Window Control Configuration
TITLE_BAR_HEIGHT_PIXELS = 30
WINDOW_RESIZE_MIN_WIDTH = 100
WINDOW_RESIZE_MIN_HEIGHT = 100

# Logging Configuration
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = "handy_mouse_cam.log"

# Network Configuration
QR_CODE_OUTPUT_PATH = "qr_code.bmp"
