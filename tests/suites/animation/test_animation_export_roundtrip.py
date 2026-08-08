"""Animation export + round-trip tests (plan IDs A-E1..A-E9)."""

from __future__ import annotations

import csv
import math
from pathlib import Path

CATEGORY = "animation/export"

_TODO = "scaffold ; not implemented yet"


def _missing(paths: list[Path]) -> list[Path]:
    return [path for path in paths if not path.is_file()]


def _write_rig_track_csv(path: Path, rig_names: list[str], track_names: set[str]) -> None:
    track_names_lower = {name.lower() for name in track_names}
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["bone_name", "rig", "track"])
        for name in rig_names:
            writer.writerow([name, 1, int(name.lower() in track_names_lower)])


def _write_bone_list(path: Path, names: list[str] | set[str]) -> None:
    path.write_text(", ".join(names), encoding="utf-8")


def _select_armature(armature) -> None:
    import bpy  # type: ignore

    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature


def _load_animation(ctx, path: Path, armature=None):
    from dow2_tools.animation.importer import load_animation_file  # type: ignore

    try:
        return load_animation_file(str(path), armature=armature)
    except Exception as exc:
        ctx.fail(f"{path.name}: animation read failed: {type(exc).__name__}: {exc}")


def _create_blend_from_hkx(ctx, hkx_path: Path, blend_path: Path) -> dict:
    import bpy  # type: ignore

    from framework import animation_import as anim_helpers

    blend_path.parent.mkdir(parents=True, exist_ok=True)
    armature = anim_helpers.load_space_marine_model(ctx)
    source_anim = _load_animation(ctx, hkx_path, armature=armature)
    if not source_anim or not source_anim.frames:
        ctx.fail(f"{hkx_path.name}: source HKX has no frames")

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    result = bpy.ops.import_scene.dow2_animation(filepath=str(hkx_path))
    if "FINISHED" not in result:
        ctx.fail(f"{hkx_path.name}: import before export returned {result}")

    action = armature.animation_data.action if armature.animation_data else None
    tracked = anim_helpers.tracked_bone_names(source_anim)
    keyed = anim_helpers.assert_keyed_bones_are_tracked(
        ctx,
        action=action,
        armature=armature,
        tracked_names=tracked,
        label=hkx_path.name,
    )
    track_name = anim_helpers.first_overlapping_tracked_bone(source_anim, armature)
    if track_name is None:
        ctx.skip(f"{hkx_path.name}: no tracked bones overlap space_marine.model")

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    rig_names = [bone.name for bone in armature.data.bones]
    return {
        "armature": armature,
        "frame_count": len(source_anim.frames),
        "rig_names": rig_names,
        "keyed_names": keyed,
        "track_name": track_name,
    }


def _export_single_hkx(ctx, *, output_path: Path) -> None:
    import bpy  # type: ignore

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.export_anim.dow2_hkx(
        filepath=str(output_path),
        quantization_bits='16',
        tolerance=0.0,
        use_block_compression=False,
        block_size='FULL',
        use_three_component_quaternions=False,
    )
    if "FINISHED" not in result or not output_path.is_file():
        ctx.fail(f"single HKX export returned {result}; exists={output_path.is_file()}")


def _assert_exported_hkx(ctx, *, hkx_path: Path, expected_frame_count: int, expected_tracks: set[str]) -> None:
    from framework import animation_import as anim_helpers

    exported = _load_animation(ctx, hkx_path)
    if not exported or not exported.frames:
        ctx.fail(f"{hkx_path.name}: exported HKX has no frames")
    if len(exported.frames) != expected_frame_count:
        ctx.fail(f"{hkx_path.name}: frame count {len(exported.frames)} != {expected_frame_count}")
    got_tracks = anim_helpers.lower_names(anim_helpers.tracked_bone_names(exported))
    expected = anim_helpers.lower_names(expected_tracks)
    if got_tracks != expected:
        ctx.fail(f"{hkx_path.name}: tracks {sorted(got_tracks)} != {sorted(expected)}")


def _create_codec_probe_scene(ctx, scratch: Path) -> dict:
    import bpy  # type: ignore
    from mathutils import Euler  # type: ignore

    from framework import animation_import as anim_helpers

    armature = anim_helpers.load_space_marine_model(ctx)
    pose_bones = list(armature.pose.bones)
    if len(pose_bones) < 4:
        ctx.skip("space_marine.model has too few bones for codec probe")

    track_names = [pose_bones[index].name for index in range(min(4, len(pose_bones)))]
    bpy.context.scene.render.fps = 30
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = 32
    action = bpy.data.actions.new(name="codec_probe")
    armature.animation_data_create()
    armature.animation_data.action = action

    for frame in range(0, 33):
        bpy.context.scene.frame_set(frame)
        phase = frame / 32.0
        for index, bone_name in enumerate(track_names):
            pose_bone = armature.pose.bones[bone_name]
            pose_bone.rotation_mode = 'QUATERNION'
            wave = math.sin((phase * math.tau) + index * 0.7)
            tiny = 0.00035 * math.sin(frame * 0.9 + index)
            pose_bone.location = (
                0.015 * wave + tiny,
                0.01 * math.cos((phase * math.tau) + index),
                0.004 * math.sin((phase * math.tau * 2.0) + index),
            )
            pose_bone.rotation_quaternion = Euler(
                (
                    -2.95 + phase * 5.9 + index * 0.03,
                    0.35 * math.sin(phase * math.tau + index),
                    0.8 * math.cos(phase * math.tau * 0.5 + index),
                ),
                'XYZ',
            ).to_quaternion()
            pose_bone.scale = (
                1.0 + 0.025 * math.sin(phase * math.tau + index),
                1.0 + 0.015 * math.cos(phase * math.tau + index),
                1.0 + 0.01 * math.sin(phase * math.tau * 1.5 + index),
            )
            pose_bone.keyframe_insert(data_path="location", frame=frame)
            pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
            pose_bone.keyframe_insert(data_path="scale", frame=frame)

    blend_path = scratch / "codec_probe.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    rig_names = [bone.name for bone in armature.data.bones]
    _write_rig_track_csv(blend_path.with_suffix(".csv"), rig_names, set(track_names))
    _select_armature(armature)
    return {"armature": armature, "track_names": set(track_names), "frame_count": 33, "blend_path": blend_path}


def _export_codec_variant(ctx, scratch: Path, name: str, **settings) -> Path:
    output_path = scratch / f"{name}.hkx"
    defaults = {
        "quantization_bits": '16',
        "tolerance": 0.0,
        "use_block_compression": False,
        "block_size": 'FULL',
        "use_three_component_quaternions": False,
    }
    defaults.update(settings)
    import bpy  # type: ignore

    result = bpy.ops.export_anim.dow2_hkx(filepath=str(output_path), **defaults)
    if "FINISHED" not in result or not output_path.is_file():
        ctx.fail(f"codec export {name} returned {result}; exists={output_path.is_file()}")
    return output_path


def _track_index_by_lower(anim) -> dict[str, int]:
    return {name.lower(): index for index, name in enumerate(anim.bones)}


def _quat_angle_degrees(left, right) -> float:
    left = left.normalized()
    right = right.normalized()
    dot = abs(max(-1.0, min(1.0, left.dot(right))))
    return math.degrees(2.0 * math.acos(dot))


def _decoded_error(reference, candidate, track_names: set[str]) -> dict:
    reference_indices = _track_index_by_lower(reference)
    candidate_indices = _track_index_by_lower(candidate)
    max_position = 0.0
    max_rotation = 0.0
    max_scale = 0.0
    frame_count = min(len(reference.frames), len(candidate.frames))

    for bone_name in track_names:
        lower = bone_name.lower()
        if lower not in reference_indices or lower not in candidate_indices:
            continue
        ref_index = reference_indices[lower]
        candidate_index = candidate_indices[lower]
        for frame in range(frame_count):
            ref_matrix = reference.frames[frame][ref_index]
            candidate_matrix = candidate.frames[frame][candidate_index]
            max_position = max(max_position, (ref_matrix.to_translation() - candidate_matrix.to_translation()).length)
            max_rotation = max(max_rotation, _quat_angle_degrees(ref_matrix.to_quaternion(), candidate_matrix.to_quaternion()))
            ref_scale = ref_matrix.to_scale()
            candidate_scale = candidate_matrix.to_scale()
            max_scale = max(
                max_scale,
                max(abs(ref_scale[index] - candidate_scale[index]) for index in range(3)),
            )

    return {
        "position": max_position,
        "rotation_deg": max_rotation,
        "scale": max_scale,
        "score": max_position + (max_rotation * 0.01) + max_scale,
    }


def _assert_codec_shape(ctx, decoded, *, expected_frame_count: int, expected_tracks: set[str], label: str) -> None:
    from framework import animation_import as anim_helpers

    if len(decoded.frames) != expected_frame_count:
        ctx.fail(f"{label}: frame count {len(decoded.frames)} != {expected_frame_count}")
    got_tracks = anim_helpers.lower_names(anim_helpers.tracked_bone_names(decoded))
    expected = anim_helpers.lower_names(expected_tracks)
    if got_tracks != expected:
        ctx.fail(f"{label}: tracks {sorted(got_tracks)} != {sorted(expected)}")


def _read_codec_variant(ctx, path: Path, *, expected_frame_count: int, expected_tracks: set[str]):
    decoded = _load_animation(ctx, path)
    _assert_codec_shape(ctx, decoded, expected_frame_count=expected_frame_count, expected_tracks=expected_tracks, label=path.name)
    return decoded





def test_roundtrip_import_export_import(ctx):
    """A-E1: import -> export .hkx -> import; keyframes match within tolerance."""
    import bpy  # type: ignore

    from framework import animation_import as anim_helpers, fixtures

    ctx.require_data()
    hkx_path = anim_helpers.default_hkx(ctx.config)
    if not hkx_path.is_file():
        ctx.skip(f"single export HKX source missing: {hkx_path}")

    with fixtures.scratch_dir(ctx.config, "anim_single_export_hkx") as scratch:
        blend_path = scratch / "single_export.blend"
        output_path = scratch / "single_export.hkx"
        info = _create_blend_from_hkx(ctx, hkx_path, blend_path)
        track_name = info["track_name"]
        _write_rig_track_csv(blend_path.with_suffix(".csv"), info["rig_names"], {track_name})

        _select_armature(info["armature"])
        _export_single_hkx(ctx, output_path=output_path)
        _assert_exported_hkx(
            ctx,
            hkx_path=output_path,
            expected_frame_count=info["frame_count"],
            expected_tracks={track_name},
        )
        source_decoded = _load_animation(ctx, hkx_path)
        exported_decoded = _load_animation(ctx, output_path)
        source_error = _decoded_error(source_decoded, exported_decoded, {track_name})
        if source_error["position"] > 0.1 or source_error["rotation_deg"] > 5.0 or source_error["scale"] > 0.1:
            ctx.fail(f"source-vs-export decoded transform delta outside budget for {track_name}: {source_error}")

        bpy.ops.wm.read_homefile(use_empty=True)
        armature = anim_helpers.load_space_marine_model(ctx)
        result = bpy.ops.import_scene.dow2_animation(filepath=str(output_path))
        if "FINISHED" not in result:
            ctx.fail(f"single exported HKX re-import returned {result}")
        action = armature.animation_data.action if armature.animation_data else None
        keyed = anim_helpers.keyed_pose_bones(action)
        if anim_helpers.lower_names(keyed) != anim_helpers.lower_names({track_name}):
            ctx.fail(f"single exported HKX re-import keyed {sorted(keyed)}, expected {track_name}")


def test_batch_folder_export_hkx_roundtrip(ctx):
    """A-E6/A-E8: batch .blend folder -> HKX; per-animation CSV rig/track config respected."""
    import bpy  # type: ignore

    from framework import animation_import as anim_helpers, fixtures

    ctx.require_data()
    source_hkx_files = anim_helpers.export_roundtrip_hkx_files(ctx.config)
    missing = _missing(source_hkx_files)
    if missing:
        ctx.skip(f"batch export HKX source missing: {missing[0]}")

    with fixtures.scratch_dir(ctx.config, "anim_batch_export_hkx") as scratch:
        expected: dict[str, dict] = {}
        global_rig_names: list[str] = []
        global_track_names: set[str] = set()

        for hkx_path in source_hkx_files:
            stem = anim_helpers.safe_clip_stem(hkx_path)
            blend_path = scratch / f"{stem}.blend"
            info = _create_blend_from_hkx(ctx, hkx_path, blend_path)
            track_name = info["track_name"]
            _write_rig_track_csv(blend_path.with_suffix(".csv"), info["rig_names"], {track_name})
            expected[stem] = {"frames": info["frame_count"], "tracks": {track_name}}
            if not global_rig_names:
                global_rig_names = info["rig_names"]
            global_track_names.update(info["keyed_names"])

        _write_bone_list(scratch / ".rig", global_rig_names)
        _write_bone_list(scratch / ".tracks", global_track_names)

        result = bpy.ops.dow2.batch_export_anims(
            directory=str(scratch),
            use_global_rig_reference=False,
            use_global_track_reference=False,
            parallel_workers=1,
            quantization_bits='16',
            tolerance=0.0,
            use_block_compression=False,
            block_size='FULL',
            use_three_component_quaternions=False,
        )
        if "FINISHED" not in result:
            ctx.fail(f"batch HKX export returned {result}")

        for stem, expected_info in expected.items():
            out_path = scratch / f"{stem}.hkx"
            if not out_path.is_file():
                ctx.fail(f"batch export missing {out_path.name}")
            _assert_exported_hkx(
                ctx,
                hkx_path=out_path,
                expected_frame_count=expected_info["frames"],
                expected_tracks=expected_info["tracks"],
            )


def test_hkanim_pack_preserves_exported_subfolders(ctx):
    """A-E6/A-E8: exported HKX files in child folders pack/unpack as separate HKANIM sets."""
    from dow2_tools.animation.hkanim import pack_hkanim_from_directory, unpack_hkanim_file  # type: ignore
    from framework import animation_import as anim_helpers, fixtures

    ctx.require_data()
    source_hkx_files = anim_helpers.export_roundtrip_hkx_files(ctx.config)
    missing = _missing(source_hkx_files)
    if missing:
        ctx.skip(f"HKANIM export source missing: {missing[0]}")

    with fixtures.scratch_dir(ctx.config, "anim_hkanim_pack_exported") as scratch:
        pack_root = scratch / "pack_root"
        unpack_root = scratch / "unpacked"
        blend_root = scratch / "blends"
        expected_by_group: dict[str, set[str]] = {}

        for hkx_path in source_hkx_files:
            group = anim_helpers.export_roundtrip_group_name(hkx_path)
            stem = hkx_path.stem
            blend_path = blend_root / group / f"{stem}.blend"
            output_path = pack_root / group / f"{stem}.hkx"
            info = _create_blend_from_hkx(ctx, hkx_path, blend_path)
            _write_rig_track_csv(blend_path.with_suffix(".csv"), info["rig_names"], {info["track_name"]})
            _select_armature(info["armature"])
            _export_single_hkx(ctx, output_path=output_path)
            _assert_exported_hkx(
                ctx,
                hkx_path=output_path,
                expected_frame_count=info["frame_count"],
                expected_tracks={info["track_name"]},
            )
            expected_by_group.setdefault(group, set()).add(stem)

        hkanim_path = scratch / "space_marine_export_test.hkanim"
        pack_hkanim_from_directory(str(pack_root), str(hkanim_path))
        if not hkanim_path.is_file():
            ctx.fail("HKANIM pack did not create output file")
        unpack_hkanim_file(str(hkanim_path), str(unpack_root))

        for group, stems in expected_by_group.items():
            group_dir = unpack_root / group
            if not group_dir.is_dir():
                ctx.fail(f"HKANIM unpack missing set folder {group}")
            unpacked_stems = {path.stem for path in group_dir.glob("*.hkx")}
            if not stems.issubset(unpacked_stems):
                ctx.fail(f"HKANIM set {group}: files {sorted(unpacked_stems)} missing {sorted(stems - unpacked_stems)}")
            for stem in stems:
                decoded = _load_animation(ctx, group_dir / f"{stem}.hkx")
                if not decoded or not decoded.frames:
                    ctx.fail(f"HKANIM unpacked {group}/{stem}.hkx did not decode")


def test_quantization_and_tolerance(ctx):
    """A-E2..A-E3: quantization_bits (1/8/16); tolerance lossless vs lossy."""
    from framework import fixtures

    ctx.require_data()
    with fixtures.scratch_dir(ctx.config, "anim_codec_quant_tolerance") as scratch:
        probe = _create_codec_probe_scene(ctx, scratch)
        track_names = probe["track_names"]
        frame_count = probe["frame_count"]

        q16_path = _export_codec_variant(ctx, scratch, "q16", quantization_bits='16')
        q8_path = _export_codec_variant(ctx, scratch, "q8", quantization_bits='8')
        q1_path = _export_codec_variant(ctx, scratch, "q1", quantization_bits='1')
        tol_path = _export_codec_variant(ctx, scratch, "tolerance_005", quantization_bits='16', tolerance=0.05)

        q16 = _read_codec_variant(ctx, q16_path, expected_frame_count=frame_count, expected_tracks=track_names)
        q8 = _read_codec_variant(ctx, q8_path, expected_frame_count=frame_count, expected_tracks=track_names)
        q1 = _read_codec_variant(ctx, q1_path, expected_frame_count=frame_count, expected_tracks=track_names)
        tolerance = _read_codec_variant(ctx, tol_path, expected_frame_count=frame_count, expected_tracks=track_names)

        q8_error = _decoded_error(q16, q8, track_names)
        q1_error = _decoded_error(q16, q1, track_names)
        if q8_error["score"] > q1_error["score"] + 1e-4:
            ctx.fail(f"8-bit quantization error exceeded 1-bit error: q8={q8_error}, q1={q1_error}")

        tolerance_error = _decoded_error(q16, tolerance, track_names)
        if tolerance_error["position"] > 0.25 or tolerance_error["rotation_deg"] > 12.0 or tolerance_error["scale"] > 0.2:
            ctx.fail(f"tolerance=0.05 decoded outside coarse budget: {tolerance_error}")
        if tol_path.stat().st_size > q16_path.stat().st_size:
            ctx.fail(f"tolerance export grew file size: {tol_path.stat().st_size} > {q16_path.stat().st_size}")


def test_block_compression_and_quaternions(ctx):
    """A-E4..A-E5: use_block_compression + block_size; three-component quats + continuity."""
    from framework import fixtures

    ctx.require_data()
    with fixtures.scratch_dir(ctx.config, "anim_codec_block_quat") as scratch:
        probe = _create_codec_probe_scene(ctx, scratch)
        track_names = probe["track_names"]
        frame_count = probe["frame_count"]

        full_path = _export_codec_variant(ctx, scratch, "full_clip", quantization_bits='16')
        full = _read_codec_variant(ctx, full_path, expected_frame_count=frame_count, expected_tracks=track_names)

        for block_size in ('4', '8', '16'):
            block_path = _export_codec_variant(
                ctx,
                scratch,
                f"block_{block_size}",
                quantization_bits='16',
                use_block_compression=True,
                block_size=block_size,
            )
            decoded = _read_codec_variant(ctx, block_path, expected_frame_count=frame_count, expected_tracks=track_names)
            error = _decoded_error(full, decoded, track_names)
            if error["position"] > 0.1 or error["rotation_deg"] > 5.0 or error["scale"] > 0.1:
                ctx.fail(f"block_size={block_size} decoded outside budget: {error}")

        quat_path = _export_codec_variant(
            ctx,
            scratch,
            "three_component_quat",
            quantization_bits='16',
            use_three_component_quaternions=True,
        )
        quat = _read_codec_variant(ctx, quat_path, expected_frame_count=frame_count, expected_tracks=track_names)
        quat_error = _decoded_error(full, quat, track_names)
        if quat_error["position"] > 0.1 or quat_error["rotation_deg"] > 5.0 or quat_error["scale"] > 0.1:
            ctx.fail(f"three-component quaternion decode outside budget: {quat_error}")


def test_batch_global_rig_track_references(ctx):
    """A-E6: batch global .rig/.tracks references override per-animation CSV flags."""
    import bpy  # type: ignore

    from framework import animation_import as anim_helpers, fixtures

    ctx.require_data()
    source_hkx_files = anim_helpers.export_roundtrip_hkx_files(ctx.config)[:2]
    missing = _missing(source_hkx_files)
    if missing:
        ctx.skip(f"global rig/track export source missing: {missing[0]}")

    with fixtures.scratch_dir(ctx.config, "anim_batch_global_rig_tracks") as scratch:
        expected_frames: dict[str, int] = {}
        global_rig_names: list[str] = []
        global_track_name = ""

        for hkx_path in source_hkx_files:
            stem = anim_helpers.safe_clip_stem(hkx_path)
            blend_path = scratch / f"{stem}.blend"
            info = _create_blend_from_hkx(ctx, hkx_path, blend_path)
            expected_frames[stem] = info["frame_count"]
            if not global_rig_names:
                global_rig_names = info["rig_names"]
                global_track_name = info["track_name"]
            per_anim_track = next((name for name in sorted(info["keyed_names"]) if name.lower() != global_track_name.lower()), None)
            _write_rig_track_csv(blend_path.with_suffix(".csv"), info["rig_names"], {per_anim_track or info["track_name"]})

        _write_bone_list(scratch / ".rig", global_rig_names)
        _write_bone_list(scratch / ".tracks", {global_track_name})

        result = bpy.ops.dow2.batch_export_anims(
            directory=str(scratch),
            use_global_rig_reference=True,
            use_global_track_reference=True,
            parallel_workers=1,
            quantization_bits='16',
            tolerance=0.0,
            use_block_compression=False,
            block_size='FULL',
            use_three_component_quaternions=False,
        )
        if "FINISHED" not in result:
            ctx.fail(f"batch global rig/track export returned {result}")

        for stem, frame_count in expected_frames.items():
            out_path = scratch / f"{stem}.hkx"
            if not out_path.is_file():
                ctx.fail(f"global rig/track batch export missing {out_path.name}")
            _assert_exported_hkx(
                ctx,
                hkx_path=out_path,
                expected_frame_count=frame_count,
                expected_tracks={global_track_name},
            )


def test_rig_track_config(ctx):
    """A-E8..A-E9: .rig/.tracks/.csv config; rig-track settings generate/refresh/reset/save."""
    import bpy  # type: ignore

    from dow2_tools.animation.rig_track_utils import parse_rig_track_csv  # type: ignore
    from framework import animation_import as anim_helpers, fixtures

    ctx.require_data()
    with fixtures.scratch_dir(ctx.config, "anim_rig_track_settings") as scratch:
        probe = _create_codec_probe_scene(ctx, scratch)
        blend_path = probe["blend_path"]
        expected_tracks = anim_helpers.lower_names(probe["track_names"])

        result = bpy.ops.dow2.generate_rig_track_settings()
        if "FINISHED" not in result:
            ctx.fail(f"generate rig/track settings returned {result}")
        csv_path = blend_path.with_suffix(".csv")
        if not csv_path.is_file():
            ctx.fail("generate rig/track settings did not write CSV")
        if not bpy.context.scene.dow2_rig_track_items:
            ctx.fail("generate rig/track settings did not populate scene items")

        rig_names, track_names = parse_rig_track_csv(str(csv_path))
        if not rig_names:
            ctx.fail("generated rig/track CSV has no rig bones")
        if anim_helpers.lower_names(set(track_names or [])) != expected_tracks:
            ctx.fail(f"generated tracks {sorted(track_names or [])} do not match keyed tracks {sorted(expected_tracks)}")

        result = bpy.ops.dow2.set_rig_track_flags(apply_track=True, track_enabled=False)
        if "FINISHED" not in result:
            ctx.fail(f"track-off flag update returned {result}")
        if any(item.track_enabled for item in bpy.context.scene.dow2_rig_track_items):
            ctx.fail("track-off flag update left enabled tracks in the scene list")
        result = bpy.ops.dow2.save_rig_track_settings()
        if "FINISHED" not in result:
            ctx.fail(f"save rig/track settings after track-off returned {result}")
        _rig_after_off, tracks_after_off = parse_rig_track_csv(str(csv_path))
        if tracks_after_off:
            ctx.fail(f"saved track-off CSV still has tracks: {tracks_after_off[:10]}")

        result = bpy.ops.dow2.refresh_rig_track_settings()
        if "FINISHED" not in result:
            ctx.fail(f"refresh rig/track settings returned {result}")
        if any(item.track_enabled for item in bpy.context.scene.dow2_rig_track_items):
            ctx.fail("refresh did not preserve saved track-off settings")

        result = bpy.ops.dow2.reset_rig_track_settings()
        if "FINISHED" not in result:
            ctx.fail(f"reset rig/track settings returned {result}")
        if not all(item.rig_enabled and item.track_enabled for item in bpy.context.scene.dow2_rig_track_items):
            ctx.fail("reset rig/track settings did not enable all flags")
        result = bpy.ops.dow2.save_rig_track_settings()
        if "FINISHED" not in result:
            ctx.fail(f"save rig/track settings after reset returned {result}")
        rig_after_reset, tracks_after_reset = parse_rig_track_csv(str(csv_path))
        if len(tracks_after_reset or []) != len(rig_after_reset or []):
            ctx.fail("reset/save did not persist all tracks enabled")
