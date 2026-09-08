from types import SimpleNamespace

import numpy as np
import pytest

from video_processor import Hand, VideoProcessor


def make_landmark_result(label="Right", score=0.9):
    points = [SimpleNamespace(x=i / 100, y=i / 200, z=-i / 300) for i in range(21)]
    classification = SimpleNamespace(category_name=label, score=score)
    return SimpleNamespace(
        hand_landmarks=[points],
        handedness=[[classification]],
    )


def test_hand_landmark_accessors_and_palm_center():
    landmarks = np.zeros((21, 3), dtype=float)
    landmarks[0] = [0.0, 0.0, 0.0]
    landmarks[4] = [0.1, 0.2, 0.3]
    landmarks[8] = [0.4, 0.5, 0.6]
    landmarks[9] = [0.2, 0.4, 0.6]
    landmarks[13] = [0.4, 0.6, 0.8]
    hand = Hand(landmarks, "Right", 0.8)

    assert hand.get_wrist() == (0.0, 0.0, 0.0)
    assert hand.get_thumb_tip() == (0.1, 0.2, 0.3)
    assert hand.get_index_tip() == (0.4, 0.5, 0.6)
    np.testing.assert_allclose(hand.get_palm_center(), [0.15, 0.25, 0.35])


def test_process_frame_converts_mediapipe_result_to_hand():
    processor = VideoProcessor.__new__(VideoProcessor)
    processor.hands = SimpleNamespace(
        detect_for_video=lambda image, timestamp: make_landmark_result()
    )
    frame = np.zeros((10, 20, 3), dtype=np.uint8)

    hands = processor.process_frame(frame)

    assert len(hands) == 1
    assert hands[0].landmarks.shape == (21, 3)
    assert hands[0].handedness == "Right"
    assert hands[0].confidence == 0.9


def test_process_frame_rejects_invalid_shape():
    processor = VideoProcessor.__new__(VideoProcessor)
    processor.hands = SimpleNamespace(process=lambda frame: make_landmark_result())

    with pytest.raises(ValueError):
        processor.process_frame(np.zeros((10, 20), dtype=np.uint8))


def test_process_frame_returns_empty_when_model_unavailable():
    processor = VideoProcessor.__new__(VideoProcessor)
    processor.hands = SimpleNamespace(
        detect_for_video=lambda image, timestamp: SimpleNamespace(
            hand_landmarks=[], handedness=[]
        )
    )
    processor._last_timestamp_ms = 0

    assert processor.process_frame(np.zeros((2, 2, 3), dtype=np.uint8)) == []


def test_frame_dimensions():
    processor = VideoProcessor.__new__(VideoProcessor)

    assert processor.get_frame_dimensions(np.zeros((24, 32, 3))) == (32, 24)


def test_close_closes_model():
    processor = VideoProcessor.__new__(VideoProcessor)
    closed = []
    processor.hands = SimpleNamespace(close=lambda: closed.append(True))

    processor.close()

    assert closed == [True]
