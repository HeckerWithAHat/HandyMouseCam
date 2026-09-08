"""
Main Flask application entry point for HandyMouseCam backend.
Handles WebRTC signaling, video streaming, and gesture control.
"""

import logging
import asyncio
import threading
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import json

from config import FLASK_PORT, FLASK_HOST, DEBUG_MODE, LOG_LEVEL, QR_CODE_OUTPUT_PATH
from signaling import WebRTCSignaling
from video_processor import AnnotatedVideoTrack, VideoProcessor
from gesture_recognizer import GestureRecognizer
from controller import OSController
from utils.qr_generator import generate_qr_code
from utils.network_utils import get_local_ip

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend/static', template_folder='../frontend/templates')
app.config['SECRET_KEY'] = 'handy-mouse-cam-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

webrtc_loop = asyncio.new_event_loop()


def _run_webrtc_loop():
    asyncio.set_event_loop(webrtc_loop)
    webrtc_loop.run_forever()


threading.Thread(target=_run_webrtc_loop, name="webrtc-loop", daemon=True).start()

# Initialize components
webrtc_signaling = WebRTCSignaling()
video_processor = VideoProcessor()
gesture_recognizer = GestureRecognizer()
os_controller = OSController()
gesture_recognizer.register_gesture_callback(os_controller.handle_gesture)


def _on_video_track(track):
    """Attach an annotated return track for incoming phone video."""
    if track.kind != "video" or webrtc_signaling.peer_connection is None:
        return
    logger.info("Starting annotated video return track")
    annotated_track = AnnotatedVideoTrack(
        track, video_processor, gesture_recognizer
    )
    webrtc_signaling.peer_connection.addTrack(annotated_track)


webrtc_signaling.add_on_track_handler(_on_video_track)


@app.route('/')
def index():
    """Serve the phone UI."""
    return render_template('index.html')


@app.route('/api/status')
def status():
    """Return server status."""
    return jsonify({
        'status': 'running',
        'webrtc_ready': webrtc_signaling is not None,
        'local_ip': get_local_ip()
    })


@socketio.on('connect')
def on_connect():
    """Handle new WebSocket connection."""
    logger.info("Client connected")
    emit('connection_response', {'status': 'connected'})


@socketio.on('disconnect')
def on_disconnect():
    """Handle WebSocket disconnection."""
    logger.info("Client disconnected")


def _run_on_webrtc_loop(coroutine):
    future = asyncio.run_coroutine_threadsafe(coroutine, webrtc_loop)
    return future.result()


@socketio.on('sdp_offer')
def on_sdp_offer(data):
    """Handle SDP offer from phone (WebRTC peer setup)."""
    logger.debug("Received SDP offer from phone")
    print(data)
    try:
        answer = _run_on_webrtc_loop(
            webrtc_signaling.handle_sdp_offer(json.dumps(data))
        )
        emit('sdp_answer', answer)
    except Exception as e:
        logger.error(f"Error handling SDP offer: {e}")


@socketio.on('ice_candidate')
def on_ice_candidate(data):
    """Handle ICE candidate from phone."""
    logger.debug("Received ICE candidate")
    print(data)
    try:
        _run_on_webrtc_loop(
            webrtc_signaling.handle_ice_candidate(json.dumps(data))
        )
    except Exception as e:
        logger.error(f"Error handling ICE candidate: {e}")


def run_server():
    """Start the Flask-SocketIO server."""
    logger.info(f"Starting server on {FLASK_HOST}:{FLASK_PORT}")
    
    # Generate and display QR code
    local_ip = get_local_ip()
    qr_url = f"https://{local_ip}:{FLASK_PORT}"
    logger.info(f"QR URL: {qr_url}")
    generate_qr_code(qr_url, QR_CODE_OUTPUT_PATH)
    socketio.run(app, host=FLASK_HOST, port=FLASK_PORT, debug=DEBUG_MODE, ssl_context='adhoc')


if __name__ == '__main__':
    run_server()
