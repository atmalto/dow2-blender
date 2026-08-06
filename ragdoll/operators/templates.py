from __future__ import annotations

from bpy.props import StringProperty
from bpy.types import Operator

from .. import load_template_library
from ..authoring import (
    RAGDOLL_BODY_ANGULAR_DAMPING_PROP,
    RAGDOLL_BODY_COLLISION_FILTER_PROP,
    RAGDOLL_BODY_FRICTION_PROP,
    RAGDOLL_BODY_LINEAR_DAMPING_PROP,
    RAGDOLL_BODY_LENGTH_PROP,
    RAGDOLL_BODY_MOTION_TYPE_PROP,
    RAGDOLL_BODY_QUALITY_TYPE_PROP,
    RAGDOLL_BODY_RADIUS_PROP,
    RAGDOLL_BODY_RESTITUTION_PROP,
    RAGDOLL_BODY_SHAPE_PROP,
    active_ragdoll_bone,
    apply_body_data_to_object,
    apply_constraint_data_to_bone,
    find_ragdoll_skeleton_for_body,
    resolve_ragdoll_body_object,
)
from ..templates import resolve_template_bundle as resolve_template_bundle_from_model_folder


_ADVANCED_BODY_FIELDS = ("shape_type", "radius", "vertex_a", "vertex_b", "half_extents", "mass", "position", "rotation")
_BASIC_CONSTRAINT_FIELDS = ("twist_min", "twist_max", "cone_angle", "plane_min", "plane_max", "hinge_min", "hinge_max", "friction_torque")
_ADVANCED_CONSTRAINT_FIELDS = ("constraint_type", "pivot_a", "pivot_b", "twist_axis_a", "twist_axis_b", "plane_axis_a", "plane_axis_b")
_TEMPLATED_CONSTRAINT_FIELDS = ()


def _resolve_template_bundle_for_loader(settings, library=None):
    active_library = library or load_template_library()
    model = (getattr(settings, "template_model", "") or "").strip()
    folder = (getattr(settings, "template_folder", "") or "").strip()
    if not model or model.startswith("__") or not folder or folder.startswith("__"):
        raise RuntimeError("Choose a template model and folder before loading a preset")
    return resolve_template_bundle_from_model_folder(model, folder, library=active_library)


def _copy_template_fields(source, field_names):
    copied = {}
    for field_name in field_names:
        if field_name not in source:
            continue
        value = source[field_name]
        copied[field_name] = list(value) if isinstance(value, list) else value
    return copied


def _apply_body_template_category(body_object, template_body, category):
    if template_body is None:
        return False

    if category == "basic":
        applied = False
        if "shape_type" in template_body:
            body_object[RAGDOLL_BODY_SHAPE_PROP] = str(template_body["shape_type"]).upper()
            applied = True
        if "radius" in template_body:
            body_object[RAGDOLL_BODY_RADIUS_PROP] = float(template_body["radius"])
            applied = True
        if "capsule_length" in template_body and template_body["capsule_length"] is not None:
            body_object[RAGDOLL_BODY_LENGTH_PROP] = float(template_body["capsule_length"])
            applied = True
        return applied

    if category == "advanced":
        payload = _copy_template_fields(template_body, _ADVANCED_BODY_FIELDS)
        if not payload:
            return False
        apply_body_data_to_object(body_object, payload, apply_world_transform="position" in payload or "rotation" in payload)
        return True

    applied = False
    prop_map = {
        "friction": RAGDOLL_BODY_FRICTION_PROP,
        "motion_type": RAGDOLL_BODY_MOTION_TYPE_PROP,
        "linear_damping": RAGDOLL_BODY_LINEAR_DAMPING_PROP,
        "angular_damping": RAGDOLL_BODY_ANGULAR_DAMPING_PROP,
        "collision_filter_info": RAGDOLL_BODY_COLLISION_FILTER_PROP,
        "quality_type": RAGDOLL_BODY_QUALITY_TYPE_PROP,
        "restitution": RAGDOLL_BODY_RESTITUTION_PROP,
    }
    for field_name, prop_name in prop_map.items():
        if field_name not in template_body:
            continue
        value = template_body[field_name]
        if value is None:
            continue
        body_object[prop_name] = value
        applied = True
    return applied


def _apply_constraint_template_category(bone, template_constraint, category):
    if bone is None or bone.parent is None or template_constraint is None:
        return False

    field_map = {
        "basic": _BASIC_CONSTRAINT_FIELDS,
        "advanced": _ADVANCED_CONSTRAINT_FIELDS,
        "templated": _TEMPLATED_CONSTRAINT_FIELDS,
    }
    payload = _copy_template_fields(template_constraint, field_map[category])
    if not payload:
        return False
    apply_constraint_data_to_bone(bone, payload)
    return True


class DOW2_OT_apply_ragdoll_template_category(Operator):
    """Load one template category onto the active rigid body and its inferred constraint target"""

    bl_idname = "dow2.apply_ragdoll_template_category"
    bl_label = "Load Ragdoll Template Category"
    bl_options = {"REGISTER", "UNDO"}

    category: StringProperty(default="basic")
    target: StringProperty(default="body")

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        if self.category not in {"basic", "advanced", "templated"}:
            self.report({"ERROR"}, f"Unknown template category: {self.category}")
            return {"CANCELLED"}
        if self.target not in {"body", "constraint", "both"}:
            self.report({"ERROR"}, f"Unknown template target: {self.target}")
            return {"CANCELLED"}

        body_object = resolve_ragdoll_body_object(context.active_object)
        if body_object is None:
            self.report({"ERROR"}, "Select a ragdoll rigid body before loading a template preset")
            return {"CANCELLED"}

        settings = context.scene.dow2_ragdoll_settings
        skeleton_object = find_ragdoll_skeleton_for_body(body_object)
        linked_bone = active_ragdoll_bone(context)
        if skeleton_object is None or linked_bone is None:
            self.report({"ERROR"}, "Could not resolve the linked ragdoll bone for the selected rigid body")
            return {"CANCELLED"}

        template_bone_name = (getattr(settings, "template_bone", "") or "").strip()
        if not template_bone_name or template_bone_name.startswith("__"):
            self.report({"ERROR"}, "Choose a template bone before loading a preset")
            return {"CANCELLED"}

        try:
            library = load_template_library()
            template_bundle = _resolve_template_bundle_for_loader(settings, library=library)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        template_body = (template_bundle.get("bodies") or {}).get(template_bone_name)
        template_constraint = (template_bundle.get("constraints") or {}).get(template_bone_name)
        if template_body is None and template_constraint is None:
            self.report({"ERROR"}, f"Template bone {template_bone_name!r} has no body or constraint data in the selected template")
            return {"CANCELLED"}

        body_applied = False
        constraint_applied = False
        if self.target in {"body", "both"}:
            body_applied = _apply_body_template_category(body_object, template_body, self.category)
        if self.target in {"constraint", "both"}:
            constraint_applied = _apply_constraint_template_category(linked_bone, template_constraint, self.category)

        if not body_applied and not constraint_applied:
            if self.target == "constraint" and self.category == "templated":
                self.report({"INFO"}, "No dedicated template-only constraint fields are defined for this category")
                return {"FINISHED"}
            if self.target == "constraint" and linked_bone.parent is None:
                self.report({"INFO"}, "Root body has no parent constraint to load a preset onto")
                return {"FINISHED"}
            self.report({"WARNING"}, "No matching fields were applied for the selected template target")
            return {"CANCELLED"}

        category_label = self.category.capitalize()
        if body_applied and constraint_applied:
            self.report({"INFO"}, f"Loaded {category_label} body and constraint preset fields")
        elif body_applied:
            self.report({"INFO"}, f"Loaded {category_label} body preset fields")
        else:
            self.report({"INFO"}, f"Loaded {category_label} constraint preset fields")
        return {"FINISHED"}