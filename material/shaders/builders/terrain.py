from __future__ import annotations

from typing import Any

from ..interfaces import MaterialBuildContext, MaterialBuildState
from ..node_passes import BaseColorNodePasses
from .base import DefaultShaderMaterialBuilder


class TerrainShaderMaterialBuilder(DefaultShaderMaterialBuilder):
    """Terrain shader strategy with non-team material behavior."""

    def use_team_colors(self, mat_data: Any) -> bool:
        return False

    def use_metal_base_blend(self, mat_data: Any) -> bool:
        return False

    def use_damage_scarring(self, mat_data: Any) -> bool:
        return False

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "terrain"
        return material


class TerrainObjectShaderMaterialBuilder(TerrainShaderMaterialBuilder):
    """Terrain object shader that approximates cliff/grass blending from surface slope."""

    def post_process_final_surface(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        base_source = BaseColorNodePasses.apply_terrain_slope_blend(
            ctx.nodes,
            ctx.links,
            ctx.principled,
            state.texture_nodes.get('clifftex1'),
            state.texture_nodes.get('grasstex1'),
            'Terrain Slope Blend',
        )
        if base_source is not None:
            BaseColorNodePasses.pop_base_color_source(ctx.links, ctx.principled)
            ctx.links.new(base_source, ctx.principled.inputs['Base Color'])

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "terrain_object"
        return material


__all__ = ["TerrainObjectShaderMaterialBuilder", "TerrainShaderMaterialBuilder"]