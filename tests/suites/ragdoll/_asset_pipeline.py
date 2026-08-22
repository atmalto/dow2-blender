"""Shared helpers for the real-asset ragdoll scope tests.

This module is intentionally not a ``test_*`` module: test discovery imports it
(so the imports must stay clean at module load) but collects no callables from
it. It centralises the one thing every ragdoll scope test needs -- driving the
FULL production path for a single real ``ragdoll.hkx``:

    ragdoll.hkx --RagdollImporter.import_scene--> Blender scene
                --force body sync (mimics viewport interaction)-->
                --export_ragdoll_hkx--> out.hkx

so the roundtrip and behaviour suites stay identical on that shared leg and only
differ in how they *judge* the exported file.
"""

from __future__ import annotations

from pathlib import Path

# Ragdolls ship as ``.../troops/<unit>/animations/<clip>/ragdoll.hkx`` and their
# source skeleton is the unit ``.model`` a couple of levels up (see
# ``framework.assets.find_ragdolls``).


def import_sync_export(ragdoll_hkx: Path, model_path: Path, out_hkx: Path, ragdoll_name: str):
    """Import ``ragdoll_hkx`` (+ its ``model_path`` skeleton), force the live
    body sync, and export to ``out_hkx`` via the real addon export path.

    Returns the resolved source armature object. Raises ``RuntimeError`` if the
    source armature cannot be resolved after import.
    """
    import bpy  # type: ignore

    from framework import blender_env

    from dow2_tools.ragdoll.scene_importer import RagdollImporter  # type: ignore
    from dow2_tools.ragdoll.authoring.body_sync import sync_ragdoll_body_objects  # type: ignore
    from dow2_tools.ragdoll.authoring.queries import find_source_armature  # type: ignore
    from dow2_tools.ragdoll.authoring.constants import RAGDOLL_SOURCE_ARMATURE_PROP  # type: ignore
    from dow2_tools.ragdoll.exporter import export_ragdoll_hkx  # type: ignore

    # Full clean-slate between assets: removing only bpy.data.objects leaves
    # armature/mesh datablocks and addon session state behind, which corrupts
    # the next ragdoll import (bodies fail to get created). Reset the whole file.
    blender_env.reset_scene()

    skeleton = RagdollImporter().import_scene(
        bpy.context, str(ragdoll_hkx), model_path=str(model_path), ragdoll_name=ragdoll_name,
    )

    # Mimic a viewport interaction / timer tick: force the live body sync to run
    # before export. This is exactly the path the old synthetic tests skipped.
    sync_ragdoll_body_objects(force=True)

    source_armature = find_source_armature(bpy.context)
    if source_armature is None:
        source_name = str(skeleton.get(RAGDOLL_SOURCE_ARMATURE_PROP, "") or "")
        source_armature = bpy.data.objects.get(source_name)
    if source_armature is None:
        raise RuntimeError("could not resolve the ragdoll source armature after import")

    export_ragdoll_hkx(source_armature, str(out_hkx), auto_generate_missing_bodies=False)
    return source_armature


def rel_label(data_root: Path, path: Path) -> str:
    """A short, deterministic label for a ragdoll asset (unit/clip)."""
    try:
        rel = path.relative_to(data_root)
    except ValueError:
        return path.name
    # ``.../troops/<unit>/animations/<clip>/ragdoll.hkx`` -> ``<unit>/<clip>``
    parts = rel.parts
    if len(parts) >= 4 and parts[-1].lower() == "ragdoll.hkx":
        return f"{parts[-4]}/{parts[-2]}"
    return str(rel).replace("\\", "/")
