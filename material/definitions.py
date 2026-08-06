VAR_TYPE_INT = 0
VAR_TYPE_FLOAT = 1
VAR_TYPE_FLOAT2 = 3
VAR_TYPE_FLOAT3 = 4
VAR_TYPE_FLOAT4 = 5
VAR_TYPE_MATRIX4 = 8
VAR_TYPE_TEXTURE = 9
VAR_TYPE_BOOL = 10

DEFAULT_MATERIAL_NAME = "relic.material.default"

TEXTURE_SLOT_NAMES = [
    "badge1Tex", "badge2Tex", "cliffNormalTex1", "cliffTex1",
    "damageDiffuseTex", "damageNormalTex", "damageSpecTex",
    "diffuseTex", "dirtTex", "dualScarDiffuseTex", "dualScarNormalTex",
    "dualScarSpecTex", "emissiveTex", "glossTex", "grassNormalTex1",
    "grassTex1", "normalMap", "normalMapCoarseTex", "normalMapFineTex",
    "normalMapFoamTex", "occlusionTex", "overlayTex", "scarTexture",
    "specularTex", "teamTex", "waterColourTex", "waterTurbulenceTex",
    "waterTurbulenceMaskTex",
]

TEXTURE_SLOTS = [
    ("badge1Tex", "Badge 1"),
    ("badge2Tex", "Badge 2"),
    ("cliffNormalTex1", "Cliff Normal 1"),
    ("cliffTex1", "Cliff 1"),
    ("damageDiffuseTex", "Damage Diffuse"),
    ("damageNormalTex", "Damage Normal"),
    ("damageSpecTex", "Damage Spec"),
    ("diffuseTex", "Diffuse"),
    ("dirtTex", "Dirt"),
    ("dualScarDiffuseTex", "Dual Scar Diffuse"),
    ("dualScarNormalTex", "Dual Scar Normal"),
    ("dualScarSpecTex", "Dual Scar Spec"),
    ("emissiveTex", "Emissive"),
    ("glossTex", "Gloss"),
    ("grassNormalTex1", "Grass Normal 1"),
    ("grassTex1", "Grass 1"),
    ("normalMap", "Normal Map"),
    ("normalMapCoarseTex", "Normal Coarse"),
    ("normalMapFineTex", "Normal Fine"),
    ("normalMapFoamTex", "Normal Foam"),
    ("occlusionTex", "Occlusion"),
    ("overlayTex", "Overlay"),
    ("scarTexture", "Scar"),
    ("specularTex", "Specular"),
    ("teamTex", "Team Color"),
    ("waterColourTex", "Water Colour"),
    ("waterTurbulenceTex", "Water Turbulence"),
    ("waterTurbulenceMaskTex", "Water Turb Mask"),
]

PARAM_SLOTS_BOOL = ["alphaTest", "bHighlight", "enableScarring", "useDepthTest", "useLighting"]
PARAM_SLOTS_INT = ["unitOcclusionFlag"]
PARAM_SLOTS_FLOAT = [
    "brightness",
    "damageTexTilingFactor",
    "dirtVisibility",
    "emissiveMultiplier",
    "glossValue",
    "uOffset",
    "vOffset",
]

BOOL_PARAMS = [
    ("alphaTest", "Alpha Test"),
    ("bHighlight", "Highlight"),
    ("enableScarring", "Enable Scarring"),
    ("useDepthTest", "Use Depth Test"),
    ("useLighting", "Use Lighting"),
]

INT_PARAMS = [
    ("unitOcclusionFlag", "Unit Occlusion Flag"),
]

FLOAT_PARAMS = [
    ("brightness", "Brightness", 1.0),
    ("damageTexTilingFactor", "Damage Tex Tiling", 1.0),
    ("dirtVisibility", "Dirt Visibility", 0.0),
    ("emissiveMultiplier", "Emissive Multiplier", 1.0),
    ("glossValue", "Gloss Value", 0.5),
    ("uOffset", "U Offset", 0.0),
    ("vOffset", "V Offset", 0.0),
]

DEFAULT_PALETTE_1 = (0.8, 0.1, 0.1, 1.0)
DEFAULT_PALETTE_2 = (0.9, 0.8, 0.2, 1.0)
DEFAULT_PALETTE_3 = (0.9, 0.9, 0.9, 1.0)
DEFAULT_PALETTE_4 = (0.9, 0.9, 0.9, 1.0)

__all__ = [
    "BOOL_PARAMS",
    "DEFAULT_MATERIAL_NAME",
    "DEFAULT_PALETTE_1",
    "DEFAULT_PALETTE_2",
    "DEFAULT_PALETTE_3",
    "DEFAULT_PALETTE_4",
    "FLOAT_PARAMS",
    "INT_PARAMS",
    "PARAM_SLOTS_BOOL",
    "PARAM_SLOTS_FLOAT",
    "PARAM_SLOTS_INT",
    "TEXTURE_SLOT_NAMES",
    "TEXTURE_SLOTS",
    "VAR_TYPE_BOOL",
    "VAR_TYPE_FLOAT",
    "VAR_TYPE_FLOAT2",
    "VAR_TYPE_FLOAT3",
    "VAR_TYPE_FLOAT4",
    "VAR_TYPE_INT",
    "VAR_TYPE_MATRIX4",
    "VAR_TYPE_TEXTURE",
]