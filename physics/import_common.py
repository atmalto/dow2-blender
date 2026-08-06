#  common utilities for xml/json physics importers:
#  1. infer_state_name: tries to guess the state name (healthy, light damage, heavy damage, wreck) based on system and body names
#  2. infer_lod_level: tries to guess the LOD level of a rigid body based on its name
#  3. normalize_motion_type: converts motion type strings to a consistent format
#  4. parse_float_sequence: extracts a list of floats from a string
#  5. extract_reference_ids: extracts reference IDs (e.g. #123) from a string
#  6. coerce_float and coerce_int: convert values to float or int since JSON may have them as strings

from __future__ import annotations

import re
from typing import List, Optional, Sequence


FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
REF_RE = re.compile(r"#\d+")
LOD_RE = re.compile(r"(?:^|[_-])lod(?:[_-]?)(\d+)(?:$|[_-])", re.IGNORECASE)

WRECK_TOKENS = (
    "wreck",
    "destroyed",
    "rubble",
    "debris",
    "damage03",
    "damage_03",
    "dmg03",
)
HEAVY_TOKENS = (
    "damage02",
    "damage_02",
    "dmg02",
    "heavydmg",
    "heavy_dmg",
    "heavydamage",
)
LIGHT_TOKENS = (
    "damage01",
    "damage_01",
    "dmg01",
    "lightdmg",
    "light_dmg",
    "lightdamage",
)
HEALTHY_TOKENS = (
    "healthy",
    "fullhealth",
    "full_health",
    "loadable",
    "intact",
    "undamaged",
)


def infer_state_name(system_name: str, body_names: Sequence[str], system_count: int, system_index: int) -> str:
    labels = [system_name, *body_names]
    combined = " ".join(label.lower() for label in labels if label)

    if any(token in combined for token in WRECK_TOKENS):
        return "wreck"
    if any(token in combined for token in HEAVY_TOKENS):
        return "heavy_damage"
    if any(token in combined for token in LIGHT_TOKENS):
        return "light_damage"
    if any(token in combined for token in HEALTHY_TOKENS):
        return "healthy"
    if system_count == 2 and ("damage" in combined or "dmg" in combined):
        return "wreck"

    fallback = {
        1: ("healthy",),
        2: ("healthy", "wreck"),
        3: ("healthy", "light_damage", "wreck"),
        4: ("healthy", "light_damage", "heavy_damage", "wreck"),
    }.get(system_count, ("healthy", "light_damage", "heavy_damage", "wreck"))
    if system_index < len(fallback):
        return fallback[system_index]
    return fallback[-1]


def infer_lod_level(body_name: str) -> int:
    lower_name = body_name.lower()
    match = LOD_RE.search(lower_name + "_")
    if match is not None:
        try:
            return int(match.group(1))
        except ValueError:
            return 0
    if "_lod" in lower_name or lower_name.endswith("lod"):
        return 1
    return 0


def normalize_motion_type(motion_type: str) -> str:
    motion_type = motion_type.strip().upper()
    if motion_type.startswith("MOTION_"):
        motion_type = motion_type[len("MOTION_") :]
    return motion_type or "FIXED"


def parse_float_sequence(text: str) -> List[float]:
    if not text:
        return []
    return [float(value) for value in FLOAT_RE.findall(text)]


def extract_reference_ids(text: str) -> List[str]:
    if not text:
        return []
    return REF_RE.findall(text)


def coerce_float(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def coerce_int(value: object) -> Optional[int]:
    number = coerce_float(value)
    if number is None:
        return None
    return int(round(number))


def parse_vector3_data(value: object) -> Optional[List[float]]:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


__all__ = [
    "coerce_float",
    "coerce_int",
    "extract_reference_ids",
    "infer_lod_level",
    "infer_state_name",
    "normalize_motion_type",
    "parse_float_sequence",
    "parse_vector3_data",
]