/**
 * HandyMouseCam Frontend JavaScript
 * Handles WebRTC connection, camera streaming, and server communication
 */

class HandyMouseCamClient {
    constructor() {
        this.socket = null;
        this.peerConnection = null;
        this.mediaStream = null;
        this.videoElement = document.getElementById('cameraVideo');
        this.statusDot = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        this.infoText = document.getElementById('infoText');
        this.debugInfo = document.getElementById('debugInfo');
        this.cameraSelect = document.getElementById('cameraSelect');
        
        this.isConnected = false;
        this.frameCount = 0;
        
        this.init();
    }
    
    /**
     * Initialize the client
     */
    async init() {
        this.log('Initializing HandyMouseCam client...');
        
        // Set up event listeners
        this.cameraSelect.addEventListener('change', () => this.switchCamera());
        
        // Connect to server
        this.connectToServer();
    }
    
    /**
     * Connect to WebSocket server for signaling
     */
    connectToServer() {
        this.log('Connecting to server...');
        
        // TODO: Implement WebSocket connection
        // Should:
        // - Connect to /socket.io endpoint
        // - Set up event handlers for SDP offer, ICE candidates
        // - Handle connection events
        
        this.socket = io();
        
        this.socket.on('connect', () => {
            this.log('Connected to server');
            this.setStatus('Connected', true);
            this.setupWebRTC();
        });
        
        this.socket.on('disconnect', () => {
            this.log('Disconnected from server');
            this.setStatus('Disconnected', false);
        });
        
        this.socket.on('sdp_answer', (data) => {
            this.log('Received SDP answer');
            // TODO: Handle SDP answer
        });
        
        this.socket.on('ice_candidate', (data) => {
            this.log('Received ICE candidate');
            // TODO: Handle ICE candidate
        });
    }
    
    /**
     * Set up WebRTC peer connection
     */
    async setupWebRTC() {
        this.log('Setting up WebRTC...');
        
        try {
            // TODO: Implement WebRTC setup
            // Should:
            // - Create RTCPeerConnection
            // - Get camera stream
            // - Add track to peer connection
            // - Create and send SDP offer
            // - Handle remote tracks
            
            // Get camera stream
            await this.getMediaStream();
            
            // Create peer connection
            this.peerConnection = new RTCPeerConnection({
                iceServers: []
            });
            
            // Add local stream tracks
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => {
                    this.peerConnection.addTrack(track, this.mediaStream);
                });
            }
            
            // Handle ICE candidates
            this.peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    this.log('Sending ICE candidate');
                    this.socket.emit('ice_candidate', event.candidate);
                }
            };
            
            // Handle remote stream
            this.peerConnection.ontrack = (event) => {
                this.log('Received remote track');
            };
            
            // Create and send offer
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            
            this.socket.emit('sdp_offer', this.peerConnection.localDescription);
            this.log('SDP offer sent');
            
        } catch (error) {
            this.log(`WebRTC setup error: ${error.message}`);
            this.setStatus('Error', false);
        }
    }
    
    /**
     * Get camera media stream
     */
    async getMediaStream() {
        this.log('Requesting camera access...');
        
        try {
            // TODO: Implement media stream acquisition
            const facingMode = this.cameraSelect.value === 'user' ? 'user' : 'environment';
            
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: facingMode,
                    width: { ideal: 1280 },
                    height: { ideal: 960 }
                },
                audio: false
            });
            
            this.videoElement.srcObject = this.mediaStream;
            this.log('Camera access granted');
            this.infoText.textContent = 'Camera active - position hands in frame';
            
        } catch (error) {
            this.log(`Camera access error: ${error.message}`);
            this.infoText.textContent = 'Camera access denied. Please allow camera permission.';
        }
    }
    
    /**
     * Switch between front and rear camera
     */
    async switchCamera() {
        this.log('Switching camera...');
        
        try {
            // TODO: Implement camera switching
            // Should:
            // - Stop current stream
            // - Get new stream with different facing mode
            // - Update video element
            
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => track.stop());
            }
            
            await this.getMediaStream();
            
        } catch (error) {
            this.log(`Camera switch error: ${error.message}`);
        }
    }
    
    /**
     * Update connection status UI
     */
    setStatus(text, connected) {
        this.isConnected = connected;
        this.statusText.textContent = text;
        
        this.statusDot.classList.remove('connected', 'disconnected');
        this.statusDot.classList.add(connected ? 'connected' : 'disconnected');
    }
    
    /**
     * Log message to debug panel
     */
    log(message) {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = `[${timestamp}] ${message}\n`;
        
        this.debugInfo.textContent += logEntry;
        
        // Keep debug panel scrolled to bottom
        const debugPanel = document.querySelector('.debug-panel');
        debugPanel.scrollTop = debugPanel.scrollHeight;
        
        console.log(message);
    }
}

// Initialize client when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new HandyMouseCamClient();
});
