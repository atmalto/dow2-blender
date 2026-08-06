from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


ADDON_PATH = Path(__file__).resolve().parents[1]
BLENDER_HKX_DIR = ADDON_PATH / "blender_hkx"


def resolve_ragdoll_exporter() -> str:
    return str(BLENDER_HKX_DIR / "havok_io_cli.exe")


RAGDOLL_EXE = resolve_ragdoll_exporter()


def run_ragdoll_exporter(json_path: str, hkx_path: str, exporter_path: str | None = None) -> tuple[bool, str]:
    executable = exporter_path or RAGDOLL_EXE
    if not os.path.exists(executable):
        return False, f"Ragdoll exporter not found: {executable}"

    output_dir = os.path.dirname(hkx_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    completed = subprocess.run(
        [executable, "ragdoll", "write", json_path, hkx_path],
        capture_output=True,
        text=True,
    )

    output = completed.stdout.strip()
    if completed.stderr.strip():
        output = f"{output}\n{completed.stderr.strip()}".strip()
    return completed.returncode == 0 and os.path.exists(hkx_path), output


def export_ragdoll_data_to_hkx(
    ragdoll_data: dict,
    output_path: str,
    json_path: str | None = None,
    exporter_path: str | None = None,
) -> tuple[bool, str, str]:
    temp_json_path = None
    actual_json_path = json_path

    if actual_json_path is None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump(ragdoll_data, handle, indent=2)
            temp_json_path = handle.name
            actual_json_path = handle.name
    else:
        actual_json = Path(actual_json_path)
        actual_json.parent.mkdir(parents=True, exist_ok=True)
        actual_json.write_text(json.dumps(ragdoll_data, indent=2), encoding="utf-8")

    try:
        success, output = run_ragdoll_exporter(actual_json_path, output_path, exporter_path=exporter_path)
        return success, output, actual_json_path
    finally:
        if temp_json_path and os.path.exists(temp_json_path):
            os.remove(temp_json_path)