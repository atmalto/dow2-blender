from __future__ import annotations

import os
from typing import Dict


class ShaderLayoutResolver:
    """Resolves per-shader layout policies (UV routing and other shader metadata)."""

    _EXACT_TEXTURE_UV_MAPS = {
        "dow2_building_brick_scar_dual": {
            "dualscardiffusetex": "UVMap2",
            "dualscarnormaltex": "UVMap2",
            "dualscarspectex": "UVMap2",
        },
        "dow2_dynamic_world_object_two_uv": {
            "overlaytex": "UVMap2",
        },
    }

    _BUILDING_UV1_TEXTURES = {
        "normalmap",
        "damagenormaltex",
        "damagediffusetex",
        "damagespectex",
    }

    def __init__(self, game_data_path: str):
        self.game_data_path = game_data_path
        self._shader_uv_cache: Dict[str, bool] = {}

    def uses_building_uv_layout(self, shader_name: str) -> bool:
        if not shader_name:
            return False

        key = shader_name.lower()
        cached = self._shader_uv_cache.get(key)
        if cached is not None:
            return cached

        shader_path = os.path.join(self.game_data_path, "shaders", f"{shader_name}.shader")
        uses_building_layout = False

        try:
            if os.path.exists(shader_path):
                with open(shader_path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                uses_building_layout = (
                    '"Building"' in content or
                    '"BuildingSkinned"' in content
                )
        except Exception:
            uses_building_layout = False

        self._shader_uv_cache[key] = uses_building_layout
        return uses_building_layout

    def get_texture_uv_map(self, shader_name: str, texture_var_name: str) -> str:
        shader_key = (shader_name or "").lower()
        texture_key = (texture_var_name or "").lower()

        exact_shader_maps = self._EXACT_TEXTURE_UV_MAPS.get(shader_key)
        if exact_shader_maps and texture_key in exact_shader_maps:
            return exact_shader_maps[texture_key]

        if not self.uses_building_uv_layout(shader_name):
            return "UVMap"

        return "UVMap2" if texture_key in self._BUILDING_UV1_TEXTURES else "UVMap"


__all__ = ["ShaderLayoutResolver"]