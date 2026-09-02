# Project Document: Hand Gesture Mouse Control ("Stark Display")

## 1. Vision

A phone-camera-fed, laptop-processed hand-tracking system that replaces (or augments) the mouse with mid-air gestures — pinch to click, grab-and-drag to move things, two-hand stretch to resize windows. Long-term aspiration is a Tony Stark–style control surface for CAD, coding, and window management. This document scopes a realistic, buildable MVP and lays out the path toward that longer-term vision.

## 2. Goals & Success Criteria

**MVP is successful if:**
- You can open a page on your phone, point the camera at your hands, and see the laptop cursor move in response to your right hand — reliably, at usable (not laggy-feeling) latency.
- Right-hand pinch (thumb+index) performs left-click/drag; right-hand pinch (thumb+middle) performs right-click.
- You can grab a window's title bar and drag it, and use a two-hand pinch-stretch gesture to resize a window.
- The system runs entirely over your local WiFi with no cloud dependency.

**Explicitly not required for MVP success:** sub-20ms latency, CAD-specific gestures (rotate/zoom/orbit), multi-monitor support, gesture customization UI.

## 3. MVP Scope

| In scope for MVP | Out of scope for MVP (future work) |
|---|---|
| Phone camera capture + WebRTC stream to laptop | Multi-monitor cursor handoff |
| Both-hand landmark tracking (MediaPipe Hands, Python) | CAD-specific gestures (orbit/zoom/pan for 3D viewports) |
| Relative/trackpad-style cursor control | Voice+gesture combo commands |
| Right-hand pinch gestures: left-click, right-click, click-drag | Gesture customization UI / user-trainable gestures |
| Window drag (grab title bar) | Non-Windows support |
| Two-hand pinch-stretch window resize | Multi-user / multi-hand-set support |
| Local WiFi pairing via QR code | Remote access over the internet |

## 4. System Architecture

### 4.1 Overview

```
┌─────────────────┐        WebRTC (video)         ┌──────────────────────────┐
│   Phone Browser   │ ─────────────────────────▶  │      Laptop (Flask)       │
│                    │                              │                            │
│  getUserMedia()    │        WebSocket             │  aiortc (WebRTC peer)      │
│  RTCPeerConnection │ ◀────────────────────────▶  │  Flask/Flask-SocketIO      │
│  (video only)      │      (SDP/ICE signaling)     │  (signaling server)        │
└─────────────────┘                                │                            │
                                                      │  Frame → MediaPipe Hands  │
                                                      │  (both hands, 21 pts each)│
                                                      │            │              │
                                                      │            ▼              │
                                                      │  Gesture Recognizer        │
                                                      │  (pinch state machine)     │
                                                      │            │              │
                                                      │            ▼              │
                                                      │  Cursor/Window Controller  │
                                                      │  (pydirectinput + pywin32) │
                                                      └──────────────────────────┘
```

### 4.2 Components

**Phone (frontend, HTML/CSS/JS):**
- Single page, served by Flask, opened via QR code that encodes `http://<laptop-local-ip>:<port>`.
- Uses `getUserMedia()` to access the rear or front camera.
- Opens an `RTCPeerConnection`, sends the camera track to the laptop.
- Minimal UI: connection status, maybe a "which camera" toggle, a big "connected" indicator so you're not staring at your phone while your hands are near the monitor.

**Laptop (backend, Flask/Python):**
- Flask serves the phone-facing page and hosts a WebSocket endpoint (Flask-SocketIO or plain `websockets`) for WebRTC signaling (SDP offer/answer, ICE candidates).
- `aiortc` handles the actual WebRTC media connection and hands you decoded video frames as numpy arrays.
- Each frame is passed to **MediaPipe Hands** (`max_num_hands=2`) to get 21 landmarks per hand, per frame.
- A **gesture recognizer** module turns raw landmarks into semantic events: `pinch_start`, `pinch_move`, `pinch_end`, per hand, per pinch type (index/middle).
- A **controller** module translates gesture events into actual OS actions.

**Why WebRTC instead of simple frame POSTs:** you specifically want lower latency over simplicity, which is the right call here — a snappy cursor is the difference between this feeling magical and feeling gimmicky. The tradeoff is signaling complexity (SDP/ICE exchange), which is why the architecture above keeps a WebSocket around purely for that handshake.

## 5. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Phone frontend | HTML/CSS/JS, `getUserMedia`, `RTCPeerConnection` | No app install; works in any modern mobile browser |
| Backend web server | Flask | Matches your preference; simple to serve the page + host signaling |
| Signaling | Flask-SocketIO (or raw `websockets`) | Carries SDP/ICE messages between phone and laptop |
| Media transport | `aiortc` (Python WebRTC) | Only mature Python-side WebRTC implementation; gives you raw video frames |
| Hand tracking | MediaPipe Hands (Python, `max_num_hands=2`) | Runs locally on laptop CPU, no cloud calls, real-time capable |
| Mouse control | `pydirectinput` (preferred) or `ctypes` + `SendInput` | More reliable than `pyautogui` across apps/games on Windows since it uses DirectX scan codes |
| Window management | `pywin32` (`win32gui`, `win32con`, `win32api`) | Needed to find window-under-cursor, get/set window rects for drag & resize |
| Pairing | QR code (generate with `qrcode` Python lib) pointing at laptop's local IP | Avoids typing an IP into your phone every session |

## 6. Gesture Mapping Spec

| Gesture | Hand(s) | Action |
|---|---|---|
| Thumb + index pinch | Right hand | Left click (tap) / left-click-drag (hold + move) |
| Thumb + middle pinch | Right hand | Right click |
| Open hand, moving | Right hand | Move cursor (relative/trackpad-style) |
| Pinch-hold on window title bar, then move hand | Right hand | Drag the window |
| Simultaneous pinch-hold, both hands, then move hands apart/together | Both hands | Resize window (stretch/shrink along the axis between the two pinch points) |
| Hand leaves frame / hand closes into a fist | Right hand | "Clutch" — pauses cursor tracking (like lifting your finger off a trackpad) so you can reposition your physical hand without dragging the cursor across the screen |

Left hand's only MVP role is the second pinch point in the two-hand resize gesture. Everything else (scroll, modifier keys, etc.) is future work — see Section 12.

## 7. Cursor Mapping: Relative/Trackpad Mode

You chose relative mapping over absolute, which matters for a few implementation details:

- **What's tracked:** the right hand's centroid (average of wrist + palm landmarks, not just the fingertip, for stability) each frame.
- **Delta, not position:** each frame computes `Δ = current_centroid - previous_centroid`, scaled by a sensitivity constant, and added to the *current* OS cursor position (not a raw remap of camera coordinates to screen coordinates).
- **Clutch mechanism:** like lifting your finger off a physical trackpad, you need a way to reposition your hand without moving the cursor. Options:
  - Closing into a fist pauses tracking until reopened.
  - Hand leaving the camera frame pauses tracking.
  - (Simplest first pass: just always track when the hand is visible and open — see how it feels before adding the clutch gesture; this is a good MVP-internal decision to make empirically.)
- **Sensitivity tuning:** will need a scaling constant (physical hand cm → screen pixels) that you'll want to expose as a config value to tune to taste, since "1cm of hand movement = X pixels" will feel very different at CAD-precision vs. general window management.

## 8. Window Drag & Resize Logic

**Drag:** on `pinch_start` (right hand, thumb+index), use `win32gui.WindowFromPoint()` at the current cursor position to find the window under the cursor. If that point falls within the window's title bar region, treat this as a drag: on `pinch_move`, call `SetWindowPos` to move the window by the same delta the cursor is moving. On `pinch_end`, drag ends.

**Resize:** on simultaneous pinch-hold from both hands, record the initial distance and angle between the two pinch points and the initial window rect (of whichever window is under one of the pinch points, or the currently focused window). On subsequent frames, compute the change in distance between the two points and apply it proportionally to the window's width/height via `SetWindowPos`, anchored at the corner nearest the hand that moved least (so it feels like stretching from a fixed corner rather than the window jumping around).

## 9. Network & Pairing

- Flask serves on `0.0.0.0:<port>` so it's reachable from other devices on the same WiFi network.
- On laptop startup, generate a QR code encoding `http://<laptop-local-ip>:<port>` and print/display it — scan once with your phone, no typing IPs.
- No STUN/TURN server needed since both devices are on the same LAN; ICE candidates should resolve directly.

## 10. Development Phases

| Phase | Deliverable | Done when... |
|---|---|---|
| 0 | Project skeleton | Flask serves a phone page; phone camera preview shows on the phone screen |
| 1 | Video pipeline | Phone camera stream arrives on laptop via WebRTC and you can display/save a frame to prove frames are being received |
| 2 | Hand tracking | MediaPipe Hands runs on incoming frames; both hands' landmarks are detected and drawn on a debug view |
| 3 | Cursor control | Right hand open-palm movement moves the OS cursor (relative mapping, no clutch yet) |
| 4 | Click gestures | Thumb+index = left click, thumb+middle = right click, both reliably distinguishable |
| 5 | Drag | Click-drag works for general dragging (e.g., selecting text, dragging icons) |
| 6 | Window drag | Pinch-hold on a title bar moves the window |
| 7 | Two-hand resize | Both-hand pinch-stretch resizes the focused/under-cursor window |
| 8 | Polish | Clutch mechanism, sensitivity tuning, reconnect handling if phone/laptop connection drops |

Recommend building and testing each phase against real use before moving to the next — gesture recognition thresholds (how close is "pinched"?) will need real-world tuning that's hard to predict on paper.

## 11. Risks & Open Questions

- **Latency stacking:** camera capture → WebRTC encode/transmit → decode → MediaPipe inference → gesture logic → OS mouse event, all need to land well under ~50ms combined to feel responsive. Worth profiling each stage separately in Phase 1–2 rather than discovering a bottleneck at the end.
- **Occlusion & hand crossing:** MediaPipe can lose track or swap left/right hand identity when hands overlap or one occludes the other — relevant for the two-hand resize gesture specifically.
- **False-positive pinches:** thumb+index vs thumb+middle need a comfortable, reliable distance threshold that doesn't misfire during normal open-hand movement.
- **Windows permissions:** `SendInput`-based mouse control can be blocked by some elevated/admin apps (UAC-elevated windows won't receive simulated input from a non-elevated process) — may need to run the controller as admin, or accept that gesture control won't reach elevated apps.
- **Camera placement:** mounting the camera under the monitor gives good hand visibility but a steep upward angle — worth testing how well MediaPipe handles that viewing angle vs. a more front-on angle, since its training data skews toward front-facing hands.

## 12. Future / Stretch Goals

- CAD-specific gestures: two-hand pinch-rotate (orbit), two-hand pinch-zoom distinct from window-resize (context-dependent on active app)
- Left-hand modifier gestures (e.g., left-hand pinch = scroll mode, or held modifier for a right-hand action)
- On-screen visual feedback (a small overlay showing detected hand state, useful for debugging and for the "Stark HUD" feel)
- Gesture customization/config UI
- Multi-monitor cursor handoff
