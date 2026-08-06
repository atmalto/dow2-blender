from __future__ import annotations

import bpy

from .terrain_material_builder import build_terrain_material


def build_nav_overlay_material(name: str = "DoW2_MapNavOverlay") -> bpy.types.Material:
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.blend_method = 'BLEND'
    if hasattr(material, "shadow_method"):
        material.shadow_method = 'NONE'
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (500, 0)
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    transparent.location = (120, -80)
    emission = nodes.new("ShaderNodeEmission")
    emission.location = (120, 100)
    emission.inputs[0].default_value = (0.18, 0.62, 1.0, 1.0)
    emission.inputs[1].default_value = 0.9
    checker = nodes.new("ShaderNodeTexChecker")
    checker.location = (-360, 120)
    checker.inputs[3].default_value = 12.0
    checker.inputs[1].default_value = (0.30, 0.76, 1.0, 1.0)
    checker.inputs[2].default_value = (0.08, 0.34, 0.72, 1.0)
    mix_color = nodes.new("ShaderNodeMixRGB")
    mix_color.location = (-120, 120)
    mix_color.blend_type = 'MULTIPLY'
    mix_color.inputs[0].default_value = 0.45
    mix_shader = nodes.new("ShaderNodeMixShader")
    mix_shader.location = (320, 0)
    mix_shader.inputs[0].default_value = 0.78

    links.new(checker.outputs[0], mix_color.inputs[1])
    links.new(checker.outputs[1], mix_color.inputs[2])
    links.new(mix_color.outputs[0], emission.inputs[0])
    links.new(transparent.outputs[0], mix_shader.inputs[1])
    links.new(emission.outputs[0], mix_shader.inputs[2])
    links.new(mix_shader.outputs[0], output.inputs[0])
    return material


__all__ = [
    "build_nav_overlay_material",
    "build_terrain_material",
]