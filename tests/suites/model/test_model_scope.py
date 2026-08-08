"""Scoped MODEL coverage over real assets from DATA_ROOT/art.

These tests are the §13 sweep layer: discover real .model files under the
configured data root, cap by --scope, and exercise import/export/re-import over
that set. The fixed seed tests remain for precise golden checks; this file is
for breadth across the actual art tree.
"""

from __future__ import annotations

import hashlib
import re

CATEGORY = "model/scope"


def _art_models(ctx):
    from framework.assets import find_models

    return find_models(ctx.config.data_root, ctx.config.model_limit)


def _rel_label(ctx, path) -> str:
    try:
        return path.relative_to(ctx.config.data_root).as_posix()
    except ValueError:
        return path.as_posix()


def _scratch_name(index: int, label: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:10]
    return f"{index:03d}_{digest}_{safe[-48:]}"


def _import_source_model(blender_env, model_path):
    return blender_env.import_model(
        model_path,
        import_simbox=False,
        import_coverbox=False,
        import_bounding_volumes=False,
    )


def _snapshot_has_meshes(snapshot: dict) -> bool:
    return any(group.get("positions") for group in snapshot.get("meshes", {}).values())


def _format_failures(title: str, failures: list[str], limit: int = 25) -> str:
    shown = failures[:limit]
    suffix = "" if len(failures) <= limit else f" | ... {len(failures) - limit} more"
    return f"{title}: " + " | ".join(shown) + suffix


def _scope_compare(model_snapshot, before: dict, after: dict) -> tuple[list[tuple[str, str]], int]:
    """Compare snapshots for broad asset sweeps.

    Golden seed tests stay exact. For the wide /art sweep, tolerate tiny triangle
    count drift from degenerate/triangulated source faces while still failing
    material, bone, marker, vertex-position, normal, and weight problems.
    """
    import re

    problems: list[tuple[str, str]] = []
    tolerated = 0
    tri_re = re.compile(r"triangles (\d+) != (\d+)$")
    for category, message in model_snapshot.compare(before, after):
        match = tri_re.search(message)
        if category == "model_mesh" and match:
            got, expected = int(match.group(1)), int(match.group(2))
            delta = abs(got - expected)
            if delta <= 2 and delta / max(expected, 1) <= 0.001:
                tolerated += 1
                continue
        problems.append((category, message))
    return problems, tolerated


def test_art_scope_imports(ctx):
    """§13/M-I scope: import real DATA_ROOT/art .model files up to --scope cap."""
    from framework import blender_env, model_snapshot

    ctx.require_data()
    assets = _art_models(ctx)
    if not assets:
        ctx.skip(f"no .model assets discovered under {ctx.config.data_root / 'art'}")

    failures: list[str] = []
    category_counts: dict[str, int] = {}
    mesh_models = 0

    for asset in assets:
        label = _rel_label(ctx, asset.path)
        category_counts[asset.category] = category_counts.get(asset.category, 0) + 1
        blender_env.reset_scene()
        result = _import_source_model(blender_env, asset.path)
        if "FINISHED" not in result:
            failures.append(f"{label}: import returned {result}")
            continue
        if _snapshot_has_meshes(model_snapshot.capture()):
            mesh_models += 1

    print(
        f"[model/scope] imported={len(assets) - len(failures)}/{len(assets)} "
        f"mesh_models={mesh_models} categories={category_counts} scope={ctx.config.scope}"
    )

    if mesh_models == 0:
        failures.append("scope imported no mesh-bearing models")
    if failures:
        ctx.fail(_format_failures("art scope import failures", failures))


def test_art_scope_roundtrip(ctx):
    """§13/M-E scope: import -> export -> import real DATA_ROOT/art mesh models."""
    from framework import blender_env, fixtures, model_snapshot

    ctx.require_data()
    assets = _art_models(ctx)
    if not assets:
        ctx.skip(f"no .model assets discovered under {ctx.config.data_root / 'art'}")

    failures: list[str] = []
    import_only = 0
    roundtripped = 0
    tolerated_triangle_drifts = 0

    with fixtures.scratch_dir(ctx.config, f"model_scope_roundtrip_{ctx.config.scope}") as scratch:
        for index, asset in enumerate(assets):
            label = _rel_label(ctx, asset.path)
            blender_env.reset_scene()
            result = _import_source_model(blender_env, asset.path)
            if "FINISHED" not in result:
                failures.append(f"{label}: source import returned {result}")
                continue

            before = model_snapshot.capture()
            if not _snapshot_has_meshes(before):
                import_only += 1
                continue

            out_model = scratch / f"{_scratch_name(index, label)}.model"
            try:
                result = blender_env.export_model(out_model)
            except Exception as exc:
                failures.append(f"{label}: export raised {type(exc).__name__}: {exc}")
                continue
            if "FINISHED" not in result or not out_model.is_file():
                failures.append(f"{label}: export returned {result}")
                continue

            blender_env.reset_scene()
            result = blender_env.import_model(
                out_model,
                import_simbox=False,
                import_coverbox=False,
                import_bounding_volumes=False,
            )
            if "FINISHED" not in result:
                failures.append(f"{label}: re-import returned {result}")
                continue

            after = model_snapshot.capture()
            problems, tolerated = _scope_compare(model_snapshot, before, after)
            tolerated_triangle_drifts += tolerated
            if problems:
                first = "; ".join(f"[{category}] {message}" for category, message in problems[:5])
                extra = "" if len(problems) <= 5 else f"; ... {len(problems) - 5} more"
                failures.append(f"{label}: {first}{extra}")
                continue

            roundtripped += 1

    print(
        f"[model/scope] roundtripped={roundtripped} import_only_no_mesh={import_only} "
        f"tolerated_triangle_drifts={tolerated_triangle_drifts} failures={len(failures)} "
        f"scope={ctx.config.scope} cap={ctx.config.model_limit}"
    )

    if roundtripped == 0:
        failures.append("scope round-tripped no mesh-bearing models")
    if failures:
        ctx.fail(_format_failures("art scope roundtrip failures", failures))
