from __future__ import annotations

from typing import Any, Iterable, List, Sequence

import bpy

from ...badges.affine import badge_viewport_affine
from ...definitions import (
    DEFAULT_PALETTE_1,
    DEFAULT_PALETTE_2,
    DEFAULT_PALETTE_3,
    DEFAULT_PALETTE_4,
    VAR_TYPE_BOOL,
    VAR_TYPE_FLOAT2,
    VAR_TYPE_FLOAT3,
    VAR_TYPE_FLOAT4,
    VAR_TYPE_INT,
    VAR_TYPE_MATRIX4,
    VAR_TYPE_TEXTURE,
)
from ..interfaces import MaterialBuildContext, MaterialBuildState, TextureSlotHandler
from ..layout import organize_material_nodes
from ..node_passes import BaseColorNodePasses
from ..texture_handlers import (
    DefaultTextureHandler,
    DiffuseTextureHandler,
    EmissiveTextureHandler,
    GlossTextureHandler,
    NormalTextureHandler,
    OcclusionTextureHandler,
    SpecularTextureHandler,
    TeamTextureHandler,
)


class DefaultShaderMaterialBuilder:
    """Default strategy that preserves current Relic material creation behavior."""

    _EMPTY_TEXTURE_KEYS: Sequence[str] = ()

    def _setup_graph(self, mat_data: Any) -> MaterialBuildContext:
        mat = bpy.data.materials.get(mat_data.name)
        if mat is None:
            mat = bpy.data.materials.new(name=mat_data.name)

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (400, 0)

        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (0, 0)
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        if 'IOR' in principled.inputs:
            principled.inputs['IOR'].default_value = 1.0

        mat["dow2_shader"] = mat_data.shader_name
        mat["dow2_shader_path"] = mat_data.shader_path

        return MaterialBuildContext(
            mat=mat,
            nodes=nodes,
            links=links,
            output=output,
            principled=principled,
        )

    @staticmethod
    def _store_variable_on_material(mat: Any, var: Any) -> None:
        if var.var_type == VAR_TYPE_TEXTURE:
            mat[f"dow2_{var.name}"] = var.value or ""
        elif var.var_type == VAR_TYPE_BOOL:
            mat[f"dow2_{var.name}"] = var.value
        elif var.var_type in [VAR_TYPE_INT]:
            mat[f"dow2_{var.name}"] = var.value
        elif var.var_type in [VAR_TYPE_FLOAT2, VAR_TYPE_FLOAT3, VAR_TYPE_FLOAT4]:
            mat[f"dow2_{var.name}"] = list(var.value)
        elif var.var_type == VAR_TYPE_MATRIX4:
            mat[f"dow2_{var.name}"] = var.value
        else:
            mat[f"dow2_{var.name}"] = var.value

    def use_team_colors(self, mat_data: Any) -> bool:
        return True

    def use_metal_base_blend(self, mat_data: Any) -> bool:
        return True

    def use_damage_scarring(self, mat_data: Any) -> bool:
        return True

    def use_overlay(self, mat_data: Any) -> bool:
        return True

    def use_ao(self, mat_data: Any) -> bool:
        return True

    def get_texture_handlers(self) -> List[TextureSlotHandler]:
        return [
            DiffuseTextureHandler(),
            NormalTextureHandler(),
            SpecularTextureHandler(),
            GlossTextureHandler(),
            EmissiveTextureHandler(),
            OcclusionTextureHandler(),
            TeamTextureHandler(),
            DefaultTextureHandler(),
        ]

    def get_uv_offset_texture_keys(self, mat_data: Any) -> Sequence[str]:
        return self._EMPTY_TEXTURE_KEYS

    def post_process_texture_nodes(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        self._apply_declared_uv_offset(ctx, state, mat_data, self.get_uv_offset_texture_keys(mat_data))
        self.post_process_specular(ctx, state, mat_data)

    def post_process_specular(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        if state.specular_tex_node is None:
            return

        state.metallic_socket = BaseColorNodePasses.apply_legacy_specular_metalness(
            ctx.nodes,
            ctx.links,
            ctx.principled,
            state.specular_tex_node,
        )

    def post_process_final_surface(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        return None

    @staticmethod
    def _get_float_value(mat_data: Any, name: str, default: float = 0.0) -> float:
        variable = mat_data.get_variable(name)
        if variable is None or variable.value is None:
            return default
        try:
            return float(variable.value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_float_sequence(mat_data: Any, name: str, length: int) -> List[float]:
        variable = mat_data.get_variable(name)
        if variable is None or variable.value is None:
            return []
        try:
            values = [float(value) for value in variable.value]
        except TypeError:
            return []
        return values if len(values) >= length else []

    @staticmethod
    def _get_color_rgba(mat_data: Any, name: str = 'colour') -> List[float]:
        variable = mat_data.get_variable(name)
        if variable is None or variable.value is None:
            return [1.0, 1.0, 1.0, 1.0]
        try:
            values = [float(value) for value in variable.value]
        except TypeError:
            return [1.0, 1.0, 1.0, 1.0]

        if len(values) >= 4:
            return values[:4]
        if len(values) == 3:
            return [values[0], values[1], values[2], 1.0]
        return [1.0, 1.0, 1.0, 1.0]

    @staticmethod
    def _apply_uv_offset_to_texture_node(ctx: MaterialBuildContext, tex_node: Any, label: str, u_offset: float, v_offset: float) -> None:
        vector_source = BaseColorNodePasses.pop_socket_source(ctx.links, tex_node, 'Vector')
        if vector_source is None:
            return

        offset_node = ctx.nodes.new('ShaderNodeVectorMath')
        offset_node.operation = 'ADD'
        offset_node.location = (tex_node.location.x - 220, tex_node.location.y)
        offset_node.label = label
        offset_node.inputs[1].default_value = (u_offset, v_offset, 0.0)
        ctx.links.new(vector_source, offset_node.inputs[0])
        ctx.links.new(offset_node.outputs['Vector'], tex_node.inputs['Vector'])

    def _apply_declared_uv_offset(
        self,
        ctx: MaterialBuildContext,
        state: MaterialBuildState,
        mat_data: Any,
        texture_keys: Iterable[str],
    ) -> None:
        u_offset = self._get_float_value(mat_data, 'uOffset')
        v_offset = self._get_float_value(mat_data, 'vOffset')

        if mat_data.get_variable('uOffset') is None and mat_data.get_variable('vOffset') is None:
            return

        for texture_key in texture_keys:
            tex_node = state.texture_nodes.get(texture_key)
            if tex_node is None:
                continue
            self._apply_uv_offset_to_texture_node(
                ctx,
                tex_node,
                f'UV Offset {tex_node.label or texture_key}',
                u_offset,
                v_offset,
            )

    @staticmethod
    def _apply_uv_scale_to_texture_node(ctx: MaterialBuildContext, tex_node: Any, label: str, u_scale: float, v_scale: float) -> None:
        vector_source = BaseColorNodePasses.pop_socket_source(ctx.links, tex_node, 'Vector')
        if vector_source is None:
            return

        mapping_node = ctx.nodes.new('ShaderNodeMapping')
        mapping_node.location = (tex_node.location.x - 220, tex_node.location.y)
        mapping_node.label = label
        mapping_node.inputs['Scale'].default_value = (u_scale, v_scale, 1.0)
        ctx.links.new(vector_source, mapping_node.inputs['Vector'])
        ctx.links.new(mapping_node.outputs['Vector'], tex_node.inputs['Vector'])

    @staticmethod
    def _apply_badge_uv_transform(
        ctx: MaterialBuildContext,
        tex_node: Any,
        label_prefix: str,
        matrix_values: Sequence[float],
        translate_values: Sequence[float],
    ) -> None:
        vector_source = BaseColorNodePasses.pop_socket_source(ctx.links, tex_node, 'Vector')
        if vector_source is None:
            return

        viewport_matrix, viewport_translate = badge_viewport_affine(
            matrix_values,
            translate_values,
            tuple(getattr(getattr(tex_node, 'image', None), 'size', (1.0, 1.0))),
        )

        separate_node = ctx.nodes.new('ShaderNodeSeparateXYZ')
        separate_node.location = (tex_node.location.x - 860, tex_node.location.y)
        separate_node.label = f'{label_prefix} UV Split'
        ctx.links.new(vector_source, separate_node.inputs['Vector'])

        mul_x_u = ctx.nodes.new('ShaderNodeMath')
        mul_x_u.operation = 'MULTIPLY'
        mul_x_u.location = (tex_node.location.x - 640, tex_node.location.y + 120)
        mul_x_u.label = f'{label_prefix} Matrix U.X'
        mul_x_u.inputs[1].default_value = viewport_matrix[0]
        ctx.links.new(separate_node.outputs['X'], mul_x_u.inputs[0])

        mul_y_u = ctx.nodes.new('ShaderNodeMath')
        mul_y_u.operation = 'MULTIPLY'
        mul_y_u.location = (tex_node.location.x - 640, tex_node.location.y + 40)
        mul_y_u.label = f'{label_prefix} Matrix U.Y'
        mul_y_u.inputs[1].default_value = viewport_matrix[1]
        ctx.links.new(separate_node.outputs['Y'], mul_y_u.inputs[0])

        add_u = ctx.nodes.new('ShaderNodeMath')
        add_u.operation = 'ADD'
        add_u.location = (tex_node.location.x - 430, tex_node.location.y + 80)
        ctx.links.new(mul_x_u.outputs['Value'], add_u.inputs[0])
        ctx.links.new(mul_y_u.outputs['Value'], add_u.inputs[1])

        translate_u = ctx.nodes.new('ShaderNodeMath')
        translate_u.operation = 'ADD'
        translate_u.location = (tex_node.location.x - 220, tex_node.location.y + 80)
        translate_u.label = f'{label_prefix} Translate U'
        translate_u.inputs[1].default_value = viewport_translate[0]
        ctx.links.new(add_u.outputs['Value'], translate_u.inputs[0])

        mul_x_v = ctx.nodes.new('ShaderNodeMath')
        mul_x_v.operation = 'MULTIPLY'
        mul_x_v.location = (tex_node.location.x - 640, tex_node.location.y - 80)
        mul_x_v.label = f'{label_prefix} Matrix V.X'
        mul_x_v.inputs[1].default_value = viewport_matrix[2]
        ctx.links.new(separate_node.outputs['X'], mul_x_v.inputs[0])

        mul_y_v = ctx.nodes.new('ShaderNodeMath')
        mul_y_v.operation = 'MULTIPLY'
        mul_y_v.location = (tex_node.location.x - 640, tex_node.location.y - 160)
        mul_y_v.label = f'{label_prefix} Matrix V.Y'
        mul_y_v.inputs[1].default_value = viewport_matrix[3]
        ctx.links.new(separate_node.outputs['Y'], mul_y_v.inputs[0])

        add_v = ctx.nodes.new('ShaderNodeMath')
        add_v.operation = 'ADD'
        add_v.location = (tex_node.location.x - 430, tex_node.location.y - 120)
        ctx.links.new(mul_x_v.outputs['Value'], add_v.inputs[0])
        ctx.links.new(mul_y_v.outputs['Value'], add_v.inputs[1])

        translate_v = ctx.nodes.new('ShaderNodeMath')
        translate_v.operation = 'ADD'
        translate_v.location = (tex_node.location.x - 220, tex_node.location.y - 120)
        translate_v.label = f'{label_prefix} Translate V'
        translate_v.inputs[1].default_value = viewport_translate[1]
        ctx.links.new(add_v.outputs['Value'], translate_v.inputs[0])

        combine_node = ctx.nodes.new('ShaderNodeCombineXYZ')
        combine_node.location = (tex_node.location.x - 20, tex_node.location.y - 20)
        combine_node.label = f'{label_prefix} UV Transform'
        ctx.links.new(translate_u.outputs['Value'], combine_node.inputs['X'])
        ctx.links.new(translate_v.outputs['Value'], combine_node.inputs['Y'])
        ctx.links.new(combine_node.outputs['Vector'], tex_node.inputs['Vector'])

    @staticmethod
    def _handle_texture_variable(
        creator: Any,
        ctx: MaterialBuildContext,
        state: MaterialBuildState,
        mat_data: Any,
        var: Any,
        handlers: List[TextureSlotHandler],
    ) -> None:
        var_name_lower = var.name.lower()
        for handler in handlers:
            if handler.can_handle(var_name_lower):
                if handler.handle(creator, ctx, state, mat_data, var):
                    return

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        ctx = self._setup_graph(mat_data)
        state = MaterialBuildState(tex_x=-600, tex_y=400, tex_y_step=-300)
        texture_handlers = self.get_texture_handlers()

        for var in mat_data.variables:
            self._store_variable_on_material(ctx.mat, var)

            if var.var_type == VAR_TYPE_TEXTURE:
                self._handle_texture_variable(creator, ctx, state, mat_data, var, texture_handlers)
            elif var.var_type == VAR_TYPE_FLOAT3 and var.name.lower() == 'colour':
                ctx.principled.inputs['Base Color'].default_value = (var.value[0], var.value[1], var.value[2], 1.0)
            elif var.var_type == VAR_TYPE_FLOAT4 and var.name.lower() == 'colour':
                ctx.principled.inputs['Base Color'].default_value = (var.value[0], var.value[1], var.value[2], var.value[3])

        self.post_process_texture_nodes(ctx, state, mat_data)

        base_source = BaseColorNodePasses.pop_base_color_source(ctx.links, ctx.principled)
        if base_source is None and state.diffuse_tex_node:
            base_source = state.diffuse_tex_node.outputs['Color']

        overlay_node = state.texture_nodes.get('overlaytex')
        if self.use_overlay(mat_data):
            base_source = BaseColorNodePasses.apply_overlay(
                ctx.nodes,
                ctx.links,
                ctx.principled,
                base_source,
                overlay_node,
            )

        if self.use_ao(mat_data):
            base_source = BaseColorNodePasses.apply_ao(
                ctx.nodes,
                ctx.links,
                ctx.principled,
                base_source,
                state.ao_tex_node,
            )

        damage_diffuse_node = state.texture_nodes.get('damagediffusetex')
        scar_mask_node = state.texture_nodes.get('scartexture')
        if self.use_damage_scarring(mat_data):
            base_source = BaseColorNodePasses.apply_damage_scarring(
                ctx.nodes,
                ctx.links,
                ctx.principled,
                ctx.mat,
                base_source,
                damage_diffuse_node,
                scar_mask_node,
            )

        if base_source is not None:
            ctx.links.new(base_source, ctx.principled.inputs['Base Color'])

        if self.use_team_colors(mat_data):
            BaseColorNodePasses.apply_team_colors_shared(
                ctx.nodes,
                ctx.links,
                ctx.principled,
                ctx.mat,
                state.team_tex_node,
                state.diffuse_tex_node,
                state.emissive_tex_node,
                (
                    DEFAULT_PALETTE_1,
                    DEFAULT_PALETTE_2,
                    DEFAULT_PALETTE_3,
                    DEFAULT_PALETTE_4,
                ),
            )

        if self.use_metal_base_blend(mat_data):
            BaseColorNodePasses.apply_metal_base_blend(
                ctx.nodes,
                ctx.links,
                ctx.principled,
                state.specular_color_socket,
                state.metallic_socket,
            )

        self.post_process_final_surface(ctx, state, mat_data)

        alpha_test = mat_data.get_variable('alphaTest')
        if alpha_test and alpha_test.value:
            if hasattr(ctx.mat, 'blend_method'):
                ctx.mat.blend_method = 'CLIP'
            if hasattr(ctx.mat, 'shadow_method'):
                ctx.mat.shadow_method = 'CLIP'

        organize_material_nodes(ctx)
        return ctx.mat


__all__ = ["DefaultShaderMaterialBuilder"]