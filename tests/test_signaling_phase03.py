import json
from types import SimpleNamespace

import pytest

from signaling import WebRTCSignaling


class FakePeerConnection:
    def __init__(self):
        self.handlers = {}
        self.remote_description = None
        self.localDescription = SimpleNamespace(sdp="answer-sdp", type="answer")
        self.added_candidates = []

    def on(self, event, callback):
        self.handlers[event] = callback

    async def setRemoteDescription(self, description):
        self.remote_description = description

    async def createAnswer(self):
        return SimpleNamespace(sdp="answer-sdp", type="answer")

    async def setLocalDescription(self, description):
        self.localDescription = description

    async def addIceCandidate(self, candidate):
        self.added_candidates.append(candidate)

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_create_peer_connection_is_cached(monkeypatch):
    peer = FakePeerConnection()
    monkeypatch.setattr("signaling.RTCPeerConnection", lambda: peer)
    signaling = WebRTCSignaling()

    first = await signaling.create_peer_connection()
    second = await signaling.create_peer_connection()

    assert first is peer
    assert second is first
    assert peer.handlers["track"] == signaling.on_track


@pytest.mark.asyncio
async def test_sdp_offer_returns_answer(monkeypatch):
    peer = FakePeerConnection()
    monkeypatch.setattr("signaling.RTCPeerConnection", lambda: peer)
    signaling = WebRTCSignaling()

    result = await signaling.handle_sdp_offer(
        json.dumps({"sdp": "offer-sdp", "type": "offer"})
    )

    answer = json.loads(result)
    assert answer == {"sdp": "answer-sdp", "type": "answer"}
    assert peer.remote_description.sdp == "offer-sdp"


@pytest.mark.asyncio
async def test_sdp_offer_requires_sdp_and_type(monkeypatch):
    peer = FakePeerConnection()
    monkeypatch.setattr("signaling.RTCPeerConnection", lambda: peer)
    signaling = WebRTCSignaling()

    with pytest.raises(ValueError):
        await signaling.handle_sdp_offer({"sdp": "missing-type"})


@pytest.mark.asyncio
async def test_track_handlers_receive_sync_and_async_callbacks():
    signaling = WebRTCSignaling()
    received = []

    def sync_callback(track):
        received.append(("sync", track))

    async def async_callback(track):
        received.append(("async", track))

    signaling.add_on_track_handler(sync_callback)
    signaling.add_on_track_handler(async_callback)
    track = SimpleNamespace(kind="video")

    await signaling.on_track(track)

    assert received == [("sync", track), ("async", track)]


@pytest.mark.asyncio
async def test_ice_candidate_is_added(monkeypatch):
    peer = FakePeerConnection()
    monkeypatch.setattr("signaling.RTCPeerConnection", lambda: peer)
    signaling = WebRTCSignaling()
    candidate = {
        "candidate": "candidate:1 1 UDP 2122260223 192.168.1.2 5000 typ host",
        "sdpMid": "0",
        "sdpMLineIndex": 0,
    }

    await signaling.handle_ice_candidate(candidate)

    assert len(peer.added_candidates) == 1
    assert peer.added_candidates[0].sdpMid == "0"
    assert peer.added_candidates[0].sdpMLineIndex == 0


@pytest.mark.asyncio
async def test_empty_ice_candidate_is_ignored(monkeypatch):
    peer = FakePeerConnection()
    monkeypatch.setattr("signaling.RTCPeerConnection", lambda: peer)
    signaling = WebRTCSignaling()

    await signaling.handle_ice_candidate({})

    assert peer.added_candidates == []


def test_track_handler_must_be_callable():
    with pytest.raises(TypeError):
        WebRTCSignaling().add_on_track_handler(None)
