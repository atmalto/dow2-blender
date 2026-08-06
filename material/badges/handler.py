from __future__ import annotations

from typing import Any


class BadgeTextureHandler:
    """Badge-owned texture handler for badge decal slots."""

    names = ("badge1tex", "badge2tex")

    def can_handle(self, var_name_lower: str) -> bool:
        return var_name_lower in self.names

    def handle(self, creator: Any, ctx: Any, state: Any, mat_data: Any, var: Any) -> bool:
        uv_map_name = creator.get_texture_uv_map(mat_data.shader_name, var.name)
        tex_node = creator.create_image_node(
            ctx.nodes,
            ctx.links,
            var.value,
            (state.tex_x, state.tex_y),
            var.name,
            uv_map_name=uv_map_name,
            extension='CLIP',
        )
        if tex_node:
            state.texture_nodes[var.name.lower()] = tex_node
        state.next_texture_row()
        return True


__all__ = ["BadgeTextureHandler"]