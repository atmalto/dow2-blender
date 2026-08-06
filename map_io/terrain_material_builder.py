from __future__ import annotations

from pathlib import Path

import bpy

from .terrain_material_images import build_texture_sets, build_usage_mask_payloads
from .terrain_material_nodes import build_layer_stack, build_mask_nodes


def build_terrain_material(
    *,
    name: str,
    tile_root: Path,
    layer_paths: list[tuple[str, str]],
    mask_payloads: list[tuple[str, int, int, bytes]],
    layer_usage_map: tuple[int, int, bytes] | None,
    tile_world_scale: float,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (1180, 0)
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (940, 0)
    if 'Roughness' in principled.inputs:
        principled.inputs['Roughness'].default_value = 0.7
    links.new(principled.outputs[0], output.inputs[0])

    mask_uv = nodes.new("ShaderNodeUVMap")
    mask_uv.location = (-1280, 420)
    mask_uv.uv_map = "TerrainMaskUV"
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-1460, 120)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-1220, 120)
    if tile_world_scale > 0.0:
        scale = 1.0 / tile_world_scale
        mapping.inputs[3].default_value[0] = scale
        mapping.inputs[3].default_value[1] = scale
        mapping.inputs[3].default_value[2] = scale
    links.new(texcoord.outputs['Object'], mapping.inputs[0])

    geometry = nodes.new("ShaderNodeNewGeometry")
    geometry.location = (-1460, -220)
    separate_normal = nodes.new("ShaderNodeSeparateXYZ")
    separate_normal.location = (-1220, -220)
    links.new(geometry.outputs['Normal'], separate_normal.inputs[0])
    abs_normal_z = nodes.new("ShaderNodeMath")
    abs_normal_z.location = (-980, -220)
    abs_normal_z.operation = 'ABSOLUTE'
    links.new(separate_normal.outputs['Z'], abs_normal_z.inputs[0])
    ground_factor = nodes.new("ShaderNodeMapRange")
    ground_factor.location = (-760, -220)
    ground_factor.clamp = True
    ground_factor.inputs[1].default_value = 0.3
    ground_factor.inputs[2].default_value = 0.85
    ground_factor.inputs[3].default_value = 0.0
    ground_factor.inputs[4].default_value = 1.0
    links.new(abs_normal_z.outputs['Value'], ground_factor.inputs[0])

    mask_nodes = build_mask_nodes(nodes, links, mask_uv.outputs[0], mask_payloads)
    usage_mask_payloads = build_usage_mask_payloads(mask_payloads, layer_usage_map)
    usage_nodes = build_mask_nodes(nodes, links, mask_uv.outputs[0], usage_mask_payloads)
    texture_sets, sampler_count, truncated_layer_count = build_texture_sets(
        tile_root=tile_root,
        layer_paths=layer_paths,
        initial_sampler_count=len(mask_nodes) + len(usage_nodes),
    )
    blend_sockets = build_layer_stack(
        nodes=nodes,
        links=links,
        vector_socket=mapping.outputs[0],
        ground_factor_socket=ground_factor.outputs[0],
        texture_sets=texture_sets,
        mask_nodes=mask_nodes,
        usage_nodes=usage_nodes,
    )

    if blend_sockets.color is None:
        rgb = nodes.new("ShaderNodeRGB")
        rgb.location = (700, 120)
        rgb.outputs[0].default_value = (0.5, 0.5, 0.5, 1.0)
        blend_sockets = type(blend_sockets)(
            color=rgb.outputs[0],
            normal=blend_sockets.normal,
            spec_alpha=blend_sockets.spec_alpha,
        )

    links.new(blend_sockets.color, principled.inputs['Base Color'])

    if blend_sockets.normal is not None and 'Normal' in principled.inputs:
        normal_map = nodes.new('ShaderNodeNormalMap')
        normal_map.location = (720, -220)
        links.new(blend_sockets.normal, normal_map.inputs['Color'])
        links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])

    if blend_sockets.spec_alpha is not None and 'Roughness' in principled.inputs:
        gloss_to_roughness = nodes.new('ShaderNodeMath')
        gloss_to_roughness.operation = 'SUBTRACT'
        gloss_to_roughness.use_clamp = True
        gloss_to_roughness.location = (720, -420)
        gloss_to_roughness.inputs[0].default_value = 2.0
        links.new(blend_sockets.spec_alpha, gloss_to_roughness.inputs[1])
        links.new(gloss_to_roughness.outputs['Value'], principled.inputs['Roughness'])

    material["dow2_sampler_count"] = sampler_count
    material["dow2_truncated_layer_count"] = truncated_layer_count
    material["dow2_terrain_material_mode"] = "layer_pair_weighted_box_projection"
    material["dow2_terrain_tile_world_scale"] = float(tile_world_scale)
    material["dow2_terrain_uses_chunk_activity"] = bool(layer_usage_map)
    material["dow2_terrain_selector_model"] = "layer_slot_fallback"
    return material


__all__ = ["build_terrain_material"]