from __future__ import annotations

from typing import Any, List, Sequence

from ...badges.handler import BadgeTextureHandler
from ..interfaces import MaterialBuildContext, MaterialBuildState, TextureSlotHandler
from ..node_passes import BaseColorNodePasses
from ..texture_handlers import (
    DefaultTextureHandler,
    DiffuseTextureHandler,
    DirtTextureHandler,
    EmissiveTextureHandler,
    GlossTextureHandler,
    NormalTextureHandler,
    OcclusionTextureHandler,
    SpecularTextureHandler,
    TeamTextureHandler,
)
from .base import DefaultShaderMaterialBuilder


class UnitShaderMaterialBuilder(DefaultShaderMaterialBuilder):
    """Unit shader strategy with colored specular and gloss-driven reflections."""

    @staticmethod
    def _badge_transform_values(mat_data: Any, matrix_name: str, translate_name: str) -> tuple[list[float], list[float]]:
        matrix_values = DefaultShaderMaterialBuilder._get_float_sequence(mat_data, matrix_name, 4)
        translate_values = DefaultShaderMaterialBuilder._get_float_sequence(mat_data, translate_name, 2)
        return matrix_values, translate_values

    def _apply_badge_texture_transforms(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        badge_specs = (
            ('badge1tex', 'Badge 1', 'badge1MatrixRow1Row2', 'badge1Translate'),
            ('badge2tex', 'Badge 2', 'badge2MatrixRow1Row2', 'badge2Translate'),
        )

        for texture_key, label, matrix_name, translate_name in badge_specs:
            tex_node = state.texture_nodes.get(texture_key)
            if tex_node is None:
                continue

            if hasattr(tex_node, 'extension'):
                tex_node.extension = 'CLIP'

            matrix_values, translate_values = self._badge_transform_values(mat_data, matrix_name, translate_name)
            if not matrix_values or not translate_values:
                continue

            self._apply_badge_uv_transform(ctx, tex_node, label, matrix_values, translate_values)

    def _apply_badge_layers(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, base_source: Any) -> Any:
        if base_source is None:
            return None

        badge_specs = (
            ('badge1tex', 'Badge 1 Layer', 'badge1MatrixRow1Row2', 'badge1Translate'),
            ('badge2tex', 'Badge 2 Layer', 'badge2MatrixRow1Row2', 'badge2Translate'),
        )

        for texture_key, layer_label, matrix_name, translate_name in badge_specs:
            tex_node = state.texture_nodes.get(texture_key)
            if tex_node is None:
                continue
            matrix_values, translate_values = self._badge_transform_values(mat_data, matrix_name, translate_name)
            if not matrix_values or not translate_values:
                continue
            base_source = BaseColorNodePasses.apply_badge_decal(
                ctx.nodes,
                ctx.links,
                ctx.principled,
                base_source,
                tex_node,
                layer_label,
            )
        return base_source

    def use_metal_base_blend(self, mat_data: Any) -> bool:
        return False

    def post_process_specular(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        if state.specular_tex_node is None:
            return

        state.metallic_socket = None
        BaseColorNodePasses.apply_reflective_specular(
            ctx.nodes,
            ctx.links,
            ctx.output,
            ctx.principled,
            state.specular_tex_node,
            normal_socket=state.normal_socket,
        )

    def post_process_texture_nodes(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        super().post_process_texture_nodes(ctx, state, mat_data)
        self._apply_badge_texture_transforms(ctx, state, mat_data)

    def post_process_final_surface(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        base_source = BaseColorNodePasses.pop_base_color_source(ctx.links, ctx.principled)
        if base_source is None and state.diffuse_tex_node is not None:
            base_source = state.diffuse_tex_node.outputs['Color']
        if base_source is None:
            return

        base_source = self._apply_badge_layers(ctx, state, mat_data, base_source)
        ctx.links.new(base_source, ctx.principled.inputs['Base Color'])

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "unit"
        return material


class WargearShaderMaterialBuilder(UnitShaderMaterialBuilder):
    """Wargear shader strategy with badge, dirt, and UV-offset handling."""

    def get_texture_handlers(self) -> List[TextureSlotHandler]:
        return [
            DiffuseTextureHandler(),
            NormalTextureHandler(),
            SpecularTextureHandler(),
            GlossTextureHandler(),
            EmissiveTextureHandler(),
            OcclusionTextureHandler(),
            TeamTextureHandler(),
            DirtTextureHandler(),
            BadgeTextureHandler(),
            DefaultTextureHandler(),
        ]

    def get_uv_offset_texture_keys(self, mat_data: Any) -> Sequence[str]:
        return (
            'diffusetex',
            'dirttex',
            'normalmap',
            'occlusiontex',
            'glosstex',
            'speculartex',
            'teamtex',
            'emissivetex',
        )

    def post_process_texture_nodes(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        super().post_process_texture_nodes(ctx, state, mat_data)

    def post_process_final_surface(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        base_source = BaseColorNodePasses.pop_base_color_source(ctx.links, ctx.principled)
        if base_source is None and state.diffuse_tex_node is not None:
            base_source = state.diffuse_tex_node.outputs['Color']
        if base_source is None:
            return

        base_source = self._apply_badge_layers(ctx, state, mat_data, base_source)
        base_source = BaseColorNodePasses.apply_dirt_layer(
            ctx.nodes,
            ctx.links,
            ctx.principled,
            base_source,
            state.texture_nodes.get('dirttex'),
            self._get_float_value(mat_data, 'dirtVisibility'),
        )
        ctx.links.new(base_source, ctx.principled.inputs['Base Color'])

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material["dow2_shader_profile"] = "wargear"
        return material


__all__ = ["UnitShaderMaterialBuilder", "WargearShaderMaterialBuilder"]