from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any, Optional, Tuple

import bpy

from .creator import RelicMaterialCreator
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


REBUILD_SKIP_DOW2_KEYS = {
    "dow2_shader",
    "dow2_shader_path",
    "dow2_shader_profile",
    "dow2_shader_vars",
    "dow2_is_relic_material",
    "dow2_force_unique_export_material",
}


def _coerce_material_sequence_value(value: Any) -> Optional[Tuple[Any, ...]]:
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


def material_to_relic_data(mat: bpy.types.Material, *, skip_ui_metadata: bool = True) -> RelicMaterialData:
    """Convert Blender custom properties back into builder-ready Relic material data."""
    mat_data = RelicMaterialData(name=mat.name)
    mat_data.shader_name = str(mat.get("dow2_shader", "") or "")
    mat_data.shader_path = str(mat.get("dow2_shader_path", "") or "")

    for key in mat.keys():
        if not key.startswith("dow2_"):
            continue
        if key in {"dow2_shader", "dow2_shader_path"}:
            continue
        if skip_ui_metadata and key in REBUILD_SKIP_DOW2_KEYS:
            continue

        var_name = key[5:]
        value = mat[key]
        sequence_value = _coerce_material_sequence_value(value)

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


def rebuild_material_graph(mat: bpy.types.Material, data_path: str = "") -> bpy.types.Material:
    """Rebuild a material node tree from its stored DoW2 custom properties."""
    creator = RelicMaterialCreator(data_path or os.getcwd())
    mat_data = material_to_relic_data(mat, skip_ui_metadata=True)
    return creator.create_material(mat_data)


__all__ = ["REBUILD_SKIP_DOW2_KEYS", "material_to_relic_data", "rebuild_material_graph"]