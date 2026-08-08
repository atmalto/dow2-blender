"""Model import tests (plan IDs M-I1..M-I13).

Golden import checks + import content toggles, driven from the two ``test_data``
seeds' original ``.model`` files under ``DATA_ROOT`` and validated with the
``model_snapshot`` capture. The remaining scene-option combinations stay as stubs.
"""

from __future__ import annotations

CATEGORY = "model/import"

_TODO = "scaffold ; not implemented yet"

_SEEDS = ("power_armour_common", "chaos_heavy_bolter_turret")


def _available_seeds(ctx):
    from framework import model_roundtrip

    return [
        (s, cfg)
        for s in _SEEDS
        if (cfg := model_roundtrip.load_seed_config(ctx.config.test_data_dir, s)) is not None
    ]


def _mesh_objects():
    import bpy  # type: ignore

    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def _bvol_objects():
    return [obj for obj in _mesh_objects() if obj.name.startswith("BVOL_")]


def _mesh_vertex_count():
    return sum(len(obj.data.vertices) for obj in _mesh_objects() if not obj.name.startswith("BVOL_"))


def _expected_group_triangles(baseline: dict) -> dict:
    agg: dict = {}
    for tid, entry in baseline.items():
        if tid == "__totals__" or not isinstance(entry, dict):
            continue
        key = f"{entry['state']}|{entry['lod']}|{entry['material']}"
        agg[key] = agg.get(key, 0) + entry["triangles"]
    return agg


def test_import_content_toggles(ctx):
    """M-I1..M-I5: meshes/materials/bones/markers/BVOL on/off toggle presence."""
    from framework import blender_env, model_snapshot

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")

    # Use a seed with markers so the markers toggle is meaningful.
    seed, cfg = next(((s, c) for s, c in seeds if s == "chaos_heavy_bolter_turret"), seeds[0])
    model_path = ctx.data_path(cfg["source_model"])
    problems: list[str] = []

    def _snap(**opts):
        blender_env.reset_scene()
        result = blender_env.import_model(model_path, **opts)
        if "FINISHED" not in result:
            problems.append(f"{seed}: import {opts} -> {result}")
            return None
        return model_snapshot.capture()

    full = _snap()
    if full is not None:
        if not full["meshes"]:
            problems.append(f"{seed}: expected meshes on full import")
        if not full["bones"]:
            problems.append(f"{seed}: expected bones on full import")
        if not full["materials"]:
            problems.append(f"{seed}: expected materials on full import")

    no_meshes = _snap(import_meshes=False)
    if no_meshes is not None and no_meshes["meshes"]:
        problems.append(f"{seed}: import_meshes=False still produced meshes")

    no_bones = _snap(import_bones=False)
    if no_bones is not None and no_bones["bones"]:
        problems.append(f"{seed}: import_bones=False still produced bones")

    no_mats = _snap(import_materials=False)
    if no_mats is not None and no_mats["materials"]:
        problems.append(f"{seed}: import_materials=False still produced materials")

    no_markers = _snap(import_markers=False)
    if full is not None and full["markers"] and no_markers is not None and no_markers["markers"]:
        problems.append(f"{seed}: import_markers=False still produced markers")

    blender_env.reset_scene()
    result = blender_env.import_model(model_path, import_bounding_volumes=True)
    if "FINISHED" not in result:
        problems.append(f"{seed}: import_bounding_volumes=True -> {result}")
    elif not _bvol_objects():
        problems.append(f"{seed}: import_bounding_volumes=True produced no BVOL_ objects")

    if problems:
        ctx.fail(" | ".join(problems))


def test_import_sidecar_toggles(ctx):
    """M-I6: import_simbox / import_coverbox sidecars on/off toggle presence."""
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    from dow2_tools.model import utils as model_utils  # type: ignore
    from framework import blender_env, fixtures

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")
    seed, cfg = seeds[0]
    seed_dir = ctx.config.test_data_dir / seed

    with fixtures.scratch_dir(ctx.config, f"import_sidecars_{seed}") as scratch:
        with fixtures.staged_textures(ctx.config, cfg.get("textures", {}), seed_dir):
            blender_env.reset_scene()
            blender_env.import_glb(seed_dir / cfg["glb"])
            if blender_env.apply_config_to_scene(cfg) == 0:
                ctx.fail(f"{seed}: no meshes configured from glb")

            armature = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
            model_utils.create_or_update_bounding_box_object(
                bpy.context.scene,
                "simbox",
                model_name="",
                location=Vector((0.3, -0.4, 1.1)),
                scale=Vector((1.2, 0.8, 1.5)),
                maintain_contour=True,
                armature_obj=armature,
            )
            model_utils.create_or_update_bounding_box_object(
                bpy.context.scene,
                "coverbox",
                model_name="",
                location=Vector((0.1, 0.2, 0.9)),
                scale=Vector((2.0, 1.0, 0.5)),
                maintain_contour=False,
                armature_obj=armature,
            )

            out_model = scratch / f"{seed}.model"
            result = blender_env.export_model(out_model, export_simbox=True, export_coverbox=True)
            if "FINISHED" not in result:
                ctx.fail(f"{seed}: setup export failed ({result})")

            blender_env.reset_scene()
            result = blender_env.import_model(out_model, import_simbox=False, import_coverbox=False)
            if "FINISHED" not in result:
                ctx.fail(f"{seed}: sidecar-off import failed ({result})")
            if model_utils.find_bounding_box_object(bpy.context.scene, "simbox", seed):
                ctx.fail(f"{seed}: import_simbox=False still imported simbox")
            if model_utils.find_bounding_box_object(bpy.context.scene, "coverbox", seed):
                ctx.fail(f"{seed}: import_coverbox=False still imported coverbox")

            blender_env.reset_scene()
            result = blender_env.import_model(out_model, import_simbox=True, import_coverbox=True)
            if "FINISHED" not in result:
                ctx.fail(f"{seed}: sidecar-on import failed ({result})")
            if model_utils.find_bounding_box_object(bpy.context.scene, "simbox", seed) is None:
                ctx.fail(f"{seed}: import_simbox=True did not import simbox")
            if model_utils.find_bounding_box_object(bpy.context.scene, "coverbox", seed) is None:
                ctx.fail(f"{seed}: import_coverbox=True did not import coverbox")


def test_import_smoothing_modes(ctx):
    """M-I7: smoothing = NONE / SMOOTH_GROUPS / NORMALS."""
    from framework import blender_env

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")
    _seed, cfg = seeds[0]
    model_path = ctx.data_path(cfg["source_model"])

    problems: list[str] = []

    blender_env.reset_scene()
    result = blender_env.import_model(model_path, smoothing="NONE")
    if "FINISHED" not in result:
        problems.append(f"smoothing NONE import failed: {result}")
    elif any(poly.use_smooth for obj in _mesh_objects() for poly in obj.data.polygons):
        problems.append("smoothing=NONE produced smooth polygons")

    blender_env.reset_scene()
    result = blender_env.import_model(model_path, smoothing="SMOOTH_GROUPS")
    if "FINISHED" not in result:
        problems.append(f"smoothing SMOOTH_GROUPS import failed: {result}")
    elif not any(poly.use_smooth for obj in _mesh_objects() for poly in obj.data.polygons):
        problems.append("smoothing=SMOOTH_GROUPS produced no smooth polygons")

    blender_env.reset_scene()
    result = blender_env.import_model(model_path, smoothing="NORMALS")
    if "FINISHED" not in result:
        problems.append(f"smoothing NORMALS import failed: {result}")
    elif not any(getattr(obj.data, "has_custom_normals", False) for obj in _mesh_objects()):
        problems.append("smoothing=NORMALS produced no custom normals")

    if problems:
        ctx.fail(" | ".join(problems))


def test_import_scene_options(ctx):
    """M-I8..M-I12: reset_scene, save_scene, merge, group_meshes, weld_vertices."""
    import shutil

    import bpy  # type: ignore

    from framework import blender_env, fixtures

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")
    seed, cfg = seeds[0]
    source_model = ctx.data_path(cfg["source_model"])
    problems: list[str] = []

    blender_env.reset_scene()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    bpy.context.active_object.name = "__reset_scene_sentinel__"
    result = blender_env.import_model(source_model, reset_scene=True)
    if "FINISHED" not in result:
        problems.append(f"reset_scene import failed: {result}")
    elif bpy.data.objects.get("__reset_scene_sentinel__") is not None:
        problems.append("reset_scene=True left the sentinel object in scene")

    blender_env.reset_scene()
    result = blender_env.import_model(source_model, group_meshes=True)
    if "FINISHED" not in result:
        problems.append(f"group_meshes=True import failed: {result}")
    elif not any(col.name.split(".")[0].lower().startswith("lod") for col in bpy.data.collections):
        problems.append("group_meshes=True created no LOD collections")

    blender_env.reset_scene()
    result = blender_env.import_model(source_model, group_meshes=False)
    if "FINISHED" not in result:
        problems.append(f"group_meshes=False import failed: {result}")
    elif any(col.name.split(".")[0].lower().startswith("lod") for col in bpy.data.collections):
        problems.append("group_meshes=False still created LOD collections")

    blender_env.reset_scene()
    result = blender_env.import_model(source_model)
    if "FINISHED" not in result:
        problems.append(f"initial merge setup import failed: {result}")
    else:
        armature_count = len([obj for obj in bpy.data.objects if obj.type == "ARMATURE"])
        result = blender_env.import_model(source_model, merge=True)
        merged_armature_count = len([obj for obj in bpy.data.objects if obj.type == "ARMATURE"])
        if "FINISHED" not in result:
            problems.append(f"merge=True import failed: {result}")
        elif merged_armature_count != armature_count:
            problems.append(f"merge=True changed armature count {armature_count} -> {merged_armature_count}")

    with fixtures.scratch_dir(ctx.config, f"save_scene_{seed}") as scratch:
        scratch_model = scratch / source_model.name
        shutil.copy2(source_model, scratch_model)
        blender_env.reset_scene()
        result = bpy.ops.import_scene.dow2_model(filepath=str(scratch_model), save_scene=True)
        blend_path = scratch_model.with_suffix(".blend")
        if "FINISHED" not in result:
            problems.append(f"save_scene import failed: {result}")
        elif not blend_path.is_file():
            problems.append("save_scene=True did not write a .blend file")

    from dow2_tools.model.import_types import ImportOptions, ImportVertex  # type: ignore
    from dow2_tools.model.importer_meshes import create_blender_mesh  # type: ignore
    from mathutils import Vector  # type: ignore
    from types import SimpleNamespace

    duplicate_vertices = []
    for co in ((0, 0, 0), (0, 0, 0), (1, 0, 0), (0, 1, 0)):
        vertex = ImportVertex()
        vertex.position = Vector(co)
        duplicate_vertices.append(vertex)

    blender_env.reset_scene()
    importer = SimpleNamespace(options=ImportOptions(weld_vertices=True, smoothing="NONE"), materials={}, armature=None)
    create_blender_mesh(importer, "weld_probe", duplicate_vertices, [(0, 2, 3), (1, 2, 3)], "", [], False, False, "healthy", 0)
    obj = bpy.data.objects.get("weld_probe")
    if obj is None:
        problems.append("weld_vertices test mesh was not created")
    elif len(obj.data.vertices) >= len(duplicate_vertices):
        problems.append("weld_vertices=True did not reduce duplicate vertex count")

    if problems:
        ctx.fail(" | ".join(problems))


def test_import_golden_models(ctx):
    """M-I13: golden .model set ; geometry/material/bone structure vs baseline."""
    from framework import blender_env, model_snapshot

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")

    problems: list[str] = []
    for seed, cfg in seeds:
        model_path = ctx.data_path(cfg["source_model"])
        blender_env.reset_scene()
        result = blender_env.import_model(model_path)
        if "FINISHED" not in result:
            problems.append(f"{seed}: import -> {result}")
            continue

        snap = model_snapshot.capture()
        expected = _expected_group_triangles(cfg.get("baseline", {}))
        actual = {k: g["triangles"] for k, g in snap["meshes"].items()}
        expected_vertices = {
            f"{entry['state']}|{entry['lod']}|{entry['material']}": entry["vertices"]
            for test_id, entry in cfg.get("baseline", {}).items()
            if test_id != "__totals__" and isinstance(entry, dict) and "vertices" in entry
        }
        actual_vertices = {k: len(g["positions"]) for k, g in snap["meshes"].items()}

        for key, exp_tris in expected.items():
            if key not in actual:
                problems.append(f"{seed}: missing group '{key}'")
            elif actual[key] != exp_tris:
                problems.append(f"{seed} {key}: triangles {actual[key]} != {exp_tris}")

        for key, exp_verts in expected_vertices.items():
            if key not in actual_vertices:
                continue
            if actual_vertices[key] != exp_verts:
                problems.append(f"{seed} {key}: vertices {actual_vertices[key]} != {exp_verts}")

        for mat_name in cfg.get("materials", {}):
            if mat_name not in snap["materials"]:
                problems.append(f"{seed}: material '{mat_name}' not imported")

        if not snap["bones"]:
            problems.append(f"{seed}: no bones imported")

    if problems:
        ctx.fail(" | ".join(problems))
