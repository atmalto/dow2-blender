from __future__ import annotations

from typing import Any, Sequence

from .interfaces import MaterialBuildContext, MaterialBuildState


class BaseTextureSlotHandler:
    names: Sequence[str] = ()
    non_color: bool = False

    def can_handle(self, var_name_lower: str) -> bool:
        return var_name_lower in self.names


class DiffuseTextureHandler(BaseTextureSlotHandler):
    names = ("diffusetex", "diffuse")

    def handle(self, creator: Any, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, var: Any) -> bool:
        uv_map_name = creator.get_texture_uv_map(mat_data.shader_name, var.name)
        tex_node = creator.create_image_node(
            ctx.nodes,
            ctx.links,
            var.value,
            (state.tex_x, state.tex_y),
            var.name,
            uv_map_name=uv_map_name,
        )
        if tex_node:
            state.texture_nodes[var.name.lower()] = tex_node
            state.diffuse_tex_node = tex_node
            ctx.links.new(tex_node.outputs['Color'], ctx.principled.inputs['Base Color'])
            ctx.links.new(tex_node.outputs['Alpha'], ctx.principled.inputs['Alpha'])
        state.next_texture_row()
        return True


class NormalTextureHandler(BaseTextureSlotHandler):
    names = ("normalmap", "normal", "normaltex")
    non_color = True

    def handle(self, creator: Any, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, var: Any) -> bool:
        uv_map_name = creator.get_texture_uv_map(mat_data.shader_name, var.name)
        tex_node = creator.create_image_node(
            ctx.nodes,
            ctx.links,
            var.value,
            (state.tex_x, state.tex_y),
            var.name,
            non_color=True,
            uv_map_name=uv_map_name,
        )
        if tex_node:
            state.texture_nodes[var.name.lower()] = tex_node
            normal_map = ctx.nodes.new('ShaderNodeNormalMap')
            normal_map.location = (state.tex_x + 300, state.tex_y)
            ctx.links.new(tex_node.outputs['Color'], normal_map.inputs['Color'])
            ctx.links.new(normal_map.outputs['Normal'], ctx.principled.inputs['Normal'])
            state.normal_socket = normal_map.outputs['Normal']
        state.next_texture_row()
        return True


class SpecularTextureHandler(BaseTextureSlotHandler):
    names = ("speculartex", "specular")
    non_color = True

    def handle(self, creator: Any, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, var: Any) -> bool:
        uv_map_name = creator.get_texture_uv_map(mat_data.shader_name, var.name)
        tex_node = creator.create_image_node(
            ctx.nodes,
            ctx.links,
            var.value,
            (state.tex_x, state.tex_y),
            var.name,
            non_color=True,
            uv_map_name=uv_map_name,
        )
        if tex_node:
            state.texture_nodes[var.name.lower()] = tex_node
            state.specular_tex_node = tex_node
            state.specular_color_socket = tex_node.outputs['Color']

        state.next_texture_row()
        return True


class GlossTextureHandler(BaseTextureSlotHandler):
    names = ("glosstex", "gloss")
    non_color = True

    def handle(self, creator: Any, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, var: Any) -> bool:
        uv_map_name = creator.get_texture_uv_map(mat_data.shader_name, var.name)
        tex_node = creator.create_image_node(
            ctx.nodes,
            ctx.links,
            var.value,
            (state.tex_x, state.tex_y),
            var.name,
            non_color=True,
            uv_map_name=uv_map_name,
        )
        if tex_node:
            state.texture_nodes[var.name.lower()] = tex_node
            invert_gloss = ctx.nodes.new('ShaderNodeInvert')
            invert_gloss.location = (state.tex_x + 260, state.tex_y)
            invert_gloss.inputs['Fac'].default_value = 0.25
            ctx.links.new(tex_node.outputs['Color'], invert_gloss.inputs['Color'])
            ctx.links.new(invert_gloss.outputs['Color'], ctx.principled.inputs['Roughness'])
        state.next_texture_row()
        return True


class EmissiveTextureHandler(BaseTextureSlotHandler):
    names = ("emissivetex", "emissive", "glowtex", "glow")

    def handle(self, creator: Any, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, var: Any) -> bool:
        uv_map_name = creator.get_texture_uv_map(mat_data.shader_name, var.name)
        tex_node = creator.create_image_node(
            ctx.nodes,
            ctx.links,
            var.value,
            (state.tex_x, state.tex_y),
            var.name,
            uv_map_name=uv_map_name,
        )
        if tex_node:
            state.texture_nodes[var.name.lower()] = tex_node
            state.emissive_tex_node = tex_node
            ctx.links.new(tex_node.outputs['Color'], ctx.principled.inputs['Emission Color'])
            emit_mult = mat_data.get_variable("emissiveMultiplier")
            if emit_mult:
                ctx.principled.inputs['Emission Strength'].default_value = emit_mult.value
            else:
                ctx.principled.inputs['Emission Strength'].default_value = 1.0
        state.next_texture_row()
        return True


class OcclusionTextureHandler(BaseTextureSlotHandler):
    names = ("occlusiontex", "occlusion", "ao")
    non_color = True

    def handle(self, creator: Any, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, var: Any) -> bool:
        uv_map_name = creator.get_texture_uv_map(mat_data.shader_name, var.name)
        tex_node = creator.create_image_node(
            ctx.nodes,
            ctx.links,
            var.value,
            (state.tex_x, state.tex_y),
            var.name,
            non_color=True,
            uv_map_name=uv_map_name,
        )
        if tex_node:
            state.texture_nodes[var.name.lower()] = tex_node
            state.ao_tex_node = tex_node
        state.next_texture_row()
        return True


class TeamTextureHandler(BaseTextureSlotHandler):
    names = ("teamtex", "teamcolour", "teamcolor")

    def handle(self, creator: Any, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, var: Any) -> bool:
        uv_map_name = creator.get_texture_uv_map(mat_data.shader_name, var.name)
        tex_node = creator.create_image_node(
            ctx.nodes,
            ctx.links,
            var.value,
            (state.tex_x, state.tex_y),
            var.name,
            uv_map_name=uv_map_name,
        )
        if tex_node:
            state.texture_nodes[var.name.lower()] = tex_node
            state.team_tex_node = tex_node
        state.next_texture_row()
        return True


class DirtTextureHandler(BaseTextureSlotHandler):
    names = ("dirttex",)

    def handle(self, creator: Any, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, var: Any) -> bool:
        uv_map_name = creator.get_texture_uv_map(mat_data.shader_name, var.name)
        tex_node = creator.create_image_node(
            ctx.nodes,
            ctx.links,
            var.value,
            (state.tex_x, state.tex_y),
            var.name,
            uv_map_name=uv_map_name,
        )
        if tex_node:
            state.texture_nodes[var.name.lower()] = tex_node
        state.next_texture_row()
        return True


class DefaultTextureHandler(BaseTextureSlotHandler):
    names = ()

    def can_handle(self, var_name_lower: str) -> bool:
        return True

    def handle(self, creator: Any, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, var: Any) -> bool:
        uv_map_name = creator.get_texture_uv_map(mat_data.shader_name, var.name)
        tex_node = creator.create_image_node(
            ctx.nodes,
            ctx.links,
            var.value,
            (state.tex_x, state.tex_y),
            var.name,
            uv_map_name=uv_map_name,
        )
        if tex_node:
            state.texture_nodes[var.name.lower()] = tex_node
        state.next_texture_row()
        return True
