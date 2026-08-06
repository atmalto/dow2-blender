from __future__ import annotations

import math
from typing import Optional, Sequence, Tuple

import bpy

from .defs import badge_control


def coerce_sequence(value) -> list[float]:
    if value is None:
        return []
    if isinstance(value, (str, bytes, bytearray)):
        return []
    if isinstance(value, (list, tuple)):
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return []
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return []


def badge_affine_from_material(material: bpy.types.Material, badge_slot: str) -> Tuple[list[float], list[float], dict]:
    _slot_name, _label, _texture_key, matrix_key, translate_key = badge_control(badge_slot)

    matrix_values = coerce_sequence(material.get(f'dow2_{matrix_key}'))
    if len(matrix_values) < 4:
        matrix_values = [1.0, 0.0, 0.0, 1.0]
    else:
        matrix_values = matrix_values[:4]

    translate_values = coerce_sequence(material.get(f'dow2_{translate_key}'))
    if len(translate_values) < 2:
        translate_values = [0.0, 0.0]
    else:
        translate_values = translate_values[:2]

    affine_model = {
        'u_coeffs': [matrix_values[0], matrix_values[1], translate_values[0]],
        'v_coeffs': [matrix_values[2], matrix_values[3], translate_values[1]],
    }
    return matrix_values, translate_values, affine_model


def image_dimensions(image) -> Tuple[float, float]:
    if image is None:
        return 1.0, 1.0
    size = getattr(image, 'size', None)
    if not size or len(size) < 2:
        return 1.0, 1.0
    width = max(float(size[0]), 1.0)
    height = max(float(size[1]), 1.0)
    return width, height


def display_pixels_to_uv(point: Tuple[float, float], image_size: Tuple[float, float]) -> Tuple[float, float]:
    width = max(float(image_size[0]), 1.0)
    height = max(float(image_size[1]), 1.0)
    return (float(point[0]) / width, 1.0 - (float(point[1]) / height))


def uv_to_display_pixels(point: Tuple[float, float], image_size: Tuple[float, float]) -> Tuple[float, float]:
    width = max(float(image_size[0]), 1.0)
    height = max(float(image_size[1]), 1.0)
    return (float(point[0]) * width, (1.0 - float(point[1])) * height)


def invert_qmatrix(matrix_values: Sequence[float], translate_values: Sequence[float]) -> Optional[Tuple[list[float], list[float]]]:
    m11 = float(matrix_values[0])
    m12 = float(matrix_values[1])
    m21 = float(matrix_values[2])
    m22 = float(matrix_values[3])
    dx = float(translate_values[0])
    dy = float(translate_values[1])
    determinant = (m11 * m22) - (m12 * m21)
    if abs(determinant) <= 1e-12:
        return None
    inv_matrix = [
        m22 / determinant,
        -m12 / determinant,
        -m21 / determinant,
        m11 / determinant,
    ]
    inv_translate = [
        ((m21 * dy) - (m22 * dx)) / determinant,
        ((m12 * dx) - (m11 * dy)) / determinant,
    ]
    return inv_matrix, inv_translate


def overlay_state_from_badge_display(
    matrix_values: Sequence[float],
    translate_values: Sequence[float],
    image_size: Tuple[float, float],
) -> Optional[Tuple[Tuple[float, float], Tuple[float, float], float]]:
    width = max(float(image_size[0]), 1.0)
    height = max(float(image_size[1]), 1.0)
    badge_side = max(min(width, height), 1.0)
    aspect = height / width

    inverse = invert_qmatrix(matrix_values, translate_values)
    if inverse is None:
        return None
    inv_matrix, inv_translate = inverse

    display_m11 = float(inv_matrix[0])
    display_m12 = -float(inv_matrix[2])
    display_m21 = -float(inv_matrix[1]) * aspect
    display_m22 = float(inv_matrix[3]) * aspect
    display_dx = float(inv_translate[0]) * width
    display_dy = float(inv_translate[1]) * height

    def transform_point(x_value: float, y_value: float) -> Tuple[float, float]:
        x_out = (display_m11 * x_value) + (display_m21 * y_value) + display_dx
        y_out = (display_m12 * x_value) + (display_m22 * y_value) + display_dy
        return display_pixels_to_uv((x_out, y_out), image_size)

    origin = transform_point(0.0, 0.0)
    x_axis_end = transform_point(badge_side, 0.0)
    y_axis_end = transform_point(0.0, badge_side)

    x_axis = (x_axis_end[0] - origin[0], x_axis_end[1] - origin[1])
    y_axis = (y_axis_end[0] - origin[0], y_axis_end[1] - origin[1])
    center = (
        origin[0] + (x_axis[0] * 0.5) + (y_axis[0] * 0.5),
        origin[1] + (x_axis[1] * 0.5) + (y_axis[1] * 0.5),
    )
    size = (
        max(math.sqrt((x_axis[0] * x_axis[0]) + (x_axis[1] * x_axis[1])), 1e-4),
        max(math.sqrt((y_axis[0] * y_axis[0]) + (y_axis[1] * y_axis[1])), 1e-4),
    )
    rotation = math.atan2(x_axis[1], x_axis[0])
    return center, size, rotation


def badge_affine_from_display_overlay(
    center: Tuple[float, float],
    size: Tuple[float, float],
    rotation: float,
    image_size: Tuple[float, float],
) -> Tuple[list[float], list[float]]:
    width = max(float(image_size[0]), 1.0)
    height = max(float(image_size[1]), 1.0)
    badge_side = max(min(width, height), 1.0)
    aspect = height / width if width else 1.0

    x_axis = (math.cos(rotation) * float(size[0]), math.sin(rotation) * float(size[0]))
    y_axis = (math.sin(rotation) * float(size[1]), -math.cos(rotation) * float(size[1]))
    origin = (
        float(center[0]) - (x_axis[0] * 0.5) - (y_axis[0] * 0.5),
        float(center[1]) - (x_axis[1] * 0.5) - (y_axis[1] * 0.5),
    )

    origin_px = uv_to_display_pixels(origin, image_size)
    x_axis_end_px = uv_to_display_pixels((origin[0] + x_axis[0], origin[1] + x_axis[1]), image_size)
    y_axis_end_px = uv_to_display_pixels((origin[0] + y_axis[0], origin[1] + y_axis[1]), image_size)

    display_m11 = (x_axis_end_px[0] - origin_px[0]) / badge_side
    display_m12 = (x_axis_end_px[1] - origin_px[1]) / badge_side
    display_m21 = (y_axis_end_px[0] - origin_px[0]) / badge_side
    display_m22 = (y_axis_end_px[1] - origin_px[1]) / badge_side
    display_dx = origin_px[0]
    display_dy = origin_px[1]

    qt_matrix = [
        display_m11,
        -display_m21 / aspect if abs(aspect) > 1e-12 else 0.0,
        -display_m12,
        display_m22 / aspect if abs(aspect) > 1e-12 else 0.0,
    ]
    qt_translate = [display_dx / width, display_dy / height]

    inverse = invert_qmatrix(qt_matrix, qt_translate)
    if inverse is None:
        return [1.0, 0.0, 0.0, 1.0], [0.0, 0.0]
    return inverse


def badge_viewport_affine(
    matrix_values: Sequence[float],
    translate_values: Sequence[float],
    image_size: Tuple[float, float],
) -> Tuple[list[float], list[float]]:
    overlay_state = overlay_state_from_badge_display(matrix_values, translate_values, image_size)
    if overlay_state is None:
        return [1.0, 0.0, 0.0, 1.0], [0.0, 0.0]

    center, size, rotation = overlay_state
    x_axis = (math.cos(rotation) * float(size[0]), math.sin(rotation) * float(size[0]))
    y_axis = (math.sin(rotation) * float(size[1]), -math.cos(rotation) * float(size[1]))
    origin = (
        float(center[0]) - (x_axis[0] * 0.5) - (y_axis[0] * 0.5),
        float(center[1]) - (x_axis[1] * 0.5) - (y_axis[1] * 0.5),
    )

    determinant = (x_axis[0] * y_axis[1]) - (x_axis[1] * y_axis[0])
    if abs(determinant) <= 1e-12:
        return [1.0, 0.0, 0.0, 1.0], [0.0, 0.0]

    viewport_matrix = [
        y_axis[1] / determinant,
        -y_axis[0] / determinant,
        x_axis[1] / determinant,
        -x_axis[0] / determinant,
    ]
    viewport_translate = [
        -((viewport_matrix[0] * origin[0]) + (viewport_matrix[1] * origin[1])),
        1.0 - ((viewport_matrix[2] * origin[0]) + (viewport_matrix[3] * origin[1])),
    ]
    return viewport_matrix, viewport_translate


def merge_sequence(prefix_values: Sequence[float], original_values: Sequence[float], minimum_size: int) -> list[float]:
    merged = list(float(value) for value in prefix_values)
    original_tail = list(float(value) for value in original_values[len(prefix_values):]) if len(original_values) > len(prefix_values) else []
    if original_tail:
        merged.extend(original_tail)
    while len(merged) < minimum_size:
        merged.append(0.0)
    return merged


__all__ = [
    "badge_affine_from_display_overlay",
    "badge_affine_from_material",
    "badge_viewport_affine",
    "coerce_sequence",
    "display_pixels_to_uv",
    "image_dimensions",
    "invert_qmatrix",
    "merge_sequence",
    "overlay_state_from_badge_display",
    "uv_to_display_pixels",
]