import json
from functools import lru_cache
from pathlib import Path

from .math_utils import float_list_from_text, matrix3x3_to_quat, transform_rows_and_translation


def _analysis_outputs_dir():
    return Path(__file__).resolve().parents[1] / "ragdoll_workspace" / "working" / "ragdoll_workspace_old" / "analysis_outputs"


def _data_dir():
    return Path(__file__).resolve().parent / "data"


FROZEN_TEMPLATE_LIBRARY_PATH = _data_dir() / "template_library.json"
TEMPLATE_INVENTORY_PATH = _analysis_outputs_dir() / "ragdoll_batch_inventory.json"


def _parse_template_source_path(hkx_path):
    parts = Path(str(hkx_path).replace("\\", "/")).parts
    art_index = parts.index("art")
    animations_index = parts.index("animations")
    race = parts[art_index + 1]
    unit = parts[animations_index - 1]
    animation_set = parts[animations_index + 1]
    return race, unit, animation_set


def _shape_type_from_class(shape_class):
    if shape_class == "hkCapsuleShape":
        return "capsule"
    if shape_class == "hkSphereShape":
        return "sphere"
    if shape_class == "hkBoxShape":
        return "box"
    return None


def _normalize_body_template(body):
    shape = body.get("shape") or {}
    motion = body.get("motion") or {}
    collidable = body.get("collidable") or {}
    material = body.get("material") or {}

    transform_values = float_list_from_text(motion.get("transform"))
    rows, translation = transform_rows_and_translation(transform_values)
    transposed_rows = [
        [rows[0][0], rows[1][0], rows[2][0]],
        [rows[0][1], rows[1][1], rows[2][1]],
        [rows[0][2], rows[1][2], rows[2][2]],
    ]
    rotation = matrix3x3_to_quat(transposed_rows)

    inertia_and_mass_inv = float_list_from_text(motion.get("inertiaAndMassInv"))
    mass = None
    if len(inertia_and_mass_inv) >= 4 and inertia_and_mass_inv[3] not in (0.0, 0):
        mass = 1.0 / inertia_and_mass_inv[3]

    vertex_a = [float(value) for value in (shape.get("vertexAValues") or [])[:3]]
    vertex_b = [float(value) for value in (shape.get("vertexBValues") or [])[:3]]
    half_extents = [float(value) for value in (shape.get("halfExtentsValues") or [])[:3]]
    capsule_length = None
    if len(vertex_a) == 3 and len(vertex_b) == 3:
        delta_x = vertex_b[0] - vertex_a[0]
        delta_y = vertex_b[1] - vertex_a[1]
        delta_z = vertex_b[2] - vertex_a[2]
        capsule_length = (delta_x * delta_x + delta_y * delta_y + delta_z * delta_z) ** 0.5

    return {
        "name": body["name"],
        "shape_class": shape.get("class"),
        "shape_type": _shape_type_from_class(shape.get("class")),
        "radius": float((shape.get("radiusValues") or [0.0])[0]),
        "vertex_a": vertex_a,
        "vertex_b": vertex_b,
        "half_extents": half_extents,
        "capsule_length": capsule_length,
        "mass": mass,
        "friction": float(material.get("friction")) if material.get("friction") is not None else None,
        "restitution": float(material.get("restitution")) if material.get("restitution") is not None else None,
        "motion_type": motion.get("type"),
        "position": [float(value) for value in translation[:3]],
        "rotation": [float(rotation[0]), float(rotation[1]), float(rotation[2]), float(rotation[3])],
        "linear_damping": float(motion.get("linearDamping")) if motion.get("linearDamping") is not None else None,
        "angular_damping": float(motion.get("angularDamping")) if motion.get("angularDamping") is not None else None,
        "collision_filter_info": int(collidable.get("collisionFilterInfo")) if collidable.get("collisionFilterInfo") is not None else None,
        "quality_type": int(collidable.get("objectQualityType")) if collidable.get("objectQualityType") is not None else None,
        "source_object": body.get("objectRef"),
    }


def _normalize_constraint_template(constraint):
    data = constraint.get("data") or {}
    transforms = data.get("transforms") or {}
    rows_a, pivot_a = transform_rows_and_translation(transforms.get("transformAValues") or float_list_from_text(transforms.get("transformA")))
    rows_b, pivot_b = transform_rows_and_translation(transforms.get("transformBValues") or float_list_from_text(transforms.get("transformB")))

    normalized = {
        "name": constraint["name"],
        "data_class": constraint["dataClass"],
        "constraint_type": "limited_hinge" if constraint["dataClass"] == "hkLimitedHingeConstraintData" else "ragdoll",
        "entity_names": list(constraint.get("entityNames") or []),
        "pivot_a": [float(pivot_a[0]), float(pivot_a[1]), float(pivot_a[2])],
        "pivot_b": [float(pivot_b[0]), float(pivot_b[1]), float(pivot_b[2])],
        "twist_axis_a": [float(rows_a[0][0]), float(rows_a[0][1]), float(rows_a[0][2])],
        "twist_axis_b": [float(rows_b[0][0]), float(rows_b[0][1]), float(rows_b[0][2])],
        "plane_axis_a": [float(rows_a[1][0]), float(rows_a[1][1]), float(rows_a[1][2])],
        "plane_axis_b": [float(rows_b[1][0]), float(rows_b[1][1]), float(rows_b[1][2])],
    }

    if constraint["dataClass"] == "hkLimitedHingeConstraintData":
        ang_limit = data.get("angLimit") or {}
        ang_friction = data.get("angFriction") or {}
        normalized.update(
            {
                "hinge_min": float(ang_limit.get("minAngle")),
                "hinge_max": float(ang_limit.get("maxAngle")),
                "friction_torque": float(ang_friction.get("maxFrictionTorque")),
            }
        )
    else:
        twist_limit = data.get("twistLimit") or {}
        cone_limit = data.get("coneLimit") or {}
        planes_limit = data.get("planesLimit") or {}
        ang_friction = data.get("angFriction") or {}
        normalized.update(
            {
                "twist_min": float(twist_limit.get("minAngle")),
                "twist_max": float(twist_limit.get("maxAngle")),
                "cone_angle": float(cone_limit.get("maxAngle")),
                "plane_min": float(planes_limit.get("minAngle")),
                "plane_max": float(planes_limit.get("maxAngle")),
                "friction_torque": float(ang_friction.get("maxFrictionTorque")),
            }
        )

    return normalized


def build_template_library(inventory_records):
    templates = {}
    tree = {}

    for item in inventory_records:
        race, unit, animation_set = _parse_template_source_path(item["hkxPath"])
        template_id = f"{race}/{unit}/{animation_set}"
        bundle = {
            "template_id": template_id,
            "race": race,
            "model": unit,
            "unit": unit,
            "folder": animation_set,
            "animation_set": animation_set,
            "source_hkx_path": item["hkxPath"],
            "source_xml_path": item.get("xmlPath"),
            "bodies": {},
            "constraints": {},
        }

        for body in item.get("rigidBodies") or []:
            bundle["bodies"][body["name"]] = _normalize_body_template(body)

        for constraint in item.get("constraintInstances") or []:
            normalized = _normalize_constraint_template(constraint)
            existing = bundle["constraints"].get(constraint["name"])
            if existing is not None and existing != normalized:
                raise ValueError(
                    f"Constraint template collision for {template_id}:{constraint['name']} with non-identical normalized payloads"
                )
            bundle["constraints"][constraint["name"]] = normalized

        bundle["bone_names"] = sorted(set(bundle["bodies"]) | set(bundle["constraints"]))

        templates[template_id] = bundle
        tree.setdefault(race, {}).setdefault(unit, {})[animation_set] = template_id

    return {
        "version": 1,
        "source_inventory": str(TEMPLATE_INVENTORY_PATH),
        "tree": tree,
        "templates": templates,
    }


def _with_template_aliases(library):
    templates = library.get("templates") or {}
    for bundle in templates.values():
        if "model" not in bundle and bundle.get("unit") is not None:
            bundle["model"] = bundle["unit"]
        if "folder" not in bundle and bundle.get("animation_set") is not None:
            bundle["folder"] = bundle["animation_set"]
        if "bone_names" not in bundle:
            bundle["bone_names"] = sorted(set(bundle.get("bodies") or {}) | set(bundle.get("constraints") or {}))
    return library


@lru_cache(maxsize=1)
def load_template_library(template_path=None):
    source_path = Path(template_path) if template_path else FROZEN_TEMPLATE_LIBRARY_PATH
    with source_path.open("r", encoding="utf-8") as handle:
        return _with_template_aliases(json.load(handle))


def build_template_library_from_inventory(inventory_path=None):
    source_path = Path(inventory_path) if inventory_path else TEMPLATE_INVENTORY_PATH
    with source_path.open("r", encoding="utf-8") as handle:
        inventory_records = json.load(handle)
    return build_template_library(inventory_records)


def write_frozen_template_library(output_path=None, inventory_path=None):
    target_path = Path(output_path) if output_path else FROZEN_TEMPLATE_LIBRARY_PATH
    library = build_template_library_from_inventory(inventory_path=inventory_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(library, indent=2), encoding="utf-8")
    return library


def list_template_tree(library=None):
    active_library = library or load_template_library()
    return active_library["tree"]


def list_template_models(library=None):
    active_library = library or load_template_library()
    models = {
        (bundle.get("model") or bundle.get("unit"))
        for bundle in (active_library.get("templates") or {}).values()
        if (bundle.get("model") or bundle.get("unit"))
    }
    return sorted(models)


def list_template_folders(model, library=None):
    active_library = library or load_template_library()
    folders = {
        (bundle.get("folder") or bundle.get("animation_set"))
        for bundle in (active_library.get("templates") or {}).values()
        if (bundle.get("model") or bundle.get("unit")) == model and (bundle.get("folder") or bundle.get("animation_set"))
    }
    return sorted(folders)


def resolve_template_bundle(model, folder, library=None):
    active_library = library or load_template_library()
    matches = [
        bundle
        for bundle in (active_library.get("templates") or {}).values()
        if (bundle.get("model") or bundle.get("unit")) == model
        and (bundle.get("folder") or bundle.get("animation_set")) == folder
    ]
    if not matches:
        raise ValueError(f"Unknown template selection: model={model!r}, folder={folder!r}")
    if len(matches) > 1:
        ids = ", ".join(bundle["template_id"] for bundle in matches)
        raise ValueError(f"Ambiguous template selection for {model}/{folder}: {ids}")
    return matches[0]


def list_template_bones(model, folder, library=None):
    bundle = resolve_template_bundle(model, folder, library=library)
    return list(bundle.get("bone_names") or [])


def apply_body_template(rigid_body, template_body):
    if template_body.get("shape_type"):
        rigid_body["shape_type"] = template_body["shape_type"]
    if template_body.get("radius") is not None:
        rigid_body["radius"] = template_body["radius"]
    if template_body.get("vertex_a"):
        rigid_body["vertex_a"] = list(template_body["vertex_a"])
    if template_body.get("vertex_b"):
        rigid_body["vertex_b"] = list(template_body["vertex_b"])
    if template_body.get("half_extents"):
        rigid_body["half_extents"] = list(template_body["half_extents"])
    if template_body.get("mass") is not None:
        rigid_body["mass"] = template_body["mass"]
    if template_body.get("friction") is not None:
        rigid_body["friction"] = template_body["friction"]
    if template_body.get("restitution") is not None:
        rigid_body["restitution"] = template_body["restitution"]
    if template_body.get("motion_type"):
        rigid_body["motion_type"] = template_body["motion_type"]
    if template_body.get("position"):
        rigid_body["position"] = list(template_body["position"])
    if template_body.get("rotation"):
        rigid_body["rotation"] = list(template_body["rotation"])
    if template_body.get("linear_damping") is not None:
        rigid_body["linear_damping"] = template_body["linear_damping"]
    if template_body.get("angular_damping") is not None:
        rigid_body["angular_damping"] = template_body["angular_damping"]
    if template_body.get("collision_filter_info") is not None:
        rigid_body["collision_filter_info"] = template_body["collision_filter_info"]
    if template_body.get("quality_type") is not None:
        rigid_body["quality_type"] = template_body["quality_type"]
    return rigid_body


def apply_constraint_template(constraint, template_constraint, ragdoll_bone_to_idx):
    entity_names = template_constraint.get("entity_names") or []
    if len(entity_names) == 2:
        constraint["body_a_index"] = ragdoll_bone_to_idx[entity_names[0]]
        constraint["body_b_index"] = ragdoll_bone_to_idx[entity_names[1]]

    constraint["constraint_type"] = template_constraint["constraint_type"]
    constraint["pivot_a"] = list(template_constraint["pivot_a"])
    constraint["pivot_b"] = list(template_constraint["pivot_b"])
    constraint["twist_axis_a"] = list(template_constraint["twist_axis_a"])
    constraint["twist_axis_b"] = list(template_constraint["twist_axis_b"])
    constraint["plane_axis_a"] = list(template_constraint["plane_axis_a"])
    constraint["plane_axis_b"] = list(template_constraint["plane_axis_b"])
    constraint["friction_torque"] = template_constraint.get("friction_torque", 0.0)

    if template_constraint["constraint_type"] == "limited_hinge":
        constraint["hinge_min"] = template_constraint["hinge_min"]
        constraint["hinge_max"] = template_constraint["hinge_max"]
    else:
        constraint["twist_min"] = template_constraint["twist_min"]
        constraint["twist_max"] = template_constraint["twist_max"]
        constraint["cone_angle"] = template_constraint["cone_angle"]
        constraint["plane_min"] = template_constraint["plane_min"]
        constraint["plane_max"] = template_constraint["plane_max"]

    return constraint