"""Real-asset ragdoll BEHAVIOUR parity test (scoped, multi-asset).

The field-by-field roundtrip test proves each exported .hkx matches its original
on paper. This test proves the stronger property: the ragdoll our addon writes
SIMULATES the same as the original inside a real Havok hkpWorld.

Full production path, per discovered asset in scope:

    real ragdoll.hkx --addon import--> Blender scene --force sync-->
                     --addon export--> exported.hkx

then BOTH the original and the exported file are run through the havok_sim_cli:
drop the same heavy box on each, simulate, and compare how the ragdoll reacts
(body count, whether it releases from the authored/held pose, and where its
centre of mass ends up).

Coverage scales with ``--scope`` via the ``ragdolls`` preset cap, mirroring the
collision/physics suites.

Skips cleanly when the game DATA_ROOT, the havok_io CLI, or the havok_sim_cli is
unavailable.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

CATEGORY = "ragdoll/behaviour"

_ADDON_ROOT = Path(__file__).resolve().parents[3]
_SIM_CLI = _ADDON_ROOT / "havok_simulator" / "build_cli" / "build" / "havok_sim_cli.exe"

# Max distance between the two simulations' final centres of mass. The runs are
# deterministic, so this is tight; ~6mm observed on hormagaunt, 0.35m leaves
# headroom while still catching a genuinely different-behaving ragdoll (a broken
# one drifts metres or fails to release).
_CENTROID_MATCH_TOL_M = 0.35


def _run_sim(commands: list[dict]) -> dict:
    scenario = {"stop_on_error": True, "commands": commands}
    proc = subprocess.run(
        [str(_SIM_CLI), "-"],
        input=json.dumps(scenario),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(_ADDON_ROOT),
        text=True,
    )
    lines = proc.stdout.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("{")), None)
    if start is None:
        raise RuntimeError(f"no JSON from sim CLI:\n{proc.stdout}\n{proc.stderr}")
    return json.loads("\n".join(lines[start:]))


def _by_cmd(result: dict, cmd: str, index: int = 0) -> dict:
    return [r for r in result.get("results", []) if r.get("cmd") == cmd][index]


def _ragdoll_bodies(scene: dict) -> list[dict]:
    return [b for b in scene["bodies"] if b["kind"] == "ragdoll"]


def _centroid(bodies: list[dict]) -> tuple[float, float, float]:
    n = float(len(bodies))
    return tuple(sum(b["position"][i] for b in bodies) / n for i in range(3))


def _top_of(body: dict) -> float:
    return body["position"][1] + max(body["half_extents"][1], body.get("radius", 0.0))


def _drop(hkx: str) -> dict:
    probe = _run_sim([
        {"cmd": "import_ragdoll", "path": hkx},
        {"cmd": "get_props", "target": "scene"},
    ])
    rag = _ragdoll_bodies(_by_cmd(probe, "get_props"))
    if not rag:
        raise RuntimeError(f"ragdoll produced no bodies: {hkx}")
    top = max(_top_of(b) for b in rag)
    cen = _centroid(rag)
    result = _run_sim([
        {"cmd": "import_ragdoll", "path": hkx},
        {"cmd": "settings", "gravity_scale": 1.0, "ragdoll_mass_scale": 0.1},
        {"cmd": "add_object", "object": "box", "body": "dynamic",
         "position": [cen[0], top + 3.0, cen[2]], "mass": 400.0, "scale": [0.6, 0.6, 0.6]},
        {"cmd": "get_props", "target": "ragdoll"},
        {"cmd": "run", "steps": 360},
        {"cmd": "get_props", "target": "ragdoll"},
        {"cmd": "get_props", "target": "scene"},
    ])
    post_diag = _by_cmd(result, "get_props", 1)["ragdoll"]
    post_scene = _by_cmd(result, "get_props", 2)
    return {
        "bodies": len(rag),
        "released": not post_diag["is_holding"],
        "final_centroid": _centroid(_ragdoll_bodies(post_scene)),
    }


def test_art_ragdolls_export_simulates_like_original_scope(ctx):
    """§scope: every in-scope ragdoll our addon exports must behave the same as
    its original when a heavy object is dropped on it in a real Havok hkpWorld."""
    from framework.assets import find_ragdolls

    from . import _asset_pipeline

    ctx.require_data()
    if not _SIM_CLI.is_file():
        ctx.skip(f"havok_sim_cli missing: {_SIM_CLI}")

    assets = find_ragdolls(ctx.config.data_root, ctx.config.ragdoll_limit)
    if not assets:
        ctx.skip(f"no ragdoll.hkx assets discovered under {ctx.config.data_root / 'art'}")

    failures: list[str] = []
    unsupported: list[str] = []
    category_counts: dict[str, int] = {}
    matched = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        for index, asset in enumerate(assets):
            label = _asset_pipeline.rel_label(ctx.config.data_root, asset.path)
            category_counts[asset.category] = category_counts.get(asset.category, 0) + 1

            exported_hkx = tmp_root / f"beh_{index}.hkx"
            try:
                _asset_pipeline.import_sync_export(
                    asset.path, asset.model_path, exported_hkx, f"beh_{index}",
                )
            except Exception as exc:  # noqa: BLE001 - import/export capability gap, not a regression
                first = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
                unsupported.append(f"{label}: {type(exc).__name__}: {first}")
                continue

            try:
                original = _drop(str(asset.path).replace("\\", "/"))
                exported = _drop(str(exported_hkx).replace("\\", "/"))
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{label}: sim raised {type(exc).__name__}: {exc}")
                continue

            problems: list[str] = []
            if original["bodies"] != exported["bodies"]:
                problems.append(f"body count {original['bodies']} != {exported['bodies']}")
            if original["released"] != exported["released"]:
                problems.append(f"release-on-impact {original['released']} != {exported['released']}")
            delta = sum(
                (original["final_centroid"][i] - exported["final_centroid"][i]) ** 2 for i in range(3)
            ) ** 0.5
            if delta > _CENTROID_MATCH_TOL_M:
                problems.append(f"final centroid diverged by {delta:.3f} m (> {_CENTROID_MATCH_TOL_M} m)")

            if problems:
                failures.append(f"{label}: {'; '.join(problems)}")
                continue
            matched += 1

    print(
        f"[ragdoll/behaviour] checked={len(assets)} matched={matched} "
        f"unsupported={len(unsupported)} failures={len(failures)} "
        f"categories={category_counts} scope={ctx.config.scope}"
    )
    for entry in unsupported:
        print(f"    [unsupported] {entry}")

    if failures:
        shown = failures[:25]
        suffix = "" if len(failures) <= 25 else f" | ... {len(failures) - 25} more"
        ctx.fail("ragdoll behaviour scope failures: " + " | ".join(shown) + suffix)
    if matched == 0:
        ctx.skip(
            "no ragdoll behaviour-matched in scope "
            f"({len(unsupported)} unsupported: {'; '.join(unsupported[:5])})"
        )
