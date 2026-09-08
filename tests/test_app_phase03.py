from types import SimpleNamespace

import numpy as np
import pytest

import app
from video_processor import AnnotatedVideoTrack


class FakeFrame:
    time = 123

    def to_ndarray(self, format):
        assert format == "rgb24"
        return np.zeros((2, 3, 3), dtype=np.uint8)


class FakeTrack:
    kind = "video"

    async def recv(self):
        return FakeFrame()


@pytest.mark.asyncio
async def test_annotated_track_processes_and_returns_frame(monkeypatch):
    processed = []
    recognized = []
    drawn = []
    monkeypatch.setattr(app.video_processor, "process_frame", lambda frame: processed.append(frame) or [])
    monkeypatch.setattr(app.gesture_recognizer, "process_hands", lambda hands, timestamp: recognized.append((hands, timestamp)))
    monkeypatch.setattr(app.video_processor, "draw_landmarks", lambda frame, hands: drawn.append((frame, hands)) or frame)

    output = await AnnotatedVideoTrack(
        FakeTrack(), app.video_processor, app.gesture_recognizer
    ).recv()

    assert output.width == 3
    assert output.height == 2
    assert processed[0].shape == (2, 3, 3)
    assert recognized == [([], 123)]
    assert len(drawn) == 1


def test_index_route_and_status_route():
    client = app.app.test_client()

    index_response = client.get("/")
    status_response = client.get("/api/status")

    assert index_response.status_code == 200
    assert status_response.status_code == 200
    assert status_response.get_json()["status"] == "running"


def test_recognizer_callback_is_registered():
    assert app.os_controller.handle_gesture in app.gesture_recognizer.gesture_callbacks


def test_video_track_adds_annotated_return_track(monkeypatch):
    added = []
    app.webrtc_signaling.peer_connection = SimpleNamespace(
        addTrack=added.append
    )

    app._on_video_track(FakeTrack())

    assert len(added) == 1
    assert isinstance(added[0], AnnotatedVideoTrack)
