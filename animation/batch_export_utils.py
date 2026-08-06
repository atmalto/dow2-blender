import json
import os
import subprocess
import tempfile

import bpy

from .batch_utils import (
    chunk_paths,
    get_chunk_total_size,
    get_parallel_worker_limit,
    unique_names,
    write_global_bone_list,
)
from .rig_track_utils import (
    build_rig_track_rows,
    find_scene_armature,
    get_action_track_bone_names,
    get_armature_bone_names,
    get_csv_path_for_blend,
    parse_bone_name_file,
    resolve_bone_names_for_armature,
    write_rig_track_csv,
)


def _get_addon_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_addon_core_path() -> str:
    return os.path.dirname(_get_addon_root())


def _get_exporter_runtime():
    from .export_core import export_animation, load_export_sets_from_csv, log_error, log_info, log_warning

    return export_animation, load_export_sets_from_csv, log_error, log_info, log_warning


def generate_missing_batch_export_configs(blend_files, directory):
    """Generate missing batch rig/track config files from the source scenes."""
    _, _, log_error, log_info, log_warning = _get_exporter_runtime()

    global_rig_path = os.path.join(directory, ".rig")
    global_track_path = os.path.join(directory, ".tracks")
    master_bone_names = parse_bone_name_file(global_rig_path)
    track_reference_names = parse_bone_name_file(global_track_path)
    missing_csv_blends = [
        blend_path for blend_path in blend_files
        if not os.path.exists(get_csv_path_for_blend(blend_path))
    ]

    missing_global_rig = not master_bone_names
    missing_global_track = not track_reference_names
    if not missing_global_rig and not missing_global_track and not missing_csv_blends:
        return {
            "generated_csv_count": 0,
            "generated_global_rig": False,
            "generated_global_tracks": False,
            "failed_blends": [],
            "fatal_error": None,
        }

    log_info("Generating missing batch rig/track config files from scene data...")

    all_scene_bone_names = []
    track_names_by_blend = {}
    failed_blends = []
    for blend_path in blend_files:
        blend_name = os.path.splitext(os.path.basename(blend_path))[0]
        try:
            bpy.ops.wm.open_mainfile(filepath=blend_path)
        except Exception as exc:
            log_warning(f"{blend_name}: unable to open blend for config generation: {exc}")
            failed_blends.append(blend_name)
            continue

        armature_obj = find_scene_armature(bpy.context.scene)
        if armature_obj is None:
            log_warning(f"{blend_name}: no armature found while generating rig/track config")
            failed_blends.append(blend_name)
            continue

        bone_names = get_armature_bone_names(armature_obj)
        all_scene_bone_names.extend(bone_names)

        action = armature_obj.animation_data.action if armature_obj.animation_data else None
        if action is None:
            log_warning(f"{blend_name}: no active action found while generating rig/track config; track flags default to 0")
            track_names_by_blend[blend_path] = []
            continue

        track_names_by_blend[blend_path] = get_action_track_bone_names(action)

    if missing_global_rig:
        master_bone_names = unique_names(all_scene_bone_names)

    if not master_bone_names:
        message = "Unable to generate batch rig/track configs: no armature bones were found in the selected folder"
        log_error(message)
        return {
            "generated_csv_count": 0,
            "generated_global_rig": False,
            "generated_global_tracks": False,
            "failed_blends": failed_blends,
            "fatal_error": message,
        }

    generated_global_rig = False
    if missing_global_rig:
        write_global_bone_list(directory, ".rig", master_bone_names)
        generated_global_rig = True

    generated_global_tracks = False
    if missing_global_track:
        write_global_bone_list(directory, ".tracks", master_bone_names)
        generated_global_tracks = True

    generated_csv_count = 0
    for blend_path in missing_csv_blends:
        if blend_path not in track_names_by_blend:
            continue
        csv_path = get_csv_path_for_blend(blend_path)
        rows = build_rig_track_rows(master_bone_names, track_names_by_blend[blend_path])
        write_rig_track_csv(csv_path, rows)
        generated_csv_count += 1

    return {
        "generated_csv_count": generated_csv_count,
        "generated_global_rig": generated_global_rig,
        "generated_global_tracks": generated_global_tracks,
        "failed_blends": failed_blends,
        "fatal_error": None,
    }


def run_batch_config_generation_worker(manifest_path):
    """Background Blender worker entry point for config generation."""
    _, _, log_error, _, _ = _get_exporter_runtime()

    result_path = ""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as handle:
            manifest = json.load(handle)

        result_path = manifest["result_path"]
        result = generate_missing_batch_export_configs(
            manifest["blend_files"],
            manifest["directory"],
        )

        with open(result_path, 'w', encoding='utf-8') as handle:
            json.dump(result, handle)

        return 0 if result.get("fatal_error") is None else 1
    except Exception as exc:
        log_error(f"Batch config generation worker failed: {exc}")
        if result_path:
            with open(result_path, 'w', encoding='utf-8') as handle:
                json.dump(
                    {
                        "generated_csv_count": 0,
                        "generated_global_rig": False,
                        "generated_global_tracks": False,
                        "failed_blends": [],
                        "fatal_error": str(exc),
                    },
                    handle,
                )
        return 1


def ensure_batch_export_configs(blend_files, directory):
    """Generate missing batch rig/track config files in a background Blender process."""
    _, _, log_error, log_info, log_warning = _get_exporter_runtime()

    global_rig_names = parse_bone_name_file(os.path.join(directory, ".rig"))
    global_track_names = parse_bone_name_file(os.path.join(directory, ".tracks"))
    missing_csv_blends = [
        blend_path for blend_path in blend_files
        if not os.path.exists(get_csv_path_for_blend(blend_path))
    ]
    if global_rig_names and global_track_names and not missing_csv_blends:
        return {
            "generated_csv_count": 0,
            "generated_global_rig": False,
            "generated_global_tracks": False,
            "failed_blends": [],
            "fatal_error": None,
        }

    blender_binary = bpy.app.binary_path
    addon_core_path = _get_addon_core_path()
    with tempfile.TemporaryDirectory(prefix="dow2_batch_config_") as temp_dir:
        result_path = os.path.join(temp_dir, "result.json")
        manifest_path = os.path.join(temp_dir, "manifest.json")
        manifest = {
            "blend_files": blend_files,
            "directory": directory,
            "result_path": result_path,
        }
        with open(manifest_path, 'w', encoding='utf-8') as handle:
            json.dump(manifest, handle)

        python_expr = (
            f"import sys; sys.path.insert(0, {addon_core_path!r}); "
            f"from dow2_tools.animation.batch_export_utils import run_batch_config_generation_worker; "
            f"raise SystemExit(run_batch_config_generation_worker({manifest_path!r}))"
        )
        process = subprocess.run(
            [
                blender_binary,
                "--background",
                "--factory-startup",
                "--python-expr",
                python_expr,
            ],
            capture_output=True,
            text=True,
        )

        if process.returncode != 0 and process.stderr and process.stderr.strip():
            log_error(f"Batch config generation stderr:\n{process.stderr.strip()}")
        elif process.returncode != 0 and process.stdout and process.stdout.strip():
            log_error(f"Batch config generation output:\n{process.stdout.strip()}")

        if not os.path.exists(result_path):
            message = "Batch config generation did not produce a result manifest"
            log_error(message)
            return {
                "generated_csv_count": 0,
                "generated_global_rig": False,
                "generated_global_tracks": False,
                "failed_blends": [],
                "fatal_error": message,
            }

        with open(result_path, 'r', encoding='utf-8') as handle:
            result = json.load(handle)

    if result.get("generated_global_rig"):
        log_info("Generated missing .rig file from batch scene bones")
    if result.get("generated_global_tracks"):
        log_info("Generated missing .tracks file from batch scene bones")
    if result.get("generated_csv_count"):
        log_info(f"Generated {result['generated_csv_count']} missing CSV config file(s) from batch scene data")
    if result.get("failed_blends"):
        preview = ", ".join(result["failed_blends"][:10])
        if len(result["failed_blends"]) > 10:
            preview += ", ..."
        log_warning(f"Some blend files could not contribute generated config data: {preview}")

    return result


def run_batch_export_jobs(
    blend_files,
    directory,
    use_global_rig_reference=False,
    use_global_track_reference=False,
    quantization_bits=8,
    tolerance=0.0,
    use_block_compression=True,
    block_size=8,
    use_three_component_quaternions=True,
):
    """Export a list of .blend files to HKX within the current Blender process."""
    export_animation, load_export_sets_from_csv, log_error, log_info, log_warning = _get_exporter_runtime()

    global_rig_path = os.path.join(directory, ".rig")
    global_track_path = os.path.join(directory, ".tracks")

    global_rig_names = None
    global_track_names = None
    if use_global_rig_reference:
        global_rig_names = parse_bone_name_file(global_rig_path)
        if not global_rig_names:
            message = f"Global rig file not found or empty: {global_rig_path}"
            log_error(message)
            return {
                "processed_count": len(blend_files),
                "success_count": 0,
                "failed_blends": [os.path.splitext(os.path.basename(path))[0] for path in blend_files],
                "fatal_error": message,
            }

    if use_global_track_reference:
        global_track_names = parse_bone_name_file(global_track_path)
        if not global_track_names:
            message = f"Global tracks file not found or empty: {global_track_path}"
            log_error(message)
            return {
                "processed_count": len(blend_files),
                "success_count": 0,
                "failed_blends": [os.path.splitext(os.path.basename(path))[0] for path in blend_files],
                "fatal_error": message,
            }

    success_count = 0
    failed_blends = []

    for blend_path in blend_files:
        blend_name = os.path.splitext(os.path.basename(blend_path))[0]
        hkx_path = os.path.join(directory, blend_name + ".hkx")

        log_info(f"Exporting: {blend_name}")

        try:
            bpy.ops.wm.open_mainfile(filepath=blend_path)

            armature_obj = None
            for obj in bpy.context.scene.objects:
                if obj.type == 'ARMATURE':
                    armature_obj = obj
                    break

            if armature_obj and armature_obj.animation_data and armature_obj.animation_data.action:
                action = armature_obj.animation_data.action
                export_bones = None
                export_tracks = None
                missing_names = []

                if use_global_rig_reference:
                    export_bones, missing_rig = resolve_bone_names_for_armature(armature_obj, global_rig_names)
                    missing_names.extend(missing_rig)
                if use_global_track_reference:
                    export_tracks, missing_tracks = resolve_bone_names_for_armature(armature_obj, global_track_names)
                    missing_names.extend(missing_tracks)

                if not use_global_rig_reference or not use_global_track_reference:
                    csv_path = get_csv_path_for_blend(blend_path)
                    csv_rig, csv_tracks, csv_missing = load_export_sets_from_csv(armature_obj, csv_path)
                    if csv_rig is None and not use_global_rig_reference:
                        log_error(f"Missing CSV config for {blend_name}: {csv_path}")
                        failed_blends.append(blend_name)
                        continue
                    if csv_tracks is None and not use_global_track_reference:
                        log_error(f"Missing CSV config for {blend_name}: {csv_path}")
                        failed_blends.append(blend_name)
                        continue
                    if not use_global_rig_reference:
                        export_bones = csv_rig
                    if not use_global_track_reference:
                        export_tracks = csv_tracks
                    missing_names.extend(csv_missing)

                if missing_names:
                    preview = ", ".join(sorted(set(missing_names))[:10])
                    if len(set(missing_names)) > 10:
                        preview += ", ..."
                    log_warning(f"{blend_name}: some configured bones were not found in the armature: {preview}")

                if export_animation(
                    armature_obj,
                    action,
                    hkx_path,
                    export_bones,
                    export_tracks,
                    quantization_bits=quantization_bits,
                    tolerance=tolerance,
                    use_block_compression=use_block_compression,
                    block_size=block_size,
                    use_three_component_quaternions=use_three_component_quaternions,
                ):
                    success_count += 1
                else:
                    log_error(f"Export failed for {blend_name}")
                    failed_blends.append(blend_name)
            else:
                log_warning(f"No animation found in {blend_name}")
                failed_blends.append(blend_name)

        except Exception as exc:
            log_error(f"Failed to export {blend_name}: {exc}")
            failed_blends.append(blend_name)

    return {
        "processed_count": len(blend_files),
        "success_count": success_count,
        "failed_blends": failed_blends,
        "fatal_error": None,
    }


def run_parallel_export_worker(manifest_path):
    """Background Blender worker entry point for parallel batch export."""
    _, _, log_error, _, _ = _get_exporter_runtime()

    result_path = ""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as handle:
            manifest = json.load(handle)

        result_path = manifest["result_path"]
        result = run_batch_export_jobs(
            manifest["blend_files"],
            manifest["directory"],
            use_global_rig_reference=manifest.get("use_global_rig_reference", False),
            use_global_track_reference=manifest.get("use_global_track_reference", False),
            quantization_bits=manifest.get("quantization_bits", 8),
            tolerance=manifest.get("tolerance", 0.0),
            use_block_compression=manifest.get("use_block_compression", True),
            block_size=manifest.get("block_size", 8),
            use_three_component_quaternions=manifest.get("use_three_component_quaternions", True),
        )

        with open(result_path, 'w', encoding='utf-8') as handle:
            json.dump(result, handle)

        return 0 if result.get("fatal_error") is None else 1
    except Exception as exc:
        log_error(f"Parallel export worker failed: {exc}")
        if result_path:
            with open(result_path, 'w', encoding='utf-8') as handle:
                json.dump(
                    {
                        "processed_count": 0,
                        "success_count": 0,
                        "failed_blends": [],
                        "fatal_error": str(exc),
                    },
                    handle,
                )
        return 1


def run_parallel_batch_export_jobs(
    blend_files,
    directory,
    use_global_rig_reference=False,
    use_global_track_reference=False,
    quantization_bits=8,
    tolerance=0.0,
    use_block_compression=True,
    block_size=8,
    use_three_component_quaternions=True,
    worker_count=1,
):
    """Export .blend files using multiple background Blender worker processes."""
    _, _, log_error, log_info, _ = _get_exporter_runtime()

    requested_worker_count = worker_count
    worker_limit = get_parallel_worker_limit()
    worker_count = max(1, min(worker_count, len(blend_files), worker_limit))
    if worker_count <= 1:
        log_info(
            f"Parallel batch export running in a single process "
            f"(requested={requested_worker_count}, files={len(blend_files)}, limit={worker_limit})"
        )
        return run_batch_export_jobs(
            blend_files,
            directory,
            use_global_rig_reference=use_global_rig_reference,
            use_global_track_reference=use_global_track_reference,
            quantization_bits=quantization_bits,
            tolerance=tolerance,
            use_block_compression=use_block_compression,
            block_size=block_size,
            use_three_component_quaternions=use_three_component_quaternions,
        )

    blender_binary = bpy.app.binary_path
    addon_core_path = _get_addon_core_path()
    chunks = chunk_paths(blend_files, worker_count)
    log_info(
        f"Parallel batch export worker allocation: requested={requested_worker_count}, "
        f"effective={worker_count}, files={len(blend_files)}, cpu_limit={worker_limit}"
    )
    for worker_index, chunk in enumerate(chunks):
        chunk_size = get_chunk_total_size(chunk)
        log_info(
            f"  Worker {worker_index + 1}: {len(chunk)} blend(s), {chunk_size} bytes total"
        )

    aggregate = {
        "processed_count": len(blend_files),
        "success_count": 0,
        "failed_blends": [],
        "fatal_error": None,
    }

    with tempfile.TemporaryDirectory(prefix="dow2_parallel_export_") as temp_dir:
        processes = []
        for worker_index, chunk in enumerate(chunks):
            result_path = os.path.join(temp_dir, f"worker_{worker_index}_result.json")
            manifest_path = os.path.join(temp_dir, f"worker_{worker_index}_manifest.json")
            manifest = {
                "blend_files": chunk,
                "directory": directory,
                "use_global_rig_reference": use_global_rig_reference,
                "use_global_track_reference": use_global_track_reference,
                "quantization_bits": quantization_bits,
                "tolerance": tolerance,
                "use_block_compression": use_block_compression,
                "block_size": block_size,
                "use_three_component_quaternions": use_three_component_quaternions,
                "result_path": result_path,
            }
            with open(manifest_path, 'w', encoding='utf-8') as handle:
                json.dump(manifest, handle)

            python_expr = (
                f"import sys; sys.path.insert(0, {addon_core_path!r}); "
                f"from dow2_tools.animation.batch_export_utils import run_parallel_export_worker; "
                f"raise SystemExit(run_parallel_export_worker({manifest_path!r}))"
            )
            process = subprocess.Popen(
                [
                    blender_binary,
                    "--background",
                    "--factory-startup",
                    "--python-expr",
                    python_expr,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            processes.append((worker_index, process, result_path, chunk))

        for worker_index, process, result_path, chunk in processes:
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                log_error(f"Parallel export worker {worker_index} exited with code {process.returncode}")
            if stderr and stderr.strip():
                log_error(f"Parallel export worker {worker_index} stderr:\n{stderr.strip()}")
            elif stdout and stdout.strip() and process.returncode != 0:
                log_error(f"Parallel export worker {worker_index} output:\n{stdout.strip()}")

            if not os.path.exists(result_path):
                aggregate["failed_blends"].extend(os.path.splitext(os.path.basename(path))[0] for path in chunk)
                continue

            with open(result_path, 'r', encoding='utf-8') as handle:
                result = json.load(handle)

            aggregate["success_count"] += result.get("success_count", 0)
            aggregate["failed_blends"].extend(result.get("failed_blends", []))
            if aggregate["fatal_error"] is None and result.get("fatal_error"):
                aggregate["fatal_error"] = result["fatal_error"]

    return aggregate
