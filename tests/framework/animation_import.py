"""Shared helpers for animation import tests."""

from __future__ import annotations

from pathlib import Path

SPACE_MARINE_REL = Path("art/race_marine/troops/space_marine")
DEFAULT_HKX_REL = Path("animations/range_missile_launcher/fb_idle_stand_01.hkx")
BATCH_HKX_RELS = (
    Path("animations/range_missile_launcher/fb_idle_stand_01.hkx"),
    Path("animations/range_missile_launcher/fb_run.hkx"),
    Path("animations/range_missile_launcher/fb_fire_stand.hkx"),
)
EXPORT_ROUNDTRIP_HKX_RELS = (
    Path("animations/range_missile_launcher/fb_idle_stand_01.hkx"),
    Path("animations/range_missile_launcher/fb_run.hkx"),
    Path("animations/range_lascannon/fb_idle_stand_01.hkx"),
    Path("animations/range_lascannon/fb_fire_stand_01.hkx"),
)


def space_marine_dir(config) -> Path:
    return config.data_root / SPACE_MARINE_REL


def space_marine_model(config) -> Path:
    return space_marine_dir(config) / "space_marine.model"


def space_marine_hkanim(config) -> Path:
    return space_marine_dir(config) / "space_marine.hkanim"


def default_hkx(config) -> Path:
    return space_marine_dir(config) / DEFAULT_HKX_REL


def batch_hkx_files(config) -> list[Path]:
    return [space_marine_dir(config) / rel for rel in BATCH_HKX_RELS]


def export_roundtrip_hkx_files(config) -> list[Path]:
    return [space_marine_dir(config) / rel for rel in EXPORT_ROUNDTRIP_HKX_RELS]


def export_roundtrip_group_name(hkx_path: Path) -> str:
    try:
        rel = hkx_path.relative_to(space_marine_dir_from_hkx(hkx_path) / "animations")
        return rel.parts[0] if len(rel.parts) > 1 else "root"
    except ValueError:
        return hkx_path.parent.name


def space_marine_dir_from_hkx(hkx_path: Path) -> Path:
    parts = hkx_path.parts
    for index in range(len(parts) - 1, -1, -1):
        if parts[index].lower() == "space_marine":
            return Path(*parts[: index + 1])
    return hkx_path.parent


def safe_clip_stem(hkx_path: Path) -> str:
    group = export_roundtrip_group_name(hkx_path)
    return f"{group}__{hkx_path.stem}"


def load_space_marine_model(ctx):
    import bpy  # type: ignore

    from framework import blender_env

    model_path = space_marine_model(ctx.config)
    if not model_path.is_file():
        ctx.skip(f"space_marine.model missing: {model_path}")

    blender_env.reset_scene()
    result = blender_env.import_model(
        model_path,
        import_meshes=True,
        import_materials=False,
        import_bones=True,
        import_markers=False,
        import_simbox=False,
        import_coverbox=False,
        import_bounding_volumes=False,
    )
    if "FINISHED" not in result:
        ctx.fail(f"space_marine.model import returned {result}")

    armature = next((obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"), None)
    if armature is None:
        ctx.fail("space_marine.model import produced no armature")
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    return armature


def keyed_pose_bones(action) -> set[str]:
    keyed: set[str] = set()
    if action is None:
        return keyed
    for fcurve in action.fcurves:
        data_path = fcurve.data_path or ""
        if not data_path.startswith('pose.bones["'):
            continue
        parts = data_path.split('"')
        if len(parts) >= 2:
            keyed.add(parts[1])
    return keyed


def tracked_bone_names(anim) -> set[str]:
    return {anim.bones[index] for index in anim.tracks if 0 <= index < len(anim.bones)}


def parse_bone_list(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return set()
    return {part.strip() for part in text.split(",") if part.strip()}


def lower_names(names: set[str]) -> set[str]:
    return {name.lower() for name in names if name}


def first_overlapping_tracked_bone(anim, armature) -> str | None:
    armature_bones_by_lower = {bone.name.lower(): bone.name for bone in armature.data.bones}
    for name in sorted(tracked_bone_names(anim)):
        exact = armature_bones_by_lower.get(name.lower())
        if exact is not None:
            return exact
    return None


def assert_keyed_bones_are_tracked(ctx, *, action, armature, tracked_names: set[str], label: str) -> set[str]:
    keyed = keyed_pose_bones(action)
    if not keyed:
        ctx.fail(f"{label}: no keyed pose bones")

    armature_bones_by_lower = {bone.name.lower(): bone.name for bone in armature.data.bones}
    tracked_on_armature = {
        armature_bones_by_lower[name.lower()]
        for name in tracked_names
        if name.lower() in armature_bones_by_lower
    }
    if not tracked_on_armature:
        ctx.fail(f"{label}: no tracked bones overlap the armature")

    unexpected = sorted(keyed - tracked_on_armature)
    if unexpected:
        ctx.fail(f"{label}: keyed non-.tracks bones: {unexpected[:10]}")
    return keyed
