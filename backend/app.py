"""
Main Flask application entry point for HandyMouseCam backend.
Handles WebRTC signaling, video streaming, and gesture control.
"""

import logging
import asyncio
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import json

from config import FLASK_PORT, FLASK_HOST, DEBUG_MODE, LOG_LEVEL, QR_CODE_OUTPUT_PATH
from signaling import WebRTCSignaling
from video_processor import VideoProcessor
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

# Initialize components
webrtc_signaling = None
video_processor = None
gesture_recognizer = None
os_controller = None


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


@socketio.on('sdp_offer')
def on_sdp_offer(data):
    """Handle SDP offer from phone (WebRTC peer setup)."""
    logger.debug("Received SDP offer from phone")
    # TODO: Implement WebRTC handshake logic
    emit('sdp_answer', {})


@socketio.on('ice_candidate')
def on_ice_candidate(data):
    """Handle ICE candidate from phone."""
    logger.debug("Received ICE candidate")
    # TODO: Process ICE candidate


def run_server():
    """Start the Flask-SocketIO server."""
    logger.info(f"Starting server on {FLASK_HOST}:{FLASK_PORT}")
    
    # Generate and display QR code
    local_ip = get_local_ip()
    qr_url = f"http://{local_ip}:{FLASK_PORT}"
    logger.info(f"QR URL: {qr_url}")
    generate_qr_code(qr_url, QR_CODE_OUTPUT_PATH)
    socketio.run(app, host=FLASK_HOST, port=FLASK_PORT, debug=DEBUG_MODE)


if __name__ == '__main__':
    run_server()
