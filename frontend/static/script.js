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
        this.debugVideoElement = document.getElementById('debugVideo');
        this.statusDot = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        this.infoText = document.getElementById('infoText');
        this.debugInfo = document.getElementById('debugInfo');
        this.cameraSelect = document.getElementById('cameraSelect');
        
        this.isConnected = false;
        this.frameCount = 0;
        this.pendingIceCandidates = [];
        this.isSettingUpWebRTC = false;
        
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
        
        if (typeof io !== 'function') {
            this.log('Socket.IO client library is unavailable');
            this.setStatus('Error', false);
            return;
        }

        this.socket = io({ transports: ['websocket', 'polling'] });
        
        this.socket.on('connect', () => {
            this.log('Connected to server');
            this.setStatus('Connected', true);
            this.setupWebRTC();
        });
        
        this.socket.on('disconnect', () => {
            this.log('Disconnected from server');
            this.setStatus('Disconnected', false);
            this.closePeerConnection();
        });

        this.socket.on('connect_error', (error) => {
            this.log(`Connection error: ${error.message}`);
            this.setStatus('Connection error', false);
        });
        
        this.socket.on('sdp_answer', (data) => {
            this.log('Received SDP answer');
            this.handleSdpAnswer(data);
        });
        
        this.socket.on('ice_candidate', (data) => {
            this.log('Received ICE candidate');
            this.handleIceCandidate(data);
        });
    }
    
    /**
     * Set up WebRTC peer connection
     */
    async setupWebRTC() {
        this.log('Setting up WebRTC...');
        
        if (this.isSettingUpWebRTC || !this.socket?.connected) {
            return;
        }

        this.isSettingUpWebRTC = true;
        try {
            await this.getMediaStream();
            this.closePeerConnection();
            
            this.peerConnection = new RTCPeerConnection({
                iceServers: []
            });

            this.peerConnection.addTransceiver('video', { direction: 'recvonly' });
            
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

            this.peerConnection.onconnectionstatechange = () => {
                const state = this.peerConnection.connectionState;
                this.log(`WebRTC connection state: ${state}`);
                if (state === 'connected') {
                    this.setStatus('Connected', true);
                } else if (['failed', 'closed', 'disconnected'].includes(state)) {
                    this.setStatus('Disconnected', false);
                }
            };
            
            this.peerConnection.ontrack = (event) => {
                this.log('Received annotated landmark video');
                if (event.track.kind === 'video' && event.streams[0]) {
                    this.debugVideoElement.srcObject = event.streams[0];
                }
            };
            
            // Create and send offer
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            
            this.socket.emit('sdp_offer', {
                type: this.peerConnection.localDescription.type,
                sdp: this.peerConnection.localDescription.sdp
            });
            this.log('SDP offer sent');
        } catch (error) {
            this.log(`WebRTC setup error: ${error.message}`);
            this.setStatus('Error', false);
        } finally {
            this.isSettingUpWebRTC = false;
        }
    }
    
    /**
     * Get camera media stream
     */
    async getMediaStream() {
        this.log('Requesting camera access...');
        
        try {
            this.log(navigator.mediaDevices);
            if (!navigator.mediaDevices?.getUserMedia) {
                throw new Error('Camera access is not supported by this browser');
            }

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
            throw error;
        }
    }
    
    /**
     * Switch between front and rear camera
     */
    async switchCamera() {
        this.log('Switching camera...');
        
        try {
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => track.stop());
            }
            
            await this.getMediaStream();

            if (this.peerConnection && this.mediaStream) {
                const videoTrack = this.mediaStream.getVideoTracks()[0];
                const sender = this.peerConnection.getSenders().find(
                    currentSender => currentSender.track?.kind === 'video'
                );
                if (videoTrack && sender) {
                    await sender.replaceTrack(videoTrack);
                }
            }
            
        } catch (error) {
            this.log(`Camera switch error: ${error.message}`);
        }
    }

    /**
     * Apply the server's SDP answer and any candidates received early.
     */
    async handleSdpAnswer(data) {
        try {
            if (!this.peerConnection) {
                throw new Error('Peer connection is not ready');
            }

            const answer = typeof data === 'string' ? JSON.parse(data) : data;
            await this.peerConnection.setRemoteDescription(answer);

            for (const candidate of this.pendingIceCandidates) {
                await this.peerConnection.addIceCandidate(candidate);
            }
            this.pendingIceCandidates = [];
        } catch (error) {
            this.log(`SDP answer error: ${error.message}`);
            this.setStatus('Error', false);
        }
    }

    /**
     * Add a remote ICE candidate after the peer connection is ready.
     */
    async handleIceCandidate(data) {
        try {
            const candidate = typeof data === 'string' ? JSON.parse(data) : data;
            if (!candidate || !this.peerConnection) {
                return;
            }
            if (!this.peerConnection.remoteDescription) {
                this.pendingIceCandidates.push(candidate);
                return;
            }
            await this.peerConnection.addIceCandidate(candidate);
        } catch (error) {
            this.log(`ICE candidate error: ${error.message}`);
        }
    }

    closePeerConnection() {
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        this.pendingIceCandidates = [];
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
