from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Final

from .hkx import resolve_ragdoll_exporter
from .import_json import parse_ragdoll_json
from .import_types import ImportedRagdollScene, RagdollImportError


RAGDOLL_EXE: Final[str] = resolve_ragdoll_exporter()


def load_ragdoll_scene(filepath: str) -> ImportedRagdollScene:
    normalized_path = os.path.abspath(filepath)
    if not os.path.exists(normalized_path):
        raise RagdollImportError(f"Ragdoll file not found: {normalized_path}")

    extension = os.path.splitext(normalized_path)[1].lower()
    if extension == ".json":
        return parse_ragdoll_json(normalized_path, source_format="json")
    if extension != ".hkx":
        raise RagdollImportError("Ragdoll import currently supports .hkx and .json files only")

    return _load_ragdoll_hkx_native(normalized_path)


def _load_ragdoll_hkx_native(input_path: str) -> ImportedRagdollScene:
    if not os.path.exists(RAGDOLL_EXE):
        raise RagdollImportError(f"Ragdoll tool was not found: {RAGDOLL_EXE}")

    with tempfile.TemporaryDirectory(prefix="dow2_ragdoll_import_") as temp_dir:
        json_path = os.path.join(temp_dir, os.path.basename(input_path) + ".json")
        completed = subprocess.run(
            [RAGDOLL_EXE, "ragdoll", "read", input_path, json_path],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 or not os.path.exists(json_path):
            output = (completed.stdout or "") + (
                "\n" if completed.stdout and completed.stderr else ""
            ) + (completed.stderr or "")
            raise RagdollImportError(
                "Failed to read HKX with the native ragdoll tool. "
                + (output.strip() or "The file may not be a supported Havok ragdoll packfile.")
            )
        return parse_ragdoll_json(json_path, source_format="hkx")


__all__ = [
    "ImportedRagdollScene",
    "RagdollImportError",
    "load_ragdoll_scene",
]