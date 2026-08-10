from typing import TYPE_CHECKING, Iterable, List, Optional, Set

import bpy

from ..material.schema import schema_material_variables
from . import utils as model_utils

if TYPE_CHECKING:
    from .exporter import DoW2ModelExporter


def collect_materials(material_names: Optional[Iterable[str]] = None) -> List[bpy.types.Material]:
    """Collect unique scene mesh materials, optionally filtered by name."""
    allowed_names: Optional[Set[str]] = set(material_names) if material_names is not None else None
    materials = []

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if model_utils.is_bounding_box_object(obj) or obj.name.startswith("BVOL_"):
            continue
        for slot in obj.material_slots:
            material = slot.material
            if material is None:
                continue
            if allowed_names is not None and material.name not in allowed_names:
                continue
            if material not in materials:
                materials.append(material)

    return materials


def export_materials(
    exporter: "DoW2ModelExporter",
    materials: Optional[List[bpy.types.Material]] = None,
) -> List[bpy.types.Material]:
    """Export materials matching MaxScript ExportMaterials."""
    print("Exporting materials...")

    if materials is None:
        materials = collect_materials()

    archive_path = exporter._get_archive_path()

    if not materials:
        print("No materials found")
        return materials

    for material in materials:
        exporter._export_single_material(material, archive_path)

    return materials


def export_single_material(exporter: "DoW2ModelExporter", mat: bpy.types.Material, archive_path: str):
    """Export a single material matching MaxScript material export."""
    mtrl_header_pos = exporter.writer.file.tell()
    mtrl_data_pos = exporter.writer.write_chunk_header("FOLD", "MTRL", 1, 0, mat.name, 0)

    shader_name = mat.get("dow2_shader", "dow2_default")

    info_size = 4 + len(shader_name)
    exporter.writer.write_chunk_header("DATA", "INFO", 1, info_size, "Material Info", -1)
    exporter.writer.write_long(len(shader_name))
    exporter.writer.write_str(shader_name)

    for var in schema_material_variables(mat, exporter.data_path):
        exporter._export_material_variable(var.name, var.value, archive_path, var.var_type)

    exporter.writer.update_chunk_size(mtrl_header_pos, mtrl_data_pos)
    print(f"Exported '{mat.name}' material")


def export_material_variable(exporter: "DoW2ModelExporter", var_name: str, value, archive_path: str, var_type=None):
    """Export a material variable matching MaxScript variable export."""
    var_header_pos = exporter.writer.file.tell()
    var_data_pos = exporter.writer.write_chunk_header("DATA", "XVAR", 1, 0, "Material Variable", -1)

    current_pos = exporter.writer.file.tell()
    exporter.writer.file.seek(var_header_pos + 4)
    exporter.writer.write_byte(0)
    exporter.writer.file.seek(current_pos)

    exporter.writer.write_long(len(var_name))
    exporter.writer.write_str(var_name)

    if var_type == 10 or (var_type is None and isinstance(value, bool)):
        exporter.writer.write_long(10)
        exporter.writer.write_long(1)
        exporter.writer.write_byte(1 if value else 0)
    elif var_type == 0 or (var_type is None and isinstance(value, int)):
        exporter.writer.write_long(0)
        exporter.writer.write_long(4)
        exporter.writer.write_long(int(value), unsigned=False)
    elif var_type == 1 or (var_type is None and isinstance(value, float)):
        exporter.writer.write_long(1)
        exporter.writer.write_long(4)
        exporter.writer.write_float(float(value))
    elif var_type == 9 or (var_type is None and isinstance(value, str)):
        tex_path = str(value or "")
        if tex_path.startswith(archive_path):
            rel_path = tex_path[len(archive_path):].lstrip("\\/")
        else:
            rel_path = tex_path
        if rel_path.lower().endswith(".dds"):
            rel_path = rel_path[:-4]
        exporter.writer.write_long(9)
        exporter.writer.write_long(len(rel_path) + 1)
        exporter.writer.write_str(rel_path)
        exporter.writer.write_byte(0)
    elif var_type in {3, 4, 5, 8} or (var_type is None and hasattr(value, "__len__")):
        arr = list(value)
        if var_type == 3 or (var_type is None and len(arr) == 2):
            exporter.writer.write_long(3)
            exporter.writer.write_long(8)
            for item in arr:
                exporter.writer.write_float(float(item))
        elif var_type == 4 or (var_type is None and len(arr) == 3):
            exporter.writer.write_long(4)
            exporter.writer.write_long(12)
            for item in arr:
                exporter.writer.write_float(float(item))
        elif var_type == 5 or (var_type is None and len(arr) == 4):
            exporter.writer.write_long(5)
            exporter.writer.write_long(16)
            for item in arr:
                exporter.writer.write_float(float(item))
        elif var_type == 8 or (var_type is None and len(arr) == 16):
            exporter.writer.write_long(8)
            exporter.writer.write_long(64)
            for item in arr:
                exporter.writer.write_float(float(item))

    exporter.writer.update_chunk_size(var_header_pos, var_data_pos)


__all__ = [
    "collect_materials",
    "export_material_variable",
    "export_materials",
    "export_single_material",
]