"""Blender operators for the Havok Simulator sync bridge."""

from __future__ import annotations

import bpy

from . import discovery, properties, service
from .client import SyncError
from .service import SyncServiceError


class DOW2_OT_sync_physics(bpy.types.Operator):
    """Push authored physics rigid bodies into the running Havok Simulator."""

    bl_idname = "dow2.sync_physics"
    bl_label = "Sync Physics Bodies"
    bl_description = (
        "Export the scene's authored physics systems and load them into a running "
        "Havok Simulator (start it with --sync-listen)"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        scene = getattr(context, "scene", None)
        if scene is None:
            return False
        try:
            return discovery.has_authored_physics(scene)
        except Exception:  # noqa: BLE001 - poll must never raise
            return False

    def execute(self, context):
        selected_only = bool(getattr(context.scene, "dow2_sync_selected_only", False))
        try:
            response = service.sync_physics(context, selected_only=selected_only)
        except SyncServiceError as exc:
            properties.set_status(context, -1, str(exc))
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except SyncError as exc:
            properties.set_status(context, 0, "Offline: {0}".format(exc))
            self.report({"ERROR"}, "Simulator unreachable: {0}".format(exc))
            return {"CANCELLED"}

        result = _first_result(response, "sync_physics")
        object_count = int(result.get("object_count", 0)) if result else 0
        matched = int(result.get("matched", 0)) if result else 0
        added = int(result.get("added", 0)) if result else 0
        summary = "Physics: {0} bodies ({1} kept, {2} new)".format(object_count, matched, added)
        properties.set_status(context, 1, summary)
        self.report({"INFO"}, "Synced {0}".format(summary))
        return {"FINISHED"}


class DOW2_OT_sync_ragdoll(bpy.types.Operator):
    """Push the authored ragdoll into the running Havok Simulator."""

    bl_idname = "dow2.sync_ragdoll"
    bl_label = "Sync Ragdoll"
    bl_description = (
        "Export the scene's ragdoll and load it into a running Havok Simulator "
        "(start it with --sync-listen)"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        try:
            return discovery.has_authored_ragdoll(context)
        except Exception:  # noqa: BLE001 - poll must never raise
            return False

    def execute(self, context):
        try:
            response = service.sync_ragdoll(context)
        except SyncServiceError as exc:
            properties.set_status(context, -1, str(exc))
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        except SyncError as exc:
            properties.set_status(context, 0, "Offline: {0}".format(exc))
            self.report({"ERROR"}, "Simulator unreachable: {0}".format(exc))
            return {"CANCELLED"}

        result = _first_result(response, "sync_ragdoll")
        matched = int(result.get("matched", 0)) if result else 0
        verb = "updated" if matched else "loaded"
        summary = "Ragdoll {0} (position preserved={1})".format(verb, bool(matched))
        properties.set_status(context, 1, summary)
        self.report({"INFO"}, "Synced {0}".format(summary))
        return {"FINISHED"}


class DOW2_OT_sync_check(bpy.types.Operator):
    """Ping the Havok Simulator and report whether the sync bridge is reachable."""

    bl_idname = "dow2.sync_check"
    bl_label = "Test Connection"
    bl_description = "Check whether a Havok Simulator is listening for sync requests"
    bl_options = {"REGISTER"}

    def execute(self, context):
        try:
            service.check_connection(context)
        except SyncError as exc:
            properties.set_status(context, 0, "Offline: {0}".format(exc))
            self.report({"WARNING"}, "Simulator not reachable: {0}".format(exc))
            return {"CANCELLED"}
        properties.set_status(context, 1, "Connected")
        self.report({"INFO"}, "Simulator connected")
        return {"FINISHED"}


def _first_result(response, cmd):
    """Return the first result dict for ``cmd`` in a run_scenario response."""
    results = response.get("results", []) if isinstance(response, dict) else []
    for result in results:
        if isinstance(result, dict) and result.get("cmd") == cmd:
            return result
    return None


_CLASSES = (DOW2_OT_sync_physics, DOW2_OT_sync_ragdoll, DOW2_OT_sync_check)



def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        if hasattr(bpy.types, cls.__name__):
            bpy.utils.unregister_class(cls)
