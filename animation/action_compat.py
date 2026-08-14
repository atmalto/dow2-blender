from __future__ import annotations

from typing import Iterable

import bpy


def _iter_layered_action_fcurve_collections(action: bpy.types.Action) -> Iterable:
    seen_handles: set[int] = set()
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            channelbags = getattr(strip, "channelbags", None)
            if channelbags is None:
                continue
            for channelbag in channelbags:
                fcurves = getattr(channelbag, "fcurves", None)
                if fcurves is None:
                    continue
                handle = int(channelbag.as_pointer())
                if handle in seen_handles:
                    continue
                seen_handles.add(handle)
                yield fcurves


def iter_action_fcurve_collections(action: bpy.types.Action | None) -> Iterable:
    if action is None:
        return ()

    direct_fcurves = getattr(action, "fcurves", None)
    if direct_fcurves is not None:
        return (direct_fcurves,)

    return _iter_layered_action_fcurve_collections(action)


def iter_action_fcurves(action: bpy.types.Action | None) -> Iterable[bpy.types.FCurve]:
    for collection in iter_action_fcurve_collections(action):
        for fcurve in collection:
            yield fcurve


def count_action_fcurves(action: bpy.types.Action | None) -> int:
    return sum(len(collection) for collection in iter_action_fcurve_collections(action))


def action_has_fcurves(action: bpy.types.Action | None) -> bool:
    return any(len(collection) > 0 for collection in iter_action_fcurve_collections(action))


def remove_action_fcurve(action: bpy.types.Action | None, fcurve: bpy.types.FCurve) -> bool:
    target_pointer = int(fcurve.as_pointer())
    for collection in iter_action_fcurve_collections(action):
        for current in collection:
            if int(current.as_pointer()) == target_pointer:
                collection.remove(current)
                return True
    return False


def ensure_action_fcurve(
    action: bpy.types.Action,
    datablock,
    data_path: str,
    index: int = 0,
    group_name: str = "",
) -> bpy.types.FCurve:
    direct_fcurves = getattr(action, "fcurves", None)
    if direct_fcurves is not None:
        existing = direct_fcurves.find(data_path, index=index)
        if existing is not None:
            return existing
        return direct_fcurves.new(data_path=data_path, index=index, action_group=group_name or None)

    if datablock is None:
        raise ValueError("datablock is required to create FCurves for layered actions")

    return action.fcurve_ensure_for_datablock(datablock, data_path, index=index, group_name=group_name or "")


__all__ = [
    "action_has_fcurves",
    "count_action_fcurves",
    "ensure_action_fcurve",
    "iter_action_fcurve_collections",
    "iter_action_fcurves",
    "remove_action_fcurve",
]