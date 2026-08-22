from __future__ import annotations

from typing import Sequence

import bpy
from bpy.app.handlers import persistent
from mathutils import Matrix, Vector

from ...utils import link_object_to_collection
from .constants import (
    RAGDOLL_BODY_HALF_EXTENTS_PROP,
    RAGDOLL_BODY_HEIGHT_PROP,
    RAGDOLL_BODY_JOINT_ORIGIN_PROP,
    RAGDOLL_BODY_LENGTH_PROP,
    RAGDOLL_BODY_PROP,
    RAGDOLL_BODY_RADIUS_PROP,
    RAGDOLL_BODY_SHAPE_PROP,
    RAGDOLL_BODY_VERTEX_A_PROP,
    RAGDOLL_BODY_VERTEX_B_PROP,
    RAGDOLL_CAPSULE_HANDLE_BODY_PROP,
    RAGDOLL_CAPSULE_HANDLE_ENDPOINT_PROP,
    RAGDOLL_CAPSULE_HANDLE_PROP,
)
from .body_authoring import update_body_mesh
from .geometry import _capsule_segment_vertices
from .props import _identity_scale, _rounded_float, _rounded_vector, _scale_components, _vector_prop
from .preview import (
    clear_constraint_preview_objects,
    register_constraint_preview_draw_handler,
    remove_legacy_constraint_preview_objects,
    sync_constraint_preview_objects,
    unregister_constraint_preview_draw_handler,
)
from .queries import is_ragdoll_body_object


_BODY_SYNC_STATE: dict[int, dict[str, object]] = {}
_BODY_SYNC_IN_PROGRESS = False
_BODY_SYNC_SUSPENDED = 0
_BODY_SYNC_TIMER_INTERVAL = 0.05


class suspend_body_sync:
    """Context manager that disables the live capsule body-sync.

    The importer places bodies at their authoritative Havok joint origins with
    asymmetric capsule vertices. Creating those meshes/handles triggers depsgraph
    updates that would otherwise fire the sync mid-import and recenter the bodies
    before their joint-origin flag is set. Suspending the sync for the duration of
    the import keeps the imported transforms intact.
    """

    def __enter__(self) -> "suspend_body_sync":
        global _BODY_SYNC_SUSPENDED
        _BODY_SYNC_SUSPENDED += 1
        return self

    def __exit__(self, *_exc) -> bool:
        global _BODY_SYNC_SUSPENDED
        if _BODY_SYNC_SUSPENDED > 0:
            _BODY_SYNC_SUSPENDED -= 1
        return False


def _capsule_handle_name(body_object: bpy.types.Object, endpoint: str) -> str:
    return f"{body_object.name}::{endpoint.lower()}"


def _capsule_handle_objects(body_object: bpy.types.Object) -> tuple[bpy.types.Object | None, bpy.types.Object | None]:
    handle_a = None
    handle_b = None
    for child in body_object.children:
        if not child.get(RAGDOLL_CAPSULE_HANDLE_PROP, False):
            continue
        if str(child.get(RAGDOLL_CAPSULE_HANDLE_BODY_PROP, "") or "") != body_object.name:
            continue
        endpoint = str(child.get(RAGDOLL_CAPSULE_HANDLE_ENDPOINT_PROP, "") or "").upper()
        if endpoint == "A":
            handle_a = child
        elif endpoint == "B":
            handle_b = child
    return handle_a, handle_b


def _capsule_handle_local_positions(body_object: bpy.types.Object) -> tuple[list[float] | None, list[float] | None]:
    handle_a, handle_b = _capsule_handle_objects(body_object)
    if handle_a is None or handle_b is None:
        return None, None
    return (
        [float(handle_a.location.x), float(handle_a.location.y), float(handle_a.location.z)],
        [float(handle_b.location.x), float(handle_b.location.y), float(handle_b.location.z)],
    )


def _sync_capsule_handles(
    body_object: bpy.types.Object,
    radius: float,
    vertex_a: Sequence[float],
    vertex_b: Sequence[float],
) -> None:
    body_collection = body_object.users_collection[0] if body_object.users_collection else None
    for endpoint, position in (("A", vertex_a), ("B", vertex_b)):
        handle_name = _capsule_handle_name(body_object, endpoint)
        handle_object = bpy.data.objects.get(handle_name)
        if handle_object is None or handle_object.type != "EMPTY":
            handle_object = bpy.data.objects.new(handle_name, None)
            if body_collection is not None:
                link_object_to_collection(handle_object, body_collection)
        elif body_collection is not None:
            link_object_to_collection(handle_object, body_collection)

        if handle_object.parent != body_object:
            handle_object.parent = body_object
            handle_object.matrix_parent_inverse = Matrix.Identity(4)

        handle_object.empty_display_type = "SPHERE"
        handle_object.empty_display_size = max(float(radius) * 0.35, 0.025)
        handle_object.show_in_front = True
        handle_object.hide_render = True
        handle_object.lock_rotation = (True, True, True)
        handle_object.lock_scale = (True, True, True)
        handle_object[RAGDOLL_CAPSULE_HANDLE_PROP] = True
        handle_object[RAGDOLL_CAPSULE_HANDLE_BODY_PROP] = body_object.name
        handle_object[RAGDOLL_CAPSULE_HANDLE_ENDPOINT_PROP] = endpoint
        handle_object.location = Vector(position[:3])


def _remove_capsule_handles(body_object: bpy.types.Object) -> None:
    handle_a, handle_b = _capsule_handle_objects(body_object)
    for handle_object in (handle_a, handle_b):
        if handle_object is not None:
            bpy.data.objects.remove(handle_object, do_unlink=True)


def _observed_body_state(body_object: bpy.types.Object) -> dict[str, object]:
    location, rotation, _world_scale = body_object.matrix_world.decompose()
    handle_a, handle_b = _capsule_handle_local_positions(body_object)
    return {
        "shape": str(body_object.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE") or "CAPSULE").upper(),
        "radius": _rounded_float(body_object.get(RAGDOLL_BODY_RADIUS_PROP, 0.1)),
        "height": _rounded_float(body_object.get(RAGDOLL_BODY_HEIGHT_PROP, 0.2)),
        "length": _rounded_float(body_object.get(RAGDOLL_BODY_LENGTH_PROP, 0.4)),
        "vertex_a": _rounded_vector(_vector_prop(body_object, RAGDOLL_BODY_VERTEX_A_PROP, [0.0, -0.2, 0.0])),
        "vertex_b": _rounded_vector(_vector_prop(body_object, RAGDOLL_BODY_VERTEX_B_PROP, [0.0, 0.2, 0.0])),
        "handle_a": _rounded_vector(handle_a if handle_a is not None else [0.0, -0.2, 0.0]),
        "handle_b": _rounded_vector(handle_b if handle_b is not None else [0.0, 0.2, 0.0]),
        "half_extents": _rounded_vector(_vector_prop(body_object, RAGDOLL_BODY_HALF_EXTENTS_PROP, [0.1, 0.2, 0.1])),
        "location": _rounded_vector((location.x, location.y, location.z)),
        "rotation": _rounded_vector((rotation.x, rotation.y, rotation.z, rotation.w), size=4),
        "scale": _rounded_vector((body_object.scale.x, body_object.scale.y, body_object.scale.z)),
    }


def _sync_capsule_body(
    body_object: bpy.types.Object,
    previous_state: dict[str, object] | None,
    shape_changed: bool,
    force: bool = False,
) -> bool:
    radius = max(float(body_object.get(RAGDOLL_BODY_RADIUS_PROP, 0.1)), 0.001)
    length = max(float(body_object.get(RAGDOLL_BODY_LENGTH_PROP, 0.4)), 0.001)
    scale = [abs(float(body_object.scale.x)), abs(float(body_object.scale.y)), abs(float(body_object.scale.z))]
    scale_changed = not _identity_scale(scale)
    prop_vertex_a = _vector_prop(body_object, RAGDOLL_BODY_VERTEX_A_PROP, [0.0, -max(length * 0.5, 0.001), 0.0])
    prop_vertex_b = _vector_prop(body_object, RAGDOLL_BODY_VERTEX_B_PROP, [0.0, max(length * 0.5, 0.001), 0.0])
    handle_vertex_a, handle_vertex_b = _capsule_handle_local_positions(body_object)
    handles_missing = handle_vertex_a is None or handle_vertex_b is None

    if scale_changed:
        body_object.scale = (1.0, 1.0, 1.0)

    dims_changed = previous_state is not None and (
        _rounded_float(radius) != previous_state["radius"]
        or _rounded_float(length) != previous_state["length"]
        or _rounded_float(radius * 2.0) != previous_state["height"]
    )
    prop_verts_changed = previous_state is not None and (
        _rounded_vector(prop_vertex_a) != previous_state["vertex_a"]
        or _rounded_vector(prop_vertex_b) != previous_state["vertex_b"]
    )
    handle_verts_changed = previous_state is not None and not handles_missing and (
        _rounded_vector(handle_vertex_a) != previous_state["handle_a"]
        or _rounded_vector(handle_vertex_b) != previous_state["handle_b"]
    )

    if handle_verts_changed:
        vertex_a = handle_vertex_a
        vertex_b = handle_vertex_b
        length = max((Vector(vertex_b) - Vector(vertex_a)).length, 0.001)
    elif prop_verts_changed:
        vertex_a = prop_vertex_a
        vertex_b = prop_vertex_b
        length = max((Vector(vertex_b) - Vector(vertex_a)).length, 0.001)
    else:
        base_vertex_a = handle_vertex_a if handle_vertex_a is not None else prop_vertex_a
        base_vertex_b = handle_vertex_b if handle_vertex_b is not None else prop_vertex_b
        if dims_changed:
            # The user changed the radius/length dimensions, so re-derive the
            # capsule segment endpoints from the new length about the existing
            # centre/axis.
            center = (Vector(base_vertex_a) + Vector(base_vertex_b)) * 0.5
            axis = Vector(base_vertex_b) - Vector(base_vertex_a)
            if axis.length < 0.001:
                axis = Vector((0.0, 1.0, 0.0))
            else:
                axis.normalize()
            segment_vertex_a, segment_vertex_b = _capsule_segment_vertices(length, radius)
            vertex_a = list(center + (axis * float(segment_vertex_a[1])))
            vertex_b = list(center + (axis * float(segment_vertex_b[1])))
        else:
            # Nothing about the capsule actually changed (e.g. a forced refresh
            # or an unrelated depsgraph tick). Preserve the authoritative stored
            # endpoints verbatim — recomputing them through
            # _capsule_segment_vertices insets each end by the radius and, on
            # imported bodies, silently shrinks the exported Havok capsule.
            vertex_a = list(base_vertex_a)
            vertex_b = list(base_vertex_b)
            length = max((Vector(vertex_b) - Vector(vertex_a)).length, 0.001)

    midpoint = (Vector(vertex_a) + Vector(vertex_b)) * 0.5
    joint_anchored = bool(body_object.get(RAGDOLL_BODY_JOINT_ORIGIN_PROP, False))
    if midpoint.length > 0.000001 and not joint_anchored:
        body_object.matrix_world.translation = body_object.matrix_world.translation + (body_object.matrix_world.to_quaternion() @ midpoint)
        vertex_a = list(Vector(vertex_a) - midpoint)
        vertex_b = list(Vector(vertex_b) - midpoint)

    if not (force or scale_changed or shape_changed or dims_changed or prop_verts_changed or handle_verts_changed or handles_missing):
        return False

    update_body_mesh(
        body_object,
        "CAPSULE",
        radius,
        radius * 2.0,
        length,
        vertex_a=vertex_a,
        vertex_b=vertex_b,
    )
    body_object[RAGDOLL_BODY_VERTEX_A_PROP] = vertex_a
    body_object[RAGDOLL_BODY_VERTEX_B_PROP] = vertex_b
    body_object[RAGDOLL_BODY_HALF_EXTENTS_PROP] = [radius, length * 0.5, radius]
    return True


def _sync_box_body(
    body_object: bpy.types.Object,
    previous_state: dict[str, object] | None,
    shape_changed: bool,
    force: bool = False,
) -> bool:
    radius = max(float(body_object.get(RAGDOLL_BODY_RADIUS_PROP, 0.1)), 0.001)
    height = max(float(body_object.get(RAGDOLL_BODY_HEIGHT_PROP, 0.2)), 0.001)
    length = max(float(body_object.get(RAGDOLL_BODY_LENGTH_PROP, 0.4)), 0.001)
    half_extents = _vector_prop(body_object, RAGDOLL_BODY_HALF_EXTENTS_PROP, [radius, length * 0.5, height * 0.5])
    scale = [abs(float(body_object.scale.x)), abs(float(body_object.scale.y)), abs(float(body_object.scale.z))]
    scale_changed = not _identity_scale(scale)

    if scale_changed:
        half_extents = _scale_components(half_extents, scale)
        radius = max(abs(half_extents[0]), 0.001)
        length = max(abs(half_extents[1]) * 2.0, 0.001)
        height = max(abs(half_extents[2]) * 2.0, 0.001)
        body_object.scale = (1.0, 1.0, 1.0)

    dims_changed = previous_state is not None and (
        _rounded_float(radius) != previous_state["radius"]
        or _rounded_float(height) != previous_state["height"]
        or _rounded_float(length) != previous_state["length"]
    )
    half_extents_changed = previous_state is not None and _rounded_vector(half_extents) != previous_state["half_extents"]

    if previous_state is None and not (force or scale_changed):
        return False
    if force or scale_changed or shape_changed or dims_changed:
        half_extents = [radius, length * 0.5, height * 0.5]
    elif half_extents_changed:
        radius = max(abs(float(half_extents[0])), 0.001)
        length = max(abs(float(half_extents[1])) * 2.0, 0.001)
        height = max(abs(float(half_extents[2])) * 2.0, 0.001)
    else:
        return False

    update_body_mesh(body_object, "BOX", radius, height, length, half_extents=half_extents)
    body_object[RAGDOLL_BODY_HALF_EXTENTS_PROP] = [radius, length * 0.5, height * 0.5]
    return True


def _sync_sphere_body(
    body_object: bpy.types.Object,
    previous_state: dict[str, object] | None,
    shape_changed: bool,
    force: bool = False,
) -> bool:
    radius = max(float(body_object.get(RAGDOLL_BODY_RADIUS_PROP, 0.1)), 0.001)
    scale = [abs(float(body_object.scale.x)), abs(float(body_object.scale.y)), abs(float(body_object.scale.z))]
    scale_changed = not _identity_scale(scale)

    if scale_changed:
        radius = max(radius * max(scale), 0.001)
        body_object.scale = (1.0, 1.0, 1.0)

    dims_changed = previous_state is not None and (
        _rounded_float(radius) != previous_state["radius"]
        or _rounded_float(radius * 2.0) != previous_state["height"]
        or _rounded_float(radius * 2.0) != previous_state["length"]
    )

    if previous_state is None and not (force or scale_changed):
        return False
    if not (force or scale_changed or shape_changed or dims_changed):
        return False

    update_body_mesh(body_object, "SPHERE", radius, radius * 2.0, radius * 2.0)
    body_object[RAGDOLL_BODY_HALF_EXTENTS_PROP] = [radius, radius, radius]
    return True


def _sync_ragdoll_body_object(
    body_object: bpy.types.Object,
    previous_state: dict[str, object] | None,
    force: bool = False,
) -> bool:
    current_state = _observed_body_state(body_object)
    if not force and previous_state == current_state:
        return False

    shape_changed = previous_state is not None and current_state["shape"] != previous_state["shape"]
    shape = str(current_state["shape"])
    if shape == "BOX":
        return _sync_box_body(body_object, previous_state, shape_changed, force=force)
    if shape == "SPHERE":
        return _sync_sphere_body(body_object, previous_state, shape_changed, force=force)
    return _sync_capsule_body(body_object, previous_state, shape_changed, force=force)


def sync_ragdoll_body_object(body_object: bpy.types.Object, force: bool = False) -> bool:
    global _BODY_SYNC_IN_PROGRESS

    if _BODY_SYNC_IN_PROGRESS or _BODY_SYNC_SUSPENDED or not is_ragdoll_body_object(body_object):
        return False

    _BODY_SYNC_IN_PROGRESS = True
    try:
        object_key = body_object.as_pointer()
        previous_state = _BODY_SYNC_STATE.get(object_key)
        did_sync = _sync_ragdoll_body_object(body_object, previous_state, force=force)
        _BODY_SYNC_STATE[object_key] = _observed_body_state(body_object)
        sync_constraint_preview_objects()
        return did_sync
    finally:
        _BODY_SYNC_IN_PROGRESS = False


def sync_ragdoll_body_objects(force: bool = False) -> int:
    global _BODY_SYNC_IN_PROGRESS

    if _BODY_SYNC_IN_PROGRESS or _BODY_SYNC_SUSPENDED:
        return 0

    objects = getattr(bpy.data, "objects", None)
    if objects is None:
        return 0

    _BODY_SYNC_IN_PROGRESS = True
    try:
        synced_count = 0
        live_keys: set[int] = set()
        for body_object in objects:
            if not is_ragdoll_body_object(body_object):
                continue
            object_key = body_object.as_pointer()
            live_keys.add(object_key)
            previous_state = _BODY_SYNC_STATE.get(object_key)
            if _sync_ragdoll_body_object(body_object, previous_state, force=force):
                synced_count += 1
            _BODY_SYNC_STATE[object_key] = _observed_body_state(body_object)

        stale_keys = [object_key for object_key in _BODY_SYNC_STATE if object_key not in live_keys]
        for object_key in stale_keys:
            del _BODY_SYNC_STATE[object_key]
        sync_constraint_preview_objects()
        return synced_count
    finally:
        _BODY_SYNC_IN_PROGRESS = False


@persistent
def _ragdoll_body_sync_handler(_scene=None, _depsgraph=None) -> None:
    sync_ragdoll_body_objects()


def _ragdoll_body_sync_timer() -> float | None:
    sync_ragdoll_body_objects()
    return _BODY_SYNC_TIMER_INTERVAL


def register_body_sync_handlers() -> None:
    handlers = bpy.app.handlers.depsgraph_update_post
    if _ragdoll_body_sync_handler not in handlers:
        handlers.append(_ragdoll_body_sync_handler)
    if not bpy.app.timers.is_registered(_ragdoll_body_sync_timer):
        bpy.app.timers.register(_ragdoll_body_sync_timer, first_interval=_BODY_SYNC_TIMER_INTERVAL)
    remove_legacy_constraint_preview_objects()
    register_constraint_preview_draw_handler()
    sync_ragdoll_body_objects(force=True)


def unregister_body_sync_handlers() -> None:
    handlers = bpy.app.handlers.depsgraph_update_post
    if _ragdoll_body_sync_handler in handlers:
        handlers.remove(_ragdoll_body_sync_handler)
    if bpy.app.timers.is_registered(_ragdoll_body_sync_timer):
        bpy.app.timers.unregister(_ragdoll_body_sync_timer)
    clear_constraint_preview_objects()
    unregister_constraint_preview_draw_handler()
    _BODY_SYNC_STATE.clear()