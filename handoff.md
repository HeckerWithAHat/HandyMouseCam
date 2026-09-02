# handoff.md - Project Handoff Guide

## Overview

This document provides a human-readable explanation of the HandyMouseCam project structure. Read this to understand the codebase you're inheriting, how the pieces fit together, and where to start implementation.

---

## What is HandyMouseCam?

HandyMouseCam (codename "Stark Display") is a system that lets you control your laptop's cursor and windows using hand gestures captured by your phone's camera. Instead of a mouse, you use mid-air gestures: move your hand to move the cursor, pinch your thumb and index finger to click, pinch with your middle finger to right-click, and use two hands together to resize windows.

The system works entirely over your local WiFi network—no cloud, no special hardware, just your phone and laptop communicating via WebRTC (the same technology used for video calls).

---

## High-Level Architecture

Think of the system as a three-layer sandwich:

**Layer 1: Phone (Frontend)**
Your phone runs a browser-based app that accesses the camera via `getUserMedia()`. This is pure HTML/CSS/JavaScript—no app installation needed. The phone sends a live video stream to your laptop using WebRTC, a modern protocol designed for real-time video communication.

**Layer 2: Laptop (Backend)**
Your laptop runs a Flask web server that receives the video stream from the phone. Using MediaPipe (a hand-tracking library), it analyzes each video frame to identify where your hands are and what your fingers are doing. This produces a stream of hand landmarks—21 points per hand (wrist, knuckles, fingertips, etc.). These landmarks are then fed into a gesture recognizer that interprets the raw hand data into meaningful gestures: "thumb and index finger are close together = pinch", "hand moving = move cursor", etc.

**Layer 3: Operating System**
The final layer translates gesture events into actual OS commands—moving the mouse cursor, clicking buttons, dragging windows around, and resizing them. This happens via direct OS APIs on Windows (pydirectinput for mouse, pywin32 for window management).

```
Phone Camera Feed (WebRTC)
    ↓
Laptop Receives Video
    ↓
MediaPipe Extracts Hand Landmarks
    ↓
Gesture Recognizer Interprets Landmarks
    ↓
OS Controller Executes Actions (mouse, windows)
```

---

## Project Structure Deep Dive

### Backend Directory: `backend/`

The backend is where all the real work happens. Here's each file:

#### `config.py` - The Control Panel

Before you run a single line of code, `config.py` is where you define how sensitive the gesture detection should be, how responsive the cursor should feel, and how the server should behave. Think of it as the dashboard of the entire system.

- **Gesture Sensitivity**: `CURSOR_SENSITIVITY = 1.5` means every 1mm your hand moves translates to 1.5 pixels of cursor movement. Lower = more precise but requires bigger movements. Higher = twitchy but more responsive.
- **Pinch Threshold**: `PINCH_DISTANCE_THRESHOLD_MM = 30` means your thumb and finger need to be within 30mm for the system to register a pinch. This prevents false positives when your hands are just passing by each other.
- **Confidence Settings**: MediaPipe reports how confident it is that it actually detected a hand. If the confidence drops below the threshold, the system ignores that frame. Higher threshold = more reliable but might miss hands.
- **Port & Host**: Flask runs on `localhost:5000` by default, but the config makes it easy to change.

All of these values are tuning knobs you'll adjust as you test with real hands and gestures.

#### `app.py` - The Main Server

This is the Flask application—the central nervous system. It does several things:

1. **Serves the Phone UI**: When you scan the QR code, Flask serves the `index.html` page to your phone browser.
2. **Hosts the WebSocket Endpoint**: The phone and laptop use a WebSocket to exchange WebRTC signaling messages (the SDP offer/answer and ICE candidates that establish the peer-to-peer connection).
3. **Orchestrates Components**: It creates instances of the VideoProcessor, GestureRecognizer, and OSController, and wires them together so they can communicate.

The file is mostly skeleton code right now—the TODO comments mark where you need to initialize these components and connect them together. When a phone connects via WebSocket, the server will receive WebRTC signaling messages and hand them off to the appropriate handler.

#### `signaling.py` - The WebRTC Gatekeeper

WebRTC is powerful but complex. Before the phone can send video to the laptop, they need to negotiate a connection through a process called SDP (Session Description Protocol) handshaking. This file handles that dance.

When you call `create_peer_connection()`, you're creating the actual WebRTC connection object on the laptop side. When `handle_sdp_offer()` is called, the phone has said "here's my media setup, do you accept?" and the laptop replies with its own setup in `handle_sdp_offer()`. ICE candidates are network addresses that the two devices can try to communicate through.

For a LAN-only system, you don't need STUN or TURN servers—the devices can reach each other directly.

#### `video_processor.py` - The Eye

This module receives raw video frames from the WebRTC stream and extracts hand information from them. It's a thin wrapper around MediaPipe Hands, a pre-trained neural network that recognizes hands and identifies 21 key points on each hand (wrist, palm, each knuckle, each fingertip).

The `Hand` class is a data structure—it holds 21 landmark coordinates per hand plus metadata like which hand it is (left or right) and how confident MediaPipe is about the detection.

The `process_frame()` method is the main workhorse: it takes a raw video frame, runs it through MediaPipe, and returns a list of `Hand` objects. The `draw_landmarks()` method is purely for debugging—it annotates the frame with circles at landmark positions and lines connecting them, so you can visually see what the system "sees".

Key insight: **This module does computer vision, not gesture logic.** It just answers "where are the hands?" and leaves the "what are they doing?" question to the gesture recognizer.

#### `gesture_recognizer.py` - The Brain

Once you know where the hands are, you need to interpret what the hand is *doing*. That's the job of this module.

The `GestureRecognizer` is a state machine. It processes each frame's hand landmarks and emits `GestureEvent` objects when it detects meaningful gestures. For example:

- If the thumb and index finger are within the pinch threshold and stay there for a few frames (the "stability frames"), it emits a `PINCH_INDEX` start event.
- If the hand is moving while not pinched, it emits `OPEN_HAND_MOVE` events with the hand position.
- If the hand closes into a fist, it emits a `CLUTCH` event to pause cursor tracking.

The key design here is **callbacks**. The gesture recognizer doesn't know (and doesn't care) what happens with the gestures it detects. Instead, it lets external code register callback functions: "when you detect a gesture, call my function." This decouples gesture recognition from OS control—you could, in theory, route gestures to different handlers (logging, visualization, OS control, etc.) without changing the recognizer.

The helper methods like `_calculate_pinch_distance()`, `_is_pinched()`, and `_is_hand_closed()` are the logic that interprets the raw landmarks. They do things like calculate distances between fingers and check if distances are below thresholds.

#### `controller.py` - The Hands

The OS controller is where the rubber meets the road. It receives `GestureEvent` objects from the gesture recognizer and translates them into actual OS actions.

- `move_cursor_relative(dx, dy)` adds an offset to the current cursor position and updates it. This is "trackpad mode"—the system doesn't map hand position directly to screen coordinates; instead, it tracks *how much* the hand moved since the last frame and applies that delta to the cursor.
- `left_click()` and `right_click()` perform clicks using `pydirectinput`, a library that simulates mouse input in a way that works across games and full-screen apps (unlike `pyautogui`, which is more fragile).
- `drag_to()` performs a click-drag operation—useful for both selecting text and implementing the click-and-drag gesture.
- Window operations (`get_window_at_cursor()`, `drag_window()`, `resize_window()`, `is_point_in_title_bar()`) use the `pywin32` library to interact with the Windows API directly.

The `_handle_*` methods are event handlers that receive gestures and decide what to do with them. For example, `_handle_index_pinch()` might say "if the pinch is on a window title bar, drag the window; otherwise, perform a click or drag operation."

The `WindowRect` class is a simple data structure representing a window's bounding box (left, top, right, bottom coordinates). It includes helper methods like `contains_point()` to check if a click happened inside the window.

#### `utils/network_utils.py` - The Network Scout

This utility module helps the server discover its own IP address on the local network so the phone can reach it. When the server starts, it needs to generate a QR code that encodes something like `http://192.168.1.100:5000` so your phone can scan it and connect.

`get_local_ip()` is the main function—it figures out what the laptop's IP is on the WiFi network. This is trickier than it sounds because a laptop can have multiple network interfaces (Ethernet, WiFi, virtual networks, etc.). The trick is to create a dummy connection to a known address and see what interface gets used.

The other functions (`get_wifi_networks()`, `test_network_connectivity()`) are helpers for debugging network issues.

#### `utils/qr_generator.py` - The QR Encoder

This tiny utility generates a QR code from a URL and saves it as a PNG, plus prints an ASCII art version to the terminal. QR codes are a user-friendly way to pair the phone and laptop without typing an IP address into your phone—just scan and go.

---

### Frontend Directory: `frontend/`

The frontend is minimal—just a single HTML page that runs in your phone's browser.

#### `templates/index.html` - The Phone UI

This is the page your phone displays. It has:

- **A video element** showing the camera feed
- **Status indicators** showing whether the laptop connection is active
- **Camera selector** to switch between front and rear cameras
- **Gesture reference** showing what each gesture does
- **Debug panel** displaying real-time log messages from the client

The UI is intentionally minimal and clean. The philosophy is: you're going to be looking at your hands (not the screen) while using this system, so the UI should get out of the way.

#### `static/style.css` - The Styling

Modern, responsive design with:

- A purple gradient background (Tony Stark aesthetic!)
- A white card-style container
- Status indicators with animated pulsing dots
- Responsive layout that works on phones from 320px to 600px wide
- A dark debug panel at the bottom with a terminal-like feel

The key design insight: the video feeds takes up most of the screen, and all the UI elements are compact and unobtrusive.

#### `static/script.js` - The Browser-Side WebRTC Logic

This is where the phone's side of the WebRTC connection lives. The key methods are:

- **`connectToServer()`**: Establishes a WebSocket connection to the Flask server. This WebSocket is *purely for signaling*—it carries the SDP messages needed to set up the actual video stream, but not the video itself.
- **`setupWebRTC()`**: Creates an `RTCPeerConnection`, requests the camera via `getUserMedia()`, adds the camera track to the connection, creates an SDP offer, and sends it to the server. Once the server responds with an SDP answer, the connection is established and video starts flowing.
- **`getMediaStream()`**: Calls the browser's `getUserMedia()` API to access the phone camera. This is where the browser prompts the user for permission.
- **`switchCamera()`**: Switches between front and rear cameras by getting a new media stream with a different facing mode.

The class also has utility methods like `log()` to update the debug panel and `setStatus()` to update the connection indicator.

Key insight: **The phone doesn't do any of the heavy lifting.** It just captures video and sends it. All the hand tracking, gesture recognition, and OS control happens on the laptop.

---

### Tests Directory: `tests/`

Two test files with placeholder tests:

#### `test_gesture_recognizer.py`

Tests for the gesture recognition logic. When you implement the gesture recognizer, you'll fill in these tests with mock hand landmarks and verify that the recognizer correctly detects pinches, movements, and clutches. Tests should cover:

- Pinch detection thresholds
- State transitions (pinch start → move → end)
- Simultaneous gestures from multiple hands
- Edge cases (occlusion, unstable landmarks, etc.)

#### `test_controller.py`

Tests for OS control. You'll mock the `pydirectinput` and `win32gui` APIs so you can test cursor movement, clicks, window operations, etc. without actually moving your real cursor during testing.

---

### Configuration & Documentation

#### `.env.example` - Environment Variables Template

Copy this to `.env` to override config values via environment variables. This is useful for deployment or sharing different configurations.

#### `pytest.ini` - Test Configuration

Tells pytest how to discover and run tests. Defines test markers (like `@pytest.mark.integration`) to organize different types of tests.

#### `requirements.txt` - Python Dependencies

Lists all the external libraries you need to install. The key ones are:

- **Flask & Flask-SocketIO**: Web server and WebSocket support
- **aiortc**: Python implementation of WebRTC
- **mediapipe**: Google's hand-tracking library
- **pydirectinput**: Cross-app mouse simulation
- **pywin32**: Windows API access
- **qrcode & Pillow**: QR code generation

#### `run.py` - Entry Point

Simple script that starts the Flask server. Just `python run.py` and you're good to go.

#### Documentation Files

- **README.md**: User-facing overview, quick start, gesture guide
- **DEVELOPMENT.md**: Developer setup, debugging tips, contribution guide
- **ARCHITECTURE.md**: Deep technical architecture, data flow, state machines
- **TODO.md** (new): Detailed checklist of every function to implement
- **handoff.md** (this file): Essay-format project overview

---

## How Everything Connects: The Complete Flow

Let's trace through what happens from the moment you scan the QR code to the moment the cursor moves:

### 1. **Startup Phase**
- You run `python run.py`
- Flask server starts on `localhost:5000`
- Server generates a QR code encoding the local IP (e.g., `http://192.168.1.100:5000`)
- You scan the QR code with your phone

### 2. **Connection Phase**
- Phone browser opens the Flask URL
- Flask serves `index.html` to the phone
- JavaScript runs in the browser and connects to Flask's WebSocket endpoint
- Phone requests camera access via `getUserMedia()` (browser asks for permission)
- Camera feed appears on phone screen

### 3. **WebRTC Handshake Phase**
- Phone JavaScript creates an `RTCPeerConnection` and adds the camera track
- Phone generates an SDP offer describing its media
- Phone sends SDP offer to laptop via WebSocket
- Laptop's Flask server receives the offer and passes it to `WebRTCSignaling`
- `WebRTCSignaling` creates an `RTCPeerConnection` on the laptop side, sets the remote description, creates an SDP answer, and sets that as the local description
- Laptop sends SDP answer back to phone via WebSocket
- Both phone and laptop exchange ICE candidates (network addresses to connect through)
- WebRTC connection is established—video now flows directly peer-to-peer

### 4. **Video Processing Phase**
- Laptop's aiortc library receives video frames from the phone in real-time
- Each frame is passed to `VideoProcessor.process_frame()`
- MediaPipe analyzes the frame and identifies hands + 21 landmarks per hand
- `VideoProcessor` returns a list of `Hand` objects
- Video frame is also drawn with landmark annotations (for debug) but not sent back to phone

### 5. **Gesture Recognition Phase**
- `Hand` objects are passed to `GestureRecognizer.process_hands()`
- Gesture recognizer analyzes landmarks and detects gestures
- For example: if thumb and index are within 30mm, it generates a `PINCH_INDEX` event
- If hand is moving and open, it generates an `OPEN_HAND_MOVE` event with the hand's current position
- Gesture recognizer calls registered callbacks (handlers) with each event

### 6. **OS Control Phase**
- `OSController` receives gesture events via callbacks
- `OSController._handle_hand_movement()` receives movement events and calls `move_cursor_relative(dx, dy)`
- Cursor position is updated via `pydirectinput.moveTo()`
- When you pinch, `_handle_index_pinch()` calls `left_click()`
- When you pinch on a window title bar, it calls `drag_window()` to move the window
- All OS API calls go through `pydirectinput` and `pywin32`

### 7. **Repeat**
- Every frame (typically 30-60 FPS depending on your WiFi and laptop), steps 4-6 repeat
- Result: smooth, real-time cursor control synchronized with your hand movements

---

## Key Design Decisions & Philosophy

### 1. **Modular Architecture**
Each module has a single responsibility: video processing does vision, gesture recognizer does logic, controller does OS actions. This makes testing easier and lets you develop/debug each piece independently.

### 2. **Callback Pattern**
The gesture recognizer doesn't know or care what happens with gestures. It just detects them and calls registered callbacks. This decouples layers and makes the system extensible (you could log gestures, visualize them, or send them to multiple handlers).

### 3. **Relative Cursor Mapping**
Instead of mapping hand position directly to screen coordinates (which would feel weird and require calibration), the system tracks *hand movement* (deltas) and applies those to the cursor. This is how physical trackpads work and feels much more natural.

### 4. **LAN-Only, Cloud-Free**
No internet required, no privacy concerns, no latency from cloud hops. Everything stays on your local WiFi network.

### 5. **No App Install**
The phone side is pure browser-based. No App Store, no permissions, no installation headaches.

### 6. **Graceful Degradation**
If the system can't control a specific window (e.g., UAC-elevated admin window), it logs the issue and continues working for other windows rather than crashing.

---

## Development Strategy

### Start Small
Begin with Phase 1: get video flowing from phone to laptop and display it. This tests your WebRTC setup, networking, and server infrastructure. Don't worry about gestures yet.

### Test Incrementally
After each phase, test with real hands and real gestures. Gesture detection thresholds need real-world tuning. Paper calculations rarely match reality.

### Profile Latency
Latency is critical. If cursor movement lags, the whole system feels broken. Profile each stage (frame capture, encoding, transmission, decoding, inference, gesture logic, OS control) separately.

### Leverage Existing TODOs
The codebase is littered with `# TODO` comments marking exactly what needs to be implemented. Follow them in order (Phases 1-8) for optimal progress.

### Focus on Core Gestures First
Get pinch and movement working before diving into two-hand gestures, clutch mechanisms, or window resizing. Basic cursor control is the MVP.

---

## File Map Quick Reference

```
HandyMouseCam/
├── backend/
│   ├── app.py                   ← Flask server, WebSocket handlers
│   ├── config.py                ← All tuning parameters
│   ├── signaling.py             ← WebRTC peer connection
│   ├── video_processor.py       ← MediaPipe hand tracking
│   ├── gesture_recognizer.py    ← Gesture detection state machine
│   ├── controller.py            ← OS-level mouse/window control
│   └── utils/
│       ├── network_utils.py     ← IP detection
│       └── qr_generator.py      ← QR code generation
├── frontend/
│   ├── templates/
│   │   └── index.html           ← Phone UI
│   └── static/
│       ├── style.css            ← Styling
│       └── script.js            ← WebRTC client + camera logic
├── tests/
│   ├── test_gesture_recognizer.py
│   └── test_controller.py
├── run.py                       ← Start here: python run.py
├── config.py                    ← Central configuration
├── requirements.txt             ← Python dependencies
├── README.md                    ← User documentation
├── DEVELOPMENT.md               ← Developer guide
├── ARCHITECTURE.md              ← Technical deep dive
├── TODO.md                      ← Implementation checklist
└── handoff.md                   ← This file
```

---

## Next Steps for You

1. **Read through the code** in order: config.py → app.py → signaling.py → video_processor.py → gesture_recognizer.py → controller.py
2. **Understand the data flow** by reading ARCHITECTURE.md
3. **Consult TODO.md** to see every function that needs implementing
4. **Start with Phase 1**: Get WebRTC video flowing. This is foundational and unblocks everything else.
5. **Test as you go**: Don't implement all of Phase 3 before testing Phase 2.
6. **Tune empirically**: Gesture thresholds need real-world calibration with actual hands.

---

## Questions to Ask Yourself While Implementing

- **Does this module have a single, clear responsibility?** (If not, it might need to be split.)
- **Can this module be tested in isolation?** (If not, its dependencies might be too tight.)
- **What happens if this fails?** (Will the whole system crash or just degrade gracefully?)
- **How will I debug this when it doesn't work?** (Is there enough logging? Can I visualize the data?)

---

Good luck! You're building a genuinely cool system. The heavy lifting (WebRTC, MediaPipe, pywin32) is already solved by open-source libraries. Your job is to glue them together elegantly.

May your gestures be smooth and your latency be low. 🎮✨

---

**Document Version:** 1.0  
**Created:** 2026-09-01  
**Status:** Ready for implementation
