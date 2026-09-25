"""Local webcam capture loop for non-WebRTC operation."""

import logging
import threading
import time

import cv2

from config import (
    LOCAL_CAMERA_FPS,
    LOCAL_CAMERA_HEIGHT,
    LOCAL_CAMERA_INDEX,
    LOCAL_CAMERA_WIDTH,
)

logger = logging.getLogger(__name__)


class LocalCameraWorker:
    """Capture webcam frames and feed them directly to the gesture pipeline."""

    def __init__(self, processor, recognizer):
        self.processor = processor
        self.recognizer = recognizer
        self._stop_event = threading.Event()
        self._thread = None
        self._capture = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="local-camera",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._capture is not None:
            self._capture.release()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _run(self):
        capture = cv2.VideoCapture(LOCAL_CAMERA_INDEX, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(LOCAL_CAMERA_INDEX)
        self._capture = capture
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, LOCAL_CAMERA_WIDTH)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, LOCAL_CAMERA_HEIGHT)
        capture.set(cv2.CAP_PROP_FPS, LOCAL_CAMERA_FPS)

        if not capture.isOpened():
            logger.error("Unable to open local webcam %s", LOCAL_CAMERA_INDEX)
            capture.release()
            self._capture = None
            return

        logger.info("Local webcam %s started", LOCAL_CAMERA_INDEX)
        try:
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok:
                    logger.warning("Unable to read a frame from local webcam")
                    time.sleep(0.05)
                    continue

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                hands = self.processor.process_frame(rgb_frame)
                gesture_events = self.recognizer.process_hands(hands, time.monotonic())
                annotated_rgb = self.processor.draw_landmarks(
                    rgb_frame, hands, gesture_events
                )
                cv2.imshow("HandyMouseCam - Camera", frame)
                cv2.imshow(
                    "HandyMouseCam - Landmark Debug",
                    cv2.cvtColor(annotated_rgb, cv2.COLOR_RGB2BGR),
                )
                if cv2.waitKey(1) & 0xFF == 27:
                    self._stop_event.set()
        except Exception:
            logger.exception("Local webcam processing stopped unexpectedly")
        finally:
            cv2.destroyWindow("HandyMouseCam - Camera")
            cv2.destroyWindow("HandyMouseCam - Landmark Debug")
            capture.release()
            self._capture = None
            logger.info("Local webcam stopped")
