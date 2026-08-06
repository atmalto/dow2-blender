import csv
import os
from dataclasses import dataclass, field
from typing import Iterable, List


@dataclass
class BatchImportRecord:
    """Batch import metadata used to write sidecar output files."""
    animation_name: str
    relative_output_path: str = ""
    bone_names: List[str] = field(default_factory=list)
    tracked_bone_names: List[str] = field(default_factory=list)
    missing_bones: List[str] = field(default_factory=list)


def unique_names(names: Iterable[str]) -> List[str]:
    """Return names in first-seen order without duplicates or empty entries."""
    seen = set()
    unique = []
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        unique.append(name)
    return unique


def reserve_output_name(used_names: set[str], preferred_name: str) -> str:
    """Return a unique flat output name for the batch output directory."""
    base_name = preferred_name or "animation"
    candidate = base_name
    suffix = 2
    while candidate in used_names:
        candidate = f"{base_name}_{suffix}"
        suffix += 1
    used_names.add(candidate)
    return candidate


def reserve_output_path(used_paths: set[str], preferred_relative_path: str) -> str:
    """Return a unique relative output stem while preserving subdirectories."""
    normalized_path = os.path.normpath(preferred_relative_path or "animation")
    parent_directory = os.path.dirname(normalized_path)
    base_name = os.path.basename(normalized_path) or "animation"

    candidate = normalized_path
    suffix = 2
    while candidate.lower() in used_paths:
        candidate_name = f"{base_name}_{suffix}"
        candidate = os.path.join(parent_directory, candidate_name) if parent_directory else candidate_name
        suffix += 1

    used_paths.add(candidate.lower())
    return candidate


def get_parallel_worker_limit() -> int:
    """Return the max worker count to offer in batch-processing UIs."""
    return max(1, (os.cpu_count() or 2) - 1)


def get_default_parallel_worker_count() -> int:
    """Return the default worker count for batch processing."""
    return get_parallel_worker_limit()


def _safe_file_size(file_path: str) -> int:
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def chunk_paths(file_paths: Iterable[str], chunk_count: int) -> List[List[str]]:
    """Split paths into size-balanced chunks using greedy bin packing."""
    file_paths = list(file_paths)
    if not file_paths:
        return []

    chunk_count = max(1, min(chunk_count, len(file_paths)))
    chunks = [[] for _ in range(chunk_count)]
    chunk_sizes = [0] * chunk_count

    sized_paths = sorted(
        ((_safe_file_size(file_path), file_path) for file_path in file_paths),
        key=lambda item: (-item[0], item[1].lower()),
    )

    for file_size, file_path in sized_paths:
        target_index = min(range(chunk_count), key=lambda index: (chunk_sizes[index], len(chunks[index])))
        chunks[target_index].append(file_path)
        chunk_sizes[target_index] += file_size

    return [chunk for chunk in chunks if chunk]


def get_chunk_total_size(file_paths: Iterable[str]) -> int:
    """Return the total on-disk size for a file chunk."""
    return sum(_safe_file_size(file_path) for file_path in file_paths)


def write_animation_config_csv(
    output_directory: str,
    relative_output_path: str,
    bone_names: Iterable[str],
    tracked_bone_names: Iterable[str],
):
    """Write one CSV config per imported animation."""
    output_path = os.path.join(output_directory, f"{relative_output_path}.csv")
    os.makedirs(os.path.dirname(output_path) or output_directory, exist_ok=True)
    tracked_bone_name_set = set(unique_names(tracked_bone_names))
    with open(output_path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(["bone_name", "rig", "track"])
        for bone_name in unique_names(bone_names):
            writer.writerow([bone_name, 1, int(bone_name in tracked_bone_name_set)])
    return output_path


def write_import_report(output_directory: str, records: Iterable[BatchImportRecord]):
    """Write a per-folder missing-bone CSV report."""
    output_path = os.path.join(output_directory, "import_report.csv")
    rows = []
    for record in records:
        missing_bones = unique_names(record.missing_bones)
        if not missing_bones:
            continue
        rows.append([record.animation_name, *missing_bones])

    with open(output_path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        if rows:
            writer.writerows(rows)
        else:
            writer.writerow(["No missing bones"])
    return output_path


def write_global_bone_list(output_directory: str, file_name: str, bone_names: Iterable[str]):
    """Write one comma-separated bone list file for a batch output folder."""
    output_path = os.path.join(output_directory, file_name)
    with open(output_path, 'w', encoding='utf-8') as handle:
        handle.write(", ".join(unique_names(bone_names)))
    return output_path


def _get_record_group_path(record: BatchImportRecord) -> str:
    normalized_path = os.path.normpath(record.relative_output_path or record.animation_name)
    group_path = os.path.dirname(normalized_path)
    return "" if group_path in ("", ".") else group_path


def write_batch_import_sidecars(output_directory: str, records: Iterable[BatchImportRecord]):
    """Write batch import sidecar files grouped by logical output folder."""
    records = list(records)
    os.makedirs(output_directory, exist_ok=True)

    for record in records:
        write_animation_config_csv(
            output_directory,
            record.relative_output_path or record.animation_name,
            record.bone_names,
            record.tracked_bone_names,
        )

    grouped_records: dict[str, list[BatchImportRecord]] = {}
    for record in records:
        group_path = _get_record_group_path(record)
        grouped_records.setdefault(group_path, []).append(record)

    sidecar_paths: dict[str, dict[str, str]] = {}
    for group_path, group_records in grouped_records.items():
        group_output_directory = os.path.join(output_directory, group_path) if group_path else output_directory
        os.makedirs(group_output_directory, exist_ok=True)

        all_bone_names = []
        all_tracked_bone_names = []
        for record in group_records:
            all_bone_names.extend(record.bone_names)
            all_tracked_bone_names.extend(record.tracked_bone_names)

        sidecar_paths[group_path] = {
            "report": write_import_report(group_output_directory, group_records),
            "rig": write_global_bone_list(group_output_directory, ".rig", all_bone_names),
            "tracks": write_global_bone_list(group_output_directory, ".tracks", all_tracked_bone_names),
        }

    return sidecar_paths