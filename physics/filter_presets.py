from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any


CUSTOM_PRESET_ID = "CUSTOM"
EVENT_FILTER_KIND = "event_filter"
USER_FILTER_KIND = "user_filter"
DEFAULT_EVENT_MIN_SUPPORT = 5
DEFAULT_USER_MIN_SUPPORT = 4

_CLASSIFICATION_ORDER = ("building", "rubble")

_EVENT_MEANING_OVERRIDES = {
    0: "no callback event bits enabled; passive callback profile",
    18: "process-contact callback profile with an undocumented 0x10 extension bit",
    19: "start-and-process callback profile with an undocumented 0x10 extension bit",
    113: "full contact lifecycle profile with 0x10, 0x20, and 0x40 extensions",
}

_USER_MEANING_OVERRIDES = {
    0: "passive body with no shared callback-family bits",
    14: "active basic callback-family mask",
    62: "active broad callback-family mask",
    63: "active broad callback-family mask with the 0x01 variant bit",
    190: "active broad callback-family mask with the 0x80 high extension bit",
    191: "active broad callback-family mask with both 0x01 and 0x80 extensions",
}


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _data_dir() -> Path:
    return Path(__file__).resolve().parent / "data"


ANALYSIS_LIBRARY_SOURCE_PATH = (
    _workspace_root()
    / "working"
    / "tests"
    / "test_output"
    / "physics_world_object_analysis"
    / "world_object_physics_analysis.json"
)
FROZEN_FILTER_LIBRARY_PATH = _data_dir() / "filter_preset_library.json"


def _class_counts_text(classification_counts: dict[str, int]) -> str:
    parts: list[str] = []
    for label in _CLASSIFICATION_ORDER:
        count = int(classification_counts.get(label, 0))
        if count:
            parts.append(f"{label} x{count}")
    for label in sorted(classification_counts):
        if label not in _CLASSIFICATION_ORDER and classification_counts[label]:
            parts.append(f"{label} x{classification_counts[label]}")
    return ", ".join(parts) or "no observed usage"


def _semantic_meaning(filter_kind: str, raw_value: int, breakdown: dict[str, Any] | None) -> str:
    if filter_kind == EVENT_FILTER_KIND and raw_value in _EVENT_MEANING_OVERRIDES:
        return _EVENT_MEANING_OVERRIDES[raw_value]
    if filter_kind == USER_FILTER_KIND and raw_value in _USER_MEANING_OVERRIDES:
        return _USER_MEANING_OVERRIDES[raw_value]

    if not breakdown:
        return "authored callback filter byte from shipped physics data"

    if filter_kind == EVENT_FILTER_KIND:
        return str(breakdown.get("intuitive_meaning") or "authored callback event byte")

    common_family_label = breakdown.get("common_family_label")
    if common_family_label:
        return f"shared-bit callback-family mask ({common_family_label})"
    return str(breakdown.get("intuitive_meaning") or "shared-bit callback-family mask")


def _build_group(
    records: list[dict[str, Any]],
    *,
    filter_kind: str,
    min_support: int,
) -> dict[str, Any]:
    counter: Counter[int] = Counter()
    classification_counts: dict[int, Counter[str]] = {}
    sample_counts: dict[int, Counter[str]] = {}
    sample_paths: dict[int, dict[str, str]] = {}
    body_names: dict[int, Counter[str]] = {}
    breakdowns: dict[int, dict[str, Any] | None] = {}

    breakdown_field = f"{filter_kind}_breakdown"
    for record in records:
        hkx_path = Path(record["hkx_path"])
        hkx_name = hkx_path.stem
        classification = str(record.get("classification") or "unknown")
        for body in record.get("rigid_bodies") or []:
            raw_value = body.get(filter_kind)
            if raw_value is None:
                continue
            raw_value = int(raw_value)
            counter[raw_value] += 1
            classification_counts.setdefault(raw_value, Counter())[classification] += 1
            sample_counts.setdefault(raw_value, Counter())[hkx_name] += 1
            sample_paths.setdefault(raw_value, {})[hkx_name] = str(hkx_path)
            body_name = str(body.get("name") or "")
            if body_name:
                body_names.setdefault(raw_value, Counter())[body_name] += 1
            if raw_value not in breakdowns:
                breakdowns[raw_value] = body.get(breakdown_field)

    entries: list[dict[str, Any]] = []
    for raw_value, total_count in counter.most_common():
        if total_count < min_support:
            continue
        representative_hkx = sample_counts[raw_value].most_common(1)[0][0]
        representative_body = body_names.get(raw_value, Counter()).most_common(1)
        breakdown = breakdowns.get(raw_value)
        class_counts_payload = dict(classification_counts[raw_value])
        semantic_meaning = _semantic_meaning(filter_kind, raw_value, breakdown)
        corpus_use = _class_counts_text(class_counts_payload)
        description = (
            f"Semantic meaning: {semantic_meaning}. "
            f"Corpus use: {corpus_use}. "
            f"Representative HKX: {representative_hkx} | {raw_value}."
        )
        entries.append(
            {
                "id": str(raw_value),
                "value": raw_value,
                "hex": f"0x{raw_value:02X}",
                "label": f"{representative_hkx} | {raw_value}",
                "description": description,
                "semantic_meaning": semantic_meaning,
                "corpus_use": corpus_use,
                "total_count": total_count,
                "classification_counts": class_counts_payload,
                "representative_hkx_name": representative_hkx,
                "representative_hkx_path": sample_paths[raw_value][representative_hkx],
                "representative_body_name": representative_body[0][0] if representative_body else None,
                "breakdown": breakdown,
            }
        )

    return {
        "kind": filter_kind,
        "custom_preset_id": CUSTOM_PRESET_ID,
        "entries": entries,
        "value_map": {entry["id"]: entry for entry in entries},
    }


def build_filter_preset_library(
    analysis_payload: dict[str, Any],
    *,
    source_path: str | None = None,
    event_min_support: int = DEFAULT_EVENT_MIN_SUPPORT,
    user_min_support: int = DEFAULT_USER_MIN_SUPPORT,
) -> dict[str, Any]:
    records = list(analysis_payload.get("records") or [])
    return {
        "version": 1,
        "source_analysis": source_path,
        "thresholds": {
            EVENT_FILTER_KIND: int(event_min_support),
            USER_FILTER_KIND: int(user_min_support),
        },
        "filters": {
            EVENT_FILTER_KIND: _build_group(
                records,
                filter_kind=EVENT_FILTER_KIND,
                min_support=event_min_support,
            ),
            USER_FILTER_KIND: _build_group(
                records,
                filter_kind=USER_FILTER_KIND,
                min_support=user_min_support,
            ),
        },
    }


def build_filter_preset_library_from_analysis(
    analysis_path: str | Path | None = None,
    *,
    event_min_support: int = DEFAULT_EVENT_MIN_SUPPORT,
    user_min_support: int = DEFAULT_USER_MIN_SUPPORT,
) -> dict[str, Any]:
    source_path = Path(analysis_path) if analysis_path else ANALYSIS_LIBRARY_SOURCE_PATH
    with source_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return build_filter_preset_library(
        payload,
        source_path=str(source_path),
        event_min_support=event_min_support,
        user_min_support=user_min_support,
    )


@lru_cache(maxsize=1)
def load_filter_preset_library(library_path: str | Path | None = None) -> dict[str, Any]:
    source_path = Path(library_path) if library_path else FROZEN_FILTER_LIBRARY_PATH
    if not source_path.exists() and library_path is None and ANALYSIS_LIBRARY_SOURCE_PATH.exists():
        return build_filter_preset_library_from_analysis()
    with source_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_frozen_filter_preset_library(
    output_path: str | Path | None = None,
    *,
    analysis_path: str | Path | None = None,
    event_min_support: int = DEFAULT_EVENT_MIN_SUPPORT,
    user_min_support: int = DEFAULT_USER_MIN_SUPPORT,
) -> dict[str, Any]:
    target_path = Path(output_path) if output_path else FROZEN_FILTER_LIBRARY_PATH
    library = build_filter_preset_library_from_analysis(
        analysis_path=analysis_path,
        event_min_support=event_min_support,
        user_min_support=user_min_support,
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(library, indent=2), encoding="utf-8")
    load_filter_preset_library.cache_clear()
    return library


def _group_for_kind(filter_kind: str, library: dict[str, Any] | None = None) -> dict[str, Any]:
    active_library = library or load_filter_preset_library()
    groups = active_library.get("filters") or {}
    return groups.get(filter_kind) or {"entries": [], "value_map": {}, "custom_preset_id": CUSTOM_PRESET_ID}


def enum_items_for_filter_kind(filter_kind: str, library: dict[str, Any] | None = None) -> list[tuple[str, str, str]]:
    group = _group_for_kind(filter_kind, library=library)
    items = [
        (
            CUSTOM_PRESET_ID,
            "Custom Override",
            "Use the raw override control directly instead of one of the curated shipped presets.",
        )
    ]
    for entry in group.get("entries") or []:
        items.append((entry["id"], entry["label"], entry["description"]))
    return items


def preset_id_for_value(filter_kind: str, raw_value: int, library: dict[str, Any] | None = None) -> str:
    group = _group_for_kind(filter_kind, library=library)
    value_map = group.get("value_map") or {}
    return str(raw_value) if str(raw_value) in value_map else CUSTOM_PRESET_ID


def value_from_preset(filter_kind: str, preset_id: str, library: dict[str, Any] | None = None) -> int | None:
    if not preset_id or preset_id == CUSTOM_PRESET_ID:
        return None
    group = _group_for_kind(filter_kind, library=library)
    entry = (group.get("value_map") or {}).get(str(preset_id))
    if entry is None:
        return None
    return int(entry["value"])


__all__ = [
    "ANALYSIS_LIBRARY_SOURCE_PATH",
    "CUSTOM_PRESET_ID",
    "DEFAULT_EVENT_MIN_SUPPORT",
    "DEFAULT_USER_MIN_SUPPORT",
    "EVENT_FILTER_KIND",
    "FROZEN_FILTER_LIBRARY_PATH",
    "USER_FILTER_KIND",
    "build_filter_preset_library",
    "build_filter_preset_library_from_analysis",
    "enum_items_for_filter_kind",
    "load_filter_preset_library",
    "preset_id_for_value",
    "value_from_preset",
    "write_frozen_filter_preset_library",
]