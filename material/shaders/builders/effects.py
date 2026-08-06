from __future__ import annotations

from typing import Any

from ..interfaces import MaterialBuildContext, MaterialBuildState
from ..node_passes import BaseColorNodePasses
from .base import DefaultShaderMaterialBuilder


class FxShaderMaterialBuilder(DefaultShaderMaterialBuilder):
    """FX shader strategy; minimizes PBR assumptions for effect meshes."""

    def use_team_colors(self, mat_data: Any) -> bool:
        return False

    def use_metal_base_blend(self, mat_data: Any) -> bool:
        return False

    def use_damage_scarring(self, mat_data: Any) -> bool:
        return False

    def use_overlay(self, mat_data: Any) -> bool:
        return False

    def use_ao(self, mat_data: Any) -> bool:
        return False

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "fx"
        return material


class FxAlphaShaderMaterialBuilder(FxShaderMaterialBuilder):
    """FX alpha shader with tinted transparent surface output."""

    def post_process_final_surface(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        base_source = BaseColorNodePasses.pop_base_color_source(ctx.links, ctx.principled)
        if base_source is None and state.diffuse_tex_node is not None:
            base_source = state.diffuse_tex_node.outputs['Color']

        color_rgba = self._get_color_rgba(mat_data)
        if mat_data.get_variable('colour') is not None:
            base_source = BaseColorNodePasses.apply_color_tint(
                ctx.nodes,
                ctx.links,
                ctx.principled,
                base_source,
                color_rgba,
                'FX Colour Tint',
            )

        if base_source is not None:
            ctx.links.new(base_source, ctx.principled.inputs['Base Color'])

        alpha_source = state.diffuse_tex_node.outputs['Alpha'] if state.diffuse_tex_node is not None else None
        alpha_socket = BaseColorNodePasses.apply_alpha_factor(
            ctx.nodes,
            ctx.links,
            ctx.principled,
            alpha_source,
            color_rgba[3],
            'FX Alpha',
        )
        if alpha_socket is not None:
            ctx.links.new(alpha_socket, ctx.principled.inputs['Alpha'])

        if hasattr(ctx.mat, 'blend_method'):
            ctx.mat.blend_method = 'BLEND'
        if hasattr(ctx.mat, 'shadow_method'):
            ctx.mat.shadow_method = 'NONE'

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "fx_alpha"
        return material


class FxAdditiveShaderMaterialBuilder(FxShaderMaterialBuilder):
    """FX additive shader approximated as transparent plus emissive output."""

    def post_process_final_surface(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        base_source = BaseColorNodePasses.pop_base_color_source(ctx.links, ctx.principled)
        if base_source is None and state.diffuse_tex_node is not None:
            base_source = state.diffuse_tex_node.outputs['Color']

        color_rgba = self._get_color_rgba(mat_data)
        if mat_data.get_variable('colour') is not None:
            base_source = BaseColorNodePasses.apply_color_tint(
                ctx.nodes,
                ctx.links,
                ctx.principled,
                base_source,
                color_rgba,
                'FX Colour Tint',
            )

        alpha_source = state.diffuse_tex_node.outputs['Alpha'] if state.diffuse_tex_node is not None else None
        alpha_socket = BaseColorNodePasses.apply_alpha_factor(
            ctx.nodes,
            ctx.links,
            ctx.principled,
            alpha_source,
            color_rgba[3],
            'Additive Alpha',
        )

        BaseColorNodePasses.pop_socket_source(ctx.links, ctx.output, 'Surface')

        transparent_node = ctx.nodes.new('ShaderNodeBsdfTransparent')
        transparent_node.location = (ctx.output.location.x - 420, ctx.output.location.y + 120)
        transparent_node.label = 'Additive Transparent'

        emission_node = ctx.nodes.new('ShaderNodeEmission')
        emission_node.location = (ctx.output.location.x - 420, ctx.output.location.y - 80)
        emission_node.label = 'Additive Emission'
        if base_source is not None:
            ctx.links.new(base_source, emission_node.inputs['Color'])
        if alpha_socket is not None:
            ctx.links.new(alpha_socket, emission_node.inputs['Strength'])
        else:
            emission_node.inputs['Strength'].default_value = max(color_rgba[3], 1.0)

        add_shader = ctx.nodes.new('ShaderNodeAddShader')
        add_shader.location = (ctx.output.location.x - 180, ctx.output.location.y)
        add_shader.label = 'Additive Surface'
        ctx.links.new(transparent_node.outputs['BSDF'], add_shader.inputs[0])
        ctx.links.new(emission_node.outputs['Emission'], add_shader.inputs[1])
        ctx.links.new(add_shader.outputs['Shader'], ctx.output.inputs['Surface'])

        if hasattr(ctx.mat, 'blend_method'):
            ctx.mat.blend_method = 'BLEND'
        if hasattr(ctx.mat, 'shadow_method'):
            ctx.mat.shadow_method = 'NONE'

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "fx_additive"
        return material


class FullbrightShaderMaterialBuilder(FxShaderMaterialBuilder):
    """Fullbright shader rendered as unlit emission output."""

    def post_process_final_surface(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        base_source = BaseColorNodePasses.pop_base_color_source(ctx.links, ctx.principled)
        if base_source is None and state.diffuse_tex_node is not None:
            base_source = state.diffuse_tex_node.outputs['Color']
        if base_source is None:
            return

        BaseColorNodePasses.pop_socket_source(ctx.links, ctx.output, 'Surface')

        emission_node = ctx.nodes.new('ShaderNodeEmission')
        emission_node.location = (ctx.output.location.x - 220, ctx.output.location.y)
        emission_node.label = 'Fullbright Emission'
        emission_node.inputs['Strength'].default_value = 1.0
        ctx.links.new(base_source, emission_node.inputs['Color'])
        ctx.links.new(emission_node.outputs['Emission'], ctx.output.inputs['Surface'])

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "fullbright"
        return material


__all__ = [
    "FullbrightShaderMaterialBuilder",
    "FxAdditiveShaderMaterialBuilder",
    "FxAlphaShaderMaterialBuilder",
    "FxShaderMaterialBuilder",
]