"""Collision import / export / round-trip tests (plan IDs C-I1..C-G1).

Scaffold: every test currently skips.
"""

from __future__ import annotations

import hashlib
import re

CATEGORY = "collision"

_TODO = "scaffold ; not implemented yet"


def _build_collision_scene(state_ids=(1, 2)):
    import bpy  # type: ignore

    from dow2_tools.collision import utils as collision_utils  # type: ignore

    bpy.ops.wm.read_homefile(use_empty=True)
    objs = []
    for index, state_id in enumerate(state_ids):
        location = (float(index) * 3.0, 0.0, 0.0)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
        obj = bpy.context.active_object
        obj.name = f"col_state_{state_id}"
        col = collision_utils.ensure_collision_state_collection(bpy.context.scene, state_id)
        if bpy.context.scene.collection in obj.users_collection:
            bpy.context.scene.collection.objects.unlink(obj)
        col.objects.link(obj)
        obj["dow2_collision_state_id"] = state_id
        objs.append(obj)
    return objs


def _rel_label(ctx, path) -> str:
    try:
        return path.relative_to(ctx.config.data_root).as_posix()
    except ValueError:
        return path.as_posix()


def _scratch_name(index: int, label: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:10]
    return f"{index:03d}_{digest}_{safe[-48:]}"


def _state_summary(collision_data):
    summary = {}
    for mesh in collision_data.meshes:
        entry = summary.setdefault(
            mesh.state_id,
            {"meshes": 0, "verts": 0, "faces": 0, "min": [None, None, None], "max": [None, None, None]},
        )
        entry["meshes"] += 1
        entry["verts"] += len(mesh.vertices)
        entry["faces"] += len(mesh.faces)
        for vertex in mesh.vertices:
            for axis, value in enumerate(vertex):
                if entry["min"][axis] is None or value < entry["min"][axis]:
                    entry["min"][axis] = value
                if entry["max"][axis] is None or value > entry["max"][axis]:
                    entry["max"][axis] = value
    return summary


def _summaries_match(before: dict, after: dict, tol: float = 1e-4) -> list[str]:
    problems: list[str] = []
    if set(before) != set(after):
        problems.append(f"states {sorted(after)} != {sorted(before)}")
        return problems
    for state_id in sorted(before):
        expected = before[state_id]
        got = after[state_id]
        for key in ("meshes", "verts", "faces"):
            if got[key] != expected[key]:
                problems.append(f"state {state_id}: {key} {got[key]} != {expected[key]}")
        for key in ("min", "max"):
            for axis, (got_value, expected_value) in enumerate(zip(got[key], expected[key])):
                if got_value is None or expected_value is None:
                    continue
                if abs(got_value - expected_value) > tol:
                    problems.append(f"state {state_id}: bbox {key}[{axis}] {got_value:.5f} != {expected_value:.5f}")
    return problems


def _export_collision(path, *, use_selection: bool, apply_modifiers: bool):
    import bpy  # type: ignore

    return bpy.ops.export_scene.dow2_collision(
        filepath=str(path),
        use_selection=use_selection,
        apply_modifiers=apply_modifiers,
    )


def test_import_options(ctx):
    """C-I1..C-I4: import_as_separate, create_collection, display_type, types 1-4 mapping."""
    import bpy  # type: ignore

    from dow2_tools.collision.collision_io import read_collision  # type: ignore
    from framework import fixtures

    ctx.require_data()
    with fixtures.scratch_dir(ctx.config, "collision_import_options") as scratch:
        src = scratch / "src.collision"
        _build_collision_scene(state_ids=(1, 2, 3, 4))
        for obj in bpy.context.scene.objects:
            obj.select_set(obj.type == "MESH")
        assert "FINISHED" in _export_collision(src, use_selection=True, apply_modifiers=True)

        bpy.ops.wm.read_homefile(use_empty=True)
        result = bpy.ops.import_scene.dow2_collision(
            filepath=str(src),
            import_as_separate=True,
            create_collection=True,
            display_type='BOUNDS',
        )
        if "FINISHED" not in result:
            ctx.fail(f"collision import failed: {result}")

        imported_meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        if len(imported_meshes) != len(read_collision(str(src)).meshes):
            ctx.fail("import_as_separate did not create one object per collision mesh")
        if any(o.display_type != 'BOUNDS' for o in imported_meshes):
            ctx.fail("display_type option not applied to imported collision meshes")
        if not all("dow2_collision_state_id" in o for o in imported_meshes):
            ctx.fail("imported collision meshes missing state metadata")
        state_ids = {int(o["dow2_collision_state_id"]) for o in imported_meshes}
        if state_ids != {1, 2, 3, 4}:
            ctx.fail(f"collision state IDs {sorted(state_ids)} != [1, 2, 3, 4]")


def test_roundtrip_import_export_import(ctx):
    """C-E1: import -> export -> import; hull geometry preserved."""
    import bpy  # type: ignore

    from dow2_tools.collision.collision_io import read_collision  # type: ignore
    from framework import fixtures

    ctx.require_data()
    with fixtures.scratch_dir(ctx.config, "collision_roundtrip") as scratch:
        src = scratch / "src.collision"
        out = scratch / "out.collision"
        _build_collision_scene()
        for obj in bpy.context.scene.objects:
            obj.select_set(obj.type == "MESH")
        assert "FINISHED" in _export_collision(src, use_selection=True, apply_modifiers=True)

        bpy.ops.wm.read_homefile(use_empty=True)
        assert "FINISHED" in bpy.ops.import_scene.dow2_collision(
            filepath=str(src),
            import_as_separate=True,
            create_collection=True,
            display_type='WIRE',
        )

        for obj in bpy.context.scene.objects:
            obj.select_set(obj.type == "MESH")
        result = _export_collision(out, use_selection=True, apply_modifiers=True)
        if "FINISHED" not in result:
            ctx.fail(f"collision re-export failed: {result}")

        c0 = read_collision(str(src))
        c1 = read_collision(str(out))
        if len(c0.meshes) != len(c1.meshes):
            ctx.fail(f"mesh count changed: {len(c0.meshes)} -> {len(c1.meshes)}")
        tri0 = sum(len(m.faces) for m in c0.meshes)
        tri1 = sum(len(m.faces) for m in c1.meshes)
        if tri0 != tri1:
            ctx.fail(f"triangle count changed: {tri0} -> {tri1}")


def test_export_options(ctx):
    """C-E2..C-E4: use_selection, apply_modifiers, state_count."""
    import bpy  # type: ignore

    from dow2_tools.collision import utils as collision_utils  # type: ignore
    from dow2_tools.collision.collision_io import read_collision  # type: ignore
    from framework import fixtures

    with fixtures.scratch_dir(ctx.config, "collision_export_options") as scratch:
        _build_collision_scene()
        out_sel = scratch / "sel.collision"
        out_all = scratch / "all.collision"

        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        bpy.ops.object.select_all(action='DESELECT')
        meshes[0].select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        result = _export_collision(out_sel, use_selection=True, apply_modifiers=False)
        if "FINISHED" not in result:
            ctx.fail(f"selection export failed: {result}")

        bpy.ops.object.select_all(action='SELECT')
        result = _export_collision(out_all, use_selection=False, apply_modifiers=True)
        if "FINISHED" not in result:
            ctx.fail(f"all export failed: {result}")

        c_sel = read_collision(str(out_sel))
        c_all = read_collision(str(out_all))
        if len(c_sel.meshes) >= len(c_all.meshes):
            ctx.fail("use_selection did not reduce exported mesh count")

        for state_count in (1, 2, 3, 4):
            bpy.ops.wm.read_homefile(use_empty=True)
            bpy.context.scene.dow2_collision_state_count = state_count
            result = bpy.ops.dow2.setup_collision_collections()
            if "FINISHED" not in result:
                ctx.fail(f"setup_collision_collections {state_count} returned {result}")
            present = {
                state_id
                for state_id, _state_name, _model_state in collision_utils.COLLISION_STATE_DEFINITIONS
                if bpy.data.collections.get(collision_utils.get_collision_collection_name(state_id)) is not None
            }
            expected = {state_id for state_id, _state_name, _model_state in collision_utils.iter_collision_states(state_count)}
            if present != expected:
                ctx.fail(f"state_count={state_count}: collections {sorted(present)} != {sorted(expected)}")


def test_art_collision_model_pairs_scope(ctx):
    """§13/C scope: real DATA_ROOT/art .collision files paired with sibling .model files."""
    import bpy  # type: ignore

    from dow2_tools.collision.collision_io import read_collision
    from framework import blender_env, fixtures
    from framework.assets import find_collisions

    ctx.require_data()
    assets = find_collisions(ctx.config.data_root, ctx.config.model_limit)
    if not assets:
        ctx.skip(f"no .collision assets discovered under {ctx.config.data_root / 'art'}")

    failures: list[str] = []
    category_counts: dict[str, int] = {}
    paired = 0
    roundtripped = 0

    with fixtures.scratch_dir(ctx.config, f"collision_scope_{ctx.config.scope}") as scratch:
        for index, asset in enumerate(assets):
            label = _rel_label(ctx, asset.path)
            category_counts[asset.category] = category_counts.get(asset.category, 0) + 1
            if asset.model_path is None:
                failures.append(f"{label}: no sibling .model file")
                continue
            paired += 1

            try:
                source_collision = read_collision(str(asset.path))
            except Exception as exc:
                failures.append(f"{label}: read raised {type(exc).__name__}: {exc}")
                continue
            bad_states = sorted({mesh.state_id for mesh in source_collision.meshes if mesh.state_id not in {1, 2, 3, 4}})
            if bad_states:
                failures.append(f"{label}: unexpected state IDs {bad_states}")
                continue

            blender_env.reset_scene()
            model_result = blender_env.import_model(
                asset.model_path,
                import_simbox=False,
                import_coverbox=False,
                import_bounding_volumes=False,
            )
            if "FINISHED" not in model_result:
                failures.append(f"{label}: sibling model import returned {model_result}")
                continue

            collision_result = bpy.ops.import_scene.dow2_collision(
                filepath=str(asset.path),
                import_as_separate=True,
                create_collection=True,
                display_type='WIRE',
            )
            if "FINISHED" not in collision_result:
                failures.append(f"{label}: collision import returned {collision_result}")
                continue

            collision_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and "dow2_collision_state_id" in obj]
            if len(collision_objects) != len(source_collision.meshes):
                failures.append(f"{label}: imported {len(collision_objects)} collision objects, expected {len(source_collision.meshes)}")
                continue
            if any(obj.display_type != 'WIRE' for obj in collision_objects):
                failures.append(f"{label}: collision display_type not applied")
                continue

            out_collision = scratch / f"{_scratch_name(index, label)}.collision"
            export_result = _export_collision(out_collision, use_selection=False, apply_modifiers=False)
            if "FINISHED" not in export_result or not out_collision.is_file():
                failures.append(f"{label}: collision export returned {export_result}")
                continue

            exported_collision = read_collision(str(out_collision))
            summary_problems = _summaries_match(_state_summary(source_collision), _state_summary(exported_collision))
            if summary_problems:
                failures.append(f"{label}: {'; '.join(summary_problems[:6])}")
                continue
            roundtripped += 1

    print(
        f"[collision/scope] checked={len(assets)} paired={paired} roundtripped={roundtripped} "
        f"failures={len(failures)} categories={category_counts} scope={ctx.config.scope}"
    )

    if roundtripped == 0:
        failures.append("scope round-tripped no collision/model pairs")
    if failures:
        shown = failures[:25]
        suffix = "" if len(failures) <= 25 else f" | ... {len(failures) - 25} more"
        ctx.fail("collision/model pair scope failures: " + " | ".join(shown) + suffix)


def _hull_generation_validity_deferred(ctx):
    """C-G1 is deferred; keep this helper undiscovered until hull generation enters scope."""
    ctx.skip(_TODO)
