from __future__ import annotations

from typing import Sequence

import bpy


def _rounded_float(value: float) -> float:
    return round(float(value), 6)


def _rounded_vector(values: Sequence[float], size: int = 3) -> tuple[float, ...]:
    return tuple(_rounded_float(values[index]) for index in range(size))


def _vector_prop(owner: bpy.types.ID, prop_name: str, default: Sequence[float]) -> list[float]:
    values = owner.get(prop_name, default)
    try:
        value_count = len(values)
    except TypeError:
        values = default
        value_count = len(default)
    if value_count < len(default):
        values = default
    return [float(values[index]) for index in range(len(default))]


def _normalized_vector_values(values: Sequence[float] | None, default: Sequence[float]) -> list[float]:
    if values is None:
        return [float(default[index]) for index in range(len(default))]
    try:
        value_count = len(values)
    except TypeError:
        value_count = 0
    if value_count < len(default):
        return [float(default[index]) for index in range(len(default))]
    return [float(values[index]) for index in range(len(default))]


def _identity_scale(scale: Sequence[float], tolerance: float = 1e-4) -> bool:
    return all(abs(float(component) - 1.0) <= tolerance for component in scale)


def _scale_components(values: Sequence[float], scale: Sequence[float]) -> list[float]:
    return [float(values[index]) * abs(float(scale[index])) for index in range(len(values))]