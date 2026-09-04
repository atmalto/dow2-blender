from __future__ import annotations

import os

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

from .. import export_ragdoll_hkx
from ..authoring import (
    BODY_SHAPE_ITEMS,
    RAGDOLL_CONSTRAINT_TYPE_PROP,
    active_ragdoll_bone,
    apply_body_shape_to_selected,
    apply_constraint_type_to_selected,
    create_or_update_bodies_for_selection,
    create_scene_ragdoll_skeleton,
    find_source_armature,
    resolved_creation_dimensions,
    resolve_ragdoll_body_object,
    resolve_selected_ragdoll_bones,
)
from ..importer import load_ragdoll_scene
from ..scene_importer import RagdollImporter
from .common import (
    _resolve_active_armature,
    _resolve_active_ragdoll_skeleton,
    _resolve_export_path,
    _resolve_selected_source_ragdoll_bone_order,
)
from ...utils import set_file_browser_start


def _resolve_existing_import_path(raw_path: str, label: str, expected_extensions: tuple[str, ...]) -> str:
    value = str(raw_path or "").strip()
    if not value:
        raise RuntimeError(f"Choose a {label} file first")

    path = os.path.abspath(bpy.path.abspath(value))
    if not os.path.isfile(path):
        raise RuntimeError(f"{label.capitalize()} file not found: {path}")

    extension = os.path.splitext(path)[1].lower()
    if extension not in expected_extensions:
        expected = " or ".join(expected_extensions)
        raise RuntimeError(f"{label.capitalize()} file must use {expected}")

    return path


class DOW2_OT_pick_ragdoll_import_path(Operator, ImportHelper):
    """Choose a ragdoll HKX file for import"""

    bl_idname = "dow2.pick_ragdoll_import_path"
    bl_label = "Choose Ragdoll HKX"
    bl_options = {"REGISTER"}

    filename_ext = ".hkx"
    filter_glob: StringProperty(default="*.hkx", options={"HIDDEN"})

    def invoke(self, context, event):
        settings = context.scene.dow2_ragdoll_settings
        self.filepath = str(settings.ragdoll_import_path or "")
        set_file_browser_start(self, context)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        context.scene.dow2_ragdoll_settings.ragdoll_import_path = self.filepath
        return {"FINISHED"}


class DOW2_OT_pick_ragdoll_model_path(Operator, ImportHelper):
    """Choose the companion DoW2 model file for ragdoll import"""

    bl_idname = "dow2.pick_ragdoll_model_path"
    bl_label = "Choose Companion Model"
    bl_options = {"REGISTER"}

    filename_ext = ".model"
    filter_glob: StringProperty(default="*.model", options={"HIDDEN"})

    def invoke(self, context, event):
        settings = context.scene.dow2_ragdoll_settings
        self.filepath = str(settings.ragdoll_model_path or "")
        set_file_browser_start(self, context)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        context.scene.dow2_ragdoll_settings.ragdoll_model_path = self.filepath
        return {"FINISHED"}


class DOW2_OT_import_ragdoll_hkx(Operator):
    """Import a Havok ragdoll HKX and build normal authored ragdoll scene state"""

    bl_idname = "dow2.import_ragdoll_hkx"
    bl_label = "Import Ragdoll HKX"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and context.scene is not None

    def execute(self, context):
        settings = context.scene.dow2_ragdoll_settings

        try:
            ragdoll_path = _resolve_existing_import_path(
                settings.ragdoll_import_path,
                "ragdoll HKX",
                (".hkx",),
            )
            model_path = None
            if (settings.ragdoll_model_path or "").strip():
                model_path = _resolve_existing_import_path(
                    settings.ragdoll_model_path,
                    "companion model",
                    (".model",),
                )
            scene_data = load_ragdoll_scene(ragdoll_path)
            importer = RagdollImporter()
            target_name = (settings.ragdoll_name or "").strip() or None
            skeleton_object = importer.import_scene(
                context,
                ragdoll_path,
                model_path=model_path,
                ragdoll_name=target_name,
            )
        except Exception as exc:
            self.report({"ERROR"}, f"Ragdoll import failed: {exc}")
            return {"CANCELLED"}

        settings.ragdoll_last_import_name = skeleton_object.name
        settings.ragdoll_last_import_collection = (
            skeleton_object.users_collection[0].name if skeleton_object.users_collection else ""
        )
        settings.ragdoll_last_import_source_format = str(scene_data.source_format or "").upper()
        settings.ragdoll_last_import_body_count = len(scene_data.rigid_bodies)
        settings.ragdoll_last_import_constraint_count = len(scene_data.constraints)

        self.report(
            {"INFO"},
            (
                f"Imported ragdoll {skeleton_object.name}: "
                f"bones={len(scene_data.ragdoll_skeleton.bones)}, "
                f"bodies={len(scene_data.rigid_bodies)}, "
                f"constraints={len(scene_data.constraints)}"
            ),
        )
        return {"FINISHED"}


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
            body_radius, body_height, body_length = resolved_creation_dimensions(
                settings.body_shape,
                settings.body_radius,
                settings.body_height,
                settings.body_length,
            )
            created_objects = create_or_update_bodies_for_selection(
                context,
                skeleton_object,
                bone_names,
                settings.body_shape,
                body_radius,
                body_height,
                body_length,
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
        changed_bodies = apply_body_shape_to_selected(context, self.shape)
        if not changed_bodies:
            self.report({"ERROR"}, "Select a compatible ragdoll rigid body first")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Set {len(changed_bodies)} rigid bod{'y' if len(changed_bodies) == 1 else 'ies'} to {self.shape.lower()}")
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
        changed_bones = apply_constraint_type_to_selected(context, self.constraint_type)
        if not changed_bones:
            self.report({"ERROR"}, "Select one or more compatible non-root ragdoll bodies first")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Set inferred constraint type to {self.constraint_type} on {len(changed_bones)} joint{'s' if len(changed_bones) != 1 else ''}")
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