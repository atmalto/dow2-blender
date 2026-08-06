SHADER_PRESETS = [
    ("NONE", "-- Select Shader --", "Select a shader to populate material properties"),
    ("dow2_unit", "Unit (Standard)", "Standard unit shader with diffuse, normal, specular, team color"),
    ("dow2_unit_alpha", "Unit (Alpha)", "Unit shader with alpha transparency"),
    ("dow2_unit_emissive", "Unit (Emissive)", "Unit shader with emissive/glow support"),
    ("dow2_building", "Building", "Building/structure shader"),
    ("dow2_building_destruct", "Building (Destructible)", "Destructible building with damage states"),
    ("dow2_terrain", "Terrain", "Terrain shader"),
    ("dow2_fx", "FX/Particle", "Effect/particle shader"),
    ("dow2_decal", "Decal", "Decal shader for ground effects"),
]

SHADER_PRESET_LABELS = {key: label for key, label, _ in SHADER_PRESETS}

SHADER_PRESET_CONFIG = {
    "dow2_unit": {
        "textures": ["diffuseTex", "normalMap", "specularTex", "teamTex"],
        "params": {"useLighting": True, "useDepthTest": True, "glossValue": 0.5},
    },
    "dow2_unit_alpha": {
        "textures": ["diffuseTex", "normalMap", "specularTex", "teamTex"],
        "params": {"useLighting": True, "useDepthTest": True, "alphaTest": True, "glossValue": 0.5},
    },
    "dow2_unit_emissive": {
        "textures": ["diffuseTex", "normalMap", "specularTex", "teamTex", "emissiveTex"],
        "params": {"useLighting": True, "useDepthTest": True, "glossValue": 0.5, "emissiveMultiplier": 1.0},
    },
    "dow2_building": {
        "textures": ["diffuseTex", "normalMap", "specularTex"],
        "params": {"useLighting": True, "useDepthTest": True, "glossValue": 0.3},
    },
    "dow2_building_destruct": {
        "textures": ["diffuseTex", "normalMap", "specularTex", "damageDiffuseTex", "damageNormalTex"],
        "params": {"useLighting": True, "useDepthTest": True, "glossValue": 0.3, "damageTexTilingFactor": 1.0},
    },
    "dow2_terrain": {
        "textures": ["diffuseTex", "normalMap"],
        "params": {"useLighting": True, "useDepthTest": True},
    },
    "dow2_fx": {
        "textures": ["diffuseTex"],
        "params": {"useLighting": False, "alphaTest": True},
    },
    "dow2_decal": {
        "textures": ["diffuseTex", "normalMap"],
        "params": {"useLighting": True, "useDepthTest": False, "alphaTest": True},
    },
}

__all__ = [
    "SHADER_PRESETS",
    "SHADER_PRESET_CONFIG",
    "SHADER_PRESET_LABELS",
]