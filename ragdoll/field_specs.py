from dataclasses import dataclass
from math import inf, pi


def radians_to_degrees(value):
    return value * 180.0 / pi


@dataclass(frozen=True)
class NumericRange:
    hard_min: float
    hard_max: float
    observed_min: float
    observed_max: float


@dataclass(frozen=True)
class FieldSpec:
    identifier: str
    label: str
    category: str
    storage_unit: str
    display_unit: str
    numeric_range: NumericRange | None
    description: str
    evidence: str

# exposed, can be preset or manually edited by user
EXPOSED_FIELD_SPECS = {
    "shape_type": FieldSpec(
        identifier="shape_type",
        label="Body Shape",
        category="exposed",
        storage_unit="enum",
        display_unit="enum",
        numeric_range=None,
        description="Rigid body shape selector. Capsules cover most shipped assets; spheres and boxes exist but are uncommon.",
        evidence="Shipped batch uses mostly capsules with a small number of spheres and boxes.",
    ),
    "capsule_radius": FieldSpec(
        identifier="capsule_radius",
        label="Capsule Radius",
        category="exposed",
        storage_unit="havok_length",
        display_unit="scene_length",
        numeric_range=NumericRange(0.0, inf, 0.033516, 0.367357),
        description="Radius for capsule and sphere rigid bodies. Stored directly in Havok length units.",
        evidence="Observed shipped radius range across 55 ragdoll assets.",
    ),
    "capsule_length": FieldSpec(
        identifier="capsule_length",
        label="Capsule Length",
        category="exposed",
        storage_unit="havok_length",
        display_unit="scene_length",
        numeric_range=NumericRange(0.0, inf, 0.005892, 2.835086),
        description="Friendly capsule centerline length derived from vertexA and vertexB. Stored/exported as explicit endpoints.",
        evidence="Observed shipped capsule endpoint distance range across 55 ragdoll assets.",
    ),
    "twist_min": FieldSpec(
        identifier="twist_min",
        label="Twist Min",
        category="exposed",
        storage_unit="radians",
        display_unit="degrees",
        numeric_range=NumericRange(-pi, pi, -pi, 0.0),
        description="Minimum ragdoll twist angle. UI should display degrees, exporter converts to radians.",
        evidence="Havok ragdoll API examples use radians; shipped batch spans [-pi, 0].",
    ),
    "twist_max": FieldSpec(
        identifier="twist_max",
        label="Twist Max",
        category="exposed",
        storage_unit="radians",
        display_unit="degrees",
        numeric_range=NumericRange(-pi, pi, 0.0, pi),
        description="Maximum ragdoll twist angle. UI should display degrees, exporter converts to radians.",
        evidence="Havok ragdoll API examples use radians; shipped batch spans [0, pi].",
    ),
    "cone_angle": FieldSpec(
        identifier="cone_angle",
        label="Cone Max",
        category="exposed",
        storage_unit="radians",
        display_unit="degrees",
        numeric_range=NumericRange(0.0, pi, 0.005236, 1.440398),
        description="Maximum ragdoll cone angle. UI should display degrees even though Havok stores radians.",
        evidence="Havok ragdoll APIs use radians; shipped batch cone max spans 0.3° to 82.5°.",
    ),
    "plane_min": FieldSpec(
        identifier="plane_min",
        label="Plane Min",
        category="exposed",
        storage_unit="radians",
        display_unit="degrees",
        numeric_range=NumericRange(-pi, 0.0, -1.308997, 0.0),
        description="Minimum ragdoll plane limit angle. UI should display degrees, exporter converts to radians.",
        evidence="Havok ragdoll APIs use radians; shipped batch plane min spans about -75° to 0°.",
    ),
    "plane_max": FieldSpec(
        identifier="plane_max",
        label="Plane Max",
        category="exposed",
        storage_unit="radians",
        display_unit="degrees",
        numeric_range=NumericRange(0.0, pi, 0.041888, 0.785398),
        description="Maximum ragdoll plane limit angle. UI should display degrees, exporter converts to radians.",
        evidence="Havok ragdoll APIs use radians; shipped batch plane max spans about 2.4° to 45°.",
    ),
    "hinge_min": FieldSpec(
        identifier="hinge_min",
        label="Hinge Min",
        category="exposed",
        storage_unit="radians",
        display_unit="degrees",
        numeric_range=NumericRange(-pi, 0.0, -2.089159, 0.0),
        description="Minimum limited hinge angle. UI should display degrees, exporter converts to radians.",
        evidence="Havok limited hinge docs define angular limits in radians with default [-pi, pi]; shipped batch spans about -119.7° to 0°.",
    ),
    "hinge_max": FieldSpec(
        identifier="hinge_max",
        label="Hinge Max",
        category="exposed",
        storage_unit="radians",
        display_unit="degrees",
        numeric_range=NumericRange(0.0, pi, 0.070686, 1.822124),
        description="Maximum limited hinge angle. UI should display degrees, exporter converts to radians.",
        evidence="Havok limited hinge docs define angular limits in radians with default [-pi, pi]; shipped batch spans about 4.0° to 104.4°.",
    ),
    "friction_torque": FieldSpec(
        identifier="friction_torque",
        label="Joint Friction Torque",
        category="exposed",
        storage_unit="torque",
        display_unit="torque",
        numeric_range=NumericRange(0.0, inf, 0.0, 1000.0),
        description="Maximum angular friction torque. Ragdoll joints reach 1000 in the shipped batch, hinge joints reach 60.",
        evidence="Havok docs describe friction torque directly; shipped batch spans 0..1000 for ragdolls and 0..60 for limited hinges.",
    ),
}


LOCKD_BACKEND_FIELDS = {
    "priority": "PRIORITY_PSI",
    "wantRuntime": False,
    "constraintModifiers": None,
    "userData": 0,
    "responseType": "RESPONSE_SIMPLE_CONTACT",
    "qualityType": 4,
    "restitution": 0.0,
    "coneMeasurementMode": "ZERO_WHEN_VECTORS_ALIGNED",
    "planeMeasurementMode": "ZERO_WHEN_VECTORS_PERPENDICULAR",
}

LOCKED_BACKEND_FIELDS = LOCKD_BACKEND_FIELDS

# presets
TEMPLATE_DRIVEN_FIELDS = {
    "collision_filter_info",
    "body_material_friction",
    "motion_type",
    "linear_damping",
    "angular_damping",
    "local_joint_frames",
    "local_joint_pivots",
    "local_joint_axes",
    "exotic_shape_type",
}


ANGLE_FIELDS = {
    "twist_min",
    "twist_max",
    "cone_angle",
    "plane_min",
    "plane_max",
    "hinge_min",
    "hinge_max",
}


def to_display_value(field_name, storage_value):
    if field_name in ANGLE_FIELDS:
        return radians_to_degrees(storage_value)
    return storage_value


def to_storage_value(field_name, display_value):
    if field_name in ANGLE_FIELDS:
        return display_value * pi / 180.0
    return display_value