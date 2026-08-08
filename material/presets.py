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
        "shader": "dow2_unit",
        "textures": ["diffuseTex", "normalMap", "specularTex", "teamTex"],
        "params": {},
    },
    "dow2_unit_alpha": {
        "shader": "dow2_unit_alpha",
        "textures": ["diffuseTex", "normalMap", "specularTex", "teamTex"],
        "params": {},
    },
    "dow2_unit_emissive": {
        "shader": "dow2_unit",
        "textures": ["diffuseTex", "normalMap", "specularTex", "teamTex", "emissiveTex"],
        "params": {"emissiveMultiplier": 1.0},
    },
    "dow2_building": {
        "shader": "dow2_building_brick",
        "textures": ["diffuseTex", "normalMap", "specularTex"],
        "params": {"glossValue": 0.3},
    },
    "dow2_building_destruct": {
        "shader": "dow2_building_brick_scar_dual",
        "textures": ["diffuseTex", "normalMap", "specularTex", "damageDiffuseTex", "damageNormalTex"],
        "params": {"glossValue": 0.3, "damageTexTilingFactor": 1.0},
    },
    "dow2_terrain": {
        "shader": "dow2_terrain_object",
        "textures": ["cliffTex1", "cliffNormalTex1", "grassTex1", "grassNormalTex1"],
        "params": {},
    },
    "dow2_fx": {
        "shader": "dow2_fxmesh_alpha",
        "textures": ["diffuseTex"],
        "params": {"useLighting": False, "useDepthTest": True},
    },
    "dow2_decal": {
        "shader": "dow2_object",
        "textures": ["diffuseTex", "normalMap"],
        "params": {},
    },
}

__all__ = [
    "SHADER_PRESETS",
    "SHADER_PRESET_CONFIG",
    "SHADER_PRESET_LABELS",
]