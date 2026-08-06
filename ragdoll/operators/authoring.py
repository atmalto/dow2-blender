from __future__ import annotations

import bpy
from bpy.props import EnumProperty
from bpy.types import Operator

from .. import export_ragdoll_hkx
from ..authoring import (
    BODY_SHAPE_ITEMS,
    RAGDOLL_CONSTRAINT_TYPE_PROP,
    active_ragdoll_bone,
    apply_body_data_to_object,
    create_or_update_bodies_for_selection,
    create_scene_ragdoll_skeleton,
    find_source_armature,
    resolve_ragdoll_body_object,
    resolve_selected_ragdoll_bones,
)
from .common import (
    _resolve_active_armature,
    _resolve_active_ragdoll_skeleton,
    _resolve_export_path,
    _resolve_selected_source_ragdoll_bone_order,
)


class DOW2_OT_create_ragdoll_skeleton(Operator):
    """Create a reduced ragdoll armature in its own collection"""

    bl_idname = "dow2.create_ragdoll_skeleton"
    bl_label = "Create Ragdoll Skeleton"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        settings = context.scene.dow2_ragdoll_settings
        source_armature = find_source_armature(context)
        if source_armature is None:
            self.report({"ERROR"}, "No source armature found. Select an animation skeleton armature first")
            return {"CANCELLED"}

        try:
            ragdoll_bone_order = _resolve_selected_source_ragdoll_bone_order(context, source_armature)
            if ragdoll_bone_order is None:
                raise RuntimeError("Select one or more source animation bones before creating a ragdoll skeleton")
            ragdoll_object = create_scene_ragdoll_skeleton(
                context,
                source_armature,
                settings.ragdoll_name,
                ragdoll_bone_order=ragdoll_bone_order,
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        bpy.ops.object.select_all(action="DESELECT")
        ragdoll_object.select_set(True)
        context.view_layer.objects.active = ragdoll_object
        self.report({"INFO"}, f"Created ragdoll skeleton with {len(ragdoll_object.data.bones)} bones")
        return {"FINISHED"}


class DOW2_OT_create_ragdoll_bodies(Operator):
    """Create or update ragdoll bodies for the selected ragdoll bones"""

    bl_idname = "dow2.create_ragdoll_bodies"
    bl_label = "Create Or Update Bodies"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        settings = context.scene.dow2_ragdoll_settings
        skeleton_object = _resolve_active_ragdoll_skeleton(context)
        if skeleton_object is None:
            self.report({"ERROR"}, "No ragdoll bone or ragdoll_skeleton object selected")
            return {"CANCELLED"}

        bone_names = resolve_selected_ragdoll_bones(context)
        if not bone_names:
            self.report({"ERROR"}, "No ragdoll bone selected. Select a ragdoll bone or the ragdoll_skeleton object")
            return {"CANCELLED"}

        try:
            created_objects = create_or_update_bodies_for_selection(
                context,
                skeleton_object,
                bone_names,
                settings.body_shape,
                settings.body_radius,
                settings.body_radius * 2.0,
                settings.body_length,
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        if not created_objects:
            self.report({"WARNING"}, "No bodies were generated for the current selection")
            return {"CANCELLED"}

        if context.mode != "OBJECT" and bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        for obj in created_objects:
            obj.select_set(True)
        context.view_layer.objects.active = created_objects[0]
        self.report({"INFO"}, f"Created or updated {len(created_objects)} ragdoll bodies")
        return {"FINISHED"}


class DOW2_OT_set_active_ragdoll_body_shape(Operator):
    """Set the active ragdoll rigid body's shape type using a fixed enum"""

    bl_idname = "dow2.set_active_ragdoll_body_shape"
    bl_label = "Set Active Ragdoll Body Shape"
    bl_options = {"REGISTER", "UNDO"}

    shape: EnumProperty(items=BODY_SHAPE_ITEMS)

    @classmethod
    def poll(cls, context):
        return resolve_ragdoll_body_object(context.active_object) is not None

    def execute(self, context):
        body_object = resolve_ragdoll_body_object(context.active_object)
        apply_body_data_to_object(body_object, {"shape_type": self.shape.lower()}, apply_world_transform=False)
        self.report({"INFO"}, f"Set active rigid body shape to {self.shape.lower()}")
        return {"FINISHED"}


class DOW2_OT_set_active_ragdoll_constraint_type(Operator):
    """Set the joint type.

    Ragdoll Joint: Can swing freely in multiple directions within angular limits,
    like a shoulder, hip, or neck.

    Hinge Joint: Moves on one axis only, like a knee, elbow, or door hinge.
    """

    bl_idname = "dow2.set_active_ragdoll_constraint_type"
    bl_label = "Set Active Ragdoll Constraint Type"
    bl_options = {"REGISTER", "UNDO"}

    constraint_type: EnumProperty(
        items=[
            (
                "ragdoll",
                "Ragdoll",
                "Can swing freely in multiple directions within angular limits, like a shoulder, hip, or neck.",
            ),
            (
                "limited_hinge",
                "Limited Hinge",
                "Moves on one axis only, like a knee, elbow, or door hinge.",
            ),
        ]
    )

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        target_bone = active_ragdoll_bone(context)
        if target_bone is None or target_bone.parent is None:
            self.report({"ERROR"}, "Select a non-root ragdoll rigid body or linked bone first")
            return {"CANCELLED"}
        target_bone[RAGDOLL_CONSTRAINT_TYPE_PROP] = self.constraint_type
        self.report({"INFO"}, f"Set inferred constraint type to {self.constraint_type}")
        return {"FINISHED"}


class DOW2_OT_export_ragdoll_hkx(Operator):
    """Export the active scene armature as a native Havok 4.5.1 ragdoll HKX"""

    bl_idname = "dow2.export_ragdoll_hkx"
    bl_label = "Export Ragdoll HKX"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        settings = context.scene.dow2_ragdoll_settings

        try:
            armature = _resolve_active_armature(context)
            hkx_path = _resolve_export_path(settings.hkx_export_path, "ragdoll HKX")
            json_path = None
            if settings.export_json_sidecar:
                json_path = _resolve_export_path(settings.json_export_path, "ragdoll JSON sidecar")
            ragdoll_data = export_ragdoll_hkx(
                armature,
                hkx_path,
                json_path=json_path,
                auto_generate_missing_bodies=settings.auto_generate_missing_bodies,
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        suffix = " with JSON sidecar" if settings.export_json_sidecar else ""
        self.report(
            {"INFO"},
            f"Exported {len(ragdoll_data['rigid_bodies'])} rigid bodies and {len(ragdoll_data['constraints'])} constraints to HKX{suffix}",
        )
        return {"FINISHED"}