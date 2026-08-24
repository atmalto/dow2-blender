"""Blocking socket client for the Blender -> Havok simulator sync bridge.

One request -> one response over loopback TCP. Pure stdlib so it works inside
Blender's bundled Python and is unit-testable against a fake server.
"""

from __future__ import annotations

import socket
from typing import Any, Dict

from . import protocol


class SyncError(Exception):
    """Raised when the sync bridge cannot be reached or returns a failure."""


class SyncClient:
    """Minimal request/response client. Not thread-safe; use per-operation."""

    def __init__(
        self,
        host: str = protocol.DEFAULT_HOST,
        port: int = protocol.DEFAULT_PORT,
        token: str = "",
        timeout: float = 10.0,
    ) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.timeout = timeout

    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send one request frame and return the decoded response object."""
        try:
            with socket.create_connection((self.host, self.port), self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall(protocol.encode_frame(message))
                return self._receive(sock)
        except (OSError, socket.timeout) as exc:  # noqa: UP041 - socket.timeout alias
            raise SyncError(
                "cannot reach simulator at {}:{} ({})".format(self.host, self.port, exc)
            ) from exc

    def ping(self) -> Dict[str, Any]:
        """Return the pong response, or raise ``SyncError`` if unreachable."""
        response = self.send(protocol.make_ping(self.token))
        if not response.get("ok"):
            raise SyncError(response.get("error", "ping failed"))
        return response

    def send_scenario(self, **fields: Any) -> Dict[str, Any]:
        """Send a command scenario (forwarded to the simulator dispatcher)."""
        request = protocol.make_request(token=self.token, **fields)
        response = self.send(request)
        if not response.get("ok"):
            raise SyncError(response.get("error", "sync command failed"))
        return response

    def _receive(self, sock: socket.socket) -> Dict[str, Any]:
        buffer = b""
        while True:
            message, buffer = protocol.decode_frame(buffer)
            if message is not None:
                return message
            chunk = sock.recv(65536)
            if not chunk:
                raise SyncError("connection closed before a full response arrived")
            buffer += chunk
