from __future__ import annotations

import bpy

from .terrain_material_images import ensure_image_from_rgba
from .terrain_material_types import TerrainBlendSockets, TerrainTextureSet


def create_texture_node(
    nodes,
    links,
    vector_socket,
    image: bpy.types.Image | None,
    location,
    label: str,
    *,
    interpolation: str = 'Linear',
    projection: str = 'FLAT',
    projection_blend: float = 0.0,
):
    if image is None:
        return None
    node = nodes.new("ShaderNodeTexImage")
    node.location = location
    node.image = image
    node.label = label
    node.extension = 'REPEAT'
    node.interpolation = interpolation
    node.projection = projection
    if hasattr(node, "projection_blend"):
        node.projection_blend = projection_blend
    links.new(vector_socket, node.inputs[0])
    return node


def create_mix_node(nodes, links, factor_socket, socket_a, socket_b, location, label: str, *, data_type: str):
    if socket_a is None:
        return socket_b
    if socket_b is None:
        return socket_a
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = data_type
    mix.blend_type = 'MIX'
    mix.clamp_factor = True
    mix.location = location
    mix.label = label
    links.new(factor_socket, mix.inputs['Factor'])
    links.new(socket_a, mix.inputs['A'])
    links.new(socket_b, mix.inputs['B'])
    return mix.outputs['Result']


def create_math_node(
    nodes,
    links,
    operation: str,
    socket_a,
    socket_b,
    location,
    label: str,
):
    node = nodes.new("ShaderNodeMath")
    node.operation = operation
    node.location = location
    node.label = label
    if socket_a is not None:
        links.new(socket_a, node.inputs[0])
    if socket_b is not None:
        links.new(socket_b, node.inputs[1])
    return node.outputs['Value']


def create_vector_math_node(
    nodes,
    links,
    operation: str,
    vector_socket,
    value_socket,
    location,
    label: str,
):
    node = nodes.new("ShaderNodeVectorMath")
    node.operation = operation
    node.location = location
    node.label = label
    if vector_socket is not None:
        links.new(vector_socket, node.inputs[0])
    if value_socket is not None:
        if operation == 'SCALE':
            links.new(value_socket, node.inputs[3])
        else:
            links.new(value_socket, node.inputs[1])
    return node.outputs['Vector']


def create_layer_weight_socket(*, nodes, links, mask_nodes, layer_index: int, location):
    if not mask_nodes:
        value = nodes.new("ShaderNodeValue")
        value.location = location
        value.label = f"Layer {layer_index} Weight"
        value.outputs[0].default_value = 1.0
        return value.outputs[0]
    mask_index = min(layer_index // 4, len(mask_nodes) - 1)
    channel_index = layer_index % 4
    if mask_index < 0 or mask_index >= len(mask_nodes):
        value = nodes.new("ShaderNodeValue")
        value.location = location
        value.label = f"Layer {layer_index} Weight"
        value.outputs[0].default_value = 1.0
        return value.outputs[0]
    return mask_nodes[mask_index][1][channel_index]


def create_layer_activity_socket(*, nodes, usage_nodes, layer_index: int, location):
    if not usage_nodes:
        value = nodes.new("ShaderNodeValue")
        value.location = location
        value.label = f"Layer {layer_index} Active"
        value.outputs[0].default_value = 1.0
        return value.outputs[0]
    usage_mask_index = layer_index // 4
    if usage_mask_index >= len(usage_nodes):
        value = nodes.new("ShaderNodeValue")
        value.location = location
        value.label = f"Layer {layer_index} Active"
        value.outputs[0].default_value = 1.0
        return value.outputs[0]
    usage_channel_index = layer_index % 4
    return usage_nodes[usage_mask_index][1][usage_channel_index]


def build_mask_nodes(nodes, links, mask_uv_socket, mask_payloads: list[tuple[str, int, int, bytes]]):
    mask_nodes: list[tuple[bpy.types.Node, tuple[bpy.types.NodeSocket, bpy.types.NodeSocket, bpy.types.NodeSocket, bpy.types.NodeSocket]]] = []
    for mask_index, (mask_name, width, height, rgba_bytes) in enumerate(mask_payloads[:2]):
        image = ensure_image_from_rgba(mask_name, width, height, rgba_bytes)
        image_node = nodes.new("ShaderNodeTexImage")
        image_node.location = (-1020, 520 - (mask_index * 260))
        image_node.image = image
        image_node.interpolation = 'Closest'
        image_node.extension = 'EXTEND'
        image_node.label = mask_name
        links.new(mask_uv_socket, image_node.inputs[0])

        separate = nodes.new("ShaderNodeSeparateColor")
        separate.location = (-780, 520 - (mask_index * 260))
        links.new(image_node.outputs[0], separate.inputs[0])
        mask_nodes.append(
            (
                image_node,
                (
                    separate.outputs[0],
                    separate.outputs[1],
                    separate.outputs[2],
                    image_node.outputs['Alpha'],
                ),
            )
        )
    return mask_nodes


def build_layer_stack(
    *,
    nodes,
    links,
    vector_socket,
    ground_factor_socket,
    texture_sets: list[TerrainTextureSet],
    mask_nodes,
    usage_nodes,
) -> TerrainBlendSockets:
    zero_rgb = nodes.new("ShaderNodeRGB")
    zero_rgb.location = (-1800, -460)
    zero_rgb.label = "Terrain Zero RGB"
    zero_rgb.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)

    zero_value = nodes.new("ShaderNodeValue")
    zero_value.location = (-1800, -560)
    zero_value.label = "Terrain Zero Value"
    zero_value.outputs[0].default_value = 0.0

    epsilon_value = nodes.new("ShaderNodeValue")
    epsilon_value.location = (-1800, -660)
    epsilon_value.label = "Terrain Weight Epsilon"
    epsilon_value.outputs[0].default_value = 0.00001

    accumulated_color_socket = zero_rgb.outputs[0]
    accumulated_normal_socket = zero_rgb.outputs[0]
    accumulated_spec_alpha_socket = zero_value.outputs[0]
    accumulated_weight_socket = zero_value.outputs[0]

    for texture_set in texture_sets:
        layer_index = texture_set.layer_index
        y = layer_index * -260

        surface_color_node = create_texture_node(
            nodes,
            links,
            vector_socket,
            texture_set.surface_diffuse,
            (-620, y),
            f"Layer {layer_index} Surface Color",
            projection='BOX',
            projection_blend=0.18,
        )
        cliff_color_node = create_texture_node(
            nodes,
            links,
            vector_socket,
            texture_set.cliff_diffuse,
            (-620, y - 120),
            f"Layer {layer_index} Cliff Color",
            projection='BOX',
            projection_blend=0.18,
        )
        surface_normal_node = create_texture_node(
            nodes,
            links,
            vector_socket,
            texture_set.surface_normal,
            (-980, y),
            f"Layer {layer_index} Surface Normal",
            projection='BOX',
            projection_blend=0.18,
        )
        cliff_normal_node = create_texture_node(
            nodes,
            links,
            vector_socket,
            texture_set.cliff_normal,
            (-980, y - 120),
            f"Layer {layer_index} Cliff Normal",
            projection='BOX',
            projection_blend=0.18,
        )
        surface_spec_node = create_texture_node(
            nodes,
            links,
            vector_socket,
            texture_set.surface_spec,
            (-1340, y),
            f"Layer {layer_index} Surface Spec",
            projection='BOX',
            projection_blend=0.18,
        )
        cliff_spec_node = create_texture_node(
            nodes,
            links,
            vector_socket,
            texture_set.cliff_spec,
            (-1340, y - 120),
            f"Layer {layer_index} Cliff Spec",
            projection='BOX',
            projection_blend=0.18,
        )

        layer_color_socket = create_mix_node(
            nodes,
            links,
            ground_factor_socket,
            cliff_color_node.outputs['Color'] if cliff_color_node is not None else None,
            surface_color_node.outputs['Color'] if surface_color_node is not None else None,
            (-360, y - 40),
            f"Layer {layer_index} Surface Cliff Color",
            data_type='RGBA',
        )
        layer_normal_socket = create_mix_node(
            nodes,
            links,
            ground_factor_socket,
            cliff_normal_node.outputs['Color'] if cliff_normal_node is not None else None,
            surface_normal_node.outputs['Color'] if surface_normal_node is not None else None,
            (-720, y - 40),
            f"Layer {layer_index} Surface Cliff Normal",
            data_type='RGBA',
        )
        layer_spec_alpha_socket = create_mix_node(
            nodes,
            links,
            ground_factor_socket,
            cliff_spec_node.outputs['Alpha'] if cliff_spec_node is not None else None,
            surface_spec_node.outputs['Alpha'] if surface_spec_node is not None else None,
            (-1080, y - 40),
            f"Layer {layer_index} Surface Cliff Spec",
            data_type='FLOAT',
        )

        layer_weight_socket = create_layer_weight_socket(
            nodes=nodes,
            links=links,
            mask_nodes=mask_nodes,
            layer_index=layer_index,
            location=(-1560, y - 40),
        )
        layer_activity_socket = create_layer_activity_socket(
            nodes=nodes,
            usage_nodes=usage_nodes,
            layer_index=layer_index,
            location=(-1560, y - 140),
        )
        layer_weight_socket = create_math_node(
            nodes,
            links,
            'MULTIPLY',
            layer_weight_socket,
            layer_activity_socket,
            (-1440, y - 90),
            f"Layer {layer_index} Active Weight",
        )
        accumulated_weight_socket = create_math_node(
            nodes,
            links,
            'ADD',
            accumulated_weight_socket,
            layer_weight_socket,
            (-1320, y - 40),
            f"Layer {layer_index} Weight Sum",
        )
        weighted_color_socket = create_vector_math_node(
            nodes,
            links,
            'SCALE',
            layer_color_socket,
            layer_weight_socket,
            (-120, y),
            f"Layer {layer_index} Weighted Color",
        )
        weighted_normal_socket = create_vector_math_node(
            nodes,
            links,
            'SCALE',
            layer_normal_socket,
            layer_weight_socket,
            (-360, y),
            f"Layer {layer_index} Weighted Normal",
        )
        weighted_spec_alpha_socket = create_math_node(
            nodes,
            links,
            'MULTIPLY',
            layer_spec_alpha_socket,
            layer_weight_socket,
            (-600, y),
            f"Layer {layer_index} Weighted Spec",
        )

        accumulated_color_socket = create_vector_math_node(
            nodes,
            links,
            'ADD',
            accumulated_color_socket,
            weighted_color_socket,
            (120, y),
            f"Layer {layer_index} Color Sum",
        )
        accumulated_normal_socket = create_vector_math_node(
            nodes,
            links,
            'ADD',
            accumulated_normal_socket,
            weighted_normal_socket,
            (-120, y - 120),
            f"Layer {layer_index} Normal Sum",
        )
        accumulated_spec_alpha_socket = create_math_node(
            nodes,
            links,
            'ADD',
            accumulated_spec_alpha_socket,
            weighted_spec_alpha_socket,
            (-360, y - 120),
            f"Layer {layer_index} Spec Sum",
        )

    safe_weight_socket = create_math_node(
        nodes,
        links,
        'MAXIMUM',
        accumulated_weight_socket,
        epsilon_value.outputs[0],
        (360, -520),
        'Terrain Safe Weight',
    )
    inverse_weight_socket = create_math_node(
        nodes,
        links,
        'DIVIDE',
        None,
        safe_weight_socket,
        (580, -520),
        'Terrain Inverse Weight',
    )
    inverse_weight_node = inverse_weight_socket.node
    inverse_weight_node.inputs[0].default_value = 1.0

    mixed_color_socket = create_vector_math_node(
        nodes,
        links,
        'SCALE',
        accumulated_color_socket,
        inverse_weight_socket,
        (760, -160),
        'Terrain Weighted Color',
    )
    mixed_normal_socket = create_vector_math_node(
        nodes,
        links,
        'SCALE',
        accumulated_normal_socket,
        inverse_weight_socket,
        (520, -280),
        'Terrain Weighted Normal',
    )
    mixed_spec_alpha_socket = create_math_node(
        nodes,
        links,
        'DIVIDE',
        accumulated_spec_alpha_socket,
        safe_weight_socket,
        (280, -400),
        'Terrain Weighted Spec',
    )

    return TerrainBlendSockets(
        color=mixed_color_socket,
        normal=mixed_normal_socket,
        spec_alpha=mixed_spec_alpha_socket,
    )


__all__ = [
    "build_layer_stack",
    "build_mask_nodes",
    "create_layer_activity_socket",
    "create_layer_weight_socket",
    "create_math_node",
    "create_mix_node",
    "create_texture_node",
    "create_vector_math_node",
]