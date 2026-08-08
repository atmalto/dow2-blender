"""Phase-A test-data generator (runs inside Blender).

Imports the seed ``.model`` assets with the addon, inspects their LOD / health-
state binning and materials, then saves a portable, deterministic copy under
``tests/test_data/<name>/``:

    model.glb        geometry + rig (via glTF exporter, custom props included)
    config.json      DoW2 material params + texture map + LOD/health binning
    textures/...     local copies of the referenced textures

Phase B round-trip tests consume this data (rebuild materials + bins from the
config, temp-stage textures into DATA_ROOT/art, export to .model, re-import).

Invoke via:  python tests/run.py --build-test-data
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import Config

# Seed models (relative to DATA_ROOT). Each entry points at the folder that
# contains the .model file.
SEED_MODEL_DIRS = [
    "art/race_marine/troops_wargear/armour/power_armour_common",
    "art/race_chaos/structures/chaos_heavy_bolter_turret",
]


@dataclass
class _Built:
    name: str
    ok: bool
    detail: str = ""


def _find_model_file(model_dir: Path) -> Path | None:
    if not model_dir.is_dir():
        return None
    # Prefer a .model named like the folder; else the first one found.
    named = model_dir / f"{model_dir.name}.model"
    if named.is_file():
        return named
    candidates = sorted(model_dir.glob("*.model"))
    return candidates[0] if candidates else None


def _reset_blender() -> None:
    import bpy  # type: ignore

    bpy.ops.wm.read_homefile(use_empty=True)


def _collect_bins() -> dict:
    """Collect meshes grouped by damage-state collection -> LOD sub-collection.

    Reimplemented inline (not imported from the addon) because the addon's
    ``utils`` name is ambiguous ; a top-level ``utils.py`` shadows the ``utils/``
    package, so ``dow2_tools.utils.scene_graph`` is not importable. Mirrors the
    collection-name conventions in utils/scene_graph.py.
    """
    import bpy  # type: ignore

    damage_states = ["healthy", "light_damage", "heavy_damage", "wreck"]
    bins: dict[str, dict[str, list[str]]] = {}

    for state_col in bpy.context.scene.collection.children:
        state_name = state_col.name.split(".")[0]
        if state_name not in damage_states:
            continue

        lods: dict[str, list[str]] = {}
        for child in state_col.children:
            if not child.name.lower().startswith("lod"):
                continue
            meshes = [o.name for o in child.objects if o.type == "MESH"]
            if meshes:
                lods[child.name.split(".")[0]] = meshes

        direct = [o.name for o in state_col.objects if o.type == "MESH"]
        if direct:
            lods.setdefault("lod0", []).extend(direct)

        if lods:
            bins[state_name] = lods

    return bins


def _prune_non_bin_meshes(bins: dict) -> int:
    """Delete mesh objects that aren't part of the damage-state/LOD bins.

    The DoW2 importer also creates helper meshes (e.g. bounding-volume
    icospheres) that live outside the ``healthy/lodN`` collections. Those would
    otherwise be baked into the ``.glb`` and picked up by the exporter during
    Phase B, polluting the round-trip. The armature and marker empties are kept.
    """
    import bpy  # type: ignore

    keep = {n for lods in bins.values() for names in lods.values() for n in names}
    removed = 0
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and obj.name not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed


def _collect_mesh_stats(bins: dict) -> tuple[dict, dict]:
    """Tag each mesh with a stable id and snapshot per-mesh ground truth.

    Every mesh object is tagged with a ``dow2_test_id`` custom property
    (``"<state>:<lod>:<n>"``). Because Phase A exports the ``.glb`` with
    ``export_extras=True``, that tag survives the glTF round-trip even though
    glTF flattens collections and can re-mangle the truncated/deduped object
    names. Phase B therefore matches objects by tag, not by name.

    Returns ``(mesh_materials, baseline)`` where both are keyed by
    ``dow2_test_id``:
      * ``mesh_materials`` -> single material slot name (or None).
      * ``baseline`` -> {name, vertices, polygons, triangles, material, state,
        lod}, plus a ``__totals__`` entry with scene-wide counts. This is the
        ground truth Phase B compares its re-export against.
    """
    import bpy  # type: ignore

    mesh_materials: dict[str, str | None] = {}
    baseline: dict[str, dict] = {}
    total_verts = total_polys = total_tris = 0

    for state, lods in bins.items():
        for lod, mesh_names in lods.items():
            for index, obj_name in enumerate(mesh_names):
                obj = bpy.data.objects.get(obj_name)
                if obj is None or obj.type != "MESH":
                    continue
                test_id = f"{state}:{lod}:{index}"
                obj["dow2_test_id"] = test_id
                mesh = obj.data
                mat_name = mesh.materials[0].name if mesh.materials and mesh.materials[0] else None
                verts = len(mesh.vertices)
                polys = len(mesh.polygons)
                tris = sum(max(len(p.vertices) - 2, 0) for p in mesh.polygons)
                mesh_materials[test_id] = mat_name
                baseline[test_id] = {
                    "name": obj_name,
                    "vertices": verts,
                    "polygons": polys,
                    "triangles": tris,
                    "material": mat_name,
                    "state": state,
                    "lod": lod,
                }
                total_verts += verts
                total_polys += polys
                total_tris += tris

    baseline["__totals__"] = {
        "meshes": len(baseline),
        "vertices": total_verts,
        "polygons": total_polys,
        "triangles": total_tris,
    }
    return mesh_materials, baseline


def _names(seq) -> set:
    """Normalize a definitions list into a set of identifier names.

    Handles lists of ``name`` strings, ``(name, label)`` tuples, or dicts keyed
    by name.
    """
    out = set()
    try:
        iterator = seq.keys() if hasattr(seq, "keys") else seq
        for item in iterator:
            if isinstance(item, (tuple, list)):
                out.add(item[0])
            else:
                out.add(item)
    except TypeError:
        pass
    return out


def _collect_materials() -> dict:
    import bpy  # type: ignore

    try:
        from dow2_tools.material.definitions import (  # type: ignore
            BOOL_PARAMS,
            FLOAT_PARAMS,
            INT_PARAMS,
            TEXTURE_SLOTS,
        )
        texture_slots = _names(TEXTURE_SLOTS)
        bool_params, int_params, float_params = _names(BOOL_PARAMS), _names(INT_PARAMS), _names(FLOAT_PARAMS)
    except Exception:
        texture_slots = bool_params = int_params = float_params = set()

    materials: dict[str, dict] = {}
    for mat in bpy.data.materials:
        dow2_keys = [k for k in mat.keys() if k.startswith("dow2_")]
        if not dow2_keys:
            continue
        entry: dict = {
            "shader": mat.get("dow2_shader", ""),
            "shader_path": mat.get("dow2_shader_path", ""),
            "is_relic": bool(mat.get("dow2_is_relic_material", False))
            or mat.name.startswith("relic.material."),
            "textures": {},
            "bool_params": {},
            "int_params": {},
            "float_params": {},
            "other": {},
        }
        for key in dow2_keys:
            short = key[len("dow2_"):]
            value = mat[key]
            if short in texture_slots:
                entry["textures"][short] = str(value)
            elif short in bool_params:
                entry["bool_params"][short] = bool(value)
            elif short in int_params:
                entry["int_params"][short] = int(value)
            elif short in float_params:
                entry["float_params"][short] = float(value)
            elif short not in ("shader", "shader_path", "is_relic_material"):
                entry["other"][short] = _jsonify(value)
        materials[mat.name] = entry
    return materials


def _jsonify(value):
    if hasattr(value, "to_list"):
        return value.to_list()
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    try:
        json.dumps(value)
        return value
    except TypeError:
        try:
            return list(value)
        except TypeError:
            return str(value)


def _copy_textures(out_dir: Path, data_root: Path) -> dict:
    """Copy referenced images locally; return {data_root-relative: local-relative}."""
    import bpy  # type: ignore

    tex_dir = out_dir / "textures"
    mapping: dict[str, str] = {}
    for image in bpy.data.images:
        if not image.filepath:
            continue
        abs_path = Path(bpy.path.abspath(image.filepath))
        if not abs_path.is_file():
            continue
        try:
            rel = abs_path.relative_to(data_root)
        except ValueError:
            rel = Path(abs_path.name)
        local = tex_dir / rel
        local.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(abs_path, local)
        mapping[rel.as_posix()] = (Path("textures") / rel).as_posix()
    return mapping


def _export_glb(glb_path: Path) -> None:
    import bpy  # type: ignore

    glb_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=False,
        export_extras=True,
        export_apply=False,
    )


def _build_one(config: Config, seed_rel: str) -> _Built:
    import bpy  # type: ignore

    data_root = config.data_root
    model_dir = data_root / seed_rel
    name = model_dir.name
    model_file = _find_model_file(model_dir)
    if model_file is None:
        return _Built(name, False, f"no .model found in {model_dir}")

    out_dir = config.test_data_dir / name
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    _reset_blender()
    result = bpy.ops.import_scene.dow2_model(
        filepath=str(model_file),
        import_meshes=True,
        import_materials=True,
        import_bones=True,
        import_markers=True,
        group_meshes=True,
    )
    if "FINISHED" not in result:
        return _Built(name, False, f"import returned {result}")

    bins = _collect_bins()
    _prune_non_bin_meshes(bins)
    mesh_materials, baseline = _collect_mesh_stats(bins)
    materials = _collect_materials()
    textures = _copy_textures(out_dir, data_root)
    _export_glb(out_dir / "model.glb")

    config_payload = {
        "name": name,
        "source_model": model_file.relative_to(data_root).as_posix(),
        "glb": "model.glb",
        "bins": bins,
        "mesh_materials": mesh_materials,
        "materials": materials,
        "textures": textures,
        "baseline": baseline,
    }
    (out_dir / "config.json").write_text(json.dumps(config_payload, indent=2), encoding="utf-8")

    mesh_count = sum(len(objs) for lods in bins.values() for objs in lods.values())
    return _Built(
        name,
        True,
        f"bins={list(bins)} meshes={mesh_count} materials={len(materials)} "
        f"textures={len(textures)} verts={baseline['__totals__']['vertices']}",
    )


def build_seed_test_data(config: Config) -> int:
    if not config.data_root_available:
        print(f"ERROR: DATA_ROOT unavailable: {config.data_root}")
        return 2

    print(f"[build-test-data] writing to {config.test_data_dir}\n")
    results = [_build_one(config, seed) for seed in SEED_MODEL_DIRS]

    print("\n[build-test-data] results:")
    failed = 0
    for r in results:
        status = "ok  " if r.ok else "FAIL"
        print(f"  {status} {r.name}: {r.detail}")
        failed += 0 if r.ok else 1

    return 1 if failed else 0
