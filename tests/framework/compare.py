"""Comparison helpers for round-trip assertions (scaffold ; stubs).

Filled in as suites are implemented. Intended helpers:
  - mesh topology (verts/edges/faces/loops) equality
  - transform equality within tolerance (matrices / quaternions)
  - bone hierarchy + rest-matrix equality
  - material param equality (TEXTURE_SLOTS + BOOL/INT/FLOAT params)
  - animation keyframe equality within tolerance
"""

from __future__ import annotations

DEFAULT_TOLERANCE = 1e-4


def approx_equal(a: float, b: float, tol: float = DEFAULT_TOLERANCE) -> bool:
    return abs(a - b) <= tol


# TODO: implement structural comparators, e.g.
#   def assert_mesh_equal(ctx, obj_a, obj_b): ...
#   def assert_transform_equal(ctx, m_a, m_b, tol=DEFAULT_TOLERANCE): ...
#   def assert_material_params_equal(ctx, mat_a, mat_b): ...
#   def assert_keyframes_equal(ctx, action_a, action_b, tol): ...
