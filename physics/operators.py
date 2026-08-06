from __future__ import annotations

import os
from typing import Dict, List

import bpy
from bpy.props import FloatProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from mathutils import Vector

from ..utils import dx_to_blender_position
from . import exporter, importer, presets, utils


def _workflow_label(settings) -> str:
    if settings.workflow == "BONE_INFLUENCES":
        return "selected bones" if settings.use_selected_only else "all owner bones"
    return "selected meshes" if settings.use_selected_only else "all source meshes"


class DOW2_OT_generate_physics_hulls(Operator):
    """Generate convex hulls into DoW2 Physics bins"""

    bl_idname = "dow2.generate_physics_hulls"
    bl_label = "Generate Hulls"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and context.scene is not None

    def execute(self, context):
        scene = context.scene
        settings = scene.dow2_physics_settings

        selected_bones = None
        selected_only = settings.use_selected_only and settings.workflow == "MESH_OBJECTS"
        source_meshes = utils.collect_source_meshes(scene, selected_only=selected_only)
        if not source_meshes:
            self.report({"ERROR"}, "No source meshes found under damage-state collections")
            return {"CANCELLED"}

        if settings.workflow == "BONE_INFLUENCES" and settings.use_selected_only:
            selected_bones = utils.get_selected_source_bone_names(context)
            if not selected_bones:
                self.report({"ERROR"}, "No selected source bones found")
                return {"CANCELLED"}

        armature_obj = utils.ensure_physics_armature(scene) if settings.workflow == "MESH_OBJECTS" else None
        generated_hulls = 0

        if settings.workflow == "BONE_INFLUENCES":
            for state_name, lod_map in source_meshes.items():
                for lod_level, meshes in lod_map.items():
                    vertices_by_bone = utils.collect_vertices_for_bones(meshes, selected_bones=selected_bones)
                    for bone_name, world_vertices in sorted(vertices_by_bone.items(), key=lambda item: item[0].lower()):
                        if len(world_vertices) < 4:
                            continue
                        hull_obj = utils.create_or_replace_hull_object(
                            scene,
                            state_name,
                            lod_level,
                            bone_name,
                            world_vertices,
                            settings.workflow,
                            None,
                            settings.generation_preset,
                        )
                        if hull_obj is not None:
                            generated_hulls += 1
        else:
            for state_name, lod_map in source_meshes.items():
                for lod_level, meshes in lod_map.items():
                    for mesh_obj in meshes:
                        body_name = mesh_obj.name
                        world_vertices = utils.gather_mesh_world_vertices(mesh_obj)
                        if len(world_vertices) < 4:
                            continue
                        utils.ensure_physics_bone(armature_obj, body_name, utils.compute_centroid(world_vertices))
                        hull_obj = utils.create_or_replace_hull_object(
                            scene,
                            state_name,
                            lod_level,
                            body_name,
                            world_vertices,
                            settings.workflow,
                            armature_obj,
                            settings.generation_preset,
                        )
                        if hull_obj is not None:
                            generated_hulls += 1

        if generated_hulls == 0:
            self.report({"WARNING"}, f"No hulls generated using {_workflow_label(settings)}")
            return {"CANCELLED"}

        state_count = utils.count_nonempty_state_bins(scene)
        self.report({"INFO"}, f"Generated {generated_hulls} hull(s) across {state_count} populated physics state bin(s)")
        return {"FINISHED"}


class DOW2_OT_export_physics_hulls(Operator, ExportHelper):
    """Export generated physics hulls to HKX"""

    bl_idname = "dow2.export_physics_hulls"
    bl_label = "Export Hulls"
    bl_options = {"REGISTER"}

    filename_ext = ".hkx"
    filter_glob: StringProperty(default="*.hkx", options={"HIDDEN"})

    def invoke(self, context, event):
        if not self.filepath:
            default_name = "dow2_physics_export.hkx"
            self.filepath = os.path.join(exporter.ADDON_PATH, "destruction_physics", "outputs", default_name)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        scene = context.scene
        settings = scene.dow2_physics_settings
        physics_systems = exporter.build_physics_systems(scene)
        if not physics_systems:
            self.report({"ERROR"}, "No generated hulls found in physics bins")
            return {"CANCELLED"}

        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        json_path = os.path.splitext(self.filepath)[0] + ".json"
        exporter.export_physics_json(physics_systems, json_path)
        success, output = exporter.run_physics_exporter(json_path, self.filepath)
        if not success:
            self.report({"ERROR"}, output or "Physics exporter failed")
            return {"CANCELLED"}

        body_count = sum(len(system.rigid_bodies) for system in physics_systems)
        self.report({"INFO"}, f"Exported {len(physics_systems)} physics system(s) and {body_count} hull body(ies)")
        if output:
            print(output)
        return {"FINISHED"}


class DOW2_OT_import_physics_hulls(Operator):
    """Import physics hulls from HKX"""

    bl_idname = "dow2.import_physics_hulls"
    bl_label = "Import Hulls"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        scene = context.scene
        settings = scene.dow2_physics_settings
        filepath = bpy.path.abspath(settings.import_filepath).strip()
        if not filepath:
            self.report({"ERROR"}, "Choose a physics HKX file to import")
            return {"CANCELLED"}

        try:
            imported_scene = importer.load_physics_scene(filepath)
        except importer.PhysicsImportError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        utils.delete_physics_hulls(scene)

        created_objects = []
        for rigid_body in imported_scene.rigid_bodies:
            blender_vertices = [
                list(dx_to_blender_position(Vector(vertex)))
                for vertex in rigid_body.vertices
            ]
            hull_obj = utils.create_or_replace_hull_object(
                scene,
                rigid_body.state_name,
                rigid_body.lod_level,
                rigid_body.name,
                blender_vertices,
                "HKX_IMPORT",
                None,
                presets.infer_preset_from_motion_type(rigid_body.motion_type),
                imported_config=rigid_body.export_config,
            )
            if hull_obj is None:
                continue
            hull_obj["dow2_physics_motion_type"] = rigid_body.motion_type
            hull_obj["dow2_physics_source_system"] = rigid_body.system_name
            created_objects.append(hull_obj)

        if not created_objects:
            self.report({"ERROR"}, "No importable convex hulls were found in the selected file")
            return {"CANCELLED"}

        bpy.ops.object.select_all(action="DESELECT")
        for obj in created_objects:
            obj.select_set(True)
        context.view_layer.objects.active = created_objects[0]

        state_count = utils.count_nonempty_state_bins(scene)
        self.report(
            {"INFO"},
            f"Imported {len(created_objects)} hull(s) across {state_count} populated physics state bin(s)",
        )
        return {"FINISHED"}


class DOW2_OT_clear_physics_hulls(Operator):
    """Delete generated physics hulls and the dedicated physics armature"""

    bl_idname = "dow2.clear_physics_hulls"
    bl_label = "Clear Hulls"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        deleted_count = utils.delete_physics_hulls(context.scene)
        self.report({"INFO"}, f"Cleared {deleted_count} generated hull(s)")
        return {"FINISHED"}


class DOW2_OT_isolate_physics_hulls(Operator):
    """Hide all non-hull objects"""

    bl_idname = "dow2.isolate_physics_hulls"
    bl_label = "Show Hulls"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        changed = utils.set_hull_visibility(context.scene, isolate_hulls=True)
        self.report({"INFO"}, f"Updated visibility on {changed} object(s)")
        return {"FINISHED"}


class DOW2_OT_hide_physics_hulls(Operator):
    """Hide only generated hulls and reveal non-hull objects"""

    bl_idname = "dow2.hide_physics_hulls"
    bl_label = "Hide Hulls"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        changed = utils.set_hull_visibility(context.scene, isolate_hulls=False)
        self.report({"INFO"}, f"Updated visibility on {changed} object(s)")
        return {"FINISHED"}


class DOW2_OT_set_selected_hull_physics_value(Operator):
    """Apply a quick-set physics value to the active hull"""

    bl_idname = "dow2.set_selected_hull_physics_value"
    bl_label = "Set Hull Physics Value"
    bl_options = {"INTERNAL", "UNDO"}

    property_name: StringProperty()
    value: FloatProperty()

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and utils.is_physics_hull_object(context.active_object)

    def execute(self, context):
        settings = context.active_object.dow2_physics_hull_settings
        current_value = getattr(settings, self.property_name)
        if isinstance(current_value, int) and not isinstance(current_value, bool):
            setattr(settings, self.property_name, int(round(self.value)))
        else:
            setattr(settings, self.property_name, self.value)
        return {"FINISHED"}


classes = [
    DOW2_OT_generate_physics_hulls,
    DOW2_OT_import_physics_hulls,
    DOW2_OT_export_physics_hulls,
    DOW2_OT_clear_physics_hulls,
    DOW2_OT_isolate_physics_hulls,
    DOW2_OT_hide_physics_hulls,
    DOW2_OT_set_selected_hull_physics_value,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)