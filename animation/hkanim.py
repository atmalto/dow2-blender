from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field


HKANIM_EXTENSION = ".hkanim"
HKX_EXTENSION = ".hkx"
ANIM_EXTENSION = ".anim"


class HkAnimToolError(RuntimeError):
    """Raised when the native hkanim pack/unpack tool fails."""


@dataclass
class BatchAnimationFiles:
    files: list[str]
    unpack_root: str | None = None
    unpacked_hkanim_paths: list[str] = field(default_factory=list)
    directory_modes: dict[str, str] = field(default_factory=dict)

    def cleanup(self) -> None:
        if self.unpack_root and os.path.isdir(self.unpack_root):
            shutil.rmtree(self.unpack_root, ignore_errors=True)


def _get_addon_path() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_hkanim_tool_path() -> str:
    return os.path.join(_get_addon_path(), "blender_hkx", "havok_io_cli.exe")


def make_unique_path(path: str) -> str:
    normalized_path = os.path.normpath(path)
    if not os.path.exists(normalized_path):
        return normalized_path

    base, extension = os.path.splitext(normalized_path)
    index = 2
    while True:
        candidate = f"{base}_{index}{extension}"
        if not os.path.exists(candidate):
            return candidate
        index += 1


def build_default_pack_output_path(input_directory: str, ensure_unique: bool = True) -> str:
    normalized_input = os.path.normpath(input_directory)
    parent_directory = os.path.dirname(normalized_input)
    base_name = os.path.basename(normalized_input.rstrip("\\/")) or "animations"
    output_path = os.path.join(parent_directory, f"{base_name}{HKANIM_EXTENSION}")
    return make_unique_path(output_path) if ensure_unique else output_path


def build_default_unpack_directory(input_path: str, ensure_unique: bool = True) -> str:
    normalized_input = os.path.normpath(input_path)
    parent_directory = os.path.dirname(normalized_input)
    base_name = os.path.splitext(os.path.basename(normalized_input))[0] or "animations"
    output_directory = os.path.join(parent_directory, base_name)
    return make_unique_path(output_directory) if ensure_unique else output_directory


def _run_hkanim_tool(arguments: list[str], tool_path: str | None = None) -> str:
    executable = tool_path or get_hkanim_tool_path()
    if not os.path.exists(executable):
        raise HkAnimToolError(f"hkanim tool not found: {executable}")

    completed = subprocess.run(
        [executable, "hkanim", *arguments],
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    if completed.stderr.strip():
        output = f"{output}\n{completed.stderr.strip()}".strip()

    if completed.returncode != 0:
        raise HkAnimToolError(output or f"hkanim tool failed with code {completed.returncode}")

    return output


def pack_hkanim_from_directory(input_directory: str, output_path: str, tool_path: str | None = None) -> str:
    normalized_input = os.path.normpath(input_directory)
    normalized_output = os.path.normpath(output_path)
    if not os.path.isdir(normalized_input):
        raise HkAnimToolError(f"Pack input folder does not exist: {normalized_input}")

    output_directory = os.path.dirname(normalized_output)
    if output_directory:
        os.makedirs(output_directory, exist_ok=True)

    _run_hkanim_tool(["pack", normalized_input, normalized_output], tool_path=tool_path)
    if not os.path.exists(normalized_output):
        raise HkAnimToolError(f"hkanim pack did not create output file: {normalized_output}")
    return normalized_output


def unpack_hkanim_file(input_path: str, output_directory: str, tool_path: str | None = None) -> str:
    normalized_input = os.path.normpath(input_path)
    normalized_output = os.path.normpath(output_directory)
    if not os.path.isfile(normalized_input):
        raise HkAnimToolError(f"Unpack input file does not exist: {normalized_input}")

    os.makedirs(os.path.dirname(normalized_output) or normalized_output, exist_ok=True)
    _run_hkanim_tool(["unpack", normalized_input, normalized_output], tool_path=tool_path)
    if not os.path.isdir(normalized_output):
        raise HkAnimToolError(f"hkanim unpack did not create output folder: {normalized_output}")
    return normalized_output


def unpack_hkanim_next_to_source(input_path: str, tool_path: str | None = None) -> str:
    output_directory = build_default_unpack_directory(input_path, ensure_unique=True)
    return unpack_hkanim_file(input_path, output_directory, tool_path=tool_path)


def _list_sorted_files_with_extension(file_names: list[str], extension: str) -> list[str]:
    lower_extension = extension.lower()
    return sorted(
        [file_name for file_name in file_names if file_name.lower().endswith(lower_extension)],
        key=str.lower,
    )


def _select_directory_mode(file_names: list[str]) -> tuple[str | None, list[str]]:
    hkanim_files = _list_sorted_files_with_extension(file_names, HKANIM_EXTENSION)
    if hkanim_files:
        return "hkanim", hkanim_files

    anim_files = _list_sorted_files_with_extension(file_names, ANIM_EXTENSION)
    if anim_files:
        return "anim", anim_files

    hkx_files = _list_sorted_files_with_extension(file_names, HKX_EXTENSION)
    if hkx_files:
        return "hkx", hkx_files

    return None, []


def _collect_hkx_files(directory: str) -> list[str]:
    hkx_files: list[str] = []
    for root, _dirs, files in os.walk(directory):
        for file_name in sorted(files, key=str.lower):
            if file_name.lower().endswith(HKX_EXTENSION):
                hkx_files.append(os.path.join(root, file_name))
    return hkx_files


def _iter_batch_source_directories(input_directory: str) -> list[str]:
    directories = [input_directory]
    child_directories: list[str] = []
    with os.scandir(input_directory) as entries:
        for entry in entries:
            if entry.is_dir():
                child_directories.append(entry.path)
    directories.extend(sorted(child_directories, key=lambda path: os.path.basename(path).lower()))
    return directories


def _list_directory_files(directory: str) -> list[str]:
    file_names: list[str] = []
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.is_file():
                file_names.append(entry.name)
    return sorted(file_names, key=str.lower)


def collect_batch_animation_files(input_directory: str, tool_path: str | None = None) -> BatchAnimationFiles:
    normalized_input = os.path.normpath(input_directory)
    if not os.path.isdir(normalized_input):
        raise HkAnimToolError(f"Batch import input folder does not exist: {normalized_input}")

    temp_root = tempfile.mkdtemp(prefix="dow2_hkanim_")
    selected_files: list[str] = []
    unpacked_hkanim_paths: list[str] = []
    directory_modes: dict[str, str] = {}
    used_unpack_root = False

    try:
        for root in _iter_batch_source_directories(normalized_input):
            files = _list_directory_files(root)
            mode, selected_names = _select_directory_mode(files)
            if mode is None:
                continue

            directory_modes[root] = mode
            if mode == "hkanim":
                used_unpack_root = True
                relative_root = os.path.relpath(root, normalized_input)
                relative_root = "" if relative_root == "." else relative_root
                for file_name in selected_names:
                    source_path = os.path.join(root, file_name)
                    unpack_base = os.path.join(temp_root, relative_root, os.path.splitext(file_name)[0])
                    unpack_directory = make_unique_path(unpack_base)
                    unpack_hkanim_file(source_path, unpack_directory, tool_path=tool_path)
                    unpacked_hkanim_paths.append(source_path)
                    selected_files.extend(_collect_hkx_files(unpack_directory))
            else:
                for file_name in selected_names:
                    selected_files.append(os.path.join(root, file_name))

        return BatchAnimationFiles(
            files=selected_files,
            unpack_root=temp_root if used_unpack_root else None,
            unpacked_hkanim_paths=unpacked_hkanim_paths,
            directory_modes=directory_modes,
        )
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
    finally:
        if not used_unpack_root and os.path.isdir(temp_root):
            shutil.rmtree(temp_root, ignore_errors=True)


__all__ = [
    "ANIM_EXTENSION",
    "BatchAnimationFiles",
    "HKANIM_EXTENSION",
    "HKX_EXTENSION",
    "HkAnimToolError",
    "build_default_pack_output_path",
    "build_default_unpack_directory",
    "collect_batch_animation_files",
    "get_hkanim_tool_path",
    "make_unique_path",
    "pack_hkanim_from_directory",
    "unpack_hkanim_file",
    "unpack_hkanim_next_to_source",
]