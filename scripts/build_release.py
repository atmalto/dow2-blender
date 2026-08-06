#!/usr/bin/env python3
"""Build an installable DoW2 Tools release zip.

The produced archive contains a single top-level ``dow2_tools/`` folder (the
Blender addon module) with the runtime source plus the compiled Havok binaries
(``havok_io_cli.exe`` + ``havok_io.dll``) that git intentionally does not track.

All development / backup / vendored folders are excluded so the zip only holds
what an end user needs to install the addon in Blender.

Usage:
    python scripts/build_release.py                 # -> dist/dow2_tools-v1.0.0.zip
    python scripts/build_release.py --output-dir X  # write the zip into X/
    python scripts/build_release.py --name my_addon # override archive base name
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
import zipfile
from pathlib import Path

# The addon module folder name (top-level folder inside the zip).
ADDON_NAME = "dow2_tools"

# Compiled binaries that must ship with the release even though git ignores them.
# Paths are relative to the addon root.
REQUIRED_BINARIES = [
    "blender_hkx/havok_io_cli.exe",
    "blender_hkx/havok_io.dll",
]

# Directories (relative to the addon root, posix style) excluded from the zip.
# ``blender_hkx`` is excluded wholesale; only REQUIRED_BINARIES are re-added.
EXCLUDE_DIRS = {
    ".git",
    ".github",
    ".venv",
    ".vscode",
    ".codewhale",
    "dist",
    "scripts",
    "working",
    "tests",
    "logs",
    "AssetCc",
    "blender_hkx",
    "blender_hkx_backup",
    "dow2_tools",  # nested duplicate copy inside the repo
    "destruction_physics",
    "max_script",
    "material/dow2_.asm_and_.shader",
}

# File suffixes and names excluded everywhere in the tree.
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".lib", ".pdb", ".exp", ".obj", ".zip")
EXCLUDE_NAMES = {".gitignore", ".gitattributes", ".DS_Store"}


def read_version(addon_root: Path) -> str:
    """Extract the ``bl_info["version"]`` tuple from __init__.py without importing bpy."""
    init_path = addon_root / "__init__.py"
    tree = ast.parse(init_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "bl_info" for t in node.targets
        ):
            if isinstance(node.value, ast.Dict):
                for key, value in zip(node.value.keys, node.value.values):
                    if isinstance(key, ast.Constant) and key.value == "version":
                        parts = [str(ast.literal_eval(elt)) for elt in value.elts]
                        return ".".join(parts)
    return "0.0.0"


def _is_excluded_dir(rel_posix: str) -> bool:
    if rel_posix in EXCLUDE_DIRS:
        return True
    return any(rel_posix.startswith(f"{prefix}/") for prefix in EXCLUDE_DIRS)


def _is_excluded_file(name: str) -> bool:
    if name in EXCLUDE_NAMES:
        return True
    return name.lower().endswith(EXCLUDE_SUFFIXES)


def collect_files(addon_root: Path) -> list[Path]:
    """Return the list of source files to include (binaries handled separately)."""
    collected: list[Path] = []
    for current_dir, dir_names, file_names in os.walk(addon_root):
        rel_dir = Path(current_dir).relative_to(addon_root).as_posix()

        # Prune excluded and __pycache__ directories in place.
        kept = []
        for d in dir_names:
            child_rel = d if rel_dir == "." else f"{rel_dir}/{d}"
            if d == "__pycache__" or _is_excluded_dir(child_rel):
                continue
            kept.append(d)
        dir_names[:] = kept

        for file_name in file_names:
            if _is_excluded_file(file_name):
                continue
            collected.append(Path(current_dir) / file_name)
    return collected


def build_release(addon_root: Path, output_dir: Path, base_name: str) -> Path:
    version = read_version(addon_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{base_name}-v{version}.zip"

    # Verify required binaries exist before building.
    missing = [b for b in REQUIRED_BINARIES if not (addon_root / b).is_file()]
    if missing:
        joined = "\n  - ".join(missing)
        raise FileNotFoundError(
            "Required Havok binaries are missing (build them first via "
            "blender_hkx/build_all.bat):\n  - " + joined
        )

    source_files = collect_files(addon_root)

    if zip_path.exists():
        zip_path.unlink()

    written = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in source_files:
            rel = file_path.relative_to(addon_root).as_posix()
            archive.write(file_path, f"{ADDON_NAME}/{rel}")
            written += 1
        for binary in REQUIRED_BINARIES:
            archive.write(addon_root / binary, f"{ADDON_NAME}/{binary}")
            written += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Built {zip_path}")
    print(f"  files: {written}")
    print(f"  size:  {size_mb:.2f} MB")
    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the DoW2 Tools release zip.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write the zip into (default: <addon>/dist).",
    )
    parser.add_argument(
        "--name",
        default=ADDON_NAME,
        help=f"Base name for the archive (default: {ADDON_NAME}).",
    )
    args = parser.parse_args(argv)

    addon_root = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir).resolve() if args.output_dir else addon_root / "dist"

    try:
        build_release(addon_root, output_dir, args.name)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
