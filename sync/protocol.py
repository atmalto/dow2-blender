"""Wire protocol for the Blender -> Havok simulator sync bridge.

Frame format (matches ``havok_simulator/include/sync_protocol.h``)::

    frame = <uint32 big-endian length N> <N bytes UTF-8 JSON>

Both a request and its response are single framed JSON objects. This module is
pure stdlib (no ``bpy``) so it can be unit-tested outside Blender.
"""

from __future__ import annotations

import json
import struct
from typing import Any, Dict, Optional, Tuple

PROTOCOL_TAG = "dow2-sync/1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 47800
TOKEN_ENV_VAR = "DOW2_SYNC_TOKEN"

_LENGTH_PREFIX = struct.Struct(">I")
MAX_FRAME_BYTES = 64 * 1024 * 1024


def encode_frame(message: Dict[str, Any]) -> bytes:
    """Serialize ``message`` to a length-prefixed JSON frame."""
    payload = json.dumps(message).encode("utf-8")
    if len(payload) > MAX_FRAME_BYTES:
        raise ValueError("sync frame exceeds maximum size")
    return _LENGTH_PREFIX.pack(len(payload)) + payload


def decode_frame(buffer: bytes) -> Tuple[Optional[Dict[str, Any]], bytes]:
    """Try to pull one frame off the front of ``buffer``.

    Returns ``(message, remainder)``. If a full frame is not yet available,
    returns ``(None, buffer)`` unchanged.
    """
    if len(buffer) < _LENGTH_PREFIX.size:
        return None, buffer
    (length,) = _LENGTH_PREFIX.unpack_from(buffer)
    if length > MAX_FRAME_BYTES:
        raise ValueError("sync frame exceeds maximum size")
    end = _LENGTH_PREFIX.size + length
    if len(buffer) < end:
        return None, buffer
    payload = buffer[_LENGTH_PREFIX.size:end]
    message = json.loads(payload.decode("utf-8"))
    return message, buffer[end:]


def make_request(token: str = "", **fields: Any) -> Dict[str, Any]:
    """Build a request envelope with the protocol tag and optional token."""
    request: Dict[str, Any] = {"protocol": PROTOCOL_TAG}
    if token:
        request["token"] = token
    request.update(fields)
    return request


def make_ping(token: str = "") -> Dict[str, Any]:
    """A liveness probe answered by ``{"ok": true, "op": "pong"}``."""
    return make_request(token=token, op="ping")
