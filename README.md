# HandyMouseCam - "Stark Display"

**Hand Gesture Mouse Control System**

A phone-camera-fed, laptop-processed hand-tracking system that replaces (or augments) your mouse with mid-air gestures. Control your cursor with open-hand movements, pinch to click, and use two-hand stretches to resize windows — all over your local WiFi network.

## 🎯 MVP Vision

- ✅ Point phone camera at hands, see laptop cursor move in real-time
- ✅ Thumb + index pinch = left-click / click-drag
- ✅ Thumb + middle pinch = right-click
- ✅ Grab-and-drag windows by their title bars
- ✅ Two-hand pinch-stretch to resize windows
- ✅ Local WiFi only (no cloud dependency)

## 📁 Project Structure

```
HandyMouseCam/
├── backend/
│   ├── app.py                 # Flask app entry point
│   ├── config.py              # Configuration constants
│   ├── signaling.py           # WebRTC signaling (SDP/ICE)
│   ├── video_processor.py     # MediaPipe Hands integration
│   ├── gesture_recognizer.py  # Gesture detection state machine
│   ├── controller.py          # OS control (mouse, windows)
│   ├── requirements.txt       # Python dependencies
│   └── utils/
│       ├── __init__.py
│       ├── network_utils.py   # IP detection, connectivity
│       └── qr_generator.py    # QR code pairing
├── frontend/
│   ├── templates/
│   │   └── index.html         # Phone UI
│   └── static/
│       ├── style.css          # Styling
│       └── script.js          # WebRTC client logic
├── tests/
│   ├── test_gesture_recognizer.py
│   └── test_controller.py
├── run.py                     # Main entry point
├── README.md
└── LICENSE
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip
- Modern browser on phone with WebRTC support
- Same WiFi network for both phone and laptop

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/HandyMouseCam.git
   cd HandyMouseCam
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Run the server:**
   ```bash
   python run.py
   ```

5. **Scan QR code:**
   - A QR code will appear in the terminal
   - Scan it with your phone camera
   - Opens `http://<laptop-ip>:5000`

6. **Position your hands:**
   - Allow camera access when prompted
   - Place hands in front of phone camera
   - Cursor on laptop should start tracking your right hand

## 🎮 Gesture Controls

| Gesture | Action |
|---------|--------|
| **Open hand, moving** | Move cursor (trackpad-style) |
| **Thumb + index pinch** | Left click or click-drag |
| **Thumb + middle pinch** | Right click |
| **Pinch on window title bar + move** | Drag window |
| **Both hands pinching, spread/squeeze** | Resize window |
| **Fist or hand out of frame** | Clutch (pause cursor tracking) |

## 🔧 Configuration

Edit `backend/config.py` to tune behavior:

```python
CURSOR_SENSITIVITY = 1.5        # Pixels per mm of hand movement
PINCH_DISTANCE_THRESHOLD_MM = 30  # Distance to trigger pinch
HAND_DETECTION_CONFIDENCE = 0.7   # MediaPipe detection confidence
FLASK_PORT = 5000                # Server port
```

## 📋 Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 | ✨ Not Started | Flask setup + phone page serving |
| 1 | ✨ Not Started | Video pipeline (WebRTC streaming) |
| 2 | ✨ Not Started | Hand tracking (MediaPipe) |
| 3 | ✨ Not Started | Cursor control (relative mapping) |
| 4 | ✨ Not Started | Click gestures (pinch detection) |
| 5 | ✨ Not Started | Drag operations |
| 6 | ✨ Not Started | Window drag |
| 7 | ✨ Not Started | Two-hand resize |
| 8 | ✨ Not Started | Polish (clutch, reconnect, tuning) |

## 🧪 Testing

Run tests with pytest:

```bash
pytest tests/
pytest tests/test_gesture_recognizer.py -v
pytest tests/test_controller.py -v
```

## 🐛 Known Issues & TODOs

- **Hand crossing occlusion:** MediaPipe may lose track when hands overlap
- **Pinch threshold tuning:** Needs real-world calibration to avoid false positives
- **Elevated windows:** `SendInput` cannot control UAC-elevated processes (may require admin)
- **Camera angle:** Works best with front-on hand positioning; steep angles may reduce accuracy

## 📊 Architecture

```
┌─────────────────┐        WebRTC video         ┌──────────────────────┐
│  Phone Browser  │ ─────────────────────────▶  │  Laptop (Flask)      │
│ getUserMedia()  │  WebSocket signaling (SDP)  │ aiortc + MediaPipe   │
│ RTCPeerConn     │ ◀───────────────────────────  │ Gesture → OS control │
└─────────────────┘                             └──────────────────────┘
```

**Key Components:**
- **Phone:** HTML/JS with `getUserMedia()` and `RTCPeerConnection`
- **Laptop Backend:** Flask + aiortc (WebRTC) + MediaPipe Hands
- **Gesture Engine:** State machine for pinch, movement, clutch detection
- **OS Controller:** `pydirectinput` for mouse, `pywin32` for windows

## 📚 Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | HTML/CSS/JS | No install required; any mobile browser |
| Signaling | Flask-SocketIO | WebRTC SDP/ICE handshake |
| Media | aiortc | Python-native WebRTC implementation |
| Hand Tracking | MediaPipe Hands | Local, real-time, robust |
| OS Control | pydirectinput + pywin32 | Reliable cross-app input simulation |
| Pairing | QR code | Avoid manual IP typing |

## 🎨 Future Enhancements

- [ ] CAD-specific gestures (orbit, zoom, pan)
- [ ] Left-hand modifier keys (scroll, shift, ctrl)
- [ ] On-screen gesture visualization (HUD overlay)
- [ ] Gesture customization UI
- [ ] Multi-monitor support
- [ ] Gesture recording/playback

## ⚠️ Troubleshooting

### Camera not detected
- Ensure camera permissions are granted in browser
- Try switching between front and rear camera
- Check that phone browser supports `getUserMedia()`

### Cursor lags or jitters
- Reduce `MAX_NUM_HANDS` in config
- Increase `CURSOR_SMOOTHING_FACTOR` (0.0-1.0)
- Check WiFi signal strength

### Gestures not detected
- Ensure hands are fully visible in camera frame
- Adjust `PINCH_DISTANCE_THRESHOLD_MM` in config
- Try with more lighting

### Connection drops
- Reconnect by scanning QR code again
- Restart server: `Ctrl+C` then `python run.py`

## 📝 License

See [LICENSE](LICENSE) file.

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -am 'Add feature'`)
4. Push to branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## 📞 Contact

For questions or suggestions, open an issue on GitHub.

---

**Built with ❤️ for gesture-based computing. Inspired by Tony Stark's interface concepts.**
