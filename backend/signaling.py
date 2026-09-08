"""
WebRTC signaling logic using aiortc.
Handles SDP offer/answer exchange and ICE candidate processing.
"""

import logging
import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.sdp import candidate_from_sdp
import json
import inspect

logger = logging.getLogger(__name__)


class WebRTCSignaling:
    """
    Manages WebRTC peer connection and signaling.
    Handles SDP offer/answer and ICE candidate exchange.
    """
    
    def __init__(self):
        """Initialize WebRTC signaling handler."""
        self.peer_connection = None
        self.remote_description = None
        self._track_handlers = []
        logger.info("WebRTCSignaling initialized")
    
    async def create_peer_connection(self):
        """
        Create and configure RTCPeerConnection.
        
        Returns:
            RTCPeerConnection: Configured peer connection instance
        """
        if self.peer_connection is not None:
            return self.peer_connection

        self.peer_connection = RTCPeerConnection()
        self.peer_connection.on("track", self.on_track)
        logger.debug("Created peer connection")
        return self.peer_connection

    async def on_track(self, track):
        """Dispatch an incoming media track to registered handlers."""
        logger.info("Received remote %s track", track.kind)
        for callback in tuple(self._track_handlers):
            try:
                result = callback(track)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Remote track handler failed")
    
    async def handle_sdp_offer(self, offer_json: str):
        """
        Process SDP offer from phone and generate answer.
        
        Args:
            offer_json: JSON-serialized SDP offer
            
        Returns:
            dict: JSON-serializable SDP answer
        """
        logger.debug("Handling SDP offer...")
        if self.peer_connection is None:
            await self.create_peer_connection()

        offer = json.loads(offer_json) if isinstance(offer_json, str) else offer_json
        if not isinstance(offer, dict) or "sdp" not in offer or "type" not in offer:
            raise ValueError("SDP offer must contain 'sdp' and 'type'")

        self.remote_description = RTCSessionDescription(
            sdp=offer["sdp"], type=offer["type"]
        )
        await self.peer_connection.setRemoteDescription(self.remote_description)
        await asyncio.sleep(0)
        answer = await self.peer_connection.createAnswer()
        await self.peer_connection.setLocalDescription(answer)
        local_description = self.peer_connection.localDescription
        return json.dumps({"sdp": local_description.sdp, "type": local_description.type})

    async def handle_ice_candidate(self, candidate_json: str):
        """
        Process ICE candidate from phone.
        
        Args:
            candidate_json: JSON-serialized ICE candidate
        """
        logger.debug("Processing ICE candidate...")
        if self.peer_connection is None:
            await self.create_peer_connection()

        try:
            candidate_data = (
                json.loads(candidate_json)
                if isinstance(candidate_json, str)
                else candidate_json
            )
            if not isinstance(candidate_data, dict):
                raise ValueError("ICE candidate must be a JSON object")

            candidate_sdp = candidate_data.get("candidate")
            if not candidate_sdp:
                return
            if candidate_sdp.startswith("candidate:"):
                candidate_sdp = candidate_sdp.split(":", 1)[1]

            candidate = candidate_from_sdp(candidate_sdp)
            candidate.sdpMid = candidate_data.get("sdpMid")
            candidate.sdpMLineIndex = candidate_data.get("sdpMLineIndex")
            await self.peer_connection.addIceCandidate(candidate)
        except Exception:
            logger.exception("Failed to process ICE candidate")
    
    def add_on_track_handler(self, callback):
        """
        Register callback for when remote track is received.
        
        Args:
            callback: Async function to handle incoming track
        """
        if not callable(callback):
            raise TypeError("track callback must be callable")
        self._track_handlers.append(callback)
        logger.debug("Registered track handler")
    
    async def close(self):
        """Clean up peer connection."""
        if self.peer_connection:
            await self.peer_connection.close()
            logger.info("Peer connection closed")
