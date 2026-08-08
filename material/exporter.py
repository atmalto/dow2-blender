from __future__ import annotations

import bpy

from .data import MaterialVariable, RelicMaterialData
from .schema import schema_material_variables


class RelicMaterialExporter:
    """Exports Blender materials to Relic material format."""

    def __init__(self, data_path: str):
        self.data_path = data_path

    def export_material(self, mat: bpy.types.Material) -> RelicMaterialData:
        """Export a Blender material to Relic material data."""
        mat_data = RelicMaterialData(name=mat.name)
        mat_data.shader_name = mat.get("dow2_shader", "")
        mat_data.shader_path = mat.get("dow2_shader_path", "")

        mat_data.variables.extend(schema_material_variables(mat, self.data_path))

        return mat_data

    def write_material_variable(self, writer, var: MaterialVariable, data_path: str):
        """Write a material variable to file."""
        writer.write_long(len(var.name))
        writer.write_str(var.name)
        writer.write_long(var.var_type)

        if var.var_type == VAR_TYPE_INT:
            writer.write_long(4)
            writer.write_long(var.value, unsigned=False)
        elif var.var_type == VAR_TYPE_FLOAT:
            writer.write_long(4)
            writer.write_float(var.value)
        elif var.var_type == VAR_TYPE_FLOAT2:
            writer.write_long(8)
            writer.write_float(var.value[0])
            writer.write_float(var.value[1])
        elif var.var_type == VAR_TYPE_FLOAT3:
            writer.write_long(12)
            writer.write_float(var.value[0])
            writer.write_float(var.value[1])
            writer.write_float(var.value[2])
        elif var.var_type == VAR_TYPE_FLOAT4:
            writer.write_long(16)
            for item in var.value[:4]:
                writer.write_float(item)
        elif var.var_type == VAR_TYPE_MATRIX4:
            writer.write_long(64)
            for item in var.value[:16]:
                writer.write_float(item)
        elif var.var_type == VAR_TYPE_TEXTURE:
            tex_path = var.value
            if tex_path and data_path:
                if tex_path.lower().startswith(data_path.lower()):
                    tex_path = tex_path[len(data_path):].lstrip('\\').lstrip('/')
                if tex_path.lower().endswith('.dds'):
                    tex_path = tex_path[:-4]

            writer.write_long(len(tex_path) + 1)
            writer.write_str(tex_path)
            writer.write_byte(0)
        elif var.var_type == VAR_TYPE_BOOL:
            writer.write_long(1)
            writer.write_byte(1 if var.value else 0)


_material_exporter: Optional[RelicMaterialExporter] = None


def get_material_exporter(data_path: str) -> RelicMaterialExporter:
    global _material_exporter
    _material_exporter = RelicMaterialExporter(data_path)
    return _material_exporter


__all__ = ["RelicMaterialExporter", "get_material_exporter"]