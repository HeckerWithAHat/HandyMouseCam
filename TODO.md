# TODO.md - Implementation Checklist

Complete list of all functions and features that need to be implemented in HandyMouseCam, organized by module and development phase.

---

## Phase 0-1: Project Setup & Video Pipeline

### `backend/signaling.py` - WebRTC Signaling
- [x] **`WebRTCSignaling.create_peer_connection()`** (async)
  - Create RTCPeerConnection instance
  - Register on_track handlers
  - Configure ICE servers (empty for LAN)
  - Return configured peer connection

- [x] **`WebRTCSignaling.handle_sdp_offer(offer_json: str)`** (async)
  - Parse JSON SDP offer
  - Set remote description on peer connection
  - Create local answer
  - Set local description
  - Return JSON-serialized SDP answer

- [x] **`WebRTCSignaling.handle_ice_candidate(candidate_json: str)`** (async)
  - Parse JSON ICE candidate
  - Add to peer connection
  - Handle any errors gracefully

- [x] **`WebRTCSignaling.add_on_track_handler(callback)`**
  - Register callback function to be called when remote track arrives
  - Store reference for later invocation

### `backend/app.py` - Flask Routes & WebSocket Handlers
- [x] **`on_sdp_offer(data)`** Socket.IO event handler
  - Extract SDP offer from data
  - Call WebRTCSignaling.handle_sdp_offer()
  - Emit SDP answer back to phone via 'sdp_answer' event
  - Log any errors

- [x] **`on_ice_candidate(data)`** Socket.IO event handler
  - Extract ICE candidate from data
  - Call WebRTCSignaling.handle_ice_candidate()
  - Handle errors gracefully

- [x] **Initialize WebRTC components on server startup**
  - Create WebRTCSignaling instance
  - Create VideoProcessor instance
  - Create GestureRecognizer instance
  - Create OSController instance
  - Wire gesture callbacks

### `frontend/static/script.js` - Phone Client
- [x] **`HandyMouseCamClient.connectToServer()`**
  - Establish SocketIO connection to server
  - Set up event listeners for connection/disconnect
  - Handle connection errors

- [x] **`HandyMouseCamClient.setupWebRTC()`**
  - Create RTCPeerConnection
  - Add local media stream tracks
  - Set up ICE candidate handler
  - Create SDP offer
  - Emit offer to server
  - Handle remote tracks

- [x] **`HandyMouseCamClient.getMediaStream()`**
  - Request camera access via getUserMedia()
  - Handle different facing modes (front/rear)
  - Attach to video element
  - Handle permission denied errors

- [x] **`HandyMouseCamClient.switchCamera()`**
  - Stop current media stream
  - Request new stream with different facing mode
  - Update video element

- [x] **`HandyMouseCamClient.setStatus(text, connected)`**
  - Update UI status indicator (dot color)
  - Update status text
  - Set connected flag

---

## Phase 1: Video Frame Processing

### `backend/video_processor.py` - Hand Tracking
- [x] **`Hand.get_palm_center()`**
  - Average wrist and MCP landmarks to find palm center
  - Return (x, y, z) tuple

- [x] **`VideoProcessor.process_frame(frame: np.ndarray)`**
  - Convert frame to RGB if needed
  - Run MediaPipe Hands inference
  - Extract landmarks for each detected hand
  - Create Hand objects with landmarks and handedness
  - Return list of Hand objects
  - Log frame processing stats

- [x] **`VideoProcessor.draw_landmarks(frame, hands)`**
  - Draw circles at landmark positions
  - Draw lines connecting hand skeleton
  - Add text labels (Left/Right, confidence)
  - Return annotated frame (for debug display)

- [x] **`VideoProcessor.get_frame_dimensions(frame)`**
  - Extract height and width
  - Return as (width, height) tuple

### `backend/utils/network_utils.py` - Network Utilities
- [x] **`get_local_ip()`**
  - Detect local IPv4 address of machine
  - Return IP suitable for LAN access
  - Handle multiple network interfaces gracefully
  - Fallback to 127.0.0.1 if detection fails

- [x] **`test_network_connectivity(host, port, timeout)`**
  - Test if host:port is reachable
  - Return boolean True/False

### `backend/utils/qr_generator.py` - QR Code
- [x] **`generate_qr_code(url, output_path, size)`**
  - Use qrcode library to generate QR from URL
  - Save PNG to output_path
  - Print ASCII art version to console
  - Handle file I/O errors

- [x] **`display_qr_ascii(url)`**
  - Generate ASCII art QR code
  - Print to terminal

---

## Phase 2: Hand Landmark & State Setup

### `backend/video_processor.py` - Frame-to-Landmark Pipeline
- [x] **Wire VideoProcessor into main loop**
  - On each WebRTC frame arrival
  - Call process_frame(frame)
  - Pass Hand objects to GestureRecognizer

### `backend/gesture_recognizer.py` - Gesture Detection Prep
- [x] **`GestureRecognizer._calculate_pinch_distance(thumb, finger)`**
  - Calculate Euclidean distance between 3D points
  - Normalize for hand size (~170mm reference)
  - Return distance in mm

- [x] **`GestureRecognizer._is_pinched(hand, finger_idx)`**
  - Calculate distance from thumb to specified finger
  - Compare against PINCH_DISTANCE_THRESHOLD_MM
  - Return boolean (True = pinched)

- [x] **`GestureRecognizer._is_hand_closed(hand)`**
  - Check if all fingertips are close to palm
  - Use multiple landmark distance checks
  - Return boolean (True = closed/fist)

---

## Phase 3: Gesture Recognition State Machine

### `backend/gesture_recognizer.py` - Core Recognition Logic
- [x] **`GestureRecognizer.process_hands(hands, timestamp)`**
  - Main gesture processing loop
  - Map hands by handedness (left/right)
  - Detect pinch start/move/end transitions
  - Detect open hand movement
  - Detect clutch (fist or out-of-frame)
  - Generate GestureEvent objects for state changes
  - Maintain frame counts for stability
  - Call callbacks for each event
  - Return list of events

- [x] **`GestureRecognizer._emit_gesture(event)`**
  - Iterate through registered callbacks
  - Call each callback with event
  - Handle callback exceptions gracefully
  - Log any errors

### Integration Points
- [x] **Wire GestureRecognizer into main loop**
  - After VideoProcessor extracts hands
  - Pass hands list to process_hands()
  - Receive GestureEvent stream

---

## Phase 4: Click & Movement Gestures

### `backend/gesture_recognizer.py` - Gesture Type Detection
- [x] **Implement gesture event generation:**
  - Thumb+Index pinch detection → GestureEvent(PINCH_INDEX, ...)
  - Thumb+Middle pinch detection → GestureEvent(PINCH_MIDDLE, ...)
  - Open hand movement → GestureEvent(OPEN_HAND_MOVE, ...)
  - Fist/out-of-frame → GestureEvent(CLUTCH, ...)

### `backend/controller.py` - Cursor Movement
- [x] **`OSController._handle_hand_movement(event)`**
  - Calculate delta from previous hand position
  - Apply CURSOR_SENSITIVITY scaling
  - Apply exponential smoothing (CURSOR_SMOOTHING_FACTOR)
  - Call move_cursor_relative(dx, dy)
  - Update tracking state

- [x] **`OSController.move_cursor_relative(dx, dy)`**
  - Get current cursor position
  - Add offset to current position
  - Call move_cursor() with new coordinates

- [x] **`OSController.move_cursor(x, y)`**
  - Use pydirectinput.moveTo(x, y)
  - Update internal cursor position tracking
  - Handle coordinate bounds checking

- [x] **`OSController._get_cursor_pos()`**
  - Call pydirectinput.position()
  - Return (x, y) tuple

### Integration
- [x] **Wire GestureRecognizer callbacks to OSController**
  - Register OSController.handle_gesture as callback
  - Receive gesture events in real-time
  - Translate to OS actions

---

## Phase 5: Click Gestures & Dragging

### `backend/controller.py` - Click Actions
- [ ] **`OSController._handle_index_pinch(event)`**
  - Detect pinch start vs. move vs. end
  - First event: left_click()
  - Move events: track hand position for drag
  - End event: release (implicit in pydirectinput)

- [ ] **`OSController._handle_middle_pinch(event)`**
  - Similar to index pinch but for right-click
  - Call right_click()

- [ ] **`OSController.left_click()`**
  - Use pydirectinput.click()
  - Log click action

- [ ] **`OSController.right_click()`**
  - Use pydirectinput.rightClick()
  - Log click action

- [ ] **`OSController.drag_to(x, y, duration)`**
  - Use pydirectinput.drag()
  - Calculate delta from current position
  - Log drag action

### Gesture State Tracking
- [ ] **Implement click-drag state machine**
  - Track pinch start position
  - On pinch_move: interpolate cursor to new position
  - On pinch_end: finalize drag

---

## Phase 6: Window Drag & Manipulation

### `backend/controller.py` - Window Operations
- [ ] **`OSController.get_window_at_cursor()`**
  - Use win32gui.WindowFromPoint(x, y)
  - Return window handle
  - Handle None case (no window)

- [ ] **`OSController.get_window_rect(hwnd)`**
  - Use win32gui.GetWindowRect(hwnd)
  - Create WindowRect object
  - Handle invalid window handles

- [ ] **`OSController.is_point_in_title_bar(hwnd, x, y)`**
  - Get window rect
  - Check if (x, y) falls within title bar region
  - Title bar height defined in config
  - Return boolean

- [ ] **`OSController.drag_window(hwnd, x, y)`**
  - Get current window rect
  - Calculate new rect with new position
  - Use win32gui.SetWindowPos()
  - Handle window state (minimized, maximized)

- [ ] **`OSController._handle_index_pinch(event)` - Window Drag Detection**
  - On pinch start: check if point is in window title bar
  - If yes: set dragging_window = True, dragging_window_hwnd = hwnd
  - On pinch move: call drag_window(hwnd, new_x, new_y)
  - On pinch end: set dragging_window = False

### Integration
- [ ] **Wire title bar detection into pinch handling**
  - Check window-under-cursor on pinch start
  - Determine if dragging window or just clicking

---

## Phase 7: Two-Hand Resize & Advanced Gestures

### `backend/gesture_recognizer.py` - Multi-Hand Gesture Detection
- [ ] **Implement two-hand pinch detection**
  - Track both hands' pinch state
  - Detect simultaneous pinches (start within N frames)
  - Calculate distance between two pinch points
  - Calculate angle between pinch points
  - Generate two-hand gesture events with both positions

### `backend/controller.py` - Window Resize
- [ ] **`OSController.resize_window(hwnd, width, height)`**
  - Use win32gui.SetWindowPos()
  - Maintain minimum window dimensions
  - Handle window constraints

- [ ] **`OSController._handle_two_hand_resize(left_event, right_event)`**
  - Get initial distance between pinch points (on start)
  - Calculate current distance between pinch points
  - Compute distance delta
  - Apply proportional resize
  - Anchor to nearest corner
  - Call resize_window()

- [ ] **Two-hand event fusion**
  - Combine left + right hand events into gesture
  - Detect pinch-stretch vs. pinch-squeeze
  - Call appropriate resize handler

---

## Phase 8: Polish & Robustness

### `backend/gesture_recognizer.py` - Clutch Mechanism
- [ ] **`OSController._handle_clutch(event)`**
  - Pause cursor tracking when triggered
  - Store "clutch_active" flag
  - Resume on hand re-open or re-entry

- [ ] **Implement clutch pause in movement handler**
  - Check clutch_active flag
  - Skip cursor updates if clutched
  - Allow re-positioning hand without cursor movement

### `backend/app.py` - Reconnection & Error Handling
- [ ] **Handle WebRTC disconnection gracefully**
  - Log disconnection events
  - Reset gesture state
  - Allow phone to reconnect

- [ ] **Frame processing error handling**
  - Handle MediaPipe inference failures
  - Skip frames with errors
  - Log warnings without crashing

### `backend/controller.py` - Permission & Admin Issues
- [ ] **Handle Windows permission errors**
  - Catch exceptions from pydirectinput/win32gui
  - Log permission-denied errors
  - Gracefully degrade functionality

- [ ] **UAC-elevated window handling**
  - Detect when target window is elevated
  - Log inability to control
  - Continue with other actions

### Configuration Tuning
- [ ] **Expose sensitivity parameters via config**
  - CURSOR_SENSITIVITY: pixels per mm
  - CURSOR_SMOOTHING_FACTOR: exponential moving average
  - PINCH_DISTANCE_THRESHOLD_MM: pinch detection threshold
  - PINCH_STABILITY_FRAMES: frames to confirm pinch

- [ ] **Real-world calibration logging**
  - Log detected hand sizes
  - Log pinch distances for analysis
  - Help users tune thresholds

---

## Testing & Validation

### `tests/test_gesture_recognizer.py`
- [ ] Test pinch detection with mock landmarks
- [ ] Test hand movement tracking
- [ ] Test clutch gesture detection
- [ ] Test gesture callbacks
- [ ] Test state machine transitions
- [ ] Test gesture event creation and serialization

### `tests/test_controller.py`
- [ ] Mock pydirectinput and test cursor movement
- [ ] Test left/right click actions
- [ ] Test drag operations
- [ ] Mock win32gui and test window operations
- [ ] Test title bar detection
- [ ] Test window drag
- [ ] Test window resize
- [ ] Integration tests for gesture-to-action pipeline

---

## Priority Implementation Order

**Recommended sequence for efficient development:**

1. **WebRTC Pipeline** (Phase 0-1)
   - signaling.py: create_peer_connection, handle_sdp_offer, handle_ice_candidate
   - script.js: setupWebRTC, getMediaStream
   - app.py: WebSocket handlers

2. **Video Capture & Hand Tracking** (Phase 1-2)
   - video_processor.py: process_frame, draw_landmarks
   - utils/network_utils.py: get_local_ip, qr_generator
   - Integration into main loop

3. **Gesture Recognition Framework** (Phase 2-3)
   - gesture_recognizer.py: core process_hands loop, pinch detection
   - Hand landmark helper methods
   - Basic open/closed hand detection

4. **Cursor Control** (Phase 4)
   - controller.py: cursor movement and clicking
   - Wire GestureRecognizer to OSController

5. **Window Control** (Phase 6-7)
   - Window detection and manipulation
   - Title bar detection
   - Window drag and resize

6. **Polish & Testing** (Phase 8)
   - Error handling and robustness
   - Test suites
   - Performance optimization

---

## Statistics

- **Total Functions to Implement:** ~50+
- **Backend Modules:** 6 (3 core + 3 utils)
- **Frontend Modules:** 1 (JavaScript)
- **Test Modules:** 2

**Estimated implementation time:** 40-80 hours depending on testing depth and debugging.

---

Last updated: 2026-09-01
