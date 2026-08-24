"""Viewport panel for the Havok Simulator sync bridge."""

from __future__ import annotations

import bpy
from bpy.types import Panel

from . import discovery


def _sync_preferences(context):
    addon_id = (__package__ or "dow2_tools").split(".", 1)[0]
    try:
        return context.preferences.addons[addon_id].preferences
    except (AttributeError, KeyError):
        return None


class DOW2_PT_sync_panel(Panel):
    """One-click push of authored physics/ragdoll into the running simulator."""

    bl_label = "Havok Simulator Sync"
    bl_idname = "DOW2_PT_sync_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_order = 999
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        wm = context.window_manager
        prefs = _sync_preferences(context)

        has_physics = False
        try:
            has_physics = discovery.has_authored_physics(scene)
        except Exception:  # noqa: BLE001 - draw must never raise
            has_physics = False

        has_ragdoll = False
        try:
            has_ragdoll = discovery.has_authored_ragdoll(context)
        except Exception:  # noqa: BLE001 - draw must never raise
            has_ragdoll = False

        # Connection status row + manual (no-polling) test button.
        online = int(getattr(wm, "dow2_sync_online", -1))
        status = str(getattr(wm, "dow2_sync_status", ""))
        status_icon = {1: "CHECKMARK", 0: "ERROR"}.get(online, "QUESTION")
        row = layout.row(align=True)
        if prefs is not None:
            row.prop(prefs, "sync_port", text="Port")
        row.operator("dow2.sync_check", icon="LINKED")
        if status:
            layout.label(text=status, icon=status_icon)
        elif online == -1:
            layout.label(text="Connection not tested", icon="QUESTION")

        # Sync buttons are only hard-disabled when we *know* the simulator is offline;
        # before any check they stay enabled (they fail fast with a clear error).
        known_offline = online == 0

        layout.prop(scene, "dow2_sync_selected_only")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.enabled = has_physics and not known_offline
        row.operator("dow2.sync_physics", icon="PHYSICS")
        if not has_physics:
            col.label(text="No authored physics in scene", icon="INFO")

        col.separator()
        row = col.row(align=True)
        row.enabled = has_ragdoll and not known_offline
        row.operator("dow2.sync_ragdoll", icon="ARMATURE_DATA")
        if not has_ragdoll:
            col.label(text="No ragdoll source armature", icon="INFO")




_CLASSES = (DOW2_PT_sync_panel,)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)
