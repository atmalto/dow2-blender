from __future__ import annotations

from typing import Any

import bpy

from ..interfaces import MaterialBuildContext, MaterialBuildState
from ..node_passes import BaseColorNodePasses
from .base import DefaultShaderMaterialBuilder


class WaterShaderMaterialBuilder(DefaultShaderMaterialBuilder):
    """Water shader strategy with layered animated normals, foam, and reflection."""

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

    def post_process_specular(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        return None

    def _set_non_color(self, tex_node: Any) -> None:
        image = getattr(tex_node, 'image', None)
        if image is None:
            return
        try:
            image.colorspace_settings.name = 'Non-Color'
        except Exception:
            return

    def _new_uv_map(self, ctx: MaterialBuildContext, uv_name: str, label: str, x: float, y: float) -> Any:
        uv_node = ctx.nodes.new('ShaderNodeUVMap')
        uv_node.uv_map = uv_name
        uv_node.location = (x, y)
        uv_node.label = label
        return uv_node

    def _new_value_node(self, ctx: MaterialBuildContext, label: str, x: float, y: float, value: float) -> Any:
        node = ctx.nodes.new('ShaderNodeValue')
        node.location = (x, y)
        node.label = label
        node.outputs['Value'].default_value = value
        return node

    def _create_scene_time_socket(self, ctx: MaterialBuildContext, x: float, y: float) -> Any:
        time_node = self._new_value_node(ctx, 'Water Time Seconds', x, y, 0.0)
        scene = bpy.context.scene
        if scene is not None:
            try:
                driver = time_node.outputs['Value'].driver_add('default_value').driver
                driver.type = 'SCRIPTED'

                frame_var = driver.variables.new()
                frame_var.name = 'frame'
                frame_var.targets[0].id_type = 'SCENE'
                frame_var.targets[0].id = scene
                frame_var.targets[0].data_path = 'frame_current'

                fps_var = driver.variables.new()
                fps_var.name = 'fps'
                fps_var.targets[0].id_type = 'SCENE'
                fps_var.targets[0].id = scene
                fps_var.targets[0].data_path = 'render.fps'

                driver.expression = 'frame / fps'
            except Exception:
                pass
        return time_node.outputs['Value']

    def _create_water_uv(self, ctx: MaterialBuildContext, time_socket: Any, label: str, scale_u: float, scale_v: float, phase_speed: float, y: float) -> Any:
        uv2_node = self._new_uv_map(ctx, 'UVMap2', f'{label} UVMap2', -1200, y)

        mapping_node = ctx.nodes.new('ShaderNodeMapping')
        mapping_node.location = (-980, y)
        mapping_node.label = label
        mapping_node.inputs['Scale'].default_value = (scale_u, scale_v, 1.0)
        ctx.links.new(uv2_node.outputs['UV'], mapping_node.inputs['Vector'])

        phase_mul = ctx.nodes.new('ShaderNodeMath')
        phase_mul.operation = 'MULTIPLY'
        phase_mul.location = (-1200, y - 180)
        phase_mul.label = f'{label} Phase'
        phase_mul.inputs[1].default_value = phase_speed
        ctx.links.new(time_socket, phase_mul.inputs[0])

        separate_node = ctx.nodes.new('ShaderNodeSeparateXYZ')
        separate_node.location = (-780, y)
        separate_node.label = f'{label} Split'
        ctx.links.new(mapping_node.outputs['Vector'], separate_node.inputs['Vector'])

        offset_v = ctx.nodes.new('ShaderNodeMath')
        offset_v.operation = 'ADD'
        offset_v.location = (-560, y - 60)
        offset_v.label = f'{label} Offset V'
        ctx.links.new(separate_node.outputs['Y'], offset_v.inputs[0])
        ctx.links.new(phase_mul.outputs['Value'], offset_v.inputs[1])

        combine_node = ctx.nodes.new('ShaderNodeCombineXYZ')
        combine_node.location = (-340, y)
        combine_node.label = f'{label} Vector'
        ctx.links.new(separate_node.outputs['X'], combine_node.inputs['X'])
        ctx.links.new(offset_v.outputs['Value'], combine_node.inputs['Y'])
        ctx.links.new(separate_node.outputs['Z'], combine_node.inputs['Z'])
        return combine_node.outputs['Vector']

    def _attach_vector_source(self, ctx: MaterialBuildContext, tex_node: Any, vector_socket: Any) -> None:
        if tex_node is None or vector_socket is None:
            return
        BaseColorNodePasses.pop_socket_source(ctx.links, tex_node, 'Vector')
        ctx.links.new(vector_socket, tex_node.inputs['Vector'])

    def _duplicate_image_node(self, ctx: MaterialBuildContext, source_node: Any, label: str, location: tuple[float, float]) -> Any:
        if source_node is None:
            return None
        dup_node = ctx.nodes.new('ShaderNodeTexImage')
        dup_node.location = location
        dup_node.label = label
        dup_node.image = getattr(source_node, 'image', None)
        if hasattr(dup_node, 'extension'):
            dup_node.extension = getattr(source_node, 'extension', 'REPEAT')
        if getattr(source_node, 'image', None) is not None:
            self._set_non_color(dup_node)
        return dup_node

    def _decode_normal_color(self, ctx: MaterialBuildContext, color_socket: Any, label: str, y: float) -> Any:
        scale_node = ctx.nodes.new('ShaderNodeVectorMath')
        scale_node.operation = 'SCALE'
        scale_node.location = (-180, y)
        scale_node.label = f'{label} x2'
        scale_node.inputs['Scale'].default_value = 2.0
        ctx.links.new(color_socket, scale_node.inputs['Vector'])

        offset_node = ctx.nodes.new('ShaderNodeVectorMath')
        offset_node.operation = 'ADD'
        offset_node.location = (40, y)
        offset_node.label = f'{label} - 1'
        offset_node.inputs[1].default_value = (-1.0, -1.0, -1.0)
        ctx.links.new(scale_node.outputs['Vector'], offset_node.inputs[0])
        return offset_node.outputs['Vector']

    def _encode_normal_vector(self, ctx: MaterialBuildContext, vector_socket: Any, label: str, y: float) -> Any:
        half_node = ctx.nodes.new('ShaderNodeVectorMath')
        half_node.operation = 'SCALE'
        half_node.location = (720, y)
        half_node.label = f'{label} * 0.5'
        half_node.inputs['Scale'].default_value = 0.5
        ctx.links.new(vector_socket, half_node.inputs['Vector'])

        add_node = ctx.nodes.new('ShaderNodeVectorMath')
        add_node.operation = 'ADD'
        add_node.location = (940, y)
        add_node.label = f'{label} + 0.5'
        add_node.inputs[1].default_value = (0.5, 0.5, 0.5)
        ctx.links.new(half_node.outputs['Vector'], add_node.inputs[0])
        return add_node.outputs['Vector']

    def _mix_color_constant(self, ctx: MaterialBuildContext, socket_a: Any, socket_b: Any, factor: float, label: str, y: float) -> Any:
        mix_node = ctx.nodes.new('ShaderNodeMix')
        mix_node.data_type = 'RGBA'
        mix_node.location = (y, 0)
        mix_node.label = label
        mix_node.inputs['Factor'].default_value = factor
        ctx.links.new(socket_a, mix_node.inputs['A'])
        ctx.links.new(socket_b, mix_node.inputs['B'])
        return mix_node.outputs['Result']

    def _build_reflection_factor(self, ctx: MaterialBuildContext, foam_factor_socket: Any, x: float, y: float) -> Any:
        layer_weight = ctx.nodes.new('ShaderNodeLayerWeight')
        layer_weight.location = (x, y)
        layer_weight.label = 'Water View Weight'
        layer_weight.inputs['Blend'].default_value = 0.2

        invert_facing = ctx.nodes.new('ShaderNodeMath')
        invert_facing.operation = 'SUBTRACT'
        invert_facing.location = (x + 220, y)
        invert_facing.label = 'Water Fresnel Approx'
        invert_facing.inputs[0].default_value = 1.0
        ctx.links.new(layer_weight.outputs['Facing'], invert_facing.inputs[1])

        reflection_mix = ctx.nodes.new('ShaderNodeMix')
        reflection_mix.data_type = 'FLOAT'
        reflection_mix.location = (x + 440, y)
        reflection_mix.label = 'Water Reflection Factor'
        reflection_mix.inputs['A'].default_value = 0.05
        ctx.links.new(foam_factor_socket, reflection_mix.inputs['Factor'])
        ctx.links.new(invert_facing.outputs['Value'], reflection_mix.inputs['B'])
        return reflection_mix.outputs['Result']

    def post_process_texture_nodes(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        for texture_key in ('normalmapcoarsetex', 'normalmapfinetex', 'normalmapfoamtex', 'waterturbulencemasktex'):
            self._set_non_color(state.texture_nodes.get(texture_key))

        time_socket = self._create_scene_time_socket(ctx, -1460, 840)

        coarse_normal_uv = self._create_water_uv(ctx, time_socket, 'Water Coarse Normal UV', 2.0, 2.0, 50.0, 520)
        fine_normal_uv = self._create_water_uv(ctx, time_socket, 'Water Fine Normal UV', 2.5, 1.0, 40.0, 160)
        coarse_turb_uv = self._create_water_uv(ctx, time_socket, 'Water Turbulence A UV', 0.66, 0.66, 16.5, -200)
        fine_turb_uv = self._create_water_uv(ctx, time_socket, 'Water Turbulence B UV', 1.1, 0.44, 17.6, -520)

        self._attach_vector_source(ctx, state.texture_nodes.get('normalmapcoarsetex'), coarse_normal_uv)
        self._attach_vector_source(ctx, state.texture_nodes.get('normalmapfinetex'), fine_normal_uv)
        self._attach_vector_source(ctx, state.texture_nodes.get('normalmapfoamtex'), coarse_normal_uv)
        self._attach_vector_source(ctx, state.texture_nodes.get('waterturbulencetex'), coarse_turb_uv)

        turbulence_node = state.texture_nodes.get('waterturbulencetex')
        if turbulence_node is not None:
            fine_turbulence = self._duplicate_image_node(
                ctx,
                turbulence_node,
                'waterTurbulenceTex Fine',
                (turbulence_node.location.x, turbulence_node.location.y - 220),
            )
            if fine_turbulence is not None:
                fine_uv_map = self._new_uv_map(ctx, 'UVMap2', 'waterTurbulenceTex Fine_UVMap2', fine_turbulence.location.x - 220, fine_turbulence.location.y)
                BaseColorNodePasses.pop_socket_source(ctx.links, fine_turbulence, 'Vector')
                ctx.links.new(fine_turb_uv, fine_turbulence.inputs['Vector'])
                state.texture_nodes['waterturbulencetex_fine'] = fine_turbulence

    def post_process_final_surface(self, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any) -> None:
        water_colour_node = state.texture_nodes.get('watercolourtex')
        turbulence_a_node = state.texture_nodes.get('waterturbulencetex')
        turbulence_b_node = state.texture_nodes.get('waterturbulencetex_fine')
        turbulence_mask_node = state.texture_nodes.get('waterturbulencemasktex')
        coarse_normal_node = state.texture_nodes.get('normalmapcoarsetex')
        fine_normal_node = state.texture_nodes.get('normalmapfinetex')
        foam_normal_node = state.texture_nodes.get('normalmapfoamtex')

        if (
            water_colour_node is None or
            turbulence_a_node is None or
            turbulence_b_node is None or
            turbulence_mask_node is None or
            coarse_normal_node is None or
            fine_normal_node is None or
            foam_normal_node is None
        ):
            return

        coarse_normal = self._decode_normal_color(ctx, coarse_normal_node.outputs['Color'], 'Water Coarse Normal', 520)
        fine_normal = self._decode_normal_color(ctx, fine_normal_node.outputs['Color'], 'Water Fine Normal', 360)
        foam_normal = self._decode_normal_color(ctx, foam_normal_node.outputs['Color'], 'Water Foam Normal', 200)

        normal_sum = ctx.nodes.new('ShaderNodeVectorMath')
        normal_sum.operation = 'ADD'
        normal_sum.location = (260, 440)
        normal_sum.label = 'Water Normal Sum'
        ctx.links.new(coarse_normal, normal_sum.inputs[0])
        ctx.links.new(fine_normal, normal_sum.inputs[1])

        mask_mul = ctx.nodes.new('ShaderNodeVectorMath')
        mask_mul.operation = 'MULTIPLY'
        mask_mul.location = (260, 200)
        mask_mul.label = 'Water Foam Normal * Mask'
        ctx.links.new(turbulence_mask_node.outputs['Color'], mask_mul.inputs[0])
        ctx.links.new(foam_normal, mask_mul.inputs[1])

        normal_add = ctx.nodes.new('ShaderNodeVectorMath')
        normal_add.operation = 'ADD'
        normal_add.location = (500, 320)
        normal_add.label = 'Water Normal + Foam'
        ctx.links.new(normal_sum.outputs['Vector'], normal_add.inputs[0])
        ctx.links.new(mask_mul.outputs['Vector'], normal_add.inputs[1])

        normal_average = ctx.nodes.new('ShaderNodeVectorMath')
        normal_average.operation = 'SCALE'
        normal_average.location = (720, 320)
        normal_average.label = 'Water Normal Average'
        normal_average.inputs['Scale'].default_value = 0.333
        ctx.links.new(normal_add.outputs['Vector'], normal_average.inputs['Vector'])

        normal_mask_alpha = ctx.nodes.new('ShaderNodeVectorMath')
        normal_mask_alpha.operation = 'SCALE'
        normal_mask_alpha.location = (940, 320)
        normal_mask_alpha.label = 'Water Normal Mask Alpha'
        ctx.links.new(normal_average.outputs['Vector'], normal_mask_alpha.inputs['Vector'])
        ctx.links.new(turbulence_mask_node.outputs['Alpha'], normal_mask_alpha.inputs['Scale'])

        encoded_normal = self._encode_normal_vector(ctx, normal_mask_alpha.outputs['Vector'], 'Water Encoded Normal', 320)
        water_normal_map = ctx.nodes.new('ShaderNodeNormalMap')
        water_normal_map.location = (1180, 320)
        water_normal_map.label = 'Water Surface Normal'
        ctx.links.new(encoded_normal, water_normal_map.inputs['Color'])
        BaseColorNodePasses.pop_socket_source(ctx.links, ctx.principled, 'Normal')
        ctx.links.new(water_normal_map.outputs['Normal'], ctx.principled.inputs['Normal'])
        state.normal_socket = water_normal_map.outputs['Normal']

        turbulence_average = ctx.nodes.new('ShaderNodeMix')
        turbulence_average.data_type = 'RGBA'
        turbulence_average.location = (260, -40)
        turbulence_average.label = 'Water Body Color'
        turbulence_average.inputs['Factor'].default_value = 0.5
        ctx.links.new(turbulence_a_node.outputs['Color'], turbulence_average.inputs['A'])
        ctx.links.new(turbulence_b_node.outputs['Color'], turbulence_average.inputs['B'])

        mask_channels = ctx.nodes.new('ShaderNodeSeparateColor')
        mask_channels.location = (260, -300)
        mask_channels.label = 'Water Foam Mask Channels'
        ctx.links.new(turbulence_mask_node.outputs['Color'], mask_channels.inputs['Color'])

        min_alpha = ctx.nodes.new('ShaderNodeMath')
        min_alpha.operation = 'MINIMUM'
        min_alpha.location = (500, -200)
        min_alpha.label = 'Water Min Turbulence Alpha'
        ctx.links.new(turbulence_a_node.outputs['Alpha'], min_alpha.inputs[0])
        ctx.links.new(turbulence_b_node.outputs['Alpha'], min_alpha.inputs[1])

        one_minus_mask = ctx.nodes.new('ShaderNodeMath')
        one_minus_mask.operation = 'SUBTRACT'
        one_minus_mask.location = (500, -340)
        one_minus_mask.label = 'Water 1 - MaskR'
        one_minus_mask.inputs[0].default_value = 1.0
        ctx.links.new(mask_channels.outputs['Red'], one_minus_mask.inputs[1])

        foam_subtract = ctx.nodes.new('ShaderNodeMath')
        foam_subtract.operation = 'SUBTRACT'
        foam_subtract.location = (720, -260)
        foam_subtract.label = 'Water Foam Seed'
        ctx.links.new(min_alpha.outputs['Value'], foam_subtract.inputs[0])
        ctx.links.new(one_minus_mask.outputs['Value'], foam_subtract.inputs[1])

        foam_clamp_low = ctx.nodes.new('ShaderNodeMath')
        foam_clamp_low.operation = 'MAXIMUM'
        foam_clamp_low.location = (940, -260)
        foam_clamp_low.label = 'Water Foam Clamp Low'
        foam_clamp_low.inputs[1].default_value = 0.0
        ctx.links.new(foam_subtract.outputs['Value'], foam_clamp_low.inputs[0])

        foam_clamp_high = ctx.nodes.new('ShaderNodeMath')
        foam_clamp_high.operation = 'MINIMUM'
        foam_clamp_high.location = (1160, -260)
        foam_clamp_high.label = 'Water Foam Clamp High'
        foam_clamp_high.inputs[1].default_value = 1.0
        ctx.links.new(foam_clamp_low.outputs['Value'], foam_clamp_high.inputs[0])

        foam_sqrt = ctx.nodes.new('ShaderNodeMath')
        foam_sqrt.operation = 'POWER'
        foam_sqrt.location = (1380, -260)
        foam_sqrt.label = 'Water Foam Factor'
        foam_sqrt.inputs[1].default_value = 0.5
        ctx.links.new(foam_clamp_high.outputs['Value'], foam_sqrt.inputs[0])

        final_color = ctx.nodes.new('ShaderNodeMix')
        final_color.data_type = 'RGBA'
        final_color.location = (1380, -40)
        final_color.label = 'Water Final Color'
        ctx.links.new(foam_sqrt.outputs['Value'], final_color.inputs['Factor'])
        ctx.links.new(turbulence_average.outputs['Result'], final_color.inputs['A'])
        ctx.links.new(water_colour_node.outputs['Color'], final_color.inputs['B'])

        BaseColorNodePasses.pop_base_color_source(ctx.links, ctx.principled)
        ctx.links.new(turbulence_average.outputs['Result'], ctx.principled.inputs['Base Color'])
        BaseColorNodePasses.pop_socket_source(ctx.links, ctx.principled, 'Roughness')
        ctx.principled.inputs['Roughness'].default_value = 0.08

        gloss_roughness = max(0.02, 1.0 - self._get_float_value(mat_data, 'glossValue', 0.5))

        body_reflection_color = ctx.nodes.new('ShaderNodeRGB')
        body_reflection_color.location = (1380, -760)
        body_reflection_color.label = 'Water Body Reflection Color'
        body_reflection_color.outputs['Color'].default_value = (0.05, 0.05, 0.05, 1.0)

        body_glossy = ctx.nodes.new('ShaderNodeBsdfGlossy')
        body_glossy.location = (1600, -760)
        body_glossy.label = 'Water Body Reflection'
        body_glossy.inputs['Roughness'].default_value = gloss_roughness
        ctx.links.new(body_reflection_color.outputs['Color'], body_glossy.inputs['Color'])
        if state.normal_socket is not None:
            ctx.links.new(state.normal_socket, body_glossy.inputs['Normal'])

        body_surface = ctx.nodes.new('ShaderNodeAddShader')
        body_surface.location = (1820, -640)
        body_surface.label = 'Water Body Surface'
        ctx.links.new(ctx.principled.outputs['BSDF'], body_surface.inputs[0])
        ctx.links.new(body_glossy.outputs['BSDF'], body_surface.inputs[1])

        foam_principled = ctx.nodes.new('ShaderNodeBsdfPrincipled')
        foam_principled.location = (1380, -260)
        foam_principled.label = 'Water Foam Surface'
        if 'IOR' in foam_principled.inputs:
            foam_principled.inputs['IOR'].default_value = 1.0
        foam_principled.inputs['Roughness'].default_value = 0.18
        ctx.links.new(water_colour_node.outputs['Color'], foam_principled.inputs['Base Color'])
        if state.normal_socket is not None:
            ctx.links.new(state.normal_socket, foam_principled.inputs['Normal'])

        layer_weight = ctx.nodes.new('ShaderNodeLayerWeight')
        layer_weight.location = (1180, -1040)
        layer_weight.label = 'Water Foam View Weight'
        layer_weight.inputs['Blend'].default_value = 0.2

        facing_square = ctx.nodes.new('ShaderNodeMath')
        facing_square.operation = 'MULTIPLY'
        facing_square.location = (1400, -1100)
        facing_square.label = 'Water Foam Facing^2'
        ctx.links.new(layer_weight.outputs['Facing'], facing_square.inputs[0])
        ctx.links.new(layer_weight.outputs['Facing'], facing_square.inputs[1])

        facing_plus_one = ctx.nodes.new('ShaderNodeMath')
        facing_plus_one.operation = 'ADD'
        facing_plus_one.location = (1400, -980)
        facing_plus_one.label = 'Water Foam 1 + Facing'
        facing_plus_one.inputs[0].default_value = 1.0
        ctx.links.new(layer_weight.outputs['Facing'], facing_plus_one.inputs[1])

        foam_reflection_strength = ctx.nodes.new('ShaderNodeMath')
        foam_reflection_strength.operation = 'SUBTRACT'
        foam_reflection_strength.location = (1620, -1040)
        foam_reflection_strength.label = 'Water Foam Reflection Strength'
        ctx.links.new(facing_plus_one.outputs['Value'], foam_reflection_strength.inputs[0])
        ctx.links.new(facing_square.outputs['Value'], foam_reflection_strength.inputs[1])

        foam_reflection_color = ctx.nodes.new('ShaderNodeCombineXYZ')
        foam_reflection_color.location = (1840, -1040)
        foam_reflection_color.label = 'Water Foam Reflection Color'
        ctx.links.new(foam_reflection_strength.outputs['Value'], foam_reflection_color.inputs['X'])
        ctx.links.new(foam_reflection_strength.outputs['Value'], foam_reflection_color.inputs['Y'])
        ctx.links.new(foam_reflection_strength.outputs['Value'], foam_reflection_color.inputs['Z'])

        foam_glossy = ctx.nodes.new('ShaderNodeBsdfGlossy')
        foam_glossy.location = (2060, -1040)
        foam_glossy.label = 'Water Foam Reflection'
        foam_glossy.inputs['Roughness'].default_value = gloss_roughness
        ctx.links.new(foam_reflection_color.outputs['Vector'], foam_glossy.inputs['Color'])
        if state.normal_socket is not None:
            ctx.links.new(state.normal_socket, foam_glossy.inputs['Normal'])

        foam_surface = ctx.nodes.new('ShaderNodeAddShader')
        foam_surface.location = (2280, -860)
        foam_surface.label = 'Water Foam Shader'
        ctx.links.new(foam_principled.outputs['BSDF'], foam_surface.inputs[0])
        ctx.links.new(foam_glossy.outputs['BSDF'], foam_surface.inputs[1])

        BaseColorNodePasses.pop_socket_source(ctx.links, ctx.output, 'Surface')

        mix_shader = ctx.nodes.new('ShaderNodeMixShader')
        mix_shader.location = (2520, -520)
        mix_shader.label = 'Water Surface Mix'
        ctx.links.new(foam_sqrt.outputs['Value'], mix_shader.inputs['Fac'])
        ctx.links.new(body_surface.outputs['Shader'], mix_shader.inputs[1])
        ctx.links.new(foam_surface.outputs['Shader'], mix_shader.inputs[2])
        ctx.links.new(mix_shader.outputs['Shader'], ctx.output.inputs['Surface'])

    def build_material(self, creator: Any, mat_data: Any) -> Any:
        material = super().build_material(creator, mat_data)
        material['dow2_shader_profile'] = 'water'
        return material


__all__ = ['WaterShaderMaterialBuilder']