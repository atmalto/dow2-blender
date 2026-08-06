from __future__ import annotations

import bpy

from .constants import RAGDOLL_BODIES_COLLECTION_NAME, RAGDOLL_SKELETON_PREFIX


def ragdoll_collection_name(name: str) -> str:
    cleaned = (name or "ragdoll").strip() or "ragdoll"
    return f"{RAGDOLL_SKELETON_PREFIX}{cleaned}"


def ensure_child_collection(parent: bpy.types.Collection, name: str) -> bpy.types.Collection:
    existing = parent.children.get(name)
    if existing is not None:
        return existing
    collection = bpy.data.collections.new(name)
    parent.children.link(collection)
    return collection


def remove_collection_tree(collection: bpy.types.Collection) -> None:
    for child in list(collection.children):
        remove_collection_tree(child)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for parent in bpy.data.collections:
        existing = parent.children.get(collection.name)
        if existing is not None:
            parent.children.unlink(existing)
    for scene in bpy.data.scenes:
        existing = scene.collection.children.get(collection.name)
        if existing is not None:
            scene.collection.children.unlink(existing)
    if collection.users == 0:
        bpy.data.collections.remove(collection)


def ensure_ragdoll_bodies_collection(skeleton_object: bpy.types.Object) -> bpy.types.Collection:
    if not skeleton_object.users_collection:
        raise RuntimeError("Ragdoll skeleton is not linked to a collection")
    return ensure_child_collection(skeleton_object.users_collection[0], RAGDOLL_BODIES_COLLECTION_NAME)