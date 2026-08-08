"""Fixture management and temporary asset staging (scaffold ; stubs).

Two fixture kinds (see working/test_plan.md):
  1. Permanent, small, checked-in fixtures under ``config.fixtures_dir``
     (rigged/textured .glb + material config JSON).
  2. Runtime scratch: generate a .model / stage textures inside DATA_ROOT/art,
     then clean everything up.

These are stubs; bodies are filled in when suites are implemented.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Iterator

from .config import Config


def test_data(config: Config, *parts: str) -> Path:
    """Path to a permanent checked-in test-data asset."""
    return config.test_data_dir.joinpath(*parts)


@contextlib.contextmanager
def scratch_dir(config: Config, name: str) -> Iterator[Path]:
    """Yield a clean per-test scratch directory, removed afterwards."""
    import shutil

    target = config.scratch_dir / name
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    try:
        yield target
    finally:
        shutil.rmtree(target, ignore_errors=True)


@contextlib.contextmanager
def staged_textures(
    config: Config,
    texture_map: dict[str, str],
    test_data_dir: Path,
) -> Iterator[Path]:
    """Ensure each referenced texture exists under ``DATA_ROOT`` for a round-trip.

    ``texture_map`` is ``config.json``'s ``textures`` block:
    ``{data_root_relative_posix: test_data_relative_posix}``. Any texture that is
    *missing* under ``DATA_ROOT`` is copied there from the portable ``test_data``
    copy at its original relative path (so the exporter/importer resolve the exact
    same mod-root-relative paths as the original model). Only files/dirs this
    helper creates are removed afterwards; pre-existing originals are untouched.

    Yields ``DATA_ROOT``.
    """
    data_root = config.data_root
    created_files: list[Path] = []
    created_dirs: list[Path] = []

    def _record_new_dirs(target_dir: Path) -> None:
        chain: list[Path] = []
        cur = target_dir
        while cur != data_root and data_root in cur.parents and not cur.exists():
            chain.append(cur)
            cur = cur.parent
        # create shallowest-first; record deepest-first for later removal
        for d in reversed(chain):
            d.mkdir(parents=True, exist_ok=True)
            created_dirs.append(d)

    try:
        for dataroot_rel, local_rel in texture_map.items():
            dst = data_root / dataroot_rel
            if dst.exists():
                continue
            src = test_data_dir / local_rel
            if not src.is_file():
                continue
            _record_new_dirs(dst.parent)
            import shutil

            shutil.copy2(src, dst)
            created_files.append(dst)
        yield data_root
    finally:
        for f in created_files:
            with contextlib.suppress(OSError):
                f.unlink()
        for d in sorted(created_dirs, key=lambda p: len(p.parts), reverse=True):
            with contextlib.suppress(OSError):
                d.rmdir()  # only succeeds if empty
