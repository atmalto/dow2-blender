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
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# The addon module folder name (top-level folder inside the zip).
ADDON_NAME = "dow2_tools"
SIMULATOR_NAME = "havok-simulator"
SIMULATOR_VERSION = "1.0.0"

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
    "havok_simulator",
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


def build_addon_release(addon_root: Path, output_dir: Path, base_name: str) -> Path:
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


def _find_bash_executable() -> str:
    if os.name != "nt":
        bash_path = shutil.which("bash")
        if bash_path:
            return bash_path
        raise RuntimeError("Could not find 'bash' in PATH.")

    preferred_candidates = [
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\msys64\usr\bin\bash.exe",
    ]
    rejected_markers = (r"\system32\bash.exe", r"\windowsapps\bash.exe")

    for candidate in preferred_candidates:
        if Path(candidate).is_file():
            return candidate

    for command_name in ("bash.exe", "bash"):
        resolved = shutil.which(command_name)
        if not resolved:
            continue
        lowered = resolved.lower()
        if any(marker in lowered for marker in rejected_markers):
            continue
        return resolved

    raise RuntimeError(
        "Could not find a Git Bash or MSYS bash executable. Install Git for Windows or MSYS2, or add its bash.exe to PATH."
    )


def _run_build_command(command: list[str], cwd: Path) -> None:
    actual_command = list(command)

    if actual_command and actual_command[0] == "bash":
        actual_command[0] = _find_bash_executable()

    try:
        subprocess.run(actual_command, cwd=str(cwd), check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing build dependency: {actual_command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        joined = " ".join(actual_command)
        raise RuntimeError(f"Build command failed in {cwd}: {joined}") from exc


def _collect_simulator_release_files(simulator_root: Path) -> dict[str, Path]:
    release_dirs = [simulator_root / "build_vs2008" / "release"]
    collected: dict[str, Path] = {}

    for release_dir in release_dirs:
        if not release_dir.is_dir():
            raise FileNotFoundError(f"Missing simulator release directory: {release_dir}")

        for pattern in ("*.exe", "*.dll"):
            for file_path in sorted(release_dir.glob(pattern)):
                existing = collected.get(file_path.name)
                if existing is None:
                    collected[file_path.name] = file_path
                    continue

                if existing.read_bytes() != file_path.read_bytes():
                    raise RuntimeError(
                        f"Conflicting simulator release files share the same name but differ: {existing} and {file_path}"
                    )

    if not collected:
        raise FileNotFoundError("No simulator release files were found after building.")

    return collected


def _copy_tree(source_dir: Path, destination_dir: Path) -> int:
    copied = 0
    for source_path in sorted(source_dir.rglob("*")):
        if source_path.is_dir():
            continue
        relative_path = source_path.relative_to(source_dir)
        target_path = destination_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied += 1
    return copied


def build_simulator_release(addon_root: Path, output_dir: Path, base_name: str, version: str) -> Path:
    simulator_root = addon_root / "havok_simulator"
    simulator_media_dir = simulator_root / "media"
    guide_root = addon_root / "working" / "guide"
    guide_pdf = guide_root / "Havok Simulator Guide.pdf"
    stage_name = f"{base_name}-{version}"
    zip_path = output_dir / f"{stage_name}.zip"

    output_dir.mkdir(parents=True, exist_ok=True)

    _run_build_command(["bash", "-lc", "./build.sh release"], simulator_root)

    release_files = _collect_simulator_release_files(simulator_root)
    if not simulator_media_dir.is_dir():
        raise FileNotFoundError(f"Missing simulator media directory: {simulator_media_dir}")
    if not guide_pdf.is_file():
        raise FileNotFoundError(f"Missing simulator guide PDF: {guide_pdf}")

    if zip_path.exists():
        zip_path.unlink()

    with tempfile.TemporaryDirectory(prefix="havok-simulator-", dir=output_dir) as temp_dir:
        stage_root = Path(temp_dir) / stage_name
        stage_root.mkdir(parents=True, exist_ok=True)
        simulator_media_root = stage_root / "media"
        docs_root = stage_root / "guide"

        for file_name, source_path in release_files.items():
            shutil.copy2(source_path, stage_root / file_name)

        copied_simulator_media_files = _copy_tree(simulator_media_dir, simulator_media_root)

        docs_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(guide_pdf, docs_root / guide_pdf.name)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for staged_file in sorted(stage_root.rglob("*")):
                if staged_file.is_dir():
                    continue
                archive.write(staged_file, f"{stage_name}/{staged_file.relative_to(stage_root).as_posix()}")

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Built {zip_path}")
    print(f"  files: {len(release_files) + copied_simulator_media_files + 1}")
    print(f"  size:  {size_mb:.2f} MB")
    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the DoW2 Tools addon or Havok Simulator release zip.")
    parser.add_argument(
        "--target",
        choices=("addon", "simulator"),
        default="addon",
        help="Select which release package to build.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write the zip into (default: <addon>/dist).",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Override the archive base name.",
    )
    parser.add_argument(
        "--sim-version",
        default=SIMULATOR_VERSION,
        help=f"Simulator package version (default: {SIMULATOR_VERSION}).",
    )
    args = parser.parse_args(argv)

    addon_root = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir).resolve() if args.output_dir else addon_root / "dist"

    try:
        if args.target == "addon":
            base_name = args.name or ADDON_NAME
            build_addon_release(addon_root, output_dir, base_name)
        else:
            base_name = args.name or SIMULATOR_NAME
            build_simulator_release(addon_root, output_dir, base_name, args.sim_version)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
