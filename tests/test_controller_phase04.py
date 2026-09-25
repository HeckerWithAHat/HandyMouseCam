from types import SimpleNamespace

import controller
from config import CURSOR_SENSITIVITY, CURSOR_SMOOTHING_FACTOR
from gesture_recognizer import GestureEvent, GestureType


def make_event(position, phase="move", hand="Right"):
    return GestureEvent(
        GestureType.OPEN_HAND_MOVE,
        hand,
        1.0,
        position,
        phase=phase,
    )


def make_controller(monkeypatch):
    monkeypatch.setattr(controller.pydirectinput, "position", lambda: (100, 200))
    return controller.OSController()


def test_first_movement_frame_only_establishes_baseline(monkeypatch):
    os_controller = make_controller(monkeypatch)
    relative_moves = []
    monkeypatch.setattr(
        os_controller, "move_cursor_relative", lambda dx, dy: relative_moves.append((dx, dy))
    )

    os_controller.handle_gesture(make_event((0.2, 0.3)))

    assert relative_moves == []
    assert os_controller.last_hand_position == (0.2, 0.3)


def test_movement_applies_sensitivity_and_smoothing(monkeypatch):
    os_controller = make_controller(monkeypatch)
    monkeypatch.setattr(
        controller.win32api,
        "GetSystemMetrics",
        lambda index: 100,
    )
    relative_moves = []
    monkeypatch.setattr(
        os_controller, "move_cursor_relative", lambda dx, dy: relative_moves.append((dx, dy))
    )

    os_controller.handle_gesture(make_event((0.0, 0.0)))
    os_controller.handle_gesture(make_event((2.0, 4.0)))

    expected_x = round(-CURSOR_SENSITIVITY * 2.0 * 100 * CURSOR_SMOOTHING_FACTOR)
    expected_y = round(CURSOR_SENSITIVITY * 4.0 * 100 * CURSOR_SMOOTHING_FACTOR)
    assert relative_moves == [(expected_x, expected_y)]


def test_right_hand_moving_left_moves_cursor_left(monkeypatch):
    os_controller = make_controller(monkeypatch)
    monkeypatch.setattr(controller.win32api, "GetSystemMetrics", lambda index: 100)
    relative_moves = []
    monkeypatch.setattr(
        os_controller, "move_cursor_relative", lambda dx, dy: relative_moves.append((dx, dy))
    )

    os_controller.handle_gesture(make_event((0.6, 0.5)))
    os_controller.handle_gesture(make_event((0.4, 0.5)))

    assert relative_moves[0][0] < 0


def test_small_normalized_hand_delta_moves_cursor(monkeypatch):
    os_controller = make_controller(monkeypatch)
    monkeypatch.setattr(
        controller.win32api,
        "GetSystemMetrics",
        lambda index: 1920 if index == 0 else 1080,
    )
    relative_moves = []
    monkeypatch.setattr(
        os_controller, "move_cursor_relative", lambda dx, dy: relative_moves.append((dx, dy))
    )

    os_controller.handle_gesture(make_event((0.500, 0.500)))
    os_controller.handle_gesture(make_event((0.505, 0.505)))

    assert relative_moves == [(round(0.005 * 1920 * CURSOR_SENSITIVITY * CURSOR_SMOOTHING_FACTOR),
                               round(0.005 * 1080 * CURSOR_SENSITIVITY * CURSOR_SMOOTHING_FACTOR))]


def test_clutch_resets_movement_baseline(monkeypatch):
    os_controller = make_controller(monkeypatch)
    relative_moves = []
    monkeypatch.setattr(
        os_controller, "move_cursor_relative", lambda dx, dy: relative_moves.append((dx, dy))
    )

    os_controller.handle_gesture(make_event((1.0, 1.0)))
    os_controller.handle_gesture(SimpleNamespace(
        gesture_type=GestureType.CLUTCH,
        hand="Right",
    ))
    os_controller.handle_gesture(make_event((2.0, 2.0)))

    assert relative_moves == []
    assert os_controller.last_hand_position == (2.0, 2.0)


def test_move_cursor_clamps_to_screen_bounds(monkeypatch):
    os_controller = make_controller(monkeypatch)
    moved_to = []
    monkeypatch.setattr(controller.win32api, "GetSystemMetrics", lambda index: 800 if index == 0 else 600)
    monkeypatch.setattr(controller.pydirectinput, "moveTo", lambda x, y: moved_to.append((x, y)))

    os_controller.move_cursor(1000, -10)

    assert moved_to == [(799, 0)]
    assert os_controller.current_cursor_pos == (799, 0)


def test_move_cursor_relative_uses_current_os_position(monkeypatch):
    os_controller = make_controller(monkeypatch)
    moved_to = []
    monkeypatch.setattr(controller.win32api, "GetSystemMetrics", lambda index: 1920 if index == 0 else 1080)
    monkeypatch.setattr(controller.pydirectinput, "position", lambda: (300, 400))
    monkeypatch.setattr(controller.pydirectinput, "moveTo", lambda x, y: moved_to.append((x, y)))

    os_controller.move_cursor_relative(12, -8)

    assert moved_to == [(312, 392)]