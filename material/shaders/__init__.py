from .builders import (
    BuildingShaderMaterialBuilder,
    DefaultShaderMaterialBuilder,
    FxShaderMaterialBuilder,
    TerrainShaderMaterialBuilder,
    UnitShaderMaterialBuilder,
    WaterShaderMaterialBuilder,
    WorldObjectShaderMaterialBuilder,
)
from .layout import ShaderLayoutResolver
from .registry import ShaderBuilderRegistry
from .texture_handlers import (
    DefaultTextureHandler,
    DiffuseTextureHandler,
    EmissiveTextureHandler,
    GlossTextureHandler,
    NormalTextureHandler,
    OcclusionTextureHandler,
    SpecularTextureHandler,
    TeamTextureHandler,
)

__all__ = [
    "ShaderLayoutResolver",
    "ShaderBuilderRegistry",
    "DefaultShaderMaterialBuilder",
    "BuildingShaderMaterialBuilder",
    "UnitShaderMaterialBuilder",
    "WorldObjectShaderMaterialBuilder",
    "TerrainShaderMaterialBuilder",
    "FxShaderMaterialBuilder",
    "WaterShaderMaterialBuilder",
    "DiffuseTextureHandler",
    "NormalTextureHandler",
    "SpecularTextureHandler",
    "GlossTextureHandler",
    "EmissiveTextureHandler",
    "OcclusionTextureHandler",
    "TeamTextureHandler",
    "DefaultTextureHandler",
]
