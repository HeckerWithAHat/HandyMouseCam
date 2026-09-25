import numpy as np

from config import PINCH_STABILITY_FRAMES
from gesture_recognizer import GestureRecognizer, GestureType, PinchType
from video_processor import Hand


def make_hand(thumb=(0.1, 0.1, 0.0), index=(0.1, 0.1, 0.0),
              middle=(0.5, 0.5, 0.0), confidence=0.9):
    landmarks = np.zeros((21, 3), dtype=float)
    landmarks[0] = [0.0, 0.0, 0.0]
    landmarks[4] = thumb
    landmarks[8] = index
    landmarks[12] = middle
    landmarks[9] = [0.0, 0.1, 0.0]
    landmarks[13] = [0.0, 0.1, 0.0]
    return Hand(landmarks, "Right", confidence)


def test_pinch_requires_stability_then_emits_start_move_end(monkeypatch):
    recognizer = GestureRecognizer()
    recognizer._is_hand_closed = lambda hand: False
    hand = make_hand()

    frames = [recognizer.process_hands([hand], timestamp) for timestamp in range(1, PINCH_STABILITY_FRAMES + 1)]

    assert all(not any(event.gesture_type == GestureType.PINCH_INDEX for event in frame)
               for frame in frames[:-1])
    assert frames[-1][0].gesture_type == GestureType.PINCH_INDEX
    assert frames[-1][0].phase == "start"
    assert frames[-1][0].pinch_type == PinchType.INDEX
    assert recognizer.process_hands([hand], 4.0)[0].phase == "move"

    end_events = recognizer.process_hands([], 5.0)
    assert any(event.gesture_type == GestureType.PINCH_INDEX
               and event.phase == "end" for event in end_events)


def test_open_hand_emits_movement_event(monkeypatch):
    recognizer = GestureRecognizer()
    recognizer._is_hand_closed = lambda hand: False
    recognizer._detect_pinch = lambda hand: (None, None)

    events = recognizer.process_hands([make_hand()], 1.0)

    right_events = [event for event in events if event.hand == "Right"]
    assert len(right_events) == 1
    assert right_events[0].gesture_type == GestureType.OPEN_HAND_MOVE
    assert right_events[0].phase == "move"


def test_closed_hand_emits_clutch_and_recovery_end():
    recognizer = GestureRecognizer()
    closed = make_hand()
    open_hand = make_hand()
    recognizer._is_hand_closed = lambda hand: hand is closed
    recognizer._detect_pinch = lambda hand: (None, None)

    clutch = recognizer.process_hands([closed], 1.0)
    assert any(event.gesture_type == GestureType.CLUTCH
               and event.phase == "start" for event in clutch)

    recovery = recognizer.process_hands([open_hand], 2.0)
    assert any(event.gesture_type == GestureType.CLUTCH
               and event.phase == "end" for event in recovery)


def test_clutch_takes_priority_over_pinch_and_resets_pinch_stability():
    recognizer = GestureRecognizer()
    hand = make_hand()
    recognizer._is_hand_closed = lambda current_hand: True
    recognizer._detect_pinch = lambda current_hand: (PinchType.INDEX, 1.0)

    events = recognizer.process_hands([hand], 1.0)

    assert [event.gesture_type for event in events if event.hand == "Right"] == [GestureType.CLUTCH]
    assert recognizer.pinch_frame_count["right"] == 0
    assert recognizer._pinch_candidates["right"] is None

    recognizer._is_hand_closed = lambda current_hand: False
    first_open_frame = recognizer.process_hands([hand], 2.0)
    assert not any(event.gesture_type == GestureType.PINCH_INDEX for event in first_open_frame)


def test_low_confidence_and_unknown_hands_are_ignored():
    recognizer = GestureRecognizer()
    low_confidence = make_hand(confidence=0.1)
    low_confidence.handedness = "Unknown"

    events = recognizer.process_hands([low_confidence], 1.0)

    assert all(event.hand != "Unknown" for event in events)
    assert {event.hand for event in events} == {"Left", "Right"}


def test_callbacks_receive_events_and_callback_errors_are_isolated():
    recognizer = GestureRecognizer()
    received = []
    recognizer.register_gesture_callback(received.append)
    recognizer.register_gesture_callback(lambda event: (_ for _ in ()).throw(RuntimeError("boom")))
    recognizer._is_hand_closed = lambda hand: False
    recognizer._detect_pinch = lambda hand: (None, None)

    events = recognizer.process_hands([make_hand()], 1.0)

    assert received == events
