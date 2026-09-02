# HandyMouseCam - Architecture Overview

## System Diagram

```
┌──────────────────────────────────────┐
│         PHONE (Mobile Browser)       │
│                                      │
│  ┌──────────────────────────────┐   │
│  │   getUserMedia() Stream      │   │
│  │   (Camera Feed)              │   │
│  └──────────────┬───────────────┘   │
│                 │                    │
│  ┌──────────────▼───────────────┐   │
│  │  RTCPeerConnection           │   │
│  │  - WebRTC media encoding     │   │
│  │  - Sends video frames        │   │
│  └──────────────┬───────────────┘   │
│                 │                    │
│  ┌──────────────▼───────────────┐   │
│  │  WebSocket (SocketIO)        │   │
│  │  - SDP Offer/Answer          │   │
│  │  - ICE Candidates            │   │
│  └──────────────────────────────┘   │
└──────────────────┬───────────────────┘
                   │
              (Network Bridge)
          ┌────────┴────────┐
          │  Local WiFi     │
          │  (same subnet)  │
          └────────┬────────┘
                   │
┌──────────────────▼───────────────────────┐
│   LAPTOP (Flask Server + Backend)        │
│                                          │
│  ┌─────────────────────────────────┐   │
│  │  Flask (Web Server)             │   │
│  │  - Serves phone UI              │   │
│  │  - /socket.io endpoint          │   │
│  └─────────────────────────────────┘   │
│                                          │
│  ┌─────────────────────────────────┐   │
│  │  WebSocket Handler              │   │
│  │  - Receives SDP offer           │   │
│  │  - Sends SDP answer             │   │
│  │  - Exchanges ICE candidates     │   │
│  └──────────────────┬──────────────┘   │
│                     │                    │
│  ┌──────────────────▼──────────────┐   │
│  │  WebRTCSignaling (aiortc)       │   │
│  │  - RTCPeerConnection            │   │
│  │  - Receives video frames        │   │
│  └──────────────────┬──────────────┘   │
│                     │                    │
│  ┌──────────────────▼──────────────┐   │
│  │  VideoProcessor                 │   │
│  │  - Frame -> RGB conversion      │   │
│  │  - MediaPipe Hands inference    │   │
│  │  - Extract 21 landmarks/hand    │   │
│  │  - Landmark visualization       │   │
│  └──────────────────┬──────────────┘   │
│                     │                    │
│  ┌──────────────────▼──────────────┐   │
│  │  GestureRecognizer              │   │
│  │  - Pinch detection (Index/Mid)  │   │
│  │  - Hand movement tracking       │   │
│  │  - Clutch detection (Fist)      │   │
│  │  - State machine logic          │   │
│  │  - Generate GestureEvents       │   │
│  └──────────────────┬──────────────┘   │
│                     │                    │
│  ┌──────────────────▼──────────────┐   │
│  │  OSController                   │   │
│  │  - Cursor movement (relative)   │   │
│  │  - Left/Right click             │   │
│  │  - Click-drag                   │   │
│  │  - Window drag/resize           │   │
│  │  - pywin32 & pydirectinput      │   │
│  └──────────────────┬──────────────┘   │
│                     │                    │
│                     ▼                    │
│            ┌─────────────────┐          │
│            │ OS Control APIs │          │
│            │  - Mouse input  │          │
│            │  - Window mgmt  │          │
│            └─────────────────┘          │
│                                          │
└──────────────────────────────────────────┘
```

## Data Flow

### Frame to Cursor Movement

```
Camera Frame (1280x960 RGB)
    ↓
[VideoProcessor]
    ↓
21 Landmarks per hand × 2 hands
    ↓
[GestureRecognizer]
    ↓
GestureEvent(OPEN_HAND_MOVE, Right, position=(x,y))
    ↓
[OSController]
    ↓
move_cursor_relative(dx, dy)
    ↓
Windows OS
    ↓
Cursor Position Updated
```

### Pinch Detection to Click

```
Hand Landmarks (21 pts each)
    ↓
[GestureRecognizer]
  Calculate distances:
  - Thumb to Index: 25mm → PINCH_INDEX
  - Thumb to Middle: 28mm → PINCH_MIDDLE
    ↓
GestureEvent(PINCH_INDEX, Right, ...) [pinch start]
GestureEvent(PINCH_INDEX, Right, ...) [pinch move]
GestureEvent(PINCH_INDEX, Right, ...) [pinch end]
    ↓
[OSController]
  - First event: left_click()
  - Move events: drag_to(x, y)
  - End event: release click
    ↓
Windows OS
    ↓
Left mouse button pressed/released
```

## Module Responsibilities

### VideoProcessor
**Inputs:** Raw video frames from WebRTC  
**Outputs:** List of Hand objects with 21 landmarks each  
**Key Methods:**
- `process_frame(frame)` → List[Hand]
- `draw_landmarks(frame, hands)` → annotated frame

### GestureRecognizer
**Inputs:** List of Hand objects per frame  
**Outputs:** GestureEvent stream  
**Key Methods:**
- `process_hands(hands, timestamp)` → List[GestureEvent]
- `register_gesture_callback(callback)`

### OSController
**Inputs:** GestureEvent stream  
**Outputs:** OS-level actions  
**Key Methods:**
- `handle_gesture(event)`
- `move_cursor_relative(dx, dy)`
- `left_click()`, `right_click()`
- `drag_window(hwnd, x, y)`

## Configuration Hierarchy

```
Hardcoded Defaults (backend/config.py)
    ↓
Environment Variables (.env)
    ↓
Runtime Adjustments (future UI)
```

## Latency Budget

Target: <100ms for responsive cursor feel

| Stage | Typical | Budget |
|-------|---------|--------|
| Camera capture + encode | 10ms | 15ms |
| Network transmission | 10-30ms | 40ms |
| Decode + MediaPipe | 20-50ms | 30ms |
| Gesture recognition | 2-5ms | 5ms |
| OS control | 5-15ms | 10ms |
| **Total** | **47-110ms** | **100ms** |

## WebRTC Signaling Flow

```
Phone                              Laptop
 │                                  │
 ├─(1) getUserMedia()───────────────┤
 │                                  │
 ├─(2) createOffer()────────────────┤
 │                                  │
 ├─(3) SDP Offer (via SocketIO)────>│
 │                                  ├─(4) setRemoteDescription()
 │                                  │
 │                                  ├─(5) createAnswer()
 │                                  │
 │<─────(6) SDP Answer (via SocketIO)─
 │
 ├─(7) setRemoteDescription()───────┤
 │                                  │
 ├─────ICE Candidates (exchange)───>│
 │<─────────────────────────────────┤
 │
 ├─(8) RTCPeerConnection ready─────>│
 │                                  │
 └───(9) Video frames flowing.....→ │
```

## State Machines

### Pinch State Machine

```
       No Pinch
          │
          ↓
    ┌──────────┐
    │ Check:   │
    │ Thumb-   │
    │ Finger   │
    │ Distance │
    └────┬─────┘
         │
    Distance < Threshold?
      YES│  NO│
         │    └──────────────→ No Pinch
         │                       ↑
         ↓                       │
    Pinch Detected          Unpin
    (frame N)               (reset)
         │                       │
         └───────────────────────┘
         │
    Stability Frames ≥ N?
      YES│  NO│
         │    └──→ No Pinch (unstable)
         │
         ↓
    Pinch Start Event
         │
         ├─→ Pinch Move Events (while stable)
         │
         ↓
    Distance ≥ Threshold?
      NO│  YES│
        │     └──→ Stay Pinched
        │
        ↓
    Pinch End Event
         │
         ↓
    No Pinch (reset state)
```

### Hand Visibility State

```
        Unknown
           │
           ↓
    ┌──────────────┐
    │ Hand Visible?│
    └──┬───────┬───┘
       │ YES   │ NO
       ↓       ↓
    Visible  Invisible
       │       (Clutch)
       │       │
       └───┬───┘
           │
    Send Gesture Events
           │
           ↓
    Continue Tracking
```

## Future Extensions

### Phase 2 (Gestures)
- Left-hand scroll modifier
- Two-hand rotate gesture (CAD)
- Keyboard shortcut combinations

### Phase 3 (UI/UX)
- On-screen gesture visualization (HUD)
- Gesture customization panel
- Sensitivity tuning UI

### Phase 4 (Advanced)
- Multi-monitor support
- Cloud-based gesture learning
- Cross-platform (macOS, Linux)
- Remote access over internet (with TURN)

---

This architecture prioritizes:
- **Latency:** Direct frame processing, no queuing
- **Reliability:** Local processing, no cloud dependency
- **Extensibility:** Modular design for adding gestures
- **Debuggability:** Visualization at each stage
