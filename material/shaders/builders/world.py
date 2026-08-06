from __future__ import annotations

from typing import Any, Sequence

from .base import DefaultShaderMaterialBuilder


class WorldObjectShaderMaterialBuilder(DefaultShaderMaterialBuilder):
    """World-object shader strategy for static/dynamic world meshes."""

    def use_team_colors(self, mat_data: Any) -> bool:
        return False

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "world_object"
        return material


class DynamicWorldObjectShaderMaterialBuilder(WorldObjectShaderMaterialBuilder):
    """Dynamic world-object shader with animated UV offset support."""

    def get_uv_offset_texture_keys(self, mat_data: Any) -> Sequence[str]:
        return (
            'diffusetex',
            'normalmap',
            'occlusiontex',
            'glosstex',
            'speculartex',
            'emissivetex',
        )

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "dynamic_world_object"
        return material


class DynamicWorldObjectTwoUvShaderMaterialBuilder(WorldObjectShaderMaterialBuilder):
    """Dynamic world-object shader that routes overlay textures through the second UV set."""

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "dynamic_world_object_two_uv"
        return material


class StaticWorldObjectShaderMaterialBuilder(WorldObjectShaderMaterialBuilder):
    """Static world-object shader with UV offset support for parity with game data."""

    def get_uv_offset_texture_keys(self, mat_data: Any) -> Sequence[str]:
        return (
            'diffusetex',
            'normalmap',
            'occlusiontex',
            'glosstex',
            'speculartex',
            'emissivetex',
        )

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "static_world_object"
        return material


__all__ = [
    "DynamicWorldObjectShaderMaterialBuilder",
    "DynamicWorldObjectTwoUvShaderMaterialBuilder",
    "StaticWorldObjectShaderMaterialBuilder",
    "WorldObjectShaderMaterialBuilder",
]