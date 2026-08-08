from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Iterable, Optional

from .data import MaterialVariable, RelicMaterialData
from .definitions import (
    FLOAT_PARAMS,
    INT_PARAMS,
    VAR_TYPE_BOOL,
    VAR_TYPE_FLOAT,
    VAR_TYPE_FLOAT2,
    VAR_TYPE_FLOAT3,
    VAR_TYPE_FLOAT4,
    VAR_TYPE_INT,
    VAR_TYPE_MATRIX4,
    VAR_TYPE_TEXTURE,
)


_BUNDLED_SHADER_DIR = os.path.join(os.path.dirname(__file__), "dow2_.asm_and_.shader")
_LINE_VALUE_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>[^,]+),?")


@dataclass(frozen=True)
class ShaderVariableSchema:
    name: str
    shader_type: str
    var_type: int
    mode: str = ""


@dataclass(frozen=True)
class ShaderSchema:
    shader_name: str
    path: str = ""
    variables: tuple[ShaderVariableSchema, ...] = field(default_factory=tuple)

    def names(self) -> list[str]:
        return [var.name for var in self.variables]

    def get(self, name: str) -> Optional[ShaderVariableSchema]:
        for var in self.variables:
            if var.name == name:
                return var
        return None


def normalize_shader_type(shader_type: str) -> str:
    return str(shader_type or "").strip().lower()


def shader_type_to_var_type(shader_type: str) -> Optional[int]:
    normalized = normalize_shader_type(shader_type)
    if normalized == "int":
        return VAR_TYPE_INT
    if normalized == "bool":
        return VAR_TYPE_BOOL
    if normalized == "float":
        return VAR_TYPE_FLOAT
    if normalized in {"vector2f", "float2"}:
        return VAR_TYPE_FLOAT2
    if normalized in {"vector3f", "float3"}:
        return VAR_TYPE_FLOAT3
    if normalized in {"vector4f", "float4"}:
        return VAR_TYPE_FLOAT4
    if normalized == "matrix4f":
        return VAR_TYPE_MATRIX4
    if normalized == "texture":
        return VAR_TYPE_TEXTURE
    return None


def is_editable_scalar_variable(var: ShaderVariableSchema) -> bool:
    return var.var_type in {VAR_TYPE_BOOL, VAR_TYPE_INT, VAR_TYPE_FLOAT}


def is_texture_variable(var: ShaderVariableSchema) -> bool:
    return var.var_type == VAR_TYPE_TEXTURE


def default_value_for_schema_var(var: ShaderVariableSchema) -> Any:
    if var.var_type == VAR_TYPE_BOOL:
        return False
    if var.var_type == VAR_TYPE_INT:
        return 0
    if var.var_type == VAR_TYPE_FLOAT:
        for name, _label, default in FLOAT_PARAMS:
            if name == var.name:
                return float(default)
        return 0.0
    if var.var_type == VAR_TYPE_TEXTURE:
        return ""
    if var.var_type == VAR_TYPE_FLOAT2:
        return [0.0, 0.0]
    if var.var_type == VAR_TYPE_FLOAT3:
        lower_name = var.name.lower()
        if "colour" in lower_name or "color" in lower_name:
            return [1.0, 1.0, 1.0]
        return [0.0, 0.0, 0.0]
    if var.var_type == VAR_TYPE_FLOAT4:
        lower_name = var.name.lower()
        if "matrixrow1row2" in lower_name:
            return [1.0, 0.0, 0.0, 1.0]
        if "colour" in lower_name or "color" in lower_name:
            return [1.0, 1.0, 1.0, 1.0]
        return [0.0, 0.0, 0.0, 0.0]
    if var.var_type == VAR_TYPE_MATRIX4:
        return [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ]
    return None


def material_data_from_shader_schema(material_name: str, schema: ShaderSchema) -> RelicMaterialData:
    mat_data = RelicMaterialData(name=material_name, shader_name=schema.shader_name, shader_path=schema.path)
    for var in schema.variables:
        value = default_value_for_schema_var(var)
        if value is not None:
            mat_data.variables.append(MaterialVariable(name=var.name, var_type=var.var_type, value=value))
    return mat_data


def shader_param_label(name: str) -> str:
    for param, label in INT_PARAMS:
        if param == name:
            return label
    for param, label, _default in FLOAT_PARAMS:
        if param == name:
            return label

    label = re.sub(r"(?<!^)(?=[A-Z])", " ", name).replace("_", " ").strip()
    return label[:1].upper() + label[1:] if label else name


def _clean_shader_value(raw_value: str) -> str:
    value = str(raw_value or "").strip().rstrip(",").strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value


@lru_cache(maxsize=256)
def parse_shader_schema_file(filepath: str) -> ShaderSchema:
    path = os.path.abspath(filepath) if filepath else ""
    shader_name = os.path.splitext(os.path.basename(path))[0] if path else ""
    if not path or not os.path.isfile(path):
        return ShaderSchema(shader_name=shader_name, path=path)

    variables: list[ShaderVariableSchema] = []
    current: dict[str, str] = {}

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = _LINE_VALUE_RE.match(line.strip())
            if not match:
                continue

            key = match.group("key")
            value = _clean_shader_value(match.group("value"))
            if key in {"name", "type", "mode"}:
                current[key] = value

            name = current.get("name")
            shader_type = current.get("type")
            if name and shader_type:
                var_type = shader_type_to_var_type(shader_type)
                if var_type is not None:
                    variables.append(
                        ShaderVariableSchema(
                            name=name,
                            shader_type=shader_type,
                            var_type=var_type,
                            mode=current.get("mode", ""),
                        )
                    )
                current = {}

    return ShaderSchema(shader_name=shader_name, path=path, variables=tuple(variables))


def find_shader_schema_path(shader_name: str, shader_path: str = "", data_path: str = "") -> str:
    if shader_path and os.path.isfile(shader_path):
        return os.path.abspath(shader_path)

    shader_stem = os.path.splitext(os.path.basename(str(shader_name or "")))[0]
    if not shader_stem:
        return ""

    candidates = []
    if data_path:
        candidates.append(os.path.join(data_path, "shaders", f"{shader_stem}.shader"))
    if shader_path:
        candidates.append(os.path.join(os.path.dirname(shader_path), f"{shader_stem}.shader"))
    candidates.append(os.path.join(_BUNDLED_SHADER_DIR, f"{shader_stem}.shader"))

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return ""


def get_shader_schema(shader_name: str, shader_path: str = "", data_path: str = "") -> ShaderSchema:
    path = find_shader_schema_path(shader_name, shader_path, data_path)
    if path:
        return parse_shader_schema_file(path)
    return ShaderSchema(shader_name=os.path.splitext(os.path.basename(str(shader_name or "")))[0])


def shader_schema_for_material(mat: Any, data_path: str = "") -> ShaderSchema:
    if mat is None:
        return ShaderSchema(shader_name="")
    return get_shader_schema(str(mat.get("dow2_shader", "") or ""), str(mat.get("dow2_shader_path", "") or ""), data_path)


def ensure_material_schema_properties(mat: Any, schema: ShaderSchema) -> None:
    if mat is None:
        return
    if schema.variables:
        mat["dow2_shader_vars"] = ",".join(schema.names())
    for var in schema.variables:
        if not (is_editable_scalar_variable(var) or is_texture_variable(var)):
            continue
        prop_name = f"dow2_{var.name}"
        if prop_name not in mat:
            mat[prop_name] = default_value_for_schema_var(var)


def coerce_schema_value(var: ShaderVariableSchema, value: Any) -> Any:
    if var.var_type == VAR_TYPE_BOOL:
        return bool(value)
    if var.var_type == VAR_TYPE_INT:
        return int(value)
    if var.var_type == VAR_TYPE_FLOAT:
        return float(value)
    if var.var_type == VAR_TYPE_TEXTURE:
        return str(value or "")
    if var.var_type in {VAR_TYPE_FLOAT2, VAR_TYPE_FLOAT3, VAR_TYPE_FLOAT4, VAR_TYPE_MATRIX4}:
        values = list(value)
        expected_lengths = {
            VAR_TYPE_FLOAT2: 2,
            VAR_TYPE_FLOAT3: 3,
            VAR_TYPE_FLOAT4: 4,
            VAR_TYPE_MATRIX4: 16,
        }
        expected_length = expected_lengths[var.var_type]
        if len(values) < expected_length:
            raise ValueError(f"{var.name} needs {expected_length} values")
        return [float(item) for item in values[:expected_length]]
    return value


def schema_material_variables(mat: Any, data_path: str = "") -> list[MaterialVariable]:
    schema = shader_schema_for_material(mat, data_path)
    if not schema.variables:
        return []

    variables: list[MaterialVariable] = []
    for var in schema.variables:
        prop_name = f"dow2_{var.name}"
        if prop_name not in mat:
            continue
        try:
            value = coerce_schema_value(var, mat[prop_name])
        except (TypeError, ValueError):
            continue
        variables.append(MaterialVariable(name=var.name, var_type=var.var_type, value=value))
    return variables


def scalar_schema_variables(schema: ShaderSchema, var_type: int) -> Iterable[ShaderVariableSchema]:
    return (var for var in schema.variables if var.var_type == var_type)


__all__ = [
    "ShaderSchema",
    "ShaderVariableSchema",
    "coerce_schema_value",
    "default_value_for_schema_var",
    "ensure_material_schema_properties",
    "find_shader_schema_path",
    "get_shader_schema",
    "is_editable_scalar_variable",
    "is_texture_variable",
    "material_data_from_shader_schema",
    "normalize_shader_type",
    "parse_shader_schema_file",
    "scalar_schema_variables",
    "schema_material_variables",
    "shader_param_label",
    "shader_schema_for_material",
    "shader_type_to_var_type",
]