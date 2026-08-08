import os

import bpy

from .definitions import BOOL_PARAMS, FLOAT_PARAMS, INT_PARAMS, TEXTURE_SLOTS
from .rebuild import rebuild_material_graph
from .schema import ensure_material_schema_properties, get_shader_schema
from ..utils import get_active_data_root


_TEXTURE_SLOT_NAMES = {slot_name for slot_name, _label in TEXTURE_SLOTS}
_BOOL_PARAM_DEFAULTS = {param: False for param, _label in BOOL_PARAMS}
_INT_PARAM_DEFAULTS = {param: 0 for param, _label in INT_PARAMS}
_FLOAT_PARAM_DEFAULTS = {param: default for param, _label, default in FLOAT_PARAMS}


def resolve_dow2_data_path(context, fallback_path: str = "") -> str:
    root = get_active_data_root(context)
    if root:
        return root
    return fallback_path or os.getcwd()


def ensure_relic_material_property_defaults(mat: bpy.types.Material) -> None:
    mat["dow2_is_relic_material"] = True
    for param, default in _BOOL_PARAM_DEFAULTS.items():
        prop_name = f"dow2_{param}"
        if prop_name not in mat:
            mat[prop_name] = default
    for param, default in _INT_PARAM_DEFAULTS.items():
        prop_name = f"dow2_{param}"
        if prop_name not in mat:
            mat[prop_name] = default
    for param, default in _FLOAT_PARAM_DEFAULTS.items():
        prop_name = f"dow2_{param}"
        if prop_name not in mat:
            mat[prop_name] = default


def seed_declared_shader_properties(mat: bpy.types.Material, shader_vars) -> None:
    for var_name in shader_vars:
        prop_name = f"dow2_{var_name}"
        if var_name in _TEXTURE_SLOT_NAMES:
            if prop_name not in mat:
                mat[prop_name] = ""
        elif var_name in _BOOL_PARAM_DEFAULTS:
            if prop_name not in mat:
                mat[prop_name] = _BOOL_PARAM_DEFAULTS[var_name]
        elif var_name in _INT_PARAM_DEFAULTS:
            if prop_name not in mat:
                mat[prop_name] = _INT_PARAM_DEFAULTS[var_name]
        elif var_name in _FLOAT_PARAM_DEFAULTS:
            if prop_name not in mat:
                mat[prop_name] = _FLOAT_PARAM_DEFAULTS[var_name]


def rebuild_dow2_material_graph(context, mat: bpy.types.Material, fallback_path: str = "") -> None:
    rebuild_material_graph(mat, resolve_dow2_data_path(context, fallback_path))


def configure_relic_material(
    context,
    mat: bpy.types.Material,
    *,
    shader_name: str,
    shader_path: str = "",
    shader_vars=(),
    param_overrides=None,
    rebuild: bool = True,
) -> None:
    mat.use_nodes = True
    mat["dow2_shader"] = shader_name or ""
    mat["dow2_shader_path"] = shader_path or ""

    schema = get_shader_schema(shader_name, shader_path, resolve_dow2_data_path(context, ""))
    declared_vars = schema.names() or list(shader_vars or [])
    if declared_vars:
        mat["dow2_shader_vars"] = ",".join(declared_vars)
    elif "dow2_shader_vars" in mat:
        del mat["dow2_shader_vars"]

    mat["dow2_is_relic_material"] = True
    if schema.variables:
        ensure_material_schema_properties(mat, schema)
    else:
        ensure_relic_material_property_defaults(mat)
        seed_declared_shader_properties(mat, shader_vars)

    if param_overrides:
        for param_name, value in param_overrides.items():
            if not schema.variables or schema.get(param_name) is not None:
                mat[f"dow2_{param_name}"] = value

    if rebuild:
        rebuild_dow2_material_graph(context, mat, shader_path)


def is_relic_material(mat: bpy.types.Material) -> bool:
    if mat is None:
        return False
    return mat.get("dow2_is_relic_material", False) or "dow2_shader" in mat


__all__ = [
    "configure_relic_material",
    "ensure_relic_material_property_defaults",
    "is_relic_material",
    "rebuild_dow2_material_graph",
    "resolve_dow2_data_path",
    "seed_declared_shader_properties",
]