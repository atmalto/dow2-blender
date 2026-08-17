"""Physics import smoke/integration tests.

Phase 1 only: operator-driven import of real ``*_physics.hkx`` and
``*_rubble_physics.hkx`` assets, paired with their sibling ``.model`` files.
This stays intentionally narrow and does not cover export or roundtrip yet.
"""

from __future__ import annotations

import hashlib
import re

CATEGORY = "physics/import"


def _rel_label(ctx, path) -> str:
    try:
        return path.relative_to(ctx.config.data_root).as_posix()
    except ValueError:
        return path.as_posix()


def _summarize_failures(failures: list[str], limit: int = 8) -> str:
    shown = failures[:limit]
    suffix = "" if len(failures) <= limit else f" | ... {len(failures) - limit} more"
    return " | ".join(shown) + suffix


def _scratch_name(index: int, label: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:10]
    return f"{index:03d}_{digest}_{safe[-48:]}"


def _import_model_for_physics(model_path):
    from framework import blender_env

    return blender_env.import_model(
        model_path,
        import_materials=False,
        import_markers=False,
    )


def _mesh_object_count() -> int:
    import bpy  # type: ignore

    from dow2_tools.physics import utils  # type: ignore

    return sum(
        1
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and not utils.is_physics_hull_object(obj)
    )


def _scene_hull_objects():
    import bpy  # type: ignore

    from dow2_tools.physics import utils  # type: ignore

    return [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and utils.is_physics_hull_object(obj)
    ]


def _run_physics_import(physics_path):
    import bpy  # type: ignore

    bpy.context.scene.dow2_physics_settings.import_filepath = str(physics_path)
    return bpy.ops.dow2.import_physics_hulls()


def _is_environment_limited_parse_failure(exc: Exception) -> bool:
    text = str(exc)
    return (
        "Failed to read HKX with the native physics tool" in text
        and "Fallback via AssetCc also failed" in text
        and "AssetCc tools were not found" in text
    )


def _compare_resolved_config(obj, expected_config: dict, tol: float = 1e-4) -> list[str]:
    from dow2_tools.physics import hull_properties  # type: ignore

    problems: list[str] = []
    resolved = hull_properties.resolve_export_settings(obj)
    for key, expected in sorted(expected_config.items()):
        actual = resolved.get(key)
        if isinstance(expected, list):
            if not isinstance(actual, (list, tuple)) or len(actual) < len(expected):
                problems.append(f"config {key} missing")
                continue
            for index, (got_value, expected_value) in enumerate(zip(actual, expected)):
                if abs(float(got_value) - float(expected_value)) > tol:
                    problems.append(
                        f"config {key}[{index}] {float(got_value):.5f} != {float(expected_value):.5f}"
                    )
                    break
            continue
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            if actual is None:
                problems.append(f"config {key} None != {float(expected):.5f}")
                continue
            actual_value = float(actual)
            expected_value = float(expected)
            limit = max(tol, max(abs(actual_value), abs(expected_value)) * 1.0e-6)
            if abs(actual_value - expected_value) > limit:
                actual_text = "None" if actual is None else f"{float(actual):.5f}"
                problems.append(f"config {key} {actual_text} != {expected_value:.5f}")
            continue
        if actual != expected:
            problems.append(f"config {key} {actual!r} != {expected!r}")
    return problems


def _unique_expected_rigid_bodies(expected_scene):
    unique = {}
    for rigid_body in expected_scene.rigid_bodies:
        key = (rigid_body.state_name, rigid_body.lod_level, rigid_body.name)
        unique[key] = rigid_body
    return list(unique.values())


def _validate_imported_scene(expected_scene) -> list[str]:
    import bpy  # type: ignore

    from dow2_tools.physics import utils  # type: ignore

    problems: list[str] = []
    expected_rigid_bodies = _unique_expected_rigid_bodies(expected_scene)
    hulls = _scene_hull_objects()
    if len(hulls) != len(expected_rigid_bodies):
        problems.append(f"hull count {len(hulls)} != expected {len(expected_rigid_bodies)}")

    selected_objects = list(bpy.context.selected_objects)
    if len(selected_objects) != len(hulls):
        problems.append(f"selected objects {len(selected_objects)} != imported hulls {len(hulls)}")
    elif any(not utils.is_physics_hull_object(obj) for obj in selected_objects):
        problems.append("selection includes non-hull objects after import")

    if bpy.context.active_object not in hulls:
        problems.append("active object is not one of the imported hulls")

    for rigid_body in expected_rigid_bodies:
        hull_obj = utils.find_existing_hull(rigid_body.state_name, rigid_body.lod_level, rigid_body.name)
        if hull_obj is None:
            problems.append(
                f"missing hull {rigid_body.state_name}/lod{rigid_body.lod_level}/{rigid_body.name}"
            )
            continue
        if hull_obj.display_type != "WIRE":
            problems.append(f"{rigid_body.name}: display_type {hull_obj.display_type!r} != 'WIRE'")
        if hull_obj.get(utils.WORKFLOW_PROP) != "HKX_IMPORT":
            problems.append(f"{rigid_body.name}: workflow {hull_obj.get(utils.WORKFLOW_PROP)!r} != 'HKX_IMPORT'")
        if hull_obj.get("dow2_physics_motion_type") != rigid_body.motion_type:
            problems.append(
                f"{rigid_body.name}: motion {hull_obj.get('dow2_physics_motion_type')!r} != {rigid_body.motion_type!r}"
            )
        if hull_obj.get("dow2_physics_source_system", "") != rigid_body.system_name:
            problems.append(
                f"{rigid_body.name}: source system {hull_obj.get('dow2_physics_source_system', '')!r} != {rigid_body.system_name!r}"
            )
        problems.extend(f"{rigid_body.name}: {msg}" for msg in _compare_resolved_config(hull_obj, rigid_body.export_config))
    return problems


def test_single_physics_import_operator(ctx):
    """P-I1: one real sibling model/physics pair imports through addon operators."""
    from framework import blender_env
    from framework.assets import find_physics

    from dow2_tools.physics import importer  # type: ignore

    ctx.require_data()
    assets = find_physics(ctx.config.data_root, limit=1)
    if not assets:
        ctx.skip(f"no exact-paired physics assets discovered under {ctx.config.data_root / 'art'}")

    asset = assets[0]
    blender_env.reset_scene()
    model_result = _import_model_for_physics(asset.model_path)
    if "FINISHED" not in model_result:
        ctx.fail(f"{_rel_label(ctx, asset.model_path)}: model import failed ({model_result})")
    if _mesh_object_count() == 0:
        ctx.fail(f"{_rel_label(ctx, asset.model_path)}: model import produced no non-hull meshes")

    try:
        expected_scene = importer.load_physics_scene(str(asset.path))
    except Exception as exc:
        if _is_environment_limited_parse_failure(exc):
            ctx.skip(f"parser unavailable for {asset.path}")
        raise
    result = _run_physics_import(asset.path)
    if "FINISHED" not in result:
        ctx.fail(f"{_rel_label(ctx, asset.path)}: physics import failed ({result})")

    problems = _validate_imported_scene(expected_scene)
    if problems:
        ctx.fail(f"{_rel_label(ctx, asset.path)}: {_summarize_failures(problems)}")


def test_art_physics_model_pairs_scope(ctx):
    """P-I2: small-scope real DATA_ROOT/art sibling model + physics pair sweep."""
    from framework import blender_env, fixtures
    from framework.assets import find_physics

    from dow2_tools.physics import importer  # type: ignore

    ctx.require_data()
    assets = find_physics(ctx.config.data_root, ctx.config.physics_limit)
    if not assets:
        ctx.skip(f"no exact-paired physics assets discovered under {ctx.config.data_root / 'art'}")

    failures: list[str] = []
    category_counts: dict[str, int] = {}
    exercised = 0
    skipped_empty_models = 0

    with fixtures.scratch_dir(ctx.config, f"physics_import_scope_{ctx.config.scope}") as scratch:
        for index, asset in enumerate(assets):
            label = _rel_label(ctx, asset.path)
            category_counts[asset.category] = category_counts.get(asset.category, 0) + 1
            blender_env.reset_scene()

            model_result = _import_model_for_physics(asset.model_path)
            if "FINISHED" not in model_result:
                failures.append(f"{label}: model import failed ({model_result})")
                continue
            if _mesh_object_count() == 0:
                skipped_empty_models += 1
                continue

            try:
                expected_scene = importer.load_physics_scene(str(asset.path))
            except Exception as exc:
                if _is_environment_limited_parse_failure(exc):
                    continue
                failures.append(f"{label}: parse raised {type(exc).__name__}: {exc}")
                continue
            if not expected_scene.rigid_bodies:
                failures.append(f"{label}: parser returned no rigid bodies")
                continue

            result = _run_physics_import(asset.path)
            if "FINISHED" not in result:
                failures.append(f"{label}: physics import failed ({result})")
                continue

            exercised += 1
            problems = _validate_imported_scene(expected_scene)
            if problems:
                failures.append(f"{label}: {_summarize_failures(problems)}")
                continue

            marker = scratch / (_scratch_name(index, label) + ".ok")
            marker.write_text("ok\n", encoding="utf-8")

    if exercised == 0:
        ctx.fail(
            f"scope={ctx.config.scope} cap={ctx.config.physics_limit} categories={category_counts} "
            f"skipped_empty_models={skipped_empty_models} failures={len(failures)} | no usable pairs exercised"
        )

    if failures:
        ctx.fail(
            f"scope={ctx.config.scope} cap={ctx.config.physics_limit} "
            f"categories={category_counts} exercised={exercised} skipped_empty_models={skipped_empty_models} "
            f"failures={len(failures)} | {_summarize_failures(failures)}"
        )