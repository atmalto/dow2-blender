import bpy
from bpy.types import Panel

from ..ragdoll import EXPOSED_FIELD_SPECS, TEMPLATE_DRIVEN_FIELDS
from ..ragdoll.authoring.preview import sync_constraint_preview_objects
from ..ragdoll.authoring import (
    body_shape_label,
    RAGDOLL_BODY_BONE_PROP,
    RAGDOLL_BODY_SHAPE_PROP,
    RAGDOLL_BODY_COLLISION_FILTER_PROP,
    RAGDOLL_BODY_FRICTION_PROP,
    RAGDOLL_BODY_HEIGHT_PROP,
    RAGDOLL_BODY_HALF_EXTENTS_PROP,
    RAGDOLL_BODY_LINEAR_DAMPING_PROP,
    RAGDOLL_BODY_LENGTH_PROP,
    RAGDOLL_BODY_MASS_PROP,
    RAGDOLL_MIN_BODY_DIMENSION,
    RAGDOLL_BODY_MOTION_TYPE_PROP,
    RAGDOLL_BODY_QUALITY_TYPE_PROP,
    RAGDOLL_BODY_RADIUS_PROP,
    RAGDOLL_BODY_RESTITUTION_PROP,
    RAGDOLL_BODY_SHAPE_OFFSET_PROP,
    RAGDOLL_BODY_VERTEX_A_PROP,
    RAGDOLL_BODY_VERTEX_B_PROP,
    RAGDOLL_BODY_ANGULAR_DAMPING_PROP,
    RAGDOLL_SOURCE_BONE_PROP,
    RAGDOLL_CONE_ANGLE_PROP,
    RAGDOLL_CONSTRAINT_TYPE_PROP,
    RAGDOLL_FRICTION_TORQUE_PROP,
    RAGDOLL_HINGE_MAX_PROP,
    RAGDOLL_HINGE_MIN_PROP,
    RAGDOLL_PIVOT_A_PROP,
    RAGDOLL_PIVOT_B_PROP,
    RAGDOLL_PLANE_MAX_PROP,
    RAGDOLL_PLANE_MIN_PROP,
    RAGDOLL_PLANE_AXIS_A_PROP,
    RAGDOLL_PLANE_AXIS_B_PROP,
    RAGDOLL_TWIST_MAX_PROP,
    RAGDOLL_TWIST_MIN_PROP,
    RAGDOLL_TWIST_AXIS_A_PROP,
    RAGDOLL_TWIST_AXIS_B_PROP,
    active_body_dimensions,
    active_ragdoll_bone,
    find_ragdoll_body_for_bone,
    find_ragdoll_skeleton_for_body,
    find_source_armature,
    is_ragdoll_body_object,
    normalize_body_shape,
    is_ragdoll_skeleton_object,
    resolve_ragdoll_body_object,
    read_constraint_settings,
    resolve_selected_ragdoll_bones,
)


_RAGDOLL_BODY_TOOLTIPS = {
    RAGDOLL_BODY_RADIUS_PROP: (
        "Capsule or sphere radius, or box half-width on the local X axis. "
        "Havok boxes are stored with half extents, so full width is double this value."
    ),
    RAGDOLL_BODY_LENGTH_PROP: (
        "Capsule end-to-end length or box length on the local Y axis."
    ),
    RAGDOLL_BODY_HEIGHT_PROP: (
        "Box height on the local Z axis. Sphere and capsule height are derived from radius."
    ),
    RAGDOLL_BODY_SHAPE_OFFSET_PROP: (
        "Local translation of the collision shape relative to the body origin and joint. "
        "Use this to author Havok translated convex primitives without moving the joint frame itself."
    ),
    RAGDOLL_BODY_RESTITUTION_PROP: (
        "How springy or bouncy the limb feels after impact or stretching. "
        "High restitution feels rubbery or cartoon-like. Low restitution feels heavy, dead-weight, or sandbag-like."
    ),
}

_RAGDOLL_CONSTRAINT_TOOLTIPS = {
    RAGDOLL_TWIST_MIN_PROP: (
        "How far the limb can rotate around its own length. "
        "Example: a forearm twisting palm-up versus palm-down."
    ),
    RAGDOLL_TWIST_MAX_PROP: (
        "How far the limb can rotate around its own length. "
        "Example: a forearm twisting palm-up versus palm-down."
    ),
    RAGDOLL_CONE_ANGLE_PROP: (
        "How freely the limb can swing away from its resting direction. "
        "A human shoulder uses a large cone. A horse leg uses a narrow cone."
    ),
    RAGDOLL_HINGE_MIN_PROP: (
        "Lower rotation limit around one hinge axis. "
        "Use this for joints that should not twist or cone, only rotate like a door hinge or a simple elbow. "
        "More negative values allow farther rotation on the negative side of that hinge."
    ),
    RAGDOLL_HINGE_MAX_PROP: (
        "Upper rotation limit around one hinge axis. "
        "Use this for joints that should not twist or cone, only rotate like a door hinge or a simple elbow. "
        "Larger positive values allow farther rotation on the positive side of that hinge."
    ),
    RAGDOLL_PLANE_MIN_PROP: (
        "Directional limit inside the cone that cuts off one side of the swing range. "
        "Use it to restrict motion in a specific direction, like a knee allowing almost no forward bend."
    ),
    RAGDOLL_PLANE_MAX_PROP: (
        "Directional limit inside the cone that cuts off the opposite side of the swing range. "
        "Use it to allow wide motion one way and tighter motion the other way, like an arm swinging farther forward than backward."
    ),
}


def _update_idprop_ui(owner, prop_name: str, **kwargs) -> None:
    if prop_name not in owner:
        return
    try:
        owner.id_properties_ui(prop_name).update(**kwargs)
    except Exception:
        return


def _ensure_authoring_tooltips(body_object, bone) -> None:
    for prop_name, description in _RAGDOLL_BODY_TOOLTIPS.items():
        _update_idprop_ui(body_object, prop_name, description=description)
    for prop_name in (RAGDOLL_BODY_RADIUS_PROP, RAGDOLL_BODY_LENGTH_PROP, RAGDOLL_BODY_HEIGHT_PROP):
        _update_idprop_ui(body_object, prop_name, min=RAGDOLL_MIN_BODY_DIMENSION, soft_min=RAGDOLL_MIN_BODY_DIMENSION)
    for prop_name, description in _RAGDOLL_CONSTRAINT_TOOLTIPS.items():
        _update_idprop_ui(bone, prop_name, description=description)


def _active_armature_label(context):
    active_object = context.view_layer.objects.active
    if active_object is not None and active_object.type == "ARMATURE" and not is_ragdoll_skeleton_object(active_object):
        return active_object.name, "ARMATURE_DATA"
    source_armature = find_source_armature(context)
    if source_armature is not None:
        return source_armature.name, "ARMATURE_DATA"
    return "Select an armature to export", "ERROR"


def _draw_preface(layout, settings):
    preface_header, preface_body = layout.panel("dow2_ragdoll_preface", default_closed=False)
    preface_header.label(text="Preface", icon="HIDE_OFF")
    if preface_body is None:
        return
    preface_body.prop(settings, "preview_constraints", text="Show Constraint Previews")


def _draw_import_section(layout, settings):
    import_header, import_body = layout.panel("dow2_ragdoll_import", default_closed=False)
    import_header.label(text="Import", icon="IMPORT")
    if import_body is None:
        return

    info_box = import_body.box()
    info_box.label(text="Choose a ragdoll HKX and its companion .model then click import.")

    ragdoll_row = import_body.row(align=True)
    ragdoll_row.prop(settings, "ragdoll_import_path", text="Ragdoll HKX")
    ragdoll_row.operator("dow2.pick_ragdoll_import_path", text="", icon="FILE_FOLDER")

    model_row = import_body.row(align=True)
    model_row.prop(settings, "ragdoll_model_path", text="Companion .model")
    model_row.operator("dow2.pick_ragdoll_model_path", text="", icon="FILE_FOLDER")

    import_body.prop(settings, "ragdoll_name", text="Target Name")

    import_button_row = import_body.row()
    import_button_row.enabled = bool(str(settings.ragdoll_import_path or "").strip())
    import_button_row.operator("dow2.import_ragdoll_hkx", text="Import Ragdoll HKX", icon="IMPORT")


def _draw_skeleton_section(layout, context, settings):
    skeleton_header, skeleton_body = layout.panel("dow2_ragdoll_skeleton_creation", default_closed=False)
    skeleton_header.label(text="1. Skeleton Creation", icon="ARMATURE_DATA")
    if skeleton_body is None:
        return

    armature_label, armature_icon = _active_armature_label(context)
    skeleton_body.label(text=armature_label, icon=armature_icon)
    skeleton_body.prop(settings, "ragdoll_name")

    info_box = skeleton_body.box()
    info_box.label(text=f"Collection: ragdoll_skeleton::{settings.ragdoll_name or 'ragdoll'}", icon="OUTLINER_COLLECTION")
    info_box.label(text="Creates a reduced ragdoll hierarchy from the source skeleton")
    skeleton_body.operator("dow2.create_ragdoll_skeleton", icon="ARMATURE_DATA")


def _draw_body_section(layout, context, settings):
    body_header, body_body = layout.panel("dow2_ragdoll_body_creation", default_closed=False)
    body_header.label(text="2. Rigid Body Creation / Edit", icon="MESH_ICOSPHERE")
    if body_body is None:
        return

    active_object = context.active_object
    selected_bones = resolve_selected_ragdoll_bones(context)
    if selected_bones and not is_ragdoll_body_object(active_object):
        body_body.label(text=f"Target bones: {len(selected_bones)}", icon="BONE_DATA")
    else:
        warning_box = body_body.box()
        warning_box.label(text="Create/replace bodies. Ensure ragdoll bone(s) selected.", icon="INFO")

    body_body.prop(settings, "body_shape", text="Shape")
    shape = normalize_body_shape(settings.body_shape)
    if shape == "SPHERE":
        body_body.prop(settings, "body_radius", text="Sphere Radius")
    elif shape == "BOX":
        row = body_body.row(align=True)
        row.prop(settings, "body_radius", text="Half Width (X)")
        row.prop(settings, "body_length", text="Length (Y)")
        row.prop(settings, "body_height", text="Height (Z)")
        body_body.label(text="Havok boxes use half extents internally; full width is double X.", icon="INFO")
    else:
        dims_row = body_body.row(align=True)
        dims_row.prop(settings, "body_radius", text="Capsule Radius")
        dims_row.prop(settings, "body_length", text="Capsule Length")
    button_row = body_body.row(align=True)
    button_row.operator("dow2.create_ragdoll_bodies", text="Create Or Update", icon="MESH_ICOSPHERE")


def _draw_custom_vector(layout, owner, prop_name, label):
    row = layout.row(align=True)
    row.label(text=label)
    for index, axis in enumerate(("X", "Y", "Z")):
        row.prop(owner, f'["{prop_name}"]', index=index, text=axis)


def _rotation_prop_name(body_object):
    return "rotation_quaternion" if body_object.rotation_mode == "QUATERNION" else "rotation_euler"


def _active_authoring_context(context):
    active_object = resolve_ragdoll_body_object(context.active_object)
    if active_object is None:
        return None

    skeleton_object = find_ragdoll_skeleton_for_body(active_object)
    linked_bone = active_ragdoll_bone(context)
    if skeleton_object is None or linked_bone is None:
        return None

    parent_body = None
    if linked_bone.parent is not None:
        parent_body = find_ragdoll_body_for_bone(skeleton_object, linked_bone.parent.name)

    return {
        "body": active_object,
        "bone": linked_bone,
        "skeleton": skeleton_object,
        "parent_body": parent_body,
    }


def _draw_template_loader(layout, settings, category):
    loader_box = layout.box()
    loader_box.label(text="Load From Template", icon="ASSET_MANAGER")
    row = loader_box.row(align=True)
    row.prop(settings, "template_model", text="")
    row.prop(settings, "template_folder", text="")
    row.prop(settings, "template_bone", text="")
    button_row = loader_box.row(align=True)
    if category != "templated":
        constraint_op = button_row.operator("dow2.apply_ragdoll_template_category", text="Load Constraint Preset", icon="CONSTRAINT_BONE")
        constraint_op.category = category
        constraint_op.target = "constraint"
    if category == "basic":
        disabled_body_row = button_row.row(align=True)
        disabled_body_row.enabled = False
        body_op = disabled_body_row.operator("dow2.apply_ragdoll_template_category", text="Load Body Preset", icon="MESH_DATA")
        body_op.category = "advanced"
        body_op.target = "body"
        loader_box.label(text="Use Advanced Body Preset to load capsule radius, length, vertices, and body pose.", icon="INFO")
    else:
        body_op = button_row.operator("dow2.apply_ragdoll_template_category", text="Load Body Preset", icon="MESH_DATA")
        body_op.category = category
        body_op.target = "body"


def _draw_basic_section(layout, settings, body_object, bone):
    basic_header, basic_body = layout.panel("dow2_ragdoll_authoring_basic", default_closed=False)
    basic_header.label(text="Basic", icon="MODIFIER")
    if basic_body is None:
        return

    body_box = basic_body.box()
    body_box.label(text="Body", icon="MESH_DATA")
    body_shape = normalize_body_shape(body_object.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE"))
    body_box.operator_menu_enum("dow2.set_active_ragdoll_body_shape", "shape", text=f"Shape Type: {body_shape_label(body_shape)}")
    if body_shape == "SPHERE":
        body_box.prop(body_object, f'["{RAGDOLL_BODY_RADIUS_PROP}"]', text="Sphere Radius")
        body_box.label(text="Sphere bodies use radius only; position and rotation stay in Advanced.", icon="INFO")
    elif body_shape == "BOX":
        row = body_box.row(align=True)
        row.prop(body_object, f'["{RAGDOLL_BODY_RADIUS_PROP}"]', text="Half Width (X)")
        row.prop(body_object, f'["{RAGDOLL_BODY_LENGTH_PROP}"]', text="Length (Y)")
        row.prop(body_object, f'["{RAGDOLL_BODY_HEIGHT_PROP}"]', text="Height (Z)")
        body_box.label(text="Shortcuts: Ctrl+Shift+Wheel for half width; Ctrl+Alt+Wheel for length; Ctrl+Shift+Alt+Wheel for height", icon="INFO")
        body_box.label(text="Advanced exposes raw Havok half extents if you need exact per-axis values.", icon="INFO")
    else:
        body_box.label(text="Move the A/B endpoint handles in the viewport to edit capsule axis and length", icon="EMPTY_AXIS")
        row = body_box.row(align=True)
        row.prop(body_object, f'["{RAGDOLL_BODY_RADIUS_PROP}"]', text="Capsule Radius")
        row.prop(body_object, f'["{RAGDOLL_BODY_LENGTH_PROP}"]', text="Capsule Length")
        body_box.label(text="Shortcuts: Ctrl+Alt+Wheel or Ctrl+Up/Down for length; Ctrl+Shift+Wheel or Ctrl+Left/Right for radius", icon="INFO")
    _draw_custom_vector(body_box, body_object, RAGDOLL_BODY_SHAPE_OFFSET_PROP, "Shape Offset")
    body_box.label(text="Offset is in the body's local space and moves only the primitive, not the joint origin.", icon="INFO")

    constraint_box = basic_body.box()
    constraint_box.label(text="Constraint", icon="CONSTRAINT_BONE")
    if bone.parent is None:
        constraint_box.label(text="Root rigid body has no parent constraint", icon="INFO")
    else:
        read_constraint_settings(bone)
        constraint_type = str(bone.get(RAGDOLL_CONSTRAINT_TYPE_PROP, "ragdoll"))
        constraint_box.label(text=f"Constraint Type: {constraint_type}")
        if constraint_type == "limited_hinge":
            row = constraint_box.row(align=True)
            row.prop(bone, f'["{RAGDOLL_HINGE_MIN_PROP}"]', text="Hinge Min")
            row.prop(bone, f'["{RAGDOLL_HINGE_MAX_PROP}"]', text="Hinge Max")
            constraint_box.label(text="Twist/cone/plane limits are not available for limited-hinge constraints", icon="INFO")
        else:
            row = constraint_box.row(align=True)
            row.prop(bone, f'["{RAGDOLL_TWIST_MIN_PROP}"]', text="Twist Min")
            row.prop(bone, f'["{RAGDOLL_TWIST_MAX_PROP}"]', text="Twist Max")
            constraint_box.prop(bone, f'["{RAGDOLL_CONE_ANGLE_PROP}"]', text="Cone Angle")
            row = constraint_box.row(align=True)
            row.prop(bone, f'["{RAGDOLL_PLANE_MIN_PROP}"]', text="Plane Min")
            row.prop(settings, "preview_plane_min", text="On" if settings.preview_plane_min else "Off", toggle=True)
            row.prop(bone, f'["{RAGDOLL_PLANE_MAX_PROP}"]', text="Plane Max")
            row.prop(settings, "preview_plane_max", text="On" if settings.preview_plane_max else "Off", toggle=True)
            constraint_box.label(text="Hinge limits are not available for ragdoll constraints", icon="INFO")
        constraint_box.prop(bone, f'["{RAGDOLL_FRICTION_TORQUE_PROP}"]', text="Joint Friction Torque")

    _draw_template_loader(basic_body, settings, "basic")


def _draw_advanced_section(layout, settings, body_object, bone):
    advanced_header, advanced_body = layout.panel("dow2_ragdoll_authoring_advanced", default_closed=True)
    advanced_header.label(text="Advanced", icon="SETTINGS")
    if advanced_body is None:
        return

    body_box = advanced_body.box()
    body_box.label(text="Body", icon="MESH_DATA")
    body_shape = normalize_body_shape(body_object.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE"))
    if body_shape == "CAPSULE":
        _draw_custom_vector(body_box, body_object, RAGDOLL_BODY_VERTEX_A_PROP, "Vertex A")
        _draw_custom_vector(body_box, body_object, RAGDOLL_BODY_VERTEX_B_PROP, "Vertex B")
    elif body_shape == "BOX":
        _draw_custom_vector(body_box, body_object, RAGDOLL_BODY_HALF_EXTENTS_PROP, "Half Extents")
    _draw_custom_vector(body_box, body_object, RAGDOLL_BODY_SHAPE_OFFSET_PROP, "Shape Offset")
    body_box.prop(body_object, f'["{RAGDOLL_BODY_MASS_PROP}"]', text="Mass")
    body_box.prop(body_object, "location", text="Position")
    body_box.prop(body_object, _rotation_prop_name(body_object), text="Rotation")

    constraint_box = advanced_body.box()
    constraint_box.label(text="Constraint", icon="CONSTRAINT_BONE")
    if bone.parent is None:
        constraint_box.label(text="Root rigid body has no parent constraint", icon="INFO")
    else:
        read_constraint_settings(bone)
        current_constraint_type = str(bone.get(RAGDOLL_CONSTRAINT_TYPE_PROP, "ragdoll") or "ragdoll")
        constraint_box.operator_menu_enum("dow2.set_active_ragdoll_constraint_type", "constraint_type", text=f"Constraint Type: {current_constraint_type}")
        _draw_custom_vector(constraint_box, bone, RAGDOLL_PIVOT_A_PROP, "Pivot A")
        _draw_custom_vector(constraint_box, bone, RAGDOLL_PIVOT_B_PROP, "Pivot B")
        _draw_custom_vector(constraint_box, bone, RAGDOLL_TWIST_AXIS_A_PROP, "Twist Axis A")
        _draw_custom_vector(constraint_box, bone, RAGDOLL_TWIST_AXIS_B_PROP, "Twist Axis B")
        _draw_custom_vector(constraint_box, bone, RAGDOLL_PLANE_AXIS_A_PROP, "Plane Axis A")
        _draw_custom_vector(constraint_box, bone, RAGDOLL_PLANE_AXIS_B_PROP, "Plane Axis B")

    _draw_template_loader(advanced_body, settings, "advanced")


def _draw_templated_section(layout, settings, body_object, bone):
    templated_header, templated_body = layout.panel("dow2_ragdoll_authoring_templated", default_closed=True)
    templated_header.label(text="Miscellaneous", icon="ASSET_MANAGER")
    if templated_body is None:
        return

    body_box = templated_body.box()
    body_box.label(text="Body", icon="MESH_DATA")
    body_fields = body_box.column()
    body_fields.prop(body_object, f'["{RAGDOLL_BODY_FRICTION_PROP}"]', text="Friction")
    body_fields.prop(body_object, f'["{RAGDOLL_BODY_MOTION_TYPE_PROP}"]', text="Motion Type")
    body_fields.prop(body_object, f'["{RAGDOLL_BODY_LINEAR_DAMPING_PROP}"]', text="Linear Damping")
    body_fields.prop(body_object, f'["{RAGDOLL_BODY_ANGULAR_DAMPING_PROP}"]', text="Angular Damping")
    body_fields.prop(body_object, f'["{RAGDOLL_BODY_COLLISION_FILTER_PROP}"]', text="Collision Filter")
    body_fields.prop(body_object, f'["{RAGDOLL_BODY_QUALITY_TYPE_PROP}"]', text="Quality Type")
    body_fields.prop(body_object, f'["{RAGDOLL_BODY_RESTITUTION_PROP}"]', text="Restitution")

    constraint_box = templated_body.box()
    constraint_box.label(text="Constraint", icon="CONSTRAINT_BONE")
    if bone.parent is None:
        constraint_box.label(text="Root rigid body has no parent constraint", icon="INFO")
    else:
        constraint_box.label(text="No dedicated miscellaneous constraint fields are defined yet", icon="INFO")

    _draw_template_loader(templated_body, settings, "templated")


def _draw_authoring_section(layout, context, settings):
    authoring_header, authoring_body = layout.panel("dow2_ragdoll_authoring", default_closed=False)
    authoring_header.label(text="3. Authoring", icon="CONSTRAINT_BONE")
    if authoring_body is None:
        return

    if settings.preview_constraints:
        sync_constraint_preview_objects()

    preview_box = authoring_body.box()
    preview_box.prop(settings, "preview_constraints", text="Show Constraint Previews In Viewport")
    if settings.preview_constraints:
        preview_box.label(text="Arrows and angular limit previews update after edits settle.", icon="HIDE_OFF")
    else:
        preview_box.label(text="Constraint previews are hidden while this is off.", icon="HIDE_ON")

    authoring_context = _active_authoring_context(context)
    if authoring_context is None:
        info_box = authoring_body.box()
        info_box.label(text="Select a ragdoll rigid body to edit body and constraint fields", icon="INFO")
        return

    body_object = authoring_context["body"]
    bone = authoring_context["bone"]
    parent_body = authoring_context["parent_body"]

    _ensure_authoring_tooltips(body_object, bone)

    header_box = authoring_body.box()
    header_box.label(text=f"Active Rigid Body: {body_object.name}", icon="MESH_DATA")
    header_box.label(text=f"Linked Bone: {bone.name}", icon="BONE_DATA")
    parent_label = parent_body.name if parent_body is not None else "None"
    header_box.label(text=f"Parent Rigid Body: {parent_label}", icon="CONSTRAINT_BONE")
    if bone.parent is None:
        header_box.label(text="Constraint Type: none (root body)")
    else:
        header_box.label(text=f"Constraint Type: {bone.get(RAGDOLL_CONSTRAINT_TYPE_PROP, 'ragdoll')}")

    _draw_basic_section(authoring_body, settings, body_object, bone)
    _draw_advanced_section(authoring_body, settings, body_object, bone)
    _draw_templated_section(authoring_body, settings, body_object, bone)


def _draw_export_section(layout, settings):
    export_header, export_body = layout.panel("dow2_ragdoll_export", default_closed=True)
    export_header.label(text="Export", icon="EXPORT")
    if export_body is None:
        return
    hkx_box = export_body.box()
    hkx_box.label(text="HKX", icon="PHYSICS")
    path_row = hkx_box.row(align=True)
    path_row.prop(settings, "hkx_export_path", text="")
    path_row.operator("dow2.export_ragdoll_hkx", text="Export Ragdoll HKX", icon="EXPORT")
    hkx_box.prop(settings, "auto_generate_missing_bodies")
    hkx_box.prop(settings, "export_json_sidecar")
    if settings.export_json_sidecar:
        hkx_box.prop(settings, "json_export_path", text="JSON Path")


class DOW2_PT_ragdoll_panel(Panel):
    """DoW2 ragdoll export using the frozen template library and native Havok backend"""

    bl_label = "Ragdoll (Experimental)"
    bl_idname = "DOW2_PT_ragdoll_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_order = 56
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.dow2_ragdoll_settings

        _draw_preface(layout, settings)
        _draw_import_section(layout, settings)
        _draw_skeleton_section(layout, context, settings)
        _draw_body_section(layout, context, settings)
        _draw_authoring_section(layout, context, settings)
        _draw_export_section(layout, settings)


RAGDOLL_PANEL_CLASSES = [
    DOW2_PT_ragdoll_panel,
]


__all__ = [
    "DOW2_PT_ragdoll_panel",
    "RAGDOLL_PANEL_CLASSES",
]