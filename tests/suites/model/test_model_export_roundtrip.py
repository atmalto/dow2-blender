"""Model export + round-trip tests (plan IDs M-E1..M-E13).

Built on ``framework.model_roundtrip`` (rebuild a seed from glb+config, export
to ``.model``, re-import) and the ``model_snapshot`` comparator. M-E1 is the
full-fidelity §14 round-trip; M-E2/M-E3 exercise the export content toggles.
Remaining M-E* are scaffold stubs.
"""

from __future__ import annotations

CATEGORY = "model/export"

_TODO = "scaffold ; not implemented yet"

_SEEDS = ("power_armour_common", "chaos_heavy_bolter_turret")


def _available_seeds(ctx):
    from framework import model_roundtrip

    return [
        (s, cfg)
        for s in _SEEDS
        if (cfg := model_roundtrip.load_seed_config(ctx.config.test_data_dir, s)) is not None
    ]


def _sanity_gate(seed: str, before: dict, baseline: dict) -> list[str]:
    """Cheap check that the glb rebuilt the expected geometry before we export."""
    exp_tris = baseline.get("__totals__", {}).get("triangles")
    if exp_tris is None:
        return []
    got = sum(g["triangles"] for g in before.get("meshes", {}).values())
    return [] if got == exp_tris else [f"{seed}: rebuilt triangles {got} != baseline {exp_tris}"]


def test_roundtrip_import_export_import(ctx):
    """M-E1: rebuild from test_data -> export .model -> re-import; full-fidelity match."""
    from framework import model_roundtrip, model_snapshot

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")

    problems: list[str] = []
    for seed, cfg in seeds:
        before, after, error = model_roundtrip.run(ctx.config, seed, cfg)
        if error:
            problems.append(f"{seed}: {error}")
            continue
        problems.extend(_sanity_gate(seed, before, cfg.get("baseline", {})))
        for category, message in model_snapshot.compare(before, after):
            problems.append(f"{seed} [{category}] {message}")

    if problems:
        ctx.fail(" | ".join(problems))


def test_export_content_toggles(ctx):
    """M-E2: export_bones / export_markers / export_materials on/off."""
    from framework import model_roundtrip, model_snapshot

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")

    # Prefer a seed that has markers so the markers toggle is meaningful.
    seed, cfg = next(
        ((s, c) for s, c in seeds if s == "chaos_heavy_bolter_turret"), seeds[0]
    )
    problems: list[str] = []

    # Baseline (all content on) ; establishes what "present" looks like.
    _before_snapshot, on_after, err = model_roundtrip.run(ctx.config, seed, cfg)
    if err:
        ctx.fail(f"{seed}: baseline export failed: {err}")
    if not on_after["bones"]:
        problems.append(f"{seed}: expected bones with export_bones=True")

    # export_bones=False -> no armature/bones after re-import.
    _before_snapshot, after, err = model_roundtrip.run(ctx.config, seed, cfg, export_bones=False)
    if err:
        problems.append(f"{seed} bones-off: {err}")
    elif after["bones"]:
        problems.append(f"{seed}: export_bones=False still produced {len(after['bones'])} bones")

    # export_markers=False -> no markers after re-import.
    if on_after["markers"]:
        _before_snapshot, after, err = model_roundtrip.run(ctx.config, seed, cfg, export_markers=False)
        if err:
            problems.append(f"{seed} markers-off: {err}")
        elif after["markers"]:
            problems.append(f"{seed}: export_markers=False still produced {len(after['markers'])} markers")

    # export_materials=False -> no DoW2 materials after re-import.
    _before_snapshot, after, err = model_roundtrip.run(ctx.config, seed, cfg, export_materials=False)
    if err:
        problems.append(f"{seed} materials-off: {err}")
    elif after["materials"]:
        problems.append(f"{seed}: export_materials=False still produced {len(after['materials'])} materials")

    if problems:
        ctx.fail(" | ".join(problems))


def test_export_rest_pose(ctx):
    """M-E3: export_rest_pose exports undeformed rest geometry from a posed scene."""
    import bpy  # type: ignore
    from mathutils import Euler  # type: ignore

    from framework import blender_env, fixtures, model_snapshot

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")
    seed, cfg = seeds[0]
    seed_dir = ctx.config.test_data_dir / seed

    with fixtures.scratch_dir(ctx.config, f"rest_pose_{seed}") as scratch:
        with fixtures.staged_textures(ctx.config, cfg.get("textures", {}), seed_dir):
            blender_env.reset_scene()
            blender_env.import_glb(seed_dir / cfg["glb"])
            if blender_env.apply_config_to_scene(cfg) == 0:
                ctx.fail(f"{seed}: no meshes configured from glb")

            rest_snapshot = model_snapshot.capture()
            armature = next((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None)
            if armature is None or not armature.pose.bones:
                ctx.skip(f"{seed}: no armature available for rest-pose test")

            pose_bone = next((bone for bone in armature.pose.bones if bone.name != "skeleton_root"), armature.pose.bones[0])
            pose_bone.rotation_mode = "XYZ"
            pose_bone.rotation_euler = Euler((0.0, 0.0, 0.35), "XYZ")
            bpy.context.view_layer.update()

            out_model = scratch / f"{seed}.model"
            result = blender_env.export_model(out_model, export_rest_pose=True)
            if "FINISHED" not in result:
                ctx.fail(f"{seed}: rest-pose export failed ({result})")

            blender_env.reset_scene()
            imported = blender_env.import_model(out_model)
            if "FINISHED" not in imported:
                ctx.fail(f"{seed}: rest-pose re-import failed ({imported})")

            after = model_snapshot.capture()
            problems = [
                f"{seed} [{category}] {message}"
                for category, message in model_snapshot.compare(rest_snapshot, after)
                if category in ("model_mesh", "model_normal", "model_weight", "model_bone")
            ]

    if problems:
        ctx.fail(" | ".join(problems))


def test_bone_limit_and_material_combine(ctx):
    """M-E4..M-E6: apply_bone_limit (>54), combine_same_material_meshes, apply_material_if_missing."""
    import bpy  # type: ignore

    from dow2_tools.model.exporter import DoW2ModelExporter  # type: ignore
    from dow2_tools.model.export_utils import ExportSubMesh, get_or_create_default_material, is_relic_material  # type: ignore
    from dow2_tools.model.export_utils import ExportOptions  # type: ignore
    from dow2_tools.model.exporter_mesh_plan import (  # type: ignore
        MAX_INFLUENCING_BONES_PER_MESH,
        PlannedTriangle,
        combine_compatible_sub_meshes,
        count_sub_mesh_influencing_bones,
        partition_triangles_by_bone_limit,
    )
    from dow2_tools.model.export_utils import assign_default_materials_to_missing_slots  # type: ignore
    from framework import blender_env

    problems: list[str] = []

    triangles = [
        PlannedTriangle(loop_indices=(index * 3, index * 3 + 1, index * 3 + 2), influencing_bones=frozenset({f"bone_{index}"}))
        for index in range(MAX_INFLUENCING_BONES_PER_MESH + 6)
    ]
    buckets = partition_triangles_by_bone_limit(triangles)
    if len(buckets) < 2:
        problems.append("apply_bone_limit planner did not split >54-bone triangles")
    if any(len(set().union(*(tri.influencing_bones for tri in bucket))) > MAX_INFLUENCING_BONES_PER_MESH for bucket in buckets):
        problems.append("apply_bone_limit planner produced a bucket over 54 bones")

    mat = bpy.data.materials.new("relic.material.__combine_probe")
    mat["dow2_shader"] = "dow2_unit"
    first = ExportSubMesh(name="first", material_name=mat.name, influencing_bone_names=("a", "b"))
    second = ExportSubMesh(name="second", material_name=mat.name, influencing_bone_names=("b", "c"))
    combined = combine_compatible_sub_meshes([first, second], {mat.name: mat})
    if len(combined) != 1:
        problems.append("combine_same_material_meshes did not combine compatible submeshes")
    elif count_sub_mesh_influencing_bones(combined[0]) > MAX_INFLUENCING_BONES_PER_MESH:
        problems.append("combine_same_material_meshes exceeded the bone limit")
    bpy.data.materials.remove(mat)

    blender_env.reset_scene()
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    first_obj = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(2.0, 0.0, 0.0))
    second_obj = bpy.context.active_object
    assigned = assign_default_materials_to_missing_slots(unique_per_mesh=True)
    if assigned != 2:
        problems.append(f"apply_material_if_missing assigned {assigned} slots, expected 2")
    assigned_names = {obj.data.materials[0].name for obj in (first_obj, second_obj) if obj.data.materials}
    if len(assigned_names) != 2:
        problems.append("apply_material_if_missing did not assign unique default materials")
    if any(not is_relic_material(obj.data.materials[0]) for obj in (first_obj, second_obj) if obj.data.materials):
        problems.append("apply_material_if_missing assigned a non-relic material")

    get_or_create_default_material()

    blender_env.reset_scene()
    bpy.ops.object.armature_add(location=(0.0, 0.0, 0.0))
    armature = bpy.context.active_object
    armature.name = "weight_limit_armature"
    bpy.ops.object.mode_set(mode='EDIT')
    root = armature.data.edit_bones[0]
    root.name = "bone_0"
    root.head = (0.0, 0.0, 0.0)
    root.tail = (0.0, 0.0, 1.0)
    for index in range(1, 5):
        bone = armature.data.edit_bones.new(f"bone_{index}")
        bone.head = (index * 0.1, 0.0, 0.0)
        bone.tail = (index * 0.1, 0.0, 1.0)
    bpy.ops.object.mode_set(mode='OBJECT')

    mesh = bpy.data.meshes.new("weight_limit_mesh")
    mesh.from_pydata([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [], [(0, 1, 2)])
    mesh.update()
    obj = bpy.data.objects.new("weight_limit_mesh", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(get_or_create_default_material())
    modifier = obj.modifiers.new("Armature", 'ARMATURE')
    modifier.object = armature
    for index in range(5):
        group = obj.vertex_groups.new(name=f"bone_{index}")
        group.add([0, 1, 2], 0.2, 'REPLACE')

    from framework import fixtures

    with fixtures.scratch_dir(ctx.config, "vertex_weight_limit_warning") as scratch:
        out_model = scratch / "weight_limit.model"
        exporter = DoW2ModelExporter(str(out_model), ExportOptions())
        result = exporter.export_model()
        if "FINISHED" not in result or not out_model.is_file():
            problems.append(f"export with >4 vertex influences did not finish: {result}")
        warning_text = "\n".join(exporter.warnings).lower()
        if "at most 4" not in warning_text or "strongest 4" not in warning_text:
            problems.append(f"export with >4 vertex influences did not warn correctly: {exporter.warnings}")

    if problems:
        ctx.fail(" | ".join(problems))


def test_damage_states_and_lod(ctx):
    """M-E7..M-E8: damage_state_* mapping x lod_count/damage_template; export_*_var data tables."""
    import bpy  # type: ignore

    from framework import blender_env, fixtures

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")
    seed, cfg = seeds[0]
    seed_dir = ctx.config.test_data_dir / seed
    problems: list[str] = []

    expected_states = {
        "SINGLE": ["healthy"],
        "SIMPLE": ["healthy", "wreck"],
        "FULL": ["healthy", "light_damage", "heavy_damage", "wreck"],
    }
    for template, states in expected_states.items():
        for lod_count in (1, 2, 4):
            blender_env.reset_scene()
            bpy.context.scene.dow2_model_damage_template = template
            bpy.context.scene.dow2_model_lod_count = lod_count
            result = bpy.ops.dow2.setup_collections()
            if "FINISHED" not in result:
                problems.append(f"setup_collections {template}/{lod_count} failed: {result}")
                continue
            for state in states:
                state_col = bpy.data.collections.get(state)
                if state_col is None:
                    problems.append(f"setup_collections missing state {state} for {template}")
                    continue
                lod_names = {child.name.split(".")[0] for child in state_col.children}
                expected_lods = {f"lod{index}" for index in range(lod_count)}
                if not expected_lods.issubset(lod_names):
                    problems.append(f"setup_collections {template}/{lod_count} missing LODs for {state}")

    with fixtures.scratch_dir(ctx.config, f"data_templates_{seed}") as scratch:
        with fixtures.staged_textures(ctx.config, cfg.get("textures", {}), seed_dir):
            for enabled in (True, False):
                blender_env.reset_scene()
                blender_env.import_glb(seed_dir / cfg["glb"])
                if blender_env.apply_config_to_scene(cfg) == 0:
                    problems.append(f"{seed}: no meshes configured from glb")
                    continue
                out_model = scratch / f"{seed}_{int(enabled)}.model"
                result = blender_env.export_model(out_model, export_damage_state_var=enabled, export_health_var=enabled)
                if "FINISHED" not in result:
                    problems.append(f"data-template export {enabled} failed: {result}")
                    continue
                blender_env.reset_scene()
                result = blender_env.import_model(out_model)
                if "FINISHED" not in result:
                    problems.append(f"data-template import {enabled} failed: {result}")
                    continue
                if bool(bpy.context.scene.get("dow2_export_damage_state", False)) != enabled:
                    problems.append(f"export_damage_state_var={enabled} did not round-trip")
                if bool(bpy.context.scene.get("dow2_export_health", False)) != enabled:
                    problems.append(f"export_health_var={enabled} did not round-trip")

    if problems:
        ctx.fail(" | ".join(problems))


def test_bvols_and_overwrite(ctx):
    """M-E10: export_existing_bvols preserves imported BVOL_ helper bounds."""
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore

    from framework import blender_env, fixtures

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")
    seed, cfg = seeds[0]
    source_model = ctx.data_path(cfg["source_model"])

    with fixtures.scratch_dir(ctx.config, f"existing_bvols_{seed}") as scratch:
        blender_env.reset_scene()
        result = blender_env.import_model(source_model, import_bounding_volumes=True)
        if "FINISHED" not in result:
            ctx.fail(f"{seed}: BVOL setup import failed ({result})")

        mesh_bvols = [obj for obj in bpy.data.objects if obj.name.startswith("BVOL_") and obj.get("dow2_bvol_type") == "mesh"]
        if not mesh_bvols:
            ctx.fail(f"{seed}: no imported mesh BVOL_ object available")

        expected_location = Vector((12.0, 13.0, 14.0))
        expected_scale = Vector((0.7, 0.8, 0.9))
        for bvol in mesh_bvols:
            bvol.location = expected_location
            bvol.scale = expected_scale

        out_model = scratch / f"{seed}.model"
        result = blender_env.export_model(out_model, export_existing_bvols=True)
        if "FINISHED" not in result:
            ctx.fail(f"{seed}: export_existing_bvols export failed ({result})")

        blender_env.reset_scene()
        result = blender_env.import_model(out_model, import_bounding_volumes=True)
        if "FINISHED" not in result:
            ctx.fail(f"{seed}: export_existing_bvols re-import failed ({result})")

        imported_bvols = [obj for obj in bpy.data.objects if obj.name.startswith("BVOL_")]
        if not any((obj.location - expected_location).length <= 1e-3 and (obj.scale - expected_scale).length <= 1e-3 for obj in imported_bvols):
            ctx.fail(f"{seed}: exported existing BVOL bounds were not preserved")


def test_check_existing(ctx):
    """M-E11: check_existing overwrite path."""
    import bpy  # type: ignore

    from framework import blender_env, fixtures

    with fixtures.scratch_dir(ctx.config, "check_existing_model") as scratch:
        out_model = scratch / "existing.model"
        out_model.write_bytes(b"do not overwrite")

        blender_env.reset_scene()
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
        result = bpy.ops.export_scene.dow2_model(filepath=str(out_model), check_existing=True)
        if "CANCELLED" not in result:
            ctx.fail(f"check_existing=True did not cancel existing-file export: {result}")
        if out_model.read_bytes() != b"do not overwrite":
            ctx.fail("check_existing=True overwrote the existing file")


def test_marker_offset_and_axis_adapter(ctx):
    """M-E12..M-E13: marker offset preservation + bone/marker axis-adapter round-trip."""
    import bpy  # type: ignore

    from dow2_tools.model import utils as model_utils  # type: ignore
    from framework import blender_env, model_roundtrip, model_snapshot

    ctx.require_data()
    seeds = _available_seeds(ctx)
    if not seeds:
        ctx.skip("no test-data seeds present (run: python tests/run.py --build-test-data)")
    seed, cfg = next(((s, c) for s, c in seeds if s == "chaos_heavy_bolter_turret"), seeds[0])
    model_path = ctx.data_path(cfg["source_model"])
    problems: list[str] = []

    blender_env.reset_scene()
    result = blender_env.import_model(model_path)
    if "FINISHED" not in result:
        problems.append(f"{seed}: marker setup import failed: {result}")
    else:
        armature = next((obj for obj in bpy.data.objects if obj.type == "ARMATURE"), None)
        markers = list(model_utils.iter_armature_markers(armature)) if armature is not None else []
        if not markers or armature is None:
            problems.append(f"{seed}: no armature markers available for offset test")
        else:
            before = {marker.name: marker.matrix_world.copy() for marker in markers}
            bpy.ops.object.select_all(action="DESELECT")
            armature.select_set(True)
            bpy.context.view_layer.objects.active = armature
            armature.rotation_euler.rotate_axis("Z", 0.25)
            result, preserved = model_utils.apply_transform_preserve_markers(
                bpy.context,
                location=False,
                rotation=True,
                scale=False,
            )
            if "FINISHED" not in result:
                problems.append(f"apply_transform_preserve_markers failed: {result}")
            elif preserved != len(markers):
                problems.append(f"preserved {preserved} markers, expected {len(markers)}")
            else:
                moved = [name for name, matrix in before.items() if (bpy.data.objects[name].matrix_world.translation - matrix.translation).length > 1e-4]
                if moved:
                    problems.append(f"marker offsets moved after apply-transform: {moved[:3]}")

    before, after, error = model_roundtrip.run(ctx.config, seed, cfg)
    if error:
        problems.append(f"{seed}: axis-adapter round-trip failed: {error}")
    else:
        for category, message in model_snapshot.compare(before, after):
            if category in ("model_bone", "model_marker"):
                problems.append(f"{seed} [{category}] {message}")

    if problems:
        ctx.fail(" | ".join(problems))

