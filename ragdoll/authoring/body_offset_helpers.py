from __future__ import annotations

from mathutils import Vector

from .props import _normalized_vector_values


def normalized_shape_offset(value: object) -> list[float]:
    return list(_normalized_vector_values(value, [0.0, 0.0, 0.0]))


def shape_offset_vector(value: object) -> Vector:
    return Vector(normalized_shape_offset(value))


def has_shape_offset(value: object, tolerance: float = 1.0e-6) -> bool:
    offset = normalized_shape_offset(value)
    return any(abs(float(component)) > tolerance for component in offset)