# DoW2 Model Exporter - Matching MaxScript ST2Export exactly
import os
from typing import Dict, List, Optional

import bpy
from mathutils import Vector

from ..chunk_lib import ChunkWriter
from .export_operators import (
    DOW2_OT_confirm_overwrite,
    DOW2_OT_export_material_warning,
    DOW2_OT_export_model,
    DOW2_OT_export_skip_materials,
    menu_func_export,
    register,
    unregister,
)
from .export_utils import (
    DAMAGE_STATE_ITEMS,
    ExportOptions,
    ExportSkinBone,
    ExportSubMesh,
    ExportVertex,
    blender_to_dx_normal,
    blender_to_dx_position,
    get_or_create_default_material,
    is_relic_material,
    validate_materials_for_export,
    weights_to_bytes,
)
from .exporter_materials import collect_materials, export_material_variable, export_materials, export_single_material
from .exporter_meshes import (
    collect_mesh_groups,
    compute_tangent_space,
    export_bounding_volumes,
    export_mesh_group,
    export_mesh_groups,
    export_meshes,
    export_sub_mesh,
    find_or_add_vertex,
    make_vertex_key,
    process_mesh_object,
    update_bounds,
    update_bounds_obj,
    write_bounding_volume,
    write_vertex,
    write_vertex_elements,
)
from .exporter_scene import export_bounding_box, export_data_templates, export_model_states, get_archive_path
from .exporter_skeleton import (
    add_bone_recursive,
    collect_armature_bones,
    collect_bone_hierarchy,
    export_bones,
    export_markers,
    get_or_create_skeleton_root,
    get_skeleton_root,
)


class DoW2ModelExporter:
    def __init__(self, filepath: str, options: ExportOptions):
        self.filepath = filepath
        self.options = options
        self.writer: Optional[ChunkWriter] = None
        self.data_path = os.path.dirname(filepath)
        self.bones: List[bpy.types.Object] = []
        self.bone_names: List[str] = []
        self.warnings: List[str] = []
        self._warning_keys = set()

    def export_model(self):
        print(f"Exporting: {self.filepath}")

        with open(self.filepath, "wb") as file:
            self.writer = ChunkWriter(file)
            self.writer.write_relic_chunky()

            modl_header_pos = file.tell()
            modl_data_pos = self.writer.write_chunk_header("FOLD", "MODL", 1, 0, None, 0)

            mesh_groups = []
            collected_materials = []
            if self.options.export_materials or self.options.export_mesh:
                collected_materials = self._collect_materials()

            if self.options.export_mesh:
                mesh_groups = self._collect_mesh_groups(collected_materials)

            materials = []
            if self.options.export_materials:
                material_names = self._collect_used_material_names(mesh_groups) if mesh_groups else None
                materials = self._collect_materials(material_names)
                self._export_materials(materials)

            if self.options.export_mesh:
                self._export_mesh_groups(mesh_groups)

            if self.options.export_markers:
                self._export_markers()

            if self.options.export_bones:
                self._export_bones()

            self._export_model_states(mesh_groups)
            self._export_data_templates()

            self.writer.update_chunk_size(modl_header_pos, modl_data_pos)

        if self.options.export_simbox:
            self._export_bounding_box("simbox")

        if self.options.export_coverbox:
            self._export_bounding_box("coverbox")

        print("Export complete")
        return {"FINISHED"}

    def _export_bounding_box(self, box_type: str):
        export_bounding_box(self, box_type)

    def _get_archive_path(self) -> str:
        return get_archive_path(self)

    def _collect_materials(self, material_names=None) -> List[bpy.types.Material]:
        return collect_materials(material_names)

    def _export_materials(self, materials: Optional[List[bpy.types.Material]] = None) -> List[bpy.types.Material]:
        return export_materials(self, materials)

    def _export_single_material(self, mat: bpy.types.Material, archive_path: str):
        export_single_material(self, mat, archive_path)

    def _export_material_variable(self, var_name: str, value, archive_path: str):
        export_material_variable(self, var_name, value, archive_path)

    def _get_or_create_skeleton_root(self) -> Optional[bpy.types.Object]:
        return get_or_create_skeleton_root(self)

    def _get_skeleton_root(self) -> Optional[bpy.types.Object]:
        return get_skeleton_root(self)

    def _export_bones(self):
        export_bones(self)

    def _collect_armature_bones(self, armature_obj: bpy.types.Object):
        collect_armature_bones(self, armature_obj)

    def _add_bone_recursive(self, bone, parent_idx: int, armature_obj: bpy.types.Object):
        add_bone_recursive(self, bone, parent_idx, armature_obj)

    def _collect_bone_hierarchy(self, obj: bpy.types.Object, parent_idx: int):
        collect_bone_hierarchy(self, obj, parent_idx)

    def _export_markers(self):
        export_markers(self)

    def _export_meshes(self, materials: List[bpy.types.Material]) -> List[str]:
        return export_meshes(self, materials)

    def _export_mesh_groups(self, mesh_groups: Dict[str, List[List[ExportSubMesh]]]) -> List[str]:
        return export_mesh_groups(self, mesh_groups)

    def _collect_mesh_groups(self, materials: List[bpy.types.Material]) -> Dict[str, List[List[ExportSubMesh]]]:
        return collect_mesh_groups(self, materials)

    def _collect_used_material_names(self, mesh_groups: Dict[str, List[List[ExportSubMesh]]]) -> List[str]:
        used_names = []
        for lods in mesh_groups.values():
            for lod_meshes in lods:
                for sub_mesh in lod_meshes:
                    if sub_mesh.material_name and sub_mesh.material_name not in used_names:
                        used_names.append(sub_mesh.material_name)
        return used_names

    def _process_mesh_object(self, obj: bpy.types.Object, materials: List[bpy.types.Material], base_name: str) -> List[ExportSubMesh]:
        return process_mesh_object(self, obj, materials, base_name)

    def _compute_tangent_space(self, sub_mesh: ExportSubMesh):
        compute_tangent_space(self, sub_mesh)

    def _make_vertex_key(self, vert: ExportVertex, orig_vert_normal: tuple = None) -> tuple:
        return make_vertex_key(self, vert, orig_vert_normal)

    def _find_or_add_vertex(self, sub_mesh: ExportSubMesh, vert: ExportVertex, orig_vert_normal: tuple = None) -> int:
        return find_or_add_vertex(self, sub_mesh, vert, orig_vert_normal)

    def _update_bounds(self, sub_mesh: ExportSubMesh, pos: Vector):
        update_bounds(self, sub_mesh, pos)

    def _update_bounds_obj(self, obj, pos: Vector):
        update_bounds_obj(self, obj, pos)

    def _export_mesh_group(self, group_name: str, lods: List[List[ExportSubMesh]]):
        export_mesh_group(self, group_name, lods)

    def _export_sub_mesh(self, sub_mesh: ExportSubMesh):
        export_sub_mesh(self, sub_mesh)

    def _write_vertex_elements(self, sub_mesh: ExportSubMesh) -> int:
        return write_vertex_elements(self, sub_mesh)

    def _write_vertex(self, vert: ExportVertex, sub_mesh: ExportSubMesh):
        write_vertex(self, vert, sub_mesh)

    def _export_bounding_volumes(self, sub_mesh: ExportSubMesh):
        export_bounding_volumes(self, sub_mesh)

    def _write_bounding_volume(self, vmin: Optional[Vector], vmax: Optional[Vector]):
        write_bounding_volume(self, vmin, vmax)

    def _export_model_states(self, mesh_groups: List[str]):
        export_model_states(self, mesh_groups)

    def _export_data_templates(self):
        export_data_templates(self)


__all__ = [
    "DAMAGE_STATE_ITEMS",
    "DOW2_OT_confirm_overwrite",
    "DOW2_OT_export_material_warning",
    "DOW2_OT_export_model",
    "DOW2_OT_export_skip_materials",
    "DoW2ModelExporter",
    "ExportOptions",
    "ExportSkinBone",
    "ExportSubMesh",
    "ExportVertex",
    "blender_to_dx_normal",
    "blender_to_dx_position",
    "get_or_create_default_material",
    "is_relic_material",
    "menu_func_export",
    "register",
    "unregister",
    "validate_materials_for_export",
    "weights_to_bytes",
]