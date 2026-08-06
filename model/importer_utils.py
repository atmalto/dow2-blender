from typing import List

from mathutils import Vector


def bytes_to_weights(values: List[int]) -> List[float]:
    """Convert packed byte weights to floats (matching MaxScript BytesToWeights)."""

    weights = [0.0, 0.0, 0.0, 0.0]
    weights[0] = round(values[2] / 255.0 * 1000 - 0.5) / 1000 if values[2] > 0 else 0.0
    weights[1] = round(values[1] / 255.0 * 1000 - 0.5) / 1000 if values[1] > 0 else 0.0
    weights[2] = round(values[0] / 255.0 * 1000 - 0.5) / 1000 if values[0] > 0 else 0.0
    weights[3] = round(values[3] / 255.0 * 1000 - 0.5) / 1000 if values[3] > 0 else 0.0

    total = sum(weights)
    if total > 0:
        weights[0] -= total - 1.0
    else:
        weights[0] = 1.0

    return weights


def dx_to_blender_position(position: Vector) -> Vector:
    """Convert DirectX position to Blender coordinates."""

    return Vector((-position.x, -position.z, position.y))


def dx_to_blender_normal(normal: Vector) -> Vector:
    """Convert DirectX normal to Blender coordinates."""

    return Vector((-normal.z, -normal.x, normal.y))