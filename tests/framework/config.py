"""Configuration loading for the test suite.

Reads ``tests/config.toml`` (falling back to ``config.example.toml`` with a
warning). Uses the stdlib ``tomllib`` shipped with Blender 4.3's Python 3.11.
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PHYSICS_LIMITS = {
    "small": 10,
    "medium": 50,
    "large": 100,
}


@dataclass(frozen=True)
class Config:
    """Resolved, absolute test-suite configuration."""

    blender_root: Path
    data_root: Path
    scratch_dir: Path
    log_dir: Path
    test_data_dir: Path
    continue_on_error: bool
    scope: str
    model_limit: int
    animation_limit: int
    physics_limit: int
    source: Path  # which toml file was loaded

    @property
    def data_root_available(self) -> bool:
        return self.data_root.is_dir()

    @property
    def blender_exe(self) -> Path:
        # Windows layout: <blender_root>/blender.exe
        return self.blender_root / "blender.exe"


def _resolve(base: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base / p)


def load_config(explicit_path: Path | None = None, scope: str | None = None) -> Config:
    """Load the test configuration.

    Search order: ``explicit_path`` -> ``tests/config.toml`` -> ``config.example.toml``.
    ``scope`` overrides ``[scope].default`` when provided.
    """
    candidates = []
    if explicit_path is not None:
        candidates.append(Path(explicit_path))
    candidates.append(TESTS_ROOT / "config.toml")
    example = TESTS_ROOT / "config.example.toml"
    candidates.append(example)

    config_path = next((c for c in candidates if c.is_file()), None)
    if config_path is None:
        raise FileNotFoundError(f"No test config found (looked for {candidates}).")

    if config_path == example:
        print(
            "[config] WARNING: using config.example.toml ; copy it to config.toml "
            "and set your machine paths.",
            file=sys.stderr,
        )

    with config_path.open("rb") as fh:
        data = tomllib.load(fh)

    paths = data.get("paths", {})
    run = data.get("run", {})
    test_data = data.get("test_data", {})
    scope_cfg = data.get("scope", {})

    presets = scope_cfg.get("presets", {})
    scope_name = scope or scope_cfg.get("default", "small")
    preset = presets.get(scope_name)
    if preset is None:
        raise ValueError(
            f"Unknown scope '{scope_name}'. Available: {sorted(presets) or '(none)'}"
        )

    return Config(
        blender_root=Path(paths.get("blender", "")),
        data_root=Path(paths.get("data_root", "")),
        scratch_dir=_resolve(TESTS_ROOT, run.get("scratch_dir", "output/scratch")),
        log_dir=_resolve(TESTS_ROOT, run.get("log_dir", "output/logs")),
        test_data_dir=_resolve(TESTS_ROOT, test_data.get("dir", "test_data")),
        continue_on_error=bool(run.get("continue_on_error", True)),
        scope=scope_name,
        model_limit=int(preset.get("models", 0)),
        animation_limit=int(preset.get("animations", 0)),
        physics_limit=int(preset.get("physics", DEFAULT_PHYSICS_LIMITS.get(scope_name, 0))),
        source=config_path,
    )
