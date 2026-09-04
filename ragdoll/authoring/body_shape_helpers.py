from __future__ import annotations

from .constants import RAGDOLL_MIN_BODY_DIMENSION
from .geometry import _capsule_segment_vertices_from_origin


_BODY_SHAPE_LABELS = {
    "CAPSULE": "Capsule",
    "SPHERE": "Sphere",
    "BOX": "Box",
}


def normalize_body_shape(shape: str | None) -> str:
    value = str(shape or "CAPSULE").strip().upper()
    if value in _BODY_SHAPE_LABELS:
        return value
    return "CAPSULE"


def body_shape_label(shape: str | None) -> str:
    return _BODY_SHAPE_LABELS.get(normalize_body_shape(shape), "Capsule")


def clamp_body_dimension(value: float, fallback: float | None = None) -> float:
    candidate = fallback if value is None and fallback is not None else value
    return max(float(candidate), RAGDOLL_MIN_BODY_DIMENSION)


def resolved_creation_dimensions(shape: str | None, radius: float, height: float, length: float) -> tuple[float, float, float]:
    normalized_shape = normalize_body_shape(shape)
    resolved_radius = clamp_body_dimension(radius, 0.1)
    if normalized_shape == "SPHERE":
        diameter = resolved_radius * 2.0
        return resolved_radius, diameter, diameter
    if normalized_shape == "BOX":
        return (
            resolved_radius,
            clamp_body_dimension(height, resolved_radius * 2.0),
            clamp_body_dimension(length, resolved_radius * 2.0),
        )
    return (
        resolved_radius,
        resolved_radius * 2.0,
        clamp_body_dimension(length, resolved_radius * 2.0),
    )


def box_half_extents(radius: float, height: float, length: float) -> list[float]:
    resolved_radius, resolved_height, resolved_length = resolved_creation_dimensions("BOX", radius, height, length)
    return [resolved_radius, resolved_length * 0.5, resolved_height * 0.5]


def sphere_half_extents(radius: float) -> list[float]:
    resolved_radius, _resolved_height, _resolved_length = resolved_creation_dimensions("SPHERE", radius, radius * 2.0, radius * 2.0)
    return [resolved_radius, resolved_radius, resolved_radius]


def build_shape_switch_payload(shape: str | None, radius: float, height: float, length: float) -> dict[str, object]:
    normalized_shape = normalize_body_shape(shape)
    resolved_radius, resolved_height, resolved_length = resolved_creation_dimensions(normalized_shape, radius, height, length)
    payload: dict[str, object] = {
        "shape_type": normalized_shape.lower(),
        "radius": resolved_radius,
    }
    if normalized_shape == "SPHERE":
        payload["half_extents"] = sphere_half_extents(resolved_radius)
        payload["vertex_a"] = [0.0, 0.0, 0.0]
        payload["vertex_b"] = [0.0, 0.0, 0.0]
        return payload
    if normalized_shape == "BOX":
        payload["half_extents"] = box_half_extents(resolved_radius, resolved_height, resolved_length)
        payload["vertex_a"] = [0.0, 0.0, 0.0]
        payload["vertex_b"] = [0.0, 0.0, 0.0]
        return payload
    vertex_a, vertex_b = _capsule_segment_vertices_from_origin(resolved_length, resolved_radius)
    payload["half_extents"] = [resolved_radius, resolved_length * 0.5, resolved_radius]
    payload["vertex_a"] = vertex_a
    payload["vertex_b"] = vertex_b
    return payload
