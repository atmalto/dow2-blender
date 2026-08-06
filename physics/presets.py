from __future__ import annotations

from typing import Dict, List


BUILDING_STATIC = "BUILDING_STATIC"
RUBBLE_BOX = "RUBBLE_BOX"
RUBBLE_SPHERE = "RUBBLE_SPHERE"

HK_REAL_MAX = 3.402820018375656e38

PRESET_ITEMS = [
    (
        BUILDING_STATIC,
        "Static Objects",
        "Use the shipped building/static profile. Corpus: 225/225 building bodies are fixed, quality 1, HK_REAL_MAX penetration, no deactivator.",
    ),
    (
        RUBBLE_BOX,
        "Motion Box Inertia",
        "Use the default rubble profile. Corpus: 515/565 rubble bodies use box inertia, quality 4, penetration 0.1, and dynamic deactivation.",
    ),
    (
        RUBBLE_SPHERE,
        "Motion Sphere Inertia",
        "Use the rubble sphere-inertia profile. Corpus: 50/565 rubble bodies use sphere inertia with the same dynamic defaults as rubble box.",
    ),
]

MASS_PRESET_VALUES = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0, 15.0, 18.0, 20.0, 25.0, 30.0, 40.0, 50.0, 100.0]
MASS_PRESET_ITEMS = [
    ("CUSTOM", "Custom", "Use the slider value directly."),
]
for value in MASS_PRESET_VALUES:
    label = str(int(value)) if value.is_integer() else str(value)
    MASS_PRESET_ITEMS.append(
        (
            f"MASS_{label.replace('.', '_')}",
            label,
            f"Common rubble mass from the analyzed corpus: {label}.",
        )
    )

QUALITY_TYPE_ITEMS = [
    ("1", "1 - Fixed", "Building corpus value. All analyzed building bodies use quality type 1."),
    ("4", "4 - Moving", "Rubble corpus value. All analyzed rubble bodies use quality type 4."),
]

DEACTIVATION_CLASS_ITEMS = [
    ("1", "1 - Static", "Building corpus value. All analyzed building bodies use deactivation class 1."),
    ("2", "2 - Dynamic", "Rubble corpus value. All analyzed rubble bodies use deactivation class 2."),
]

CENTER_OF_MASS_MODE_ITEMS = [
    ("ZERO", "Zero", "Write a zero center of mass. Used by fixed/static building bodies."),
    (
        "COMPUTE_FROM_SHAPE",
        "Compute From Shape",
        "Compute center of mass from the generated hull shape. This matches the default rubble export behavior.",
    ),
    (
        "CUSTOM",
        "Custom Override",
        "Write the custom center of mass vector directly. Use this only when matching authored Havok data exactly.",
    ),
]

FRICTION_QUICK_VALUES = [0.5, 0.1, 0.2, 0.3]
RESTITUTION_QUICK_VALUES = [0.4, 0.1, 0.2, 0.3, 0.0]
PENETRATION_QUICK_VALUES = [HK_REAL_MAX, 0.1]

PRESET_DEFAULTS: Dict[str, Dict[str, object]] = {
    BUILDING_STATIC: {
        "preset": BUILDING_STATIC,
        "mass": 0.0,
        "mass_preset": "CUSTOM",
        "allowed_penetration_depth": HK_REAL_MAX,
        "friction": 0.5,
        "restitution": 0.4,
        "quality_type": "1",
        "process_contact_callback_delay": 65535,
        "deactivation_class": "1",
        "deactivation_integrate_counter": 255,
        "linear_damping": 0.0,
        "angular_damping": 0.05,
        "max_linear_velocity": 200.0,
        "max_angular_velocity": 200.0,
        "collision_filter_info": 0,
        "event_filter": 0,
        "user_filter": 0,
        "center_of_mass_mode": "ZERO",
        "center_of_mass_override": [0.0, 0.0, 0.0],
        "shape_radius": 0.05,
    },
    RUBBLE_BOX: {
        "preset": RUBBLE_BOX,
        "mass": 5.0,
        "mass_preset": "MASS_5",
        "allowed_penetration_depth": 0.1,
        "friction": 0.5,
        "restitution": 0.4,
        "quality_type": "4",
        "process_contact_callback_delay": 65535,
        "deactivation_class": "2",
        "deactivation_integrate_counter": 15,
        "linear_damping": 0.0,
        "angular_damping": 0.05,
        "max_linear_velocity": 200.0,
        "max_angular_velocity": 200.0,
        "collision_filter_info": 0,
        "event_filter": 0,
        "user_filter": 0,
        "center_of_mass_mode": "COMPUTE_FROM_SHAPE",
        "center_of_mass_override": [0.0, 0.0, 0.0],
        "shape_radius": 0.05,
    },
    RUBBLE_SPHERE: {
        "preset": RUBBLE_SPHERE,
        "mass": 5.0,
        "mass_preset": "MASS_5",
        "allowed_penetration_depth": 0.1,
        "friction": 0.5,
        "restitution": 0.4,
        "quality_type": "4",
        "process_contact_callback_delay": 65535,
        "deactivation_class": "2",
        "deactivation_integrate_counter": 15,
        "linear_damping": 0.0,
        "angular_damping": 0.05,
        "max_linear_velocity": 200.0,
        "max_angular_velocity": 200.0,
        "collision_filter_info": 0,
        "event_filter": 0,
        "user_filter": 0,
        "center_of_mass_mode": "COMPUTE_FROM_SHAPE",
        "center_of_mass_override": [0.0, 0.0, 0.0],
        "shape_radius": 0.05,
    },
}


def get_preset_defaults(preset_id: str) -> Dict[str, object]:
    return dict(PRESET_DEFAULTS.get(preset_id, PRESET_DEFAULTS[BUILDING_STATIC]))


def motion_type_for_preset(preset_id: str) -> str:
    if preset_id == RUBBLE_SPHERE:
        return "SPHERE_INERTIA"
    if preset_id == RUBBLE_BOX:
        return "BOX_INERTIA"
    return "FIXED"


def deactivator_present_for_preset(preset_id: str) -> bool:
    return preset_id != BUILDING_STATIC


def infer_preset_from_motion_type(motion_type: str) -> str:
    normalized = (motion_type or "FIXED").strip().upper()
    if normalized.startswith("MOTION_"):
        normalized = normalized[len("MOTION_") :]
    if normalized == "SPHERE_INERTIA":
        return RUBBLE_SPHERE
    if normalized == "BOX_INERTIA":
        return RUBBLE_BOX
    return BUILDING_STATIC


def mass_value_from_preset(mass_preset: str) -> float | None:
    if not mass_preset or mass_preset == "CUSTOM":
        return None
    if not mass_preset.startswith("MASS_"):
        return None
    number_text = mass_preset[len("MASS_") :].replace("_", ".")
    try:
        return float(number_text)
    except ValueError:
        return None


def mass_preset_for_value(value: float) -> str:
    rounded = round(float(value), 3)
    for preset_value in MASS_PRESET_VALUES:
        if abs(rounded - preset_value) <= 1.0e-3:
            label = str(int(preset_value)) if preset_value.is_integer() else str(preset_value)
            return f"MASS_{label.replace('.', '_')}"
    return "CUSTOM"


def preset_label(preset_id: str) -> str:
    for value, label, _description in PRESET_ITEMS:
        if value == preset_id:
            return label
    return preset_id


__all__: List[str] = [
    "BUILDING_STATIC",
    "CENTER_OF_MASS_MODE_ITEMS",
    "DEACTIVATION_CLASS_ITEMS",
    "FRICTION_QUICK_VALUES",
    "HK_REAL_MAX",
    "MASS_PRESET_ITEMS",
    "PENETRATION_QUICK_VALUES",
    "PRESET_DEFAULTS",
    "PRESET_ITEMS",
    "QUALITY_TYPE_ITEMS",
    "RESTITUTION_QUICK_VALUES",
    "RUBBLE_BOX",
    "RUBBLE_SPHERE",
    "deactivator_present_for_preset",
    "get_preset_defaults",
    "infer_preset_from_motion_type",
    "mass_preset_for_value",
    "mass_value_from_preset",
    "motion_type_for_preset",
    "preset_label",
]