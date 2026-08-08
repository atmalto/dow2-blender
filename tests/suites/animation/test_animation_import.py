"""Animation import tests (plan IDs A-I1..A-I4).
"""

from __future__ import annotations

import csv
import shutil

CATEGORY = "animation/import"

_TODO = "scaffold ; not implemented yet"


def test_import_anim(ctx):
    """A-I1: .anim import -> keyframes on expected bones."""
    ctx.skip(_TODO)


def test_import_hkx(ctx):
    """A-I2: .hkx import via native CLI; HkxNonAnimationAssetError on non-anim hkx."""
    import bpy  # type: ignore

    from dow2_tools.animation.importer import load_animation_file  # type: ignore
    from framework import animation_import as anim_helpers, fixtures

    ctx.require_data()
    hkx_path = anim_helpers.default_hkx(ctx.config)
    if not hkx_path.is_file():
        ctx.skip(f"single HKX test clip missing: {hkx_path}")

    with fixtures.scratch_dir(ctx.config, "anim_single_hkx") as scratch:
        armature = anim_helpers.load_space_marine_model(ctx)
        bpy.ops.wm.save_as_mainfile(filepath=str(scratch / "space_marine_single.blend"))

        anim = load_animation_file(str(hkx_path), armature=armature)
        if not anim or not anim.frames:
            ctx.fail(f"{hkx_path.name}: native HKX reader returned no frames")
        tracked = anim_helpers.tracked_bone_names(anim)
        if not tracked:
            ctx.fail(f"{hkx_path.name}: native HKX reader returned no tracked bones")

        result = bpy.ops.import_scene.dow2_animation(filepath=str(hkx_path))
        if "FINISHED" not in result:
            ctx.fail(f"{hkx_path.name}: import returned {result}")

        action = armature.animation_data.action if armature.animation_data else None
        keyed = anim_helpers.assert_keyed_bones_are_tracked(ctx, action=action, armature=armature, tracked_names=tracked, label=hkx_path.name)
        if bpy.context.scene.frame_end < len(anim.frames) - 1:
            ctx.fail(f"{hkx_path.name}: scene frame_end {bpy.context.scene.frame_end} shorter than {len(anim.frames)} frames")

        rig = anim_helpers.parse_bone_list(scratch / ".rig")
        tracks = anim_helpers.parse_bone_list(scratch / ".tracks")
        if not rig:
            ctx.fail(f"{hkx_path.name}: single import did not write .rig")
        if not tracks:
            ctx.fail(f"{hkx_path.name}: single import did not write .tracks")
        missing_from_tracks = anim_helpers.lower_names(keyed) - anim_helpers.lower_names(tracks)
        if missing_from_tracks:
            ctx.fail(f"{hkx_path.name}: keyed bones missing from .tracks: {sorted(missing_from_tracks)[:10]}")


def test_import_selected_bones_only(ctx):
    """A-I3: import_selected_bones_only keys only selected bones."""
    import bpy  # type: ignore

    from dow2_tools.animation.importer import load_animation_file  # type: ignore
    from framework import animation_import as anim_helpers, fixtures

    ctx.require_data()
    hkx_path = anim_helpers.default_hkx(ctx.config)
    if not hkx_path.is_file():
        ctx.skip(f"single HKX test clip missing: {hkx_path}")

    with fixtures.scratch_dir(ctx.config, "anim_selected_hkx") as scratch:
        armature = anim_helpers.load_space_marine_model(ctx)
        bpy.ops.wm.save_as_mainfile(filepath=str(scratch / "space_marine_selected.blend"))

        anim = load_animation_file(str(hkx_path), armature=armature)
        tracked = anim_helpers.tracked_bone_names(anim)
        armature_bones_by_lower = {bone.name.lower(): bone.name for bone in armature.data.bones}
        selected_name = next((armature_bones_by_lower[name.lower()] for name in sorted(tracked) if name.lower() in armature_bones_by_lower), None)
        if selected_name is None:
            ctx.skip(f"{hkx_path.name}: no tracked bones overlap space_marine.model")

        for bone in armature.data.bones:
            bone.select = False
        armature.data.bones[selected_name].select = True
        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature

        result = bpy.ops.import_scene.dow2_animation(filepath=str(hkx_path), import_selected_bones_only=True)
        if "FINISHED" not in result:
            ctx.fail(f"selected-bone import returned {result}")
        action = armature.animation_data.action if armature.animation_data else None
        keyed = anim_helpers.keyed_pose_bones(action)
        if keyed != {selected_name}:
            ctx.fail(f"selected-bone import keyed {sorted(keyed)}, expected only {selected_name}")


def test_batch_import(ctx):
    """A-I4: batch import directory; all_animations.blend when enabled."""
    import bpy  # type: ignore

    from dow2_tools.utils import get_addon_preferences  # type: ignore
    from dow2_tools.animation.hkanim import collect_batch_animation_files  # type: ignore
    from framework import animation_import as anim_helpers, fixtures

    ctx.require_data()
    space_marine_dir = anim_helpers.space_marine_dir(ctx.config)
    hkanim_path = anim_helpers.space_marine_hkanim(ctx.config)
    if not hkanim_path.is_file():
        ctx.skip(f"space_marine.hkanim missing: {hkanim_path}")

    collected = collect_batch_animation_files(str(space_marine_dir))
    try:
        if str(hkanim_path) not in {str(path) for path in collected.unpacked_hkanim_paths}:
            ctx.fail("space_marine.hkanim was not unpacked by batch collection")
        if not collected.files:
            ctx.fail("space_marine.hkanim unpacked no HKX files")
    finally:
        collected.cleanup()

    source_hkx_files = anim_helpers.batch_hkx_files(ctx.config)
    missing = [path for path in source_hkx_files if not path.is_file()]
    if missing:
        ctx.skip(f"batch HKX test clips missing: {missing[0]}")

    with fixtures.scratch_dir(ctx.config, "anim_batch_hkx") as scratch:
        input_dir = scratch / "input"
        output_dir = scratch / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        for path in source_hkx_files:
            shutil.copy2(path, input_dir / path.name)

        armature = anim_helpers.load_space_marine_model(ctx)
        prefs = get_addon_preferences(bpy.context)
        if prefs is not None:
            prefs.batch_import_output_directory = str(output_dir)
            prefs.batch_import_write_all_animations_blend = False
        bpy.context.scene.dow2_batch_import_output_directory = str(output_dir)
        bpy.context.scene.dow2_batch_import_write_all_animations_blend = False

        result = bpy.ops.import_scene.dow2_animations_batch(directory=str(input_dir))
        if "FINISHED" not in result:
            ctx.fail(f"batch HKX import returned {result}")

        rig = anim_helpers.parse_bone_list(output_dir / ".rig")
        tracks = anim_helpers.parse_bone_list(output_dir / ".tracks")
        if not rig:
            ctx.fail("batch import did not write .rig")
        if not tracks:
            ctx.fail("batch import did not write .tracks")
        tracks_not_in_rig = anim_helpers.lower_names(tracks) - anim_helpers.lower_names(rig)
        if tracks_not_in_rig:
            ctx.fail(f"batch .tracks contains bones not in .rig: {sorted(tracks_not_in_rig)[:10]}")

        blend_files = sorted(output_dir.glob("*.blend"))
        if len(blend_files) != len(source_hkx_files):
            ctx.fail(f"batch wrote {len(blend_files)} .blend files, expected {len(source_hkx_files)}")

        csv_files = sorted(output_dir.glob("*.csv"))
        per_anim_csvs = [path for path in csv_files if path.name != "import_report.csv"]
        if len(per_anim_csvs) != len(source_hkx_files):
            ctx.fail(f"batch wrote {len(per_anim_csvs)} per-animation CSV files, expected {len(source_hkx_files)}")

        for blend_path in blend_files:
            csv_path = output_dir / f"{blend_path.stem}.csv"
            if not csv_path.is_file():
                ctx.fail(f"missing CSV for {blend_path.name}")
            tracked_from_csv = set()
            with csv_path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if row.get("track") == "1":
                        tracked_from_csv.add(row.get("bone_name", ""))
            if not tracked_from_csv:
                ctx.fail(f"{csv_path.name}: no tracked bones")

            bpy.ops.wm.open_mainfile(filepath=str(blend_path))
            armature = next((obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"), None)
            if armature is None:
                ctx.fail(f"{blend_path.name}: saved blend has no armature")
            action = armature.animation_data.action if armature.animation_data else None
            keyed = anim_helpers.assert_keyed_bones_are_tracked(
                ctx,
                action=action,
                armature=armature,
                tracked_names=tracked_from_csv,
                label=blend_path.name,
            )
            missing_from_tracks = anim_helpers.lower_names(keyed) - anim_helpers.lower_names(tracks)
            if missing_from_tracks:
                ctx.fail(f"{blend_path.name}: keyed bones missing from batch .tracks: {sorted(missing_from_tracks)[:10]}")
