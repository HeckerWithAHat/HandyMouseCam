# HandyMouseCam - Development Guide

This guide will help you set up the development environment and understand the project structure for contributing to HandyMouseCam.

## Prerequisites

- **Python 3.8 or later**
- **Git**
- **A modern browser** (Chrome, Firefox, Safari, Edge)
- **A smartphone** with a camera
- **Two devices on the same WiFi network**

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/HandyMouseCam.git
cd HandyMouseCam
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt  # For development/testing
```

### 4. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your settings (optional)
```

## Project Structure Explanation

### Backend (`backend/`)

- **app.py** - Flask application entry point; sets up routes and WebSocket events
- **config.py** - Central configuration; tune gesture detection, cursor sensitivity, network settings
- **signaling.py** - WebRTC peer connection management; handles SDP offer/answer and ICE candidates
- **video_processor.py** - MediaPipe Hands integration; processes frames and extracts landmarks
- **gesture_recognizer.py** - State machine for gesture detection; pinch, movement, clutch logic
- **controller.py** - OS-level control; mouse movement, clicks, window manipulation
- **utils/** - Helper modules for networking and QR code generation

### Frontend (`frontend/`)

- **templates/index.html** - Phone UI served to browser
- **static/style.css** - Responsive styling
- **static/script.js** - WebRTC client logic; camera setup and signaling

### Tests (`tests/`)

- **test_gesture_recognizer.py** - Unit tests for gesture detection
- **test_controller.py** - Unit tests for OS control

## Running the Application

### Start Server

```bash
python run.py
```

The server will output:
- Local IP address
- QR code (text and PNG)
- Server status

### Open on Phone

1. Scan the displayed QR code with your phone
2. Open the link in your browser
3. Allow camera permission when prompted
4. Position hands in front of camera

### Verify Connection

- Status should change from "Disconnected" to "Connected"
- You should see camera feed on phone
- Debug panel shows connection info

## Development Workflow

### Adding a Feature

1. **Identify the module:** Which component needs changes?
   - Gesture detection → `gesture_recognizer.py`
   - OS control → `controller.py`
   - UI → `frontend/static/script.js`

2. **Implement with TODOs:** The codebase has `# TODO` comments marking unimplemented functions

3. **Write tests:** Add tests in `tests/` matching the module

4. **Run tests:**
   ```bash
   pytest tests/test_gesture_recognizer.py -v
   ```

5. **Manual testing:**
   ```bash
   python run.py
   # Test with actual phone/hand gestures
   ```

### Debugging Tips

**Python Backend:**
- Check `backend/config.py` for logging level
- Logs appear in terminal running `python run.py`
- Add print statements or use `logger.debug()`

**Frontend/JavaScript:**
- Open DevTools on phone browser (F12)
- Console shows WebRTC status
- Network tab shows signaling traffic

**Hand Tracking:**
- `video_processor.py` has `draw_landmarks()` for visualization
- Look for hand detection confidence in debug panel
- Check lighting and hand positioning

## Key Implementation Areas (TODOs)

### Phase 0-1: Network & Video
- [ ] `signaling.py` - WebRTC peer connection setup
- [ ] `app.py` - WebSocket event handlers
- [ ] `script.js` - Camera stream and peer connection

### Phase 2: Hand Tracking
- [ ] `video_processor.py` - MediaPipe inference loop
- [ ] `video_processor.py` - Landmark drawing for debug

### Phase 3-4: Gesture Recognition
- [ ] `gesture_recognizer.py` - Pinch detection
- [ ] `gesture_recognizer.py` - Hand movement tracking
- [ ] `gesture_recognizer.py` - State machine logic

### Phase 5+: OS Control
- [ ] `controller.py` - Cursor movement (relative/trackpad)
- [ ] `controller.py` - Click and drag
- [ ] `controller.py` - Window drag/resize

## Testing Strategy

### Unit Tests
- Mock hand landmarks and test gesture logic
- Mock OS calls and test cursor/window control
- Test state machine transitions

### Integration Tests
- Test full pipeline from landmarks to OS action
- Test WebRTC signaling and frame flow

### Manual Testing
- Test with real hands at different angles
- Test on different phones and laptops
- Test gesture edge cases (hand crossing, slow motion, etc.)

## Common Issues & Solutions

### ImportError: No module named 'mediapipe'
```bash
pip install mediapipe
```

### Camera permission denied (browser)
- Check browser settings for camera permissions
- Try incognito/private mode
- Restart browser

### WebRTC connection fails
- Verify both devices on same WiFi
- Check firewall isn't blocking port 5000
- Try `http://` not `https://`

### Hand tracking not working
- Ensure good lighting
- Position hands fully in camera frame
- Check MediaPipe detection confidence (`config.py`)

### Cursor doesn't move
- Verify `pydirectinput` installation
- Try running as administrator
- Check if keyboard/mouse is being controlled by other app

## Performance Profiling

### Latency Measurement
Profile each stage:
1. Frame capture → encoding: ~10ms
2. WebRTC transmission: ~10-30ms
3. Decoding → MediaPipe: ~15-40ms
4. Gesture logic: ~2-5ms
5. OS control: ~5-15ms

Total aim: <100ms for responsive feel

### Memory Usage
Monitor for leaks:
```bash
pip install memory-profiler
python -m memory_profiler run.py
```

## Code Style

- Follow PEP 8 for Python
- Use type hints where helpful
- Comment complex logic
- Keep functions focused and testable

## Building Documentation

Generate API docs:
```bash
pip install sphinx
cd docs/
sphinx-quickstart
```

## Deployment Considerations

- [ ] Configuration management (environment variables)
- [ ] Logging and monitoring
- [ ] Error recovery and reconnection
- [ ] Performance optimization
- [ ] Security (HTTPS for production)
- [ ] Multi-user support

## Resources

- **MediaPipe Hands:** https://google.github.io/mediapipe/solutions/hands
- **aiortc:** https://github.com/aiortc/aiortc
- **Flask-SocketIO:** https://flask-socketio.readthedocs.io/
- **pywin32:** https://github.com/pywin32/pywin32

## Getting Help

- Check existing issues on GitHub
- Review the project document (`hand-gesture-mouse-project-doc.md`)
- Add debug logging to isolate problems
- Test incrementally (one phase at a time)

---

Happy coding! 🎮✨
