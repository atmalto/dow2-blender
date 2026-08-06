from __future__ import annotations

from typing import Dict, Optional

from .builders import (
    BuildingShaderMaterialBuilder,
    BuildingBrickScarDualShaderMaterialBuilder,
    DefaultShaderMaterialBuilder,
    DynamicWorldObjectShaderMaterialBuilder,
    DynamicWorldObjectTwoUvShaderMaterialBuilder,
    FullbrightShaderMaterialBuilder,
    FxAdditiveShaderMaterialBuilder,
    FxAlphaShaderMaterialBuilder,
    FxShaderMaterialBuilder,
    StaticWorldObjectShaderMaterialBuilder,
    TerrainShaderMaterialBuilder,
    TerrainObjectShaderMaterialBuilder,
    UnitShaderMaterialBuilder,
    WargearShaderMaterialBuilder,
    WaterShaderMaterialBuilder,
    WorldObjectShaderMaterialBuilder,
)
from .interfaces import ShaderMaterialBuilder
from .layout import ShaderLayoutResolver


class ShaderBuilderRegistry:
    """Resolves shader name to concrete material builder strategy."""

    def __init__(self, layout_resolver: ShaderLayoutResolver):
        self.layout_resolver = layout_resolver
        self._default_builder = DefaultShaderMaterialBuilder()
        self._building_builder = BuildingShaderMaterialBuilder()
        self._building_scar_dual_builder = BuildingBrickScarDualShaderMaterialBuilder()
        self._unit_builder = UnitShaderMaterialBuilder()
        self._wargear_builder = WargearShaderMaterialBuilder()
        self._world_object_builder = WorldObjectShaderMaterialBuilder()
        self._dynamic_world_object_builder = DynamicWorldObjectShaderMaterialBuilder()
        self._dynamic_world_object_two_uv_builder = DynamicWorldObjectTwoUvShaderMaterialBuilder()
        self._static_world_object_builder = StaticWorldObjectShaderMaterialBuilder()
        self._terrain_builder = TerrainShaderMaterialBuilder()
        self._terrain_object_builder = TerrainObjectShaderMaterialBuilder()
        self._fx_builder = FxShaderMaterialBuilder()
        self._fx_alpha_builder = FxAlphaShaderMaterialBuilder()
        self._fx_additive_builder = FxAdditiveShaderMaterialBuilder()
        self._fullbright_builder = FullbrightShaderMaterialBuilder()
        self._water_builder = WaterShaderMaterialBuilder()

        self._exact_map: Dict[str, ShaderMaterialBuilder] = {
            "dow2_building_brick": self._building_builder,
            "dow2_building_brick_scar_dual": self._building_scar_dual_builder,
            "dow2_unit": self._unit_builder,
            "dow2_unit_2uv": self._unit_builder,
            "dow2_unit_alpha": self._unit_builder,
            "dow2_wargear": self._wargear_builder,
            "dow2_dynamic_world_object": self._dynamic_world_object_builder,
            "dow2_dynamic_world_object_two_uv": self._dynamic_world_object_two_uv_builder,
            "dow2_static_world_object": self._static_world_object_builder,
            "dow2_terrain_object": self._terrain_object_builder,
            "dow2_terrain_tile_object": self._terrain_builder,
            "dow2_fxmesh_alpha": self._fx_alpha_builder,
            "dow2_fxmesh_additive": self._fx_additive_builder,
            "dow2_fxmesh_additive_falloff": self._fx_builder,
            "dow2_fullbright": self._fullbright_builder,
            "dow2_water_object": self._water_builder,
            "dow2_environmentprobe": self._world_object_builder,
            "dow2_light": self._fx_builder,
            "dow2_lightprobe": self._fx_builder,
        }

        self._prefix_map = [
            ("dow2_building", self._building_builder),
            ("dow2_unit", self._unit_builder),
            ("dow2_wargear", self._wargear_builder),
            ("dow2_dynamic_world_object", self._world_object_builder),
            ("dow2_static_world_object", self._world_object_builder),
            ("dow2_terrain", self._terrain_builder),
            ("dow2_fxmesh", self._fx_builder),
            ("dow2_water", self._water_builder),
            ("dow2_light", self._fx_builder),
        ]

    def get_builder(self, shader_name: Optional[str]) -> ShaderMaterialBuilder:
        key = (shader_name or "").strip().lower()
        if not key:
            return self._default_builder

        builder = self._exact_map.get(key)
        if builder is not None:
            return builder

        for prefix, mapped_builder in self._prefix_map:
            if key.startswith(prefix):
                return mapped_builder

        if self.layout_resolver.uses_building_uv_layout(key):
            return self._building_builder

        return self._default_builder
