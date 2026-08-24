"""Transport-level tests for the sync bridge (no Blender, no simulator).

These validate the wire framing and the :class:`SyncClient` round-trip against a
tiny in-process fake server that mimics the C++ ``SyncServer`` ping/token logic.
Run with: ``pytest tests/test_sync_protocol.py``.
"""

from __future__ import annotations

import json
import os
import socket
import struct
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sync import protocol  # noqa: E402
from sync.client import SyncClient, SyncError  # noqa: E402


# --- framing ---------------------------------------------------------------

def test_encode_decode_roundtrip():
    message = {"protocol": protocol.PROTOCOL_TAG, "op": "ping"}
    frame = protocol.encode_frame(message)
    (length,) = struct.unpack_from(">I", frame)
    assert length == len(frame) - 4
    decoded, remainder = protocol.decode_frame(frame)
    assert decoded == message
    assert remainder == b""


def test_decode_waits_for_full_frame():
    frame = protocol.encode_frame({"op": "ping"})
    # Only the length prefix is available: no message yet.
    decoded, remainder = protocol.decode_frame(frame[:4])
    assert decoded is None
    assert remainder == frame[:4]
    # Feed the rest: message emerges, buffer drained.
    decoded, remainder = protocol.decode_frame(frame)
    assert decoded == {"op": "ping"}
    assert remainder == b""


def test_decode_leaves_trailing_bytes():
    frame = protocol.encode_frame({"op": "ping"})
    decoded, remainder = protocol.decode_frame(frame + b"leftover")
    assert decoded == {"op": "ping"}
    assert remainder == b"leftover"


# --- fake server + client --------------------------------------------------

class _FakeSyncServer:
    """Single-connection loopback server mirroring SyncServer's P1 behavior."""

    def __init__(self, token: str = ""):
        self.token = token
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(1)
        self.port = self._sock.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        try:
            self._sock.close()
        except OSError:
            pass

    def _serve(self):
        try:
            conn, _ = self._sock.accept()
        except OSError:
            return
        with conn:
            buffer = b""
            while True:
                message, buffer = protocol.decode_frame(buffer)
                if message is None:
                    chunk = conn.recv(65536)
                    if not chunk:
                        return
                    buffer += chunk
                    continue
                conn.sendall(protocol.encode_frame(self._respond(message)))

    def _respond(self, message):
        if self.token and message.get("token") != self.token:
            return {"ok": False, "error": "unauthorized"}
        if message.get("op") == "ping":
            return {"ok": True, "op": "pong", "protocol": protocol.PROTOCOL_TAG}
        commands = message.get("commands", [])
        return {"ok": True, "results": [], "received": len(commands)}


def test_client_ping_roundtrip():
    with _FakeSyncServer() as server:
        client = SyncClient(port=server.port, timeout=5.0)
        response = client.ping()
        assert response["ok"] is True
        assert response["op"] == "pong"


def test_client_scenario_roundtrip():
    with _FakeSyncServer() as server:
        client = SyncClient(port=server.port, timeout=5.0)
        response = client.send_scenario(commands=[{"cmd": "noop"}, {"cmd": "noop"}])
        assert response["received"] == 2


def test_client_token_enforced():
    with _FakeSyncServer(token="secret") as server:
        good = SyncClient(port=server.port, token="secret", timeout=5.0)
        assert good.ping()["ok"] is True

    with _FakeSyncServer(token="secret") as server:
        bad = SyncClient(port=server.port, token="wrong", timeout=5.0)
        with pytest.raises(SyncError):
            bad.ping()


def test_client_unreachable_raises():
    # Nothing is listening on this port.
    client = SyncClient(port=1, timeout=1.0)
    with pytest.raises(SyncError):
        client.ping()
