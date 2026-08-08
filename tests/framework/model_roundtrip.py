"""Shared model round-trip driver (runs inside Blender).

Rebuilds a model from a ``test_data`` seed (glb + config.json), snapshots the
source scene, exports to a temp ``.model`` with the given options, re-imports,
and snapshots again. Texture staging + scratch cleanup are handled internally.

Used by the §14 round-trip and the MODEL-export toggle tests so they share the
exact same build/export/import path and the ``model_snapshot`` comparator.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import blender_env, fixtures, model_snapshot


def load_seed_config(test_data_dir: Path, seed: str) -> dict | None:
    path = test_data_dir / seed / "config.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run(config, seed: str, data: dict, **export_opts):
    """Rebuild -> snapshot -> export(**opts) -> reimport -> snapshot.

    Returns ``(before, after, error)``. ``after`` is ``None`` (with a message in
    ``error``) if export or re-import fails; ``error`` is ``None`` on success.
    """
    seed_dir = config.test_data_dir / seed
    with fixtures.scratch_dir(config, f"rt_{seed}") as scratch:
        with fixtures.staged_textures(config, data.get("textures", {}), seed_dir):
            blender_env.reset_scene()
            blender_env.import_glb(seed_dir / data["glb"])
            if blender_env.apply_config_to_scene(data) == 0:
                return None, None, "no meshes configured from glb"

            before = model_snapshot.capture()

            out_model = scratch / f"{seed}.model"
            result = blender_env.export_model(out_model, **export_opts)
            if "FINISHED" not in result or not out_model.is_file():
                return before, None, f"export failed ({result})"

            blender_env.reset_scene()
            imported = blender_env.import_model(out_model)
            if "FINISHED" not in imported:
                return before, None, f"re-import failed ({imported})"

            after = model_snapshot.capture()
    return before, after, None
