"""Sync orchestration: gather -> export to temp HKX -> push to running simulator.

Physics sync exports the active physics tree to a temporary HKX using the
*existing* physics exporter (so all baking/coordinate conversion is identical to
a normal export), then tells the simulator to ``sync_physics`` via the shared
``run_scenario`` dispatcher. ``sync_physics`` replaces the previously-synced group
in place and preserves the per-body pose the user set in the simulator; the temp
files are removed once the simulator acknowledges.

Nothing here imports Blender at module load; ``bpy``-touching work happens inside
the functions so the transport layer stays unit-testable.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from typing import Any, Dict

from .client import SyncClient, SyncError


class SyncServiceError(Exception):
    """Raised when a sync operation cannot be completed."""


def _client_from_prefs(context) -> SyncClient:
    """Build a :class:`SyncClient` from add-on preferences (with fallbacks)."""
    from . import protocol

    host = protocol.DEFAULT_HOST
    port = protocol.DEFAULT_PORT
    token = ""
    try:
        prefs = context.preferences.addons[__package__.split(".", 1)[0]].preferences
        host = getattr(prefs, "sync_host", host) or host
        port = int(getattr(prefs, "sync_port", port) or port)
        token = getattr(prefs, "sync_token", token) or ""
    except (KeyError, AttributeError):
        pass
    return SyncClient(host=host, port=port, token=token)


def _export_physics_temp_hkx(scene) -> str:
    """Export the active physics tree to a temp HKX; return its path.

    Reuses ``physics.exporter`` end to end. The JSON is written next to the HKX
    in the OS temp dir and removed immediately; only the HKX path is returned.
    """
    from ..physics import exporter as physics_exporter

    systems = physics_exporter.build_physics_systems(scene)
    if not systems:
        raise SyncServiceError("No authored physics bodies found in the scene.")

    stem = "dow2_sync_physics_{0}".format(uuid.uuid4().hex)
    temp_dir = tempfile.gettempdir()
    json_path = os.path.join(temp_dir, stem + ".json")
    hkx_path = os.path.join(temp_dir, stem + ".hkx")

    physics_exporter.export_physics_json(systems, json_path)
    try:
        ok, message = physics_exporter.run_physics_exporter(json_path, hkx_path)
    finally:
        _silent_remove(json_path)

    if not ok:
        _silent_remove(hkx_path)
        raise SyncServiceError("Physics HKX export failed: {0}".format(message or "unknown error"))
    return hkx_path


def sync_physics(context, selected_only: bool = False) -> Dict[str, Any]:
    """Push the scene's authored physics systems into the running simulator.

    When ``selected_only`` is set, only the selected physics hull bodies are sent
    and the simulator updates just those (partial mode), leaving other synced
    bodies in place.

    Returns the simulator's response object. Raises :class:`SyncServiceError`
    (export problems) or :class:`SyncError` (transport problems).
    """
    from . import discovery

    scene = context.scene
    client = _client_from_prefs(context)

    only_names = []
    if selected_only:
        only_names = discovery.selected_physics_body_names(context)
        if not only_names:
            raise SyncServiceError(
                "Selected Only is on but no physics hull objects are selected."
            )

    # Fail fast with a clear message if the simulator isn't listening.
    client.ping()

    hkx_path = _export_physics_temp_hkx(scene)
    try:
        # Forward slashes keep the JSON payload clean and are accepted on Windows.
        wire_path = hkx_path.replace("\\", "/")
        command = {"cmd": "sync_physics", "path": wire_path, "sync_id": "dow2_physics"}
        if selected_only:
            command["partial"] = True
            command["only_names"] = only_names
        response = client.send_scenario(commands=[command])
    finally:
        _silent_remove(hkx_path)
    return response



def _export_ragdoll_temp_hkx(context) -> str:
    """Export the scene's ragdoll to a temp HKX; return its path.

    Reuses ``ragdoll.exporter.export_ragdoll_hkx`` end to end (same source armature
    selection and baking as a normal ragdoll export). The intermediate JSON is
    written next to the HKX and removed immediately; only the HKX path is returned.
    """
    from ..ragdoll import exporter as ragdoll_exporter
    from . import discovery

    armature = discovery.ragdoll_source_armature(context)
    if armature is None:
        raise SyncServiceError(
            "No ragdoll source armature found. Select the source armature, or keep "
            "exactly one non-ragdoll armature in the scene."
        )

    stem = "dow2_sync_ragdoll_{0}".format(uuid.uuid4().hex)
    temp_dir = tempfile.gettempdir()
    json_path = os.path.join(temp_dir, stem + ".json")
    hkx_path = os.path.join(temp_dir, stem + ".hkx")

    try:
        ragdoll_exporter.export_ragdoll_hkx(armature, hkx_path, json_path=json_path)
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the operator
        _silent_remove(hkx_path)
        raise SyncServiceError("Ragdoll HKX export failed: {0}".format(exc))
    finally:
        _silent_remove(json_path)

    if not os.path.exists(hkx_path):
        raise SyncServiceError("Ragdoll HKX export produced no file.")
    return hkx_path


def sync_ragdoll(context) -> Dict[str, Any]:
    """Push the scene's authored ragdoll into the running simulator.

    Returns the simulator's response object. Raises :class:`SyncServiceError`
    (export problems) or :class:`SyncError` (transport problems).
    """
    client = _client_from_prefs(context)

    # Fail fast with a clear message if the simulator isn't listening.
    client.ping()

    hkx_path = _export_ragdoll_temp_hkx(context)
    try:
        wire_path = hkx_path.replace("\\", "/")
        response = client.send_scenario(
            commands=[
                {"cmd": "sync_ragdoll", "path": wire_path, "sync_id": "dow2_ragdoll"},
            ]
        )
    finally:
        _silent_remove(hkx_path)
    return response



def _silent_remove(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def check_connection(context) -> Dict[str, Any]:
    """Ping the simulator. Returns the pong response or raises :class:`SyncError`."""
    client = _client_from_prefs(context)
    return client.ping()
