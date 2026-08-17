"""Physics export roundtrip tests.

These validate export correctness against the original authored HKX summary while
still exercising the actual addon import/export operators.
"""

from __future__ import annotations

import math
from pathlib import Path

from .test_physics_import import (
    _import_model_for_physics,
    _mesh_object_count,
    _rel_label,
    _run_physics_import,
    _scratch_name,
    _summarize_failures,
    _validate_imported_scene,
)

CATEGORY = "physics/roundtrip"

GEOM_FRAC_TOL = 0.03
VOLUME_FRAC_TOL = 0.10
ROUNDTRIP_CONFIG_KEYS = (
    "motion_type",
    "mass",
    "allowed_penetration_depth",
    "friction",
    "restitution",
    "quality_type",
    "process_contact_callback_delay",
    "deactivation_class",
    "deactivation_integrate_counter",
    "linear_damping",
    "angular_damping",
    "collision_filter_info",
    "event_filter",
    "user_filter",
    "center_of_mass_override",
    "shape_radius",
)


def _is_world_objects_asset(data_root: Path, physics_path: Path) -> bool:
    rel_parts = {part.lower() for part in physics_path.relative_to(data_root / "art").parts}
    return "world_objects" in rel_parts


def _roundtrip_assets(ctx):
    from framework.assets import find_physics

    assets = find_physics(ctx.config.data_root)
    physics_assets = [asset for asset in assets if asset.category == "physics"]
    rubble_assets = [asset for asset in assets if asset.category == "rubble"]

    def _priority(asset) -> tuple[int, str]:
        return (
            0 if _is_world_objects_asset(ctx.config.data_root, asset.path) else 1,
            asset.path.as_posix(),
        )

    physics_assets.sort(key=_priority)
    rubble_assets.sort(key=_priority)

    selected = []
    index = 0
    while len(selected) < ctx.config.physics_limit and (physics_assets or rubble_assets):
        if index % 2 == 0 and physics_assets:
            selected.append(physics_assets.pop(0))
        elif index % 2 == 1 and rubble_assets:
            selected.append(rubble_assets.pop(0))
        elif physics_assets:
            selected.append(physics_assets.pop(0))
        elif rubble_assets:
            selected.append(rubble_assets.pop(0))
        index += 1
    return selected


def _run_physics_export(output_path: Path):
    import bpy  # type: ignore

    return bpy.ops.dow2.export_physics_hulls(filepath=str(output_path))


def _roundtrip_export_name(index: int, category: str) -> str:
    suffix = "rubble" if category == "rubble" else "static"
    return f"rt_{index:03d}_{suffix}.hkx"


def _bbox(vertices: list[list[float]]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    for vertex in vertices:
        for axis in range(3):
            mins[axis] = min(mins[axis], float(vertex[axis]))
            maxs[axis] = max(maxs[axis], float(vertex[axis]))
    return (tuple(mins), tuple(maxs))


def _centroid(vertices: list[list[float]]) -> tuple[float, float, float]:
    count = max(len(vertices), 1)
    accum = [0.0, 0.0, 0.0]
    for vertex in vertices:
        for axis in range(3):
            accum[axis] += float(vertex[axis])
    return (accum[0] / count, accum[1] / count, accum[2] / count)


def _extents(bounds: tuple[tuple[float, float, float], tuple[float, float, float]]) -> tuple[float, float, float]:
    mins, maxs = bounds
    return tuple(float(maxs[axis] - mins[axis]) for axis in range(3))


def _diag(extents: tuple[float, float, float]) -> float:
    return math.sqrt(sum(component * component for component in extents))


def _bbox_volume(extents: tuple[float, float, float]) -> float:
    return max(extents[0], 0.0) * max(extents[1], 0.0) * max(extents[2], 0.0)


def _scene_body_map(scene_data) -> dict[tuple[str, int, str], dict]:
    mapped: dict[tuple[str, int, str], dict] = {}
    for rigid_body in scene_data.rigid_bodies:
        key = (rigid_body.state_name, rigid_body.lod_level, rigid_body.name)
        bounds = _bbox(rigid_body.vertices)
        extents = _extents(bounds)
        mapped[key] = {
            "motion_type": rigid_body.motion_type,
            "config": dict(rigid_body.export_config),
            "centroid": _centroid(rigid_body.vertices),
            "bbox_min": bounds[0],
            "bbox_max": bounds[1],
            "extents": extents,
            "diag": _diag(extents),
            "bbox_volume": _bbox_volume(extents),
            "vertex_count": len(rigid_body.vertices),
            "position": tuple(float(value) for value in rigid_body.position[:3]) if rigid_body.position else None,
            "rotation": tuple(float(value) for value in rigid_body.rotation[:4]) if rigid_body.rotation else None,
        }
    return mapped


def _normalize_body_map_states(body_map: dict[tuple[str, int, str], dict]) -> dict[tuple[str, int, str], dict]:
    states = {state_name for state_name, _lod_level, _name in body_map}
    damaged_states = sorted(state_name for state_name in states if state_name != "healthy")
    if len(damaged_states) != 1:
        return body_map

    authored_damage_state = damaged_states[0]
    normalized = {}
    for (state_name, lod_level, name), payload in body_map.items():
        normalized_state = "healthy" if state_name == "healthy" else authored_damage_state
        normalized[(normalized_state, lod_level, name)] = payload
    return normalized


def _compare_config(before: dict, after: dict) -> list[str]:
    problems: list[str] = []
    for key in ROUNDTRIP_CONFIG_KEYS:
        if key not in before:
            continue
        expected = before[key]
        actual = after.get(key)
        if isinstance(expected, list):
            if not isinstance(actual, list) or len(actual) < len(expected):
                problems.append(f"config {key} missing")
                continue
            for index, (got_value, expected_value) in enumerate(zip(actual, expected)):
                if abs(float(got_value) - float(expected_value)) > 1.0e-4:
                    problems.append(
                        f"config {key}[{index}] {float(got_value):.5f} != {float(expected_value):.5f}"
                    )
                    break
            continue
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            if actual is None:
                problems.append(f"config {key} missing")
                continue
            expected_value = float(expected)
            actual_value = float(actual)
            limit = max(1.0e-4, max(abs(expected_value), abs(actual_value)) * 1.0e-6)
            if abs(actual_value - expected_value) > limit:
                problems.append(f"config {key} {actual_value:.5f} != {expected_value:.5f}")
            continue
        if actual != expected:
            problems.append(f"config {key} {actual!r} != {expected!r}")
    return problems


def _compare_scene_maps(before: dict, after: dict) -> list[str]:
    problems: list[str] = []
    matched_pairs: list[tuple[tuple[str, int, str], tuple[str, int, str]]] = []
    before_only = set(before) - set(after)
    after_only = set(after) - set(before)

    for key in sorted(set(before) & set(after)):
        matched_pairs.append((key, key))

    for before_key in sorted(before_only):
        before_state, before_lod, before_name = before_key
        if before_state == "healthy":
            continue
        match = next(
            (
                after_key
                for after_key in sorted(after_only)
                if after_key[1] == before_lod and after_key[2] == before_name and after_key[0] != "healthy"
            ),
            None,
        )
        if match is None:
            continue
        matched_pairs.append((before_key, match))
        before_only.discard(before_key)
        after_only.discard(match)

    if before_only:
        problems.append(f"missing bodies {sorted(before_only)[:4]}")
    if after_only:
        problems.append(f"extra bodies {sorted(after_only)[:4]}")
    if problems:
        return problems

    for before_key, after_key in matched_pairs:
        expected = before[before_key]
        actual = after[after_key]
        key = before_key
        if actual["motion_type"] != expected["motion_type"]:
            problems.append(f"{key}: motion {actual['motion_type']!r} != {expected['motion_type']!r}")

        problems.extend(f"{key}: {msg}" for msg in _compare_config(expected["config"], actual["config"]))

        diag = max(expected["diag"], 1.0)
        geom_limit = max(1.0e-4, diag * GEOM_FRAC_TOL)
        centroid_limit = max(0.25, diag * 0.05)
        transform_limit = max(1.0e-4, diag * 1.0e-6)

        if expected["position"] is not None and actual["position"] is not None:
            for axis, (got_value, expected_value) in enumerate(zip(actual["position"], expected["position"])):
                if abs(float(got_value) - float(expected_value)) > transform_limit:
                    problems.append(
                        f"{key}: position[{axis}] {float(got_value):.5f} != {float(expected_value):.5f}"
                    )
        if expected["rotation"] is not None and actual["rotation"] is not None:
            for axis, (got_value, expected_value) in enumerate(zip(actual["rotation"], expected["rotation"])):
                if abs(float(got_value) - float(expected_value)) > 1.0e-5:
                    problems.append(
                        f"{key}: rotation[{axis}] {float(got_value):.5f} != {float(expected_value):.5f}"
                    )

        for axis, (got_value, expected_value) in enumerate(zip(actual["centroid"], expected["centroid"])):
            if abs(float(got_value) - float(expected_value)) > centroid_limit:
                problems.append(
                    f"{key}: centroid[{axis}] {float(got_value):.5f} != {float(expected_value):.5f}"
                )
        for label in ("bbox_min", "bbox_max", "extents"):
            for axis, (got_value, expected_value) in enumerate(zip(actual[label], expected[label])):
                if abs(float(got_value) - float(expected_value)) > geom_limit:
                    problems.append(
                        f"{key}: {label}[{axis}] {float(got_value):.5f} != {float(expected_value):.5f}"
                    )
        expected_volume = max(expected["bbox_volume"], 1.0e-6)
        volume_delta = abs(float(actual["bbox_volume"]) - float(expected["bbox_volume"])) / expected_volume
        if volume_delta > VOLUME_FRAC_TOL:
            problems.append(
                f"{key}: bbox_volume {float(actual['bbox_volume']):.5f} != {float(expected['bbox_volume']):.5f}"
            )
    return problems


def _roundtrip_one_asset(ctx, asset, scratch: Path, index: int = 0) -> list[str]:
    from framework import blender_env

    from dow2_tools.physics import importer  # type: ignore

    label = _rel_label(ctx, asset.path)
    problems: list[str] = []

    blender_env.reset_scene()
    model_result = _import_model_for_physics(asset.model_path)
    if "FINISHED" not in model_result:
        return [f"{label}: model import failed ({model_result})"]
    if _mesh_object_count() == 0:
        return [f"{label}: sibling model import produced no non-hull meshes"]

    source_scene = importer.load_physics_scene(str(asset.path))
    source_map = _normalize_body_map_states(_scene_body_map(source_scene))

    result = _run_physics_import(asset.path)
    if "FINISHED" not in result:
        return [f"{label}: source physics import failed ({result})"]

    import_problems = _validate_imported_scene(source_scene)
    if import_problems:
        problems.append(f"{label}: source import validation: {_summarize_failures(import_problems)}")

    export_path = scratch / _roundtrip_export_name(index, asset.category)
    export_result = _run_physics_export(export_path)
    if "FINISHED" not in export_result:
        return problems + [f"{label}: export failed ({export_result})"]
    if not export_path.is_file():
        return problems + [f"{label}: export did not create HKX output"]
    if not export_path.with_suffix(".json").is_file():
        return problems + [f"{label}: export did not create JSON sidecar"]

    exported_scene = importer.load_physics_scene(str(export_path))
    exported_map = _normalize_body_map_states(_scene_body_map(exported_scene))
    problems.extend(f"{label}: {msg}" for msg in _compare_scene_maps(source_map, exported_map))

    blender_env.reset_scene()
    result = _run_physics_import(export_path)
    if "FINISHED" not in result:
        problems.append(f"{label}: exported HKX re-import failed ({result})")
        return problems
    problems.extend(
        f"{label}: exported import validation: {msg}"
        for msg in _validate_imported_scene(exported_scene)
    )
    return problems


def test_single_world_object_physics_export_roundtrip(ctx):
    """P-E1: one world_objects static/rubble-authored asset roundtrips through addon operators."""
    from framework import fixtures

    ctx.require_data()
    assets = _roundtrip_assets(ctx)
    if not assets:
        ctx.skip(f"no exact-paired physics assets discovered under {ctx.config.data_root / 'art'}")

    world_assets = [asset for asset in assets if _is_world_objects_asset(ctx.config.data_root, asset.path)]
    asset = world_assets[0] if world_assets else assets[0]

    with fixtures.scratch_dir(ctx.config, "physics_roundtrip_single") as scratch:
        problems = _roundtrip_one_asset(ctx, asset, scratch)
    if problems:
        ctx.fail(_summarize_failures(problems))


def test_world_objects_physics_roundtrip_scope(ctx):
    """P-E2: small-scope world_objects-first static+rubble roundtrip sweep."""
    from framework import fixtures

    ctx.require_data()
    assets = _roundtrip_assets(ctx)
    if not assets:
        ctx.skip(f"no exact-paired physics assets discovered under {ctx.config.data_root / 'art'}")

    failures: list[str] = []
    selected_world_objects = 0
    static_count = 0
    rubble_count = 0
    exercised = 0
    skipped_empty_models = 0

    with fixtures.scratch_dir(ctx.config, f"physics_roundtrip_scope_{ctx.config.scope}") as scratch:
        for index, asset in enumerate(assets):
            if _is_world_objects_asset(ctx.config.data_root, asset.path):
                selected_world_objects += 1
            if asset.category == "physics":
                static_count += 1
            else:
                rubble_count += 1

            asset_scratch = scratch / f"asset_{index:03d}"
            asset_scratch.mkdir(parents=True, exist_ok=True)
            problems = _roundtrip_one_asset(ctx, asset, asset_scratch, index=index)
            if problems == [f"{_rel_label(ctx, asset.path)}: sibling model import produced no non-hull meshes"]:
                skipped_empty_models += 1
                continue
            exercised += 1
            if problems:
                failures.extend(problems)

    if static_count == 0 or rubble_count == 0:
        ctx.fail(
            f"scope={ctx.config.scope} cap={ctx.config.physics_limit} selected insufficient body types: "
            f"static={static_count} rubble={rubble_count}"
        )
    if selected_world_objects == 0:
        ctx.fail(f"scope={ctx.config.scope} cap={ctx.config.physics_limit}: selected no world_objects assets")
    if exercised == 0:
        ctx.fail(
            f"scope={ctx.config.scope} cap={ctx.config.physics_limit} world_objects={selected_world_objects} "
            f"static={static_count} rubble={rubble_count} skipped_empty_models={skipped_empty_models} | no usable pairs exercised"
        )
    if failures:
        ctx.fail(
            f"scope={ctx.config.scope} cap={ctx.config.physics_limit} world_objects={selected_world_objects} "
            f"static={static_count} rubble={rubble_count} exercised={exercised} "
            f"skipped_empty_models={skipped_empty_models} failures={len(failures)} | {_summarize_failures(failures)}"
        )