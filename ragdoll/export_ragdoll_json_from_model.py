import os
import sys
import traceback
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _parse_args() -> tuple[str, str, str | None]:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    if len(argv) < 2:
        raise SystemExit(
            "Usage: blender --background --factory-startup --python ragdoll/export_ragdoll_json_from_model.py -- <model_path> <output_json> [output_hkx]"
        )

    return (
        argv[0],
        argv[1],
        argv[2] if len(argv) > 2 else None,
    )


def _ensure_addon_registered(script_path: Path) -> None:
    addon_parent = script_path.resolve().parents[2]
    addon_name = script_path.resolve().parents[1].name
    addon_package_parent = str(addon_parent)
    if addon_package_parent not in sys.path:
        sys.path.insert(0, addon_package_parent)

    addon_module = __import__(addon_name)
    if hasattr(addon_module, "register"):
        addon_module.register()


def main() -> int:
    model_path, output_json, output_hkx = _parse_args()
    _ensure_addon_registered(Path(__file__))

    from dow2_tools.ragdoll import export_ragdoll_hkx, export_ragdoll_json, get_armature, import_model

    print("=" * 72)
    print("DoW2 Ragdoll JSON Export")
    print("=" * 72)
    print(f"Model: {model_path}")
    print(f"Output JSON: {output_json}")
    if output_hkx:
        print(f"Output HKX: {output_hkx}")
    print("=" * 72)

    result = import_model(model_path)
    if result != {"FINISHED"}:
        print(f"ERROR: import failed: {result}")
        return 1

    armature = get_armature()
    if armature is None:
        print("ERROR: no armature found after import")
        return 1

    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    ragdoll_data = export_ragdoll_json(armature, output_json)

    if output_hkx:
        export_ragdoll_hkx(armature, output_hkx, json_path=output_json)

    print(f"Imported armature: {armature.name}")
    print(f"Animation bones: {len(ragdoll_data['animation_skeleton']['bones'])}")
    print(f"Ragdoll bones: {len(ragdoll_data['ragdoll_skeleton']['bones'])}")
    print(f"Rigid bodies: {len(ragdoll_data['rigid_bodies'])}")
    print(f"Constraints: {len(ragdoll_data['constraints'])}")
    if output_hkx:
        print("HKX export complete")
    print("JSON export complete")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)