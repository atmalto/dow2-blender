from __future__ import annotations

import os

import bpy

from ..creator import get_material_creator


def addon_preferences(context):
    addon = context.preferences.addons.get('dow2_tools') if context is not None else None
    return getattr(addon, 'preferences', None) if addon is not None else None


def data_path(context) -> str:
    prefs = addon_preferences(context)
    if prefs is None:
        return ""
    dow2_path = str(getattr(prefs, 'dow2_path', '') or '').strip()
    if not dow2_path:
        return ""
    return os.path.join(dow2_path, 'Codex', 'Data')


def _node_tree(material: bpy.types.Material):
    if material is None or not material.use_nodes:
        return None
    return getattr(material, 'node_tree', None)


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


def resolve_texture_image(context, material: bpy.types.Material, texture_key: str):
    if material is None:
        return None

    tex_node = _find_texture_node(material, texture_key)
    if tex_node is not None and getattr(tex_node, 'image', None) is not None:
        return tex_node.image

    texture_value = str(material.get(f'dow2_{texture_key}', '') or '').strip()
    if not texture_value:
        return None

    current_data_path = data_path(context)
    if current_data_path:
        creator = get_material_creator(current_data_path)
        file_path = creator.find_texture_file(texture_value)
        if file_path:
            try:
                return bpy.data.images.load(file_path, check_existing=True)
            except Exception:
                return None

    candidates = []
    normalized = texture_value.replace('/', os.sep).replace('\\', os.sep)
    if os.path.isabs(normalized):
        candidates.append(normalized)
    elif current_data_path:
        candidates.append(os.path.join(current_data_path, normalized))

    for candidate in list(candidates):
        root, ext = os.path.splitext(candidate)
        if ext:
            continue
        candidates.extend([f'{candidate}.dds', f'{candidate}.png', f'{candidate}.tga'])

    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        try:
            return bpy.data.images.load(candidate, check_existing=True)
        except Exception:
            continue
    return None


__all__ = [
    "addon_preferences",
    "data_path",
    "resolve_texture_image",
]