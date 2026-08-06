from __future__ import annotations

from typing import Any

from ..interfaces import MaterialBuildContext, MaterialBuildState
from ..node_passes import BaseColorNodePasses
from .base import DefaultShaderMaterialBuilder


class BuildingShaderMaterialBuilder(DefaultShaderMaterialBuilder):
    """Building shader strategy with building-appropriate viewport behavior."""

    def use_team_colors(self, mat_data: Any) -> bool:
        return False

    def use_metal_base_blend(self, mat_data: Any) -> bool:
        return False

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "building"
        return material


class BuildingBrickScarDualShaderMaterialBuilder(BuildingShaderMaterialBuilder):
    """Building shader variant with dual-scar diffuse blending and tiled scar UVs."""

    def use_damage_scarring(self, mat_data: Any) -> bool:
        return False

    def post_process_texture_nodes(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        super().post_process_texture_nodes(ctx, state, mat_data)

        tiling_factor = self._get_float_value(mat_data, 'damageTexTilingFactor', 1.0)
        if mat_data.get_variable('damageTexTilingFactor') is None:
            return

        for texture_key in ('dualscardiffusetex', 'dualscarnormaltex', 'dualscarspectex'):
            tex_node = state.texture_nodes.get(texture_key)
            if tex_node is None:
                continue
            self._apply_uv_scale_to_texture_node(
                ctx,
                tex_node,
                f'Dual Scar Tiling {tex_node.label or texture_key}',
                tiling_factor,
                tiling_factor,
            )

    def post_process_final_surface(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        base_source = BaseColorNodePasses.pop_base_color_source(ctx.links, ctx.principled)
        if base_source is None and state.diffuse_tex_node is not None:
            base_source = state.diffuse_tex_node.outputs['Color']

        base_source = BaseColorNodePasses.apply_dual_scar_blend(
            ctx.nodes,
            ctx.links,
            ctx.principled,
            base_source,
            state.texture_nodes.get('dualscardiffusetex'),
            state.texture_nodes.get('scartexture'),
            'Dual Scar Layer',
        )
        if base_source is not None:
            ctx.links.new(base_source, ctx.principled.inputs['Base Color'])

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "building_brick_scar_dual"
        return material


__all__ = [
    "BuildingBrickScarDualShaderMaterialBuilder",
    "BuildingShaderMaterialBuilder",
]