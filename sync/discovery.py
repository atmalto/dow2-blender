"""Scene discovery helpers for the sync bridge.

Thin wrappers over the existing physics/ragdoll authoring modules so the sync
service never re-derives what "authored" means. Import of these submodules is
deferred to call time so the transport layer (protocol/client) stays bpy-free.
"""

from __future__ import annotations

from typing import List


def physics_system_names(scene) -> List[str]:
    """Names of the non-empty physics systems (damage states) authored in the scene.

    Reuses ``physics.exporter.build_physics_systems`` so the definition of an
    exportable system is identical to a normal physics export.
    """
    from ..physics import exporter as physics_exporter

    systems = physics_exporter.build_physics_systems(scene)
    return [system.name for system in systems]


def has_authored_physics(scene) -> bool:
    """True when at least one non-empty physics system exists in the scene."""
    return bool(physics_system_names(scene))


def ragdoll_source_armature(context):
    """The source armature a ragdoll export would use, or ``None``.

    Reuses ``ragdoll.authoring.find_source_armature`` so "which ragdoll" matches
    exactly what the normal ragdoll exporter would pick (selected armature, or the
    single non-ragdoll armature in the scene).
    """
    from ..ragdoll.authoring import find_source_armature

    return find_source_armature(context)


def has_authored_ragdoll(context) -> bool:
    """True when the scene has a source armature that a ragdoll export could use."""
    try:
        return ragdoll_source_armature(context) is not None
    except Exception:  # noqa: BLE001 - discovery must never raise into poll/draw
        return False


def selected_physics_body_names(context) -> List[str]:
    """Havok body names of the currently-selected physics hull objects.

    Used by the "selected only" sync path so the simulator updates just those
    bodies. Reuses ``physics.utils`` helpers so the body name matches the export.
    """
    from ..physics import utils as physics_utils

    scene = getattr(context, "scene", None)
    if scene is None:
        return []

    selected = {obj for obj in getattr(context, "selected_objects", []) or []}
    names: List[str] = []
    hulls_by_state = physics_utils.collect_physics_hulls(scene)
    for state_name, lod_map in hulls_by_state.items():
        for hull_objects in lod_map.values():
            for hull_obj in hull_objects:
                if hull_obj in selected:
                    names.append(physics_utils.get_hull_body_name(hull_obj))
    return names


