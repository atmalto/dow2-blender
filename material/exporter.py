from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Optional, Tuple

import bpy

from .data import MaterialVariable, RelicMaterialData
from .definitions import (
    VAR_TYPE_BOOL,
    VAR_TYPE_FLOAT,
    VAR_TYPE_FLOAT2,
    VAR_TYPE_FLOAT3,
    VAR_TYPE_FLOAT4,
    VAR_TYPE_INT,
    VAR_TYPE_MATRIX4,
    VAR_TYPE_TEXTURE,
)


class RelicMaterialExporter:
    """Exports Blender materials to Relic material format."""

    def __init__(self, data_path: str):
        self.data_path = data_path

    def _coerce_sequence_value(self, value: Any) -> Optional[Tuple[Any, ...]]:
        """Normalize Blender array-like custom properties into plain tuples for export."""
        if isinstance(value, (str, bytes, bytearray)):
            return None
        if isinstance(value, (list, tuple)):
            return tuple(value)
        if isinstance(value, Sequence):
            return tuple(value)
        if hasattr(value, "to_list"):
            converted = value.to_list()
            if isinstance(converted, list):
                return tuple(converted)
        try:
            return tuple(value)
        except TypeError:
            return None

    def export_material(self, mat: bpy.types.Material) -> RelicMaterialData:
        """Export a Blender material to Relic material data."""
        mat_data = RelicMaterialData(name=mat.name)
        mat_data.shader_name = mat.get("dow2_shader", "")
        mat_data.shader_path = mat.get("dow2_shader_path", "")

        for key in mat.keys():
            if not key.startswith("dow2_"):
                continue
            if key in ["dow2_shader", "dow2_shader_path"]:
                continue

            var_name = key[5:]
            value = mat[key]
            sequence_value = self._coerce_sequence_value(value)

            if isinstance(value, bool):
                var_type = VAR_TYPE_BOOL
            elif isinstance(value, int):
                var_type = VAR_TYPE_INT
            elif isinstance(value, float):
                var_type = VAR_TYPE_FLOAT
            elif isinstance(value, str):
                var_type = VAR_TYPE_TEXTURE
            elif sequence_value is not None:
                value = sequence_value
                if len(value) == 2:
                    var_type = VAR_TYPE_FLOAT2
                elif len(value) == 3:
                    var_type = VAR_TYPE_FLOAT3
                elif len(value) == 4:
                    var_type = VAR_TYPE_FLOAT4
                elif len(value) == 16:
                    var_type = VAR_TYPE_MATRIX4
                else:
                    continue
            else:
                continue

            mat_data.variables.append(MaterialVariable(name=var_name, var_type=var_type, value=value))

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