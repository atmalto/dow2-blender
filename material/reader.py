from __future__ import annotations

import os
from typing import Optional

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


class RelicMaterialReader:
    """Reads material data from model file chunks."""

    @staticmethod
    def read_material_variable(reader, data_path: str) -> Optional[MaterialVariable]:
        """Read a single material variable from file."""
        name_len = reader.read_long()
        var_name = reader.read_str(name_len) if name_len > 0 else ""
        var_type = reader.read_long()
        var_size = reader.read_long()

        value = None

        if var_type == VAR_TYPE_INT:
            value = reader.read_long(unsigned=False)
        elif var_type == VAR_TYPE_FLOAT:
            value = reader.read_float()
        elif var_type == VAR_TYPE_FLOAT2:
            value = (reader.read_float(), reader.read_float())
        elif var_type == VAR_TYPE_FLOAT3:
            value = (reader.read_float(), reader.read_float(), reader.read_float())
        elif var_type == VAR_TYPE_FLOAT4:
            value = (
                reader.read_float(),
                reader.read_float(),
                reader.read_float(),
                reader.read_float(),
            )
        elif var_type == VAR_TYPE_MATRIX4:
            value = [reader.read_float() for _ in range(16)]
        elif var_type == VAR_TYPE_TEXTURE:
            value = reader.read_str(var_size).rstrip('\x00')
        elif var_type == VAR_TYPE_BOOL:
            value = reader.read_byte() == 1
        else:
            reader.file.read(var_size)
            return None

        return MaterialVariable(name=var_name, var_type=var_type, value=value)

    @staticmethod
    def read_material(reader, mtrl_chunk, data_path: str) -> RelicMaterialData:
        """Read a complete material from an MTRL chunk."""
        mat_data = RelicMaterialData(name=mtrl_chunk.name or "Material")

        if not mtrl_chunk.children:
            return mat_data

        info_chunk = mtrl_chunk.children[0]
        if info_chunk.chunk_type == "INFO":
            reader.seek_chunk(info_chunk)
            shader_len = reader.read_long()
            if shader_len > 0:
                mat_data.shader_name = reader.read_str(shader_len)
                mat_data.shader_path = os.path.join(data_path, "shaders", mat_data.shader_name + ".shader")

        for child in mtrl_chunk.children[1:]:
            reader.seek_chunk(child)
            var = RelicMaterialReader.read_material_variable(reader, data_path)
            if var is not None:
                mat_data.variables.append(var)

        return mat_data


__all__ = ["RelicMaterialReader"]