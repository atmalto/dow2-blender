from mathutils import Vector

try:
    from dow2_tools.utils import blender_to_dx_position
except ModuleNotFoundError:
    from utils import blender_to_dx_position

from .naming import canonicalize_bone_name
from .templates import apply_body_template


def radius_scale_for_ragdoll_bone(rag_bone_name):
    normalized = canonicalize_bone_name(rag_bone_name)
    if normalized == "bip01":
        return 0.5
    if "head" in normalized:
        return 0.6
    if "spine" in normalized:
        return 0.35
    if "tail" in normalized:
        return 0.2
    if "thigh" in normalized or "upperarm" in normalized:
        return 0.2
    if "calf" in normalized or "forearm" in normalized:
        return 0.16
    if "hand" in normalized or "foot" in normalized or "toe" in normalized:
        return 0.24
    return 0.2


def mass_for_ragdoll_bone(rag_bone_name):
    normalized = canonicalize_bone_name(rag_bone_name)
    if normalized == "bip01":
        return 50.0
    if "spine" in normalized:
        return 12.0
    if "tail" in normalized:
        return 4.0
    if "head" in normalized:
        return 5.0
    if "thigh" in normalized:
        return 8.0
    if "calf" in normalized:
        return 5.0
    if "upperarm" in normalized:
        return 4.0
    if "forearm" in normalized:
        return 2.5
    if "hand" in normalized or "foot" in normalized or "toe" in normalized:
        return 1.5
    return 5.0


def _preferred_generation_child(bone):
    if not bone.children:
        return None
    parent_children = [child for child in bone.children if child.children]
    if parent_children:
        return parent_children[0]
    return bone.children[0]


def _choose_child_head(bone):
    child = _preferred_generation_child(bone)
    return None if child is None else child.head_local.copy()


def _generated_capsule_segment_local(bone):
    head = bone.head_local.copy()
    child_head = _choose_child_head(bone)
    if child_head is not None and (child_head - head).length >= 0.001:
        return head, child_head, False

    direction = bone.tail_local - head
    if bone.parent is not None:
        parent_direction = head - bone.parent.head_local
        if parent_direction.length >= 0.001:
            direction = parent_direction
    fallback_length = max(0.04, min(max(direction.length, 0.0) * 0.5, 0.12))
    if direction.length < 0.001:
        direction = Vector((0.0, fallback_length, 0.0))
    return head, head + direction.normalized() * fallback_length, True


def _generated_capsule_radius(rag_bone_name, segment_length, is_leaf):
    base_radius = segment_length * radius_scale_for_ragdoll_bone(rag_bone_name)
    max_radius = 0.05 if is_leaf else 0.12
    min_radius = 0.015 if is_leaf else 0.02
    return max(min_radius, min(max_radius, base_radius))


def _capsule_segment_vertices(full_length, radius):
    usable_length = max(full_length, 0.001)
    inset = min(max(radius * 1.05, 0.001), usable_length * 0.45)
    line_start = inset
    line_end = usable_length - inset
    if line_end <= line_start:
        midpoint = usable_length * 0.5
        half_line = min(max(usable_length * 0.05, 0.0025), usable_length * 0.5)
        line_start = max(0.0, midpoint - half_line)
        line_end = min(usable_length, midpoint + half_line)
    return [0.0, line_start, 0.0], [0.0, line_end, 0.0]


def _body_frame_in_dx(segment_start, segment_end):
    dx_start = Vector(blender_to_dx_position(segment_start))
    dx_end = Vector(blender_to_dx_position(segment_end))
    dx_segment = dx_end - dx_start
    length = max(dx_segment.length, 0.04)
    if dx_segment.length < 0.001:
        dx_segment = Vector((0.0, length, 0.0))
    rotation = dx_segment.normalized().to_track_quat("Y", "Z")
    return dx_start, rotation, length


def create_rigid_bodies_from_skeleton(ragdoll_skeleton, armature, ragdoll_bone_map, template_bundle=None):
    rigid_bodies = []
    bone_lookup = {bone.name.lower(): bone for bone in armature.data.bones}

    for index, rag_bone_name in enumerate(ragdoll_skeleton["bones"]):
        anim_bone_name = ragdoll_bone_map.get(rag_bone_name)
        bone = bone_lookup.get(anim_bone_name.lower()) if anim_bone_name else None
        if bone:
            segment_start, segment_end, used_leaf_fallback = _generated_capsule_segment_local(bone)
            segment = segment_end - segment_start
            length = max(segment.length, 0.04)
            radius = _generated_capsule_radius(rag_bone_name, length, used_leaf_fallback)
            position_vec, rotation_quat, length = _body_frame_in_dx(segment_start, segment_end)
            vertex_a, vertex_b = _capsule_segment_vertices(length, radius)
            position = [position_vec.x, position_vec.y, position_vec.z]
            rotation = [rotation_quat.x, rotation_quat.y, rotation_quat.z, rotation_quat.w]
        else:
            length = 0.12
            radius = 0.05
            vertex_a, vertex_b = _capsule_segment_vertices(length, radius)
            position = [0.0, 1.0, 0.0]
            rotation = [0.0, 0.0, 0.0, 1.0]

        rigid_body = {
            "name": rag_bone_name,
            "bone_index": index,
            "shape_type": "sphere" if "Head" in rag_bone_name else "capsule",
            "radius": radius,
            "vertex_a": vertex_a,
            "vertex_b": vertex_b,
            "mass": mass_for_ragdoll_bone(rag_bone_name),
            "friction": 1.0,
            "restitution": 0.0,
            "motion_type": "MOTION_BOX_INERTIA",
            "position": position,
            "rotation": rotation,
            "linear_damping": 1.0,
            "angular_damping": 3.0,
            "collision_filter_info": 65984,
            "quality_type": 4,
            "half_extents": [radius, length * 0.5, radius],
        }

        template_body = None if template_bundle is None else template_bundle["bodies"].get(rag_bone_name)
        if template_body is not None:
            rigid_body = apply_body_template(rigid_body, template_body)

        rigid_bodies.append(rigid_body)

    return rigid_bodies