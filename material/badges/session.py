from __future__ import annotations

from typing import Optional, Tuple

import bpy

from .affine import (
    badge_affine_from_display_overlay,
    badge_affine_from_material,
    coerce_sequence,
    image_dimensions,
    merge_sequence,
    overlay_state_from_badge_display,
)
from .defs import badge_control
from .nodes import sync_badge_transform_nodes


def capture_badge_session(material: bpy.types.Material, badge_slot: str, base_image=None) -> Tuple[Optional[dict], str]:
    _slot_name, _label, texture_key, matrix_key, translate_key = badge_control(badge_slot)
    matrix_values, translate_values, _affine_model = badge_affine_from_material(material, badge_slot)
    current_image_size = image_dimensions(base_image)
    overlay_state = overlay_state_from_badge_display(matrix_values, translate_values, current_image_size)
    if overlay_state is None:
        overlay_state = ((0.5, 0.5), (1.0, 1.0), 0.0)

    original_matrix = coerce_sequence(material.get(f'dow2_{matrix_key}')) or list(matrix_values)
    original_translate = coerce_sequence(material.get(f'dow2_{translate_key}')) or list(translate_values)
    original_center, original_size, original_rotation = overlay_state
    return {
        'material_name': material.name,
        'badge_slot': badge_slot,
        'texture_key': texture_key,
        'matrix_key': matrix_key,
        'translate_key': translate_key,
        'original_matrix': original_matrix,
        'original_translate': original_translate,
        'image_size': current_image_size,
        'original_center': original_center,
        'original_size': original_size,
        'original_rotation': original_rotation,
    }, ''


def apply_badge_session_transform(
    session: dict,
    *,
    current_center: Tuple[float, float],
    current_size: Tuple[float, float],
    rotation: float,
) -> None:
    material = bpy.data.materials.get(str(session.get('material_name', '')))
    if material is None:
        return

    current_image_size = tuple(session.get('image_size', (1.0, 1.0)))
    matrix_values, translate_values = badge_affine_from_display_overlay(current_center, current_size, rotation, current_image_size)
    original_matrix = coerce_sequence(session.get('original_matrix')) or [1.0, 0.0, 0.0, 1.0]
    original_translate = coerce_sequence(session.get('original_translate')) or [0.0, 0.0, 0.0, 0.0]

    material[f"dow2_{session['matrix_key']}"] = merge_sequence(matrix_values, original_matrix, 4)
    material[f"dow2_{session['translate_key']}"] = merge_sequence(translate_values, original_translate, max(len(original_translate), 4))
    sync_badge_transform_nodes(material, str(session['badge_slot']), matrix_values, translate_values)


def restore_badge_session(session: dict) -> None:
    material = bpy.data.materials.get(str(session.get('material_name', '')))
    if material is None:
        return

    original_matrix = coerce_sequence(session.get('original_matrix')) or [1.0, 0.0, 0.0, 1.0]
    original_translate = coerce_sequence(session.get('original_translate')) or [0.0, 0.0, 0.0, 0.0]
    material[f"dow2_{session['matrix_key']}"] = list(original_matrix)
    material[f"dow2_{session['translate_key']}"] = list(original_translate)
    sync_badge_transform_nodes(material, str(session['badge_slot']), original_matrix[:4], original_translate[:2])


__all__ = [
    "apply_badge_session_transform",
    "capture_badge_session",
    "restore_badge_session",
]