from __future__ import annotations

from dataclasses import dataclass

import bpy


@dataclass(slots=True)
class TerrainTextureSet:
    layer_index: int
    surface_path: str
    cliff_path: str
    surface_diffuse: bpy.types.Image | None
    cliff_diffuse: bpy.types.Image | None
    surface_normal: bpy.types.Image | None
    cliff_normal: bpy.types.Image | None
    surface_spec: bpy.types.Image | None
    cliff_spec: bpy.types.Image | None


@dataclass(slots=True)
class TerrainBlendSockets:
    color: bpy.types.NodeSocket | None
    normal: bpy.types.NodeSocket | None
    spec_alpha: bpy.types.NodeSocket | None


__all__ = [
    "TerrainBlendSockets",
    "TerrainTextureSet",
]