"""Blender-side helpers for tests (only usable inside a running Blender).

Thin, defensive wrappers; kept separate so pure-logic unit tests can import the
rest of the framework without requiring ``bpy``.
"""

from __future__ import annotations

ADDON_MODULE = "dow2_tools"


def ensure_addon_enabled() -> None:
    """Enable the DoW2 Tools addon if it is not already active."""
    import addon_utils  # type: ignore

    is_enabled, _ = addon_utils.check(ADDON_MODULE)
    if not is_enabled:
        addon_utils.enable(ADDON_MODULE, default_set=True, persistent=True)


def reset_scene() -> None:
    """Return Blender to a clean, empty state between tests."""
    import bpy  # type: ignore

    bpy.ops.wm.read_homefile(use_empty=True)


DAMAGE_STATES = ("healthy", "light_damage", "heavy_damage", "wreck")


def import_glb(glb_path) -> None:
    """Import a ``.glb`` (geometry + rig + object custom-prop extras)."""
    import bpy  # type: ignore

    bpy.ops.import_scene.gltf(filepath=str(glb_path))


def rebuild_material(name: str, entry: dict):
    """Create/refresh a DoW2 material from a ``config.json`` material entry.

    The exporter reads material data purely from ``dow2_*`` custom properties
    (not the node graph), so rebuilding only needs to set those props.
    """
    import bpy  # type: ignore

    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    for key in [k for k in mat.keys() if k.startswith("dow2_")]:
        del mat[key]

    mat["dow2_shader"] = entry.get("shader", "dow2_unit")
    if entry.get("shader_path"):
        mat["dow2_shader_path"] = entry["shader_path"]
    if entry.get("is_relic"):
        mat["dow2_is_relic_material"] = True
    for slot, path in entry.get("textures", {}).items():
        mat[f"dow2_{slot}"] = path
    for key, value in entry.get("bool_params", {}).items():
        mat[f"dow2_{key}"] = bool(value)
    for key, value in entry.get("int_params", {}).items():
        mat[f"dow2_{key}"] = int(value)
    for key, value in entry.get("float_params", {}).items():
        mat[f"dow2_{key}"] = float(value)
    for key, value in entry.get("other", {}).items():
        mat[f"dow2_{key}"] = value
    return mat


def apply_config_to_scene(config: dict) -> int:
    """Reconstruct DoW2 export state on the glb-imported scene.

    For each mesh object, uses its ``dow2_test_id`` tag (falling back to name)
    to look up the baseline entry, tags it with ``dow2_group``/``dow2_lod`` (so
    the exporter groups it correctly without relying on collections, which glTF
    flattens), rebuilds its material from the config, and attaches it.

    Returns the number of mesh objects configured.
    """
    import bpy  # type: ignore

    baseline = config.get("baseline", {})
    mesh_materials = config.get("mesh_materials", {})
    materials = config.get("materials", {})

    name_to_id = {
        b["name"]: tid
        for tid, b in baseline.items()
        if tid != "__totals__" and isinstance(b, dict) and "name" in b
    }

    configured = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        test_id = obj.get("dow2_test_id") or name_to_id.get(obj.name)
        if test_id is None or test_id not in baseline:
            continue
        entry = baseline[test_id]
        obj["dow2_group"] = entry["state"]
        obj["dow2_lod"] = int(str(entry["lod"]).replace("lod", "") or 0)

        mat_name = mesh_materials.get(test_id) or entry.get("material")
        if mat_name and mat_name in materials:
            mat = rebuild_material(mat_name, materials[mat_name])
            obj.data.materials.clear()
            obj.data.materials.append(mat)
        configured += 1

    # Safety net: drop any mesh not part of the tracked model (e.g. a stray
    # bounding-volume helper), so the exporter doesn't bake it into the .model.
    for obj in list(bpy.data.objects):
        if obj.type != "MESH":
            continue
        if obj.get("dow2_test_id") is None and obj.name not in name_to_id:
            bpy.data.objects.remove(obj, do_unlink=True)

    return configured


def export_model(filepath, **option_overrides):
    """Export the current scene to a DoW2 ``.model`` via the exporter class."""
    from dow2_tools.model.exporter import DoW2ModelExporter  # type: ignore
    from dow2_tools.model.export_utils import ExportOptions  # type: ignore

    opts = ExportOptions(
        apply_bone_limit=False,
        combine_same_material_meshes=False,
        export_simbox=False,
        export_coverbox=False,
    )
    for key, value in option_overrides.items():
        setattr(opts, key, value)
    return DoW2ModelExporter(str(filepath), opts).export_model()


def import_model(filepath, **options):
    """Import a DoW2 ``.model`` via the registered operator."""
    import bpy  # type: ignore

    kwargs = dict(
        filepath=str(filepath),
        import_meshes=True,
        import_materials=True,
        import_bones=True,
        import_markers=True,
        group_meshes=True,
    )
    kwargs.update(options)
    return bpy.ops.import_scene.dow2_model(**kwargs)


def _group_lod_of(obj) -> tuple[str, str]:
    """Resolve (state, lod) for a mesh object via props or collection nesting."""
    import bpy  # type: ignore

    if "dow2_group" in obj:
        lod = f"lod{int(obj['dow2_lod'])}" if "dow2_lod" in obj else "lod0"
        return str(obj["dow2_group"]), lod

    for col in obj.users_collection:
        if col.name.lower().startswith("lod"):
            lod = f"lod{col.name[3:].split('.')[0]}"
            for parent in bpy.data.collections:
                if col.name in [c.name for c in parent.children]:
                    return parent.name.split(".")[0], lod
            return "healthy", lod
    for col in obj.users_collection:
        base = col.name.split(".")[0]
        if base in DAMAGE_STATES:
            return base, "lod0"
    return "healthy", "lod0"
