from __future__ import annotations

import bpy
from bpy.props import EnumProperty, FloatProperty
from bpy.types import Operator

from ..authoring import RAGDOLL_BODY_LENGTH_PROP, RAGDOLL_BODY_RADIUS_PROP, resolve_ragdoll_body_object, sync_ragdoll_body_object


_BODY_SHORTCUT_RADIUS_STEP = 0.01
_BODY_SHORTCUT_LENGTH_STEP = 0.025
_ADDON_KEYMAPS: list[tuple[object, object]] = []


def _active_ragdoll_body(context):
    return resolve_ragdoll_body_object(context.active_object)


def _tag_view3d_redraw(context) -> None:
    window_manager = getattr(context, "window_manager", None)
    if window_manager is None:
        return
    for window in window_manager.windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _adjust_active_body_dimension(context, dimension: str, delta: float) -> tuple[bool, str]:
    body_object = _active_ragdoll_body(context)
    if body_object is None:
        return False, "No active ragdoll rigid body"

    prop_map = {
        "radius": RAGDOLL_BODY_RADIUS_PROP,
        "length": RAGDOLL_BODY_LENGTH_PROP,
    }
    prop_name = prop_map.get(dimension)
    if prop_name is None:
        return False, f"Unsupported body dimension: {dimension}"

    current_value = float(body_object.get(prop_name, 0.0))
    body_object[prop_name] = max(0.001, current_value + float(delta))
    sync_ragdoll_body_object(body_object, force=True)
    body_object.data.update()
    context.view_layer.update()
    _tag_view3d_redraw(context)
    return True, body_object.name


class DOW2_OT_adjust_active_ragdoll_body_dimension(Operator):
    """Adjust the active ragdoll body's radius or length using shortcut-friendly deltas"""

    bl_idname = "dow2.adjust_active_ragdoll_body_dimension"
    bl_label = "Adjust Active Ragdoll Body Dimension"
    bl_options = {"REGISTER", "UNDO"}

    dimension: EnumProperty(
        items=[
            ("radius", "Radius", "Adjust capsule radius"),
            ("length", "Length", "Adjust capsule length"),
        ]
    )
    delta: FloatProperty(default=0.0)

    @classmethod
    def poll(cls, context):
        return _active_ragdoll_body(context) is not None

    def execute(self, context):
        success, message = _adjust_active_body_dimension(context, self.dimension, self.delta)
        if not success:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        return {"FINISHED"}


def register_keymaps() -> None:
    window_manager = getattr(bpy.context, "window_manager", None)
    keyconfigs = getattr(window_manager, "keyconfigs", None) if window_manager is not None else None
    addon_keyconfig = getattr(keyconfigs, "addon", None) if keyconfigs is not None else None
    if addon_keyconfig is None:
        return

    bindings = [
        ("WHEELUPMOUSE", {"ctrl": True, "alt": True}, "length", _BODY_SHORTCUT_LENGTH_STEP),
        ("WHEELDOWNMOUSE", {"ctrl": True, "alt": True}, "length", -_BODY_SHORTCUT_LENGTH_STEP),
        ("WHEELUPMOUSE", {"ctrl": True, "shift": True}, "radius", _BODY_SHORTCUT_RADIUS_STEP),
        ("WHEELDOWNMOUSE", {"ctrl": True, "shift": True}, "radius", -_BODY_SHORTCUT_RADIUS_STEP),
        ("UP_ARROW", {"ctrl": True}, "length", -_BODY_SHORTCUT_LENGTH_STEP),
        ("DOWN_ARROW", {"ctrl": True}, "length", _BODY_SHORTCUT_LENGTH_STEP),
        ("LEFT_ARROW", {"ctrl": True}, "radius", -_BODY_SHORTCUT_RADIUS_STEP),
        ("RIGHT_ARROW", {"ctrl": True}, "radius", _BODY_SHORTCUT_RADIUS_STEP),
    ]
    keymap_specs = [
        ("3D View Generic", "VIEW_3D"),
        ("Object Mode", "EMPTY"),
    ]
    for keymap_name, space_type in keymap_specs:
        km = addon_keyconfig.keymaps.new(name=keymap_name, space_type=space_type)
        for event_type, modifiers, dimension, delta in bindings:
            kmi = km.keymap_items.new(
                DOW2_OT_adjust_active_ragdoll_body_dimension.bl_idname,
                event_type,
                "PRESS",
                head=True,
                **modifiers,
            )
            kmi.properties.dimension = dimension
            kmi.properties.delta = delta
            _ADDON_KEYMAPS.append((km, kmi))


def unregister_keymaps() -> None:
    while _ADDON_KEYMAPS:
        km, kmi = _ADDON_KEYMAPS.pop()
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass