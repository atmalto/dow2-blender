from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Final

from .import_json import parse_physics_json
from .import_types import ImportedPhysicsScene, ImportedRigidBody, PhysicsImportError
from .import_xml import parse_physics_xml

ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ADDON_PATH, "blender_hkx")
ASSET_CC_DIR = os.path.join(ADDON_PATH, "blender_hkx", "BatchProcess", "AssetCc")


def _resolve_physics_tool() -> str:
    return os.path.join(SCRIPTS_DIR, "havok_io_cli.exe")


PHYSICS_EXE: Final[str] = _resolve_physics_tool()


def load_physics_scene(filepath: str) -> ImportedPhysicsScene:
    normalized_path = os.path.abspath(filepath)
    if not os.path.exists(normalized_path):
        raise PhysicsImportError(f"Physics file not found: {normalized_path}")

    extension = os.path.splitext(normalized_path)[1].lower()
    if extension == ".xml":
        return parse_physics_xml(normalized_path, source_format="xml")
    if extension != ".hkx":
        raise PhysicsImportError("Physics import currently supports .hkx and .xml files only")

    try:
        return _load_physics_hkx_native(normalized_path)
    except PhysicsImportError as native_error:
        native_message = str(native_error).strip()

    with tempfile.TemporaryDirectory(prefix="dow2_physics_import_") as temp_dir:
        xml_path = os.path.join(temp_dir, os.path.basename(normalized_path) + ".xml")
        try:
            _convert_hkx_to_xml(normalized_path, xml_path)
            return parse_physics_xml(xml_path, source_format="hkx")
        except PhysicsImportError as fallback_error:
            fallback_message = str(fallback_error).strip()
            raise PhysicsImportError(
                native_message
                + ("\nFallback via AssetCc also failed: " + fallback_message if fallback_message else "")
            ) from fallback_error


def _load_physics_hkx_native(input_path: str) -> ImportedPhysicsScene:
    if not os.path.exists(PHYSICS_EXE):
        raise PhysicsImportError(f"Physics tool was not found: {PHYSICS_EXE}")

    with tempfile.TemporaryDirectory(prefix="dow2_physics_native_import_") as temp_dir:
        json_path = os.path.join(temp_dir, os.path.basename(input_path) + ".json")
        completed = subprocess.run(
            [PHYSICS_EXE, "physics", "read", input_path, json_path],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 or not os.path.exists(json_path):
            output = (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
            raise PhysicsImportError(
                "Failed to read HKX with the native physics tool. "
                + (output.strip() or "The file may not be a supported Havok physics packfile.")
            )
        return parse_physics_json(json_path, source_format="hkx")


def _convert_hkx_to_xml(input_path: str, output_path: str) -> None:
    candidates = [
        os.path.join(ASSET_CC_DIR, "AssetCc1.exe"),
        os.path.join(ASSET_CC_DIR, "AssetCc2.exe"),
    ]
    available = [candidate for candidate in candidates if os.path.exists(candidate)]
    if not available:
        raise PhysicsImportError(f"AssetCc tools were not found in: {ASSET_CC_DIR}")

    last_error = ""
    for exe_path in available:
        completed = subprocess.run(
            [exe_path, input_path, output_path],
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0 and os.path.exists(output_path):
            return
        last_error = (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")

    raise PhysicsImportError(
        "Failed to convert HKX to XML with AssetCc. "
        + (last_error.strip() or "The file may not be a supported Havok packfile.")
    )


__all__ = [
    "ImportedPhysicsScene",
    "ImportedRigidBody",
    "PhysicsImportError",
    "load_physics_scene",
]