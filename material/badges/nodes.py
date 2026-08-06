from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

import bpy

from .affine import badge_affine_from_material, badge_viewport_affine, image_dimensions
from .assets import data_path, resolve_texture_image
from .defs import BADGE_NODE_LABELS, BADGE_SLOTS, badge_control
from ..creator import get_material_creator
from ..shaders.node_passes import BaseColorNodePasses


def _node_tree(material: Optional[bpy.types.Material]):
    if material is None or not material.use_nodes:
        return None
    return getattr(material, 'node_tree', None)


def _find_principled_node(material: bpy.types.Material):
    node_tree = _node_tree(material)
    if node_tree is None:
        return None
    for node in node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            return node
    return None


def _find_texture_node(material: bpy.types.Material, texture_key: str):
    node_tree = _node_tree(material)
    if node_tree is None:
        return None

    key_lower = texture_key.lower()
    preferred_name = f'dow2_{texture_key}'.lower()
    for node in node_tree.nodes:
        if node.type != 'TEX_IMAGE':
            continue
        node_name = str(getattr(node, 'name', '') or '').strip().lower()
        node_label = str(getattr(node, 'label', '') or '').strip().lower()
        if node_name in {preferred_name, key_lower} or node_label == key_lower:
            return node

    texture_value = str(material.get(f'dow2_{texture_key}', '') or '').strip().replace('\\', '/').lower()
    texture_stem = texture_value.rsplit('.', 1)[0] if '.' in texture_value else texture_value
    if texture_stem:
        for node in node_tree.nodes:
            if node.type != 'TEX_IMAGE':
                continue
            image = getattr(node, 'image', None)
            image_path = str(getattr(image, 'filepath', '') or '').replace('\\', '/').lower()
            image_name = str(getattr(image, 'name', '') or '').lower()
            if texture_stem and (texture_stem in image_path or texture_stem.endswith(image_name.rsplit('.', 1)[0])):
                return node
    return None


def _socket_input(node: bpy.types.Node, socket_name: str):
    try:
        return node.inputs[socket_name]
    except Exception:
        return None


def _socket_output(node: bpy.types.Node, socket_name: str):
    try:
        return node.outputs[socket_name]
    except Exception:
        return None


def _linked_from_socket(input_socket):
    if input_socket is None or not getattr(input_socket, 'links', None):
        return None
    return input_socket.links[0].from_socket


def _linked_badge_base_source(principled: bpy.types.Node):
    base_input = _socket_input(principled, 'Base Color')
    current_source = _linked_from_socket(base_input)
    labels = []
    while current_source is not None:
        current_node = getattr(current_source, 'node', None)
        current_label = str(getattr(current_node, 'label', '') or '')
        if current_label not in {'Badge 1 Layer', 'Badge 2 Layer'}:
            break
        labels.append(current_label)
        current_source = _linked_from_socket(_socket_input(current_node, 'A'))
    return current_source, labels


def _resolve_badge_uv_map_name(context, material: bpy.types.Material, texture_key: str) -> str:
    current_data_path = data_path(context)
    shader_name = str(material.get('dow2_shader', '') or '').strip()
    if current_data_path and shader_name:
        try:
            creator = get_material_creator(current_data_path)
            uv_map_name = str(creator.get_texture_uv_map(shader_name, texture_key) or '').strip()
            if uv_map_name:
                return uv_map_name
        except Exception:
            pass
    return 'UVMap'


def _ensure_badge_texture_node(context, material: bpy.types.Material, texture_key: str):
    tex_node = _find_texture_node(material, texture_key)
    node_tree = _node_tree(material)
    if node_tree is None:
        return None

    if tex_node is None:
        image = resolve_texture_image(context, material, texture_key)
        if image is None:
            return None

        principled = _find_principled_node(material)
        anchor_x = -600.0
        anchor_y = -500.0 if texture_key.lower() == 'badge1tex' else -820.0
        if principled is not None:
            anchor_x = principled.location.x - 650.0
            anchor_y = principled.location.y - (360.0 if texture_key.lower() == 'badge1tex' else 640.0)

        tex_node = node_tree.nodes.new('ShaderNodeTexImage')
        tex_node.name = f'dow2_{texture_key}'
        tex_node.label = texture_key
        tex_node.location = (anchor_x, anchor_y)
        tex_node.image = image

    if getattr(tex_node, 'image', None) is None:
        image = resolve_texture_image(context, material, texture_key)
        if image is not None:
            tex_node.image = image

    if hasattr(tex_node, 'extension'):
        tex_node.extension = 'CLIP'

    vector_input = _socket_input(tex_node, 'Vector')
    if vector_input is not None and not vector_input.links:
        uv_node = node_tree.nodes.new('ShaderNodeUVMap')
        uv_node.location = (tex_node.location.x - 220.0, tex_node.location.y)
        uv_node.label = f'{texture_key} UV'
        uv_node.uv_map = _resolve_badge_uv_map_name(context, material, texture_key)
        node_tree.links.new(_socket_output(uv_node, 'UV'), vector_input)

    return tex_node


def _badge_transform_labels(badge_slot: str) -> set[str]:
    _slot_name, label_prefix, _texture_key, _matrix_key, _translate_key = badge_control(badge_slot)
    labels = set(BADGE_NODE_LABELS[badge_slot].values())
    labels.add(f'{label_prefix} UV Split')
    labels.add(f'{label_prefix} UV Transform')
    return labels


def _upstream_badge_vector_source(tex_node: bpy.types.Node, badge_slot: str):
    vector_input = _socket_input(tex_node, 'Vector')
    current_source = _linked_from_socket(vector_input)
    if current_source is None:
        return None

    _slot_name, label_prefix, _texture_key, _matrix_key, _translate_key = badge_control(badge_slot)
    if str(getattr(current_source.node, 'label', '') or '') != f'{label_prefix} UV Transform':
        return current_source

    target_label = f'{label_prefix} UV Split'
    visited = set()
    pending = [current_source.node]
    while pending:
        node = pending.pop()
        node_id = id(node)
        if node_id in visited:
            continue
        visited.add(node_id)
        if str(getattr(node, 'label', '') or '') == target_label:
            return _linked_from_socket(_socket_input(node, 'Vector'))
        for input_socket in getattr(node, 'inputs', ()):
            source = _linked_from_socket(input_socket)
            if source is not None and getattr(source, 'node', None) is not None:
                pending.append(source.node)
    return None


def _remove_badge_transform_nodes(material: bpy.types.Material, badge_slot: str) -> None:
    node_tree = _node_tree(material)
    if node_tree is None:
        return
    labels = _badge_transform_labels(badge_slot)
    for node in list(node_tree.nodes):
        if str(getattr(node, 'label', '') or '') in labels:
            node_tree.nodes.remove(node)


def _clear_badge_layer_stack(material: bpy.types.Material):
    node_tree = _node_tree(material)
    principled = _find_principled_node(material)
    if node_tree is None or principled is None:
        return None

    base_source, active_labels = _linked_badge_base_source(principled)
    if not active_labels:
        return _linked_from_socket(_socket_input(principled, 'Base Color'))

    current_source = BaseColorNodePasses.pop_base_color_source(node_tree.links, principled)
    if base_source is None:
        base_source = current_source
    if base_source is None:
        diffuse_node = _find_texture_node(material, 'diffuseTex')
        if diffuse_node is not None:
            base_source = _socket_output(diffuse_node, 'Color')

    for node in list(node_tree.nodes):
        if str(getattr(node, 'label', '') or '') in {'Badge 1 Layer', 'Badge 2 Layer'}:
            node_tree.nodes.remove(node)

    if base_source is not None:
        node_tree.links.new(base_source, _socket_input(principled, 'Base Color'))
    node_tree.update_tag()
    return base_source


def _rebuild_badge_transform_nodes(
    material: bpy.types.Material,
    badge_slot: str,
    tex_node: bpy.types.Node,
    matrix_values: Sequence[float],
    translate_values: Sequence[float],
) -> bool:
    node_tree = _node_tree(material)
    if node_tree is None:
        return False

    vector_source = _upstream_badge_vector_source(tex_node, badge_slot)
    if vector_source is None:
        vector_source = _linked_from_socket(_socket_input(tex_node, 'Vector'))
    if vector_source is None:
        return False

    viewport_matrix, viewport_translate = badge_viewport_affine(
        matrix_values,
        translate_values,
        image_dimensions(getattr(tex_node, 'image', None)),
    )

    _remove_badge_transform_nodes(material, badge_slot)
    BaseColorNodePasses.pop_socket_source(node_tree.links, tex_node, 'Vector')

    _slot_name, label_prefix, _texture_key, _matrix_key, _translate_key = badge_control(badge_slot)
    separate_node = node_tree.nodes.new('ShaderNodeSeparateXYZ')
    separate_node.location = (tex_node.location.x - 860.0, tex_node.location.y)
    separate_node.label = f'{label_prefix} UV Split'
    node_tree.links.new(vector_source, _socket_input(separate_node, 'Vector'))

    mul_x_u = node_tree.nodes.new('ShaderNodeMath')
    mul_x_u.operation = 'MULTIPLY'
    mul_x_u.location = (tex_node.location.x - 640.0, tex_node.location.y + 120.0)
    mul_x_u.label = f'{label_prefix} Matrix U.X'
    mul_x_u.inputs[1].default_value = float(viewport_matrix[0])
    node_tree.links.new(_socket_output(separate_node, 'X'), mul_x_u.inputs[0])

    mul_y_u = node_tree.nodes.new('ShaderNodeMath')
    mul_y_u.operation = 'MULTIPLY'
    mul_y_u.location = (tex_node.location.x - 640.0, tex_node.location.y + 40.0)
    mul_y_u.label = f'{label_prefix} Matrix U.Y'
    mul_y_u.inputs[1].default_value = float(viewport_matrix[1])
    node_tree.links.new(_socket_output(separate_node, 'Y'), mul_y_u.inputs[0])

    add_u = node_tree.nodes.new('ShaderNodeMath')
    add_u.operation = 'ADD'
    add_u.location = (tex_node.location.x - 430.0, tex_node.location.y + 80.0)
    node_tree.links.new(_socket_output(mul_x_u, 'Value'), add_u.inputs[0])
    node_tree.links.new(_socket_output(mul_y_u, 'Value'), add_u.inputs[1])

    translate_u = node_tree.nodes.new('ShaderNodeMath')
    translate_u.operation = 'ADD'
    translate_u.location = (tex_node.location.x - 220.0, tex_node.location.y + 80.0)
    translate_u.label = f'{label_prefix} Translate U'
    translate_u.inputs[1].default_value = float(viewport_translate[0])
    node_tree.links.new(_socket_output(add_u, 'Value'), translate_u.inputs[0])

    mul_x_v = node_tree.nodes.new('ShaderNodeMath')
    mul_x_v.operation = 'MULTIPLY'
    mul_x_v.location = (tex_node.location.x - 640.0, tex_node.location.y - 80.0)
    mul_x_v.label = f'{label_prefix} Matrix V.X'
    mul_x_v.inputs[1].default_value = float(viewport_matrix[2])
    node_tree.links.new(_socket_output(separate_node, 'X'), mul_x_v.inputs[0])

    mul_y_v = node_tree.nodes.new('ShaderNodeMath')
    mul_y_v.operation = 'MULTIPLY'
    mul_y_v.location = (tex_node.location.x - 640.0, tex_node.location.y - 160.0)
    mul_y_v.label = f'{label_prefix} Matrix V.Y'
    mul_y_v.inputs[1].default_value = float(viewport_matrix[3])
    node_tree.links.new(_socket_output(separate_node, 'Y'), mul_y_v.inputs[0])

    add_v = node_tree.nodes.new('ShaderNodeMath')
    add_v.operation = 'ADD'
    add_v.location = (tex_node.location.x - 430.0, tex_node.location.y - 120.0)
    node_tree.links.new(_socket_output(mul_x_v, 'Value'), add_v.inputs[0])
    node_tree.links.new(_socket_output(mul_y_v, 'Value'), add_v.inputs[1])

    translate_v = node_tree.nodes.new('ShaderNodeMath')
    translate_v.operation = 'ADD'
    translate_v.location = (tex_node.location.x - 220.0, tex_node.location.y - 120.0)
    translate_v.label = f'{label_prefix} Translate V'
    translate_v.inputs[1].default_value = float(viewport_translate[1])
    node_tree.links.new(_socket_output(add_v, 'Value'), translate_v.inputs[0])

    combine_node = node_tree.nodes.new('ShaderNodeCombineXYZ')
    combine_node.location = (tex_node.location.x - 20.0, tex_node.location.y - 20.0)
    combine_node.label = f'{label_prefix} UV Transform'
    node_tree.links.new(_socket_output(translate_u, 'Value'), _socket_input(combine_node, 'X'))
    node_tree.links.new(_socket_output(translate_v, 'Value'), _socket_input(combine_node, 'Y'))
    node_tree.links.new(_socket_output(combine_node, 'Vector'), _socket_input(tex_node, 'Vector'))
    return True


def _ensure_badge_layer_stack(material: bpy.types.Material) -> bool:
    node_tree = _node_tree(material)
    principled = _find_principled_node(material)
    if node_tree is None or principled is None:
        return False

    available_layers = []
    for _slot_name, label, texture_key, _matrix_key, _translate_key in BADGE_SLOTS:
        tex_node = _find_texture_node(material, texture_key)
        if tex_node is not None and getattr(tex_node, 'image', None) is not None:
            available_layers.append((f'{label} Layer', tex_node))
    if not available_layers:
        _clear_badge_layer_stack(material)
        return True

    base_source, active_labels = _linked_badge_base_source(principled)
    desired_top_down = [label for label, _tex_node in reversed(available_layers)]
    if active_labels == desired_top_down:
        return True

    if active_labels:
        _clear_badge_layer_stack(material)
        base_source = None

    current_source = BaseColorNodePasses.pop_base_color_source(node_tree.links, principled)
    if base_source is None:
        base_source = current_source
    if base_source is None:
        diffuse_node = _find_texture_node(material, 'diffuseTex')
        if diffuse_node is not None:
            base_source = _socket_output(diffuse_node, 'Color')
    if base_source is None:
        return False

    layered_source = base_source
    for label, tex_node in available_layers:
        layered_source = BaseColorNodePasses.apply_badge_decal(
            node_tree.nodes,
            node_tree.links,
            principled,
            layered_source,
            tex_node,
            label,
        )

    node_tree.links.new(layered_source, _socket_input(principled, 'Base Color'))
    node_tree.update_tag()
    return True


def clear_badge_preview(material: bpy.types.Material, badge_slot: str) -> bool:
    node_tree = _node_tree(material)
    if node_tree is None:
        return False

    _slot_name, _label, texture_key, _matrix_key, _translate_key = badge_control(badge_slot)
    tex_node = _find_texture_node(material, texture_key)
    if tex_node is not None:
        tex_node.image = None

    _remove_badge_transform_nodes(material, badge_slot)
    _ensure_badge_layer_stack(material)
    node_tree.update_tag()
    return True


def _badge_node_value_map(badge_slot: str, matrix_values: Sequence[float], translate_values: Sequence[float]) -> Dict[str, float]:
    labels = BADGE_NODE_LABELS[badge_slot]
    return {
        labels['matrix_u_x']: float(matrix_values[0]),
        labels['matrix_u_y']: float(matrix_values[1]),
        labels['translate_u']: float(translate_values[0]),
        labels['matrix_v_x']: float(matrix_values[2]),
        labels['matrix_v_y']: float(matrix_values[3]),
        labels['translate_v']: float(translate_values[1]),
    }


def sync_badge_transform_nodes(
    material: bpy.types.Material,
    badge_slot: str,
    matrix_values: Sequence[float],
    translate_values: Sequence[float],
) -> bool:
    if material is None or not material.use_nodes or material.node_tree is None:
        return False

    _slot_name, _label, texture_key, _matrix_key, _translate_key = badge_control(badge_slot)
    tex_node = _find_texture_node(material, texture_key)
    viewport_matrix, viewport_translate = badge_viewport_affine(
        matrix_values,
        translate_values,
        image_dimensions(getattr(tex_node, 'image', None) if tex_node is not None else None),
    )

    expected = _badge_node_value_map(badge_slot, viewport_matrix, viewport_translate)
    matched = 0
    for node in material.node_tree.nodes:
        value = expected.get(str(getattr(node, 'label', '') or ''))
        if value is None:
            continue
        if len(getattr(node, 'inputs', ())) < 2:
            continue
        node.inputs[1].default_value = value
        matched += 1

    if matched:
        material.node_tree.update_tag()
    return matched == len(expected)


def ensure_badge_preview_nodes(context, material: bpy.types.Material, badge_slot: str) -> Tuple[bool, str]:
    matrix_values, translate_values, _affine_model = badge_affine_from_material(material, badge_slot)
    _slot_name, _label, texture_key, _matrix_key, _translate_key = badge_control(badge_slot)

    if sync_badge_transform_nodes(material, badge_slot, matrix_values, translate_values):
        _ensure_badge_layer_stack(material)
        return True, ''

    tex_node = _ensure_badge_texture_node(context, material, texture_key)
    if tex_node is None:
        return False, 'Badge texture preview could not be prepared for this material'

    if not _rebuild_badge_transform_nodes(material, badge_slot, tex_node, matrix_values, translate_values):
        return False, 'Badge transform preview could not be prepared for this material'

    _ensure_badge_layer_stack(material)
    if sync_badge_transform_nodes(material, badge_slot, matrix_values, translate_values):
        return True, ''
    return False, 'Badge transform preview could not be prepared for this material'


__all__ = [
    "clear_badge_preview",
    "ensure_badge_preview_nodes",
    "sync_badge_transform_nodes",
]