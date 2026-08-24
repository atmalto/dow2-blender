"""Runtime state + scene settings for the sync panel (P5 UX polish).

Kept tiny and additive: a persisted "selected only" toggle on the Scene, plus
runtime connection status on the WindowManager (not saved with the .blend). The
status is updated only when the user clicks Sync or Test Connection — there is no
polling, matching the bridge's user-triggered design.
"""

from __future__ import annotations

import bpy


def register():
    bpy.types.Scene.dow2_sync_selected_only = bpy.props.BoolProperty(
        name="Selected Only",
        description=(
            "Sync only the selected physics hull objects, leaving the other synced "
            "bodies in the simulator untouched"
        ),
        default=False,
    )
    # Runtime-only connection status (never saved to the .blend).
    bpy.types.WindowManager.dow2_sync_status = bpy.props.StringProperty(
        name="Sync Status",
        default="",
    )
    # -1 = unknown (not checked yet), 0 = offline, 1 = online.
    bpy.types.WindowManager.dow2_sync_online = bpy.props.IntProperty(
        name="Sync Online",
        default=-1,
    )


def unregister():
    for owner, attr in (
        (bpy.types.WindowManager, "dow2_sync_online"),
        (bpy.types.WindowManager, "dow2_sync_status"),
        (bpy.types.Scene, "dow2_sync_selected_only"),
    ):
        if hasattr(owner, attr):
            delattr(owner, attr)


def set_status(context, online: int, message: str) -> None:
    """Record the latest connection status for the panel to display."""
    wm = getattr(context, "window_manager", None)
    if wm is None:
        return
    wm.dow2_sync_online = online
    wm.dow2_sync_status = message
