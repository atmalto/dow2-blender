RAGDOLL_SKELETON_PREFIX = "ragdoll_skeleton::"
RAGDOLL_ANIMATION_PREFIX = "ragdoll_animation::"
RAGDOLL_BODIES_COLLECTION_NAME = "ragdoll_bodies"
RAGDOLL_SKELETON_PROP = "dow2_ragdoll_skeleton"
RAGDOLL_ANIMATION_SKELETON_PROP = "dow2_ragdoll_animation_skeleton"
RAGDOLL_BONE_ORDER_PROP = "dow2_ragdoll_bone_order"
RAGDOLL_SOURCE_ARMATURE_PROP = "dow2_ragdoll_source_armature"
RAGDOLL_SOURCE_BONE_PROP = "dow2_ragdoll_source_bone"
# Stores the ragdoll->animation bone-mapping transform (pos+rot+scale, 10 floats)
# exactly as read from the shipped .hkx, so export can re-emit the original
# mapping instead of collapsing every mapping to identity.
RAGDOLL_MAPPING_TRANSFORM_PROP = "dow2_ragdoll_mapping_transform"
RAGDOLL_LOCAL_POS_PROP = "dow2_ragdoll_local_pos"
RAGDOLL_LOCAL_ROT_PROP = "dow2_ragdoll_local_rot"
RAGDOLL_LOCAL_SCALE_PROP = "dow2_ragdoll_local_scale"
RAGDOLL_BODY_PROP = "dow2_ragdoll_body"
RAGDOLL_BODY_BONE_PROP = "dow2_ragdoll_body_bone"
RAGDOLL_BODY_SHAPE_PROP = "dow2_ragdoll_body_shape"
RAGDOLL_BODY_RADIUS_PROP = "dow2_ragdoll_body_radius"
RAGDOLL_BODY_HEIGHT_PROP = "dow2_ragdoll_body_height"
RAGDOLL_BODY_LENGTH_PROP = "dow2_ragdoll_body_length"
RAGDOLL_BODY_VERTEX_A_PROP = "dow2_ragdoll_body_vertex_a"
RAGDOLL_BODY_VERTEX_B_PROP = "dow2_ragdoll_body_vertex_b"
# Marks a body whose object origin is authoritative (imported at the Havok joint
# with asymmetric capsule vertices). The live capsule sync must NOT recenter such
# a body onto its geometric midpoint, or the origin drifts off the joint and the
# exported body no longer matches its constraint pivots.
RAGDOLL_BODY_JOINT_ORIGIN_PROP = "dow2_ragdoll_body_joint_origin"
RAGDOLL_CAPSULE_HANDLE_PROP = "dow2_ragdoll_capsule_handle"
RAGDOLL_CAPSULE_HANDLE_BODY_PROP = "dow2_ragdoll_capsule_handle_body"
RAGDOLL_CAPSULE_HANDLE_ENDPOINT_PROP = "dow2_ragdoll_capsule_handle_endpoint"
RAGDOLL_BODY_HALF_EXTENTS_PROP = "dow2_ragdoll_body_half_extents"
RAGDOLL_BODY_MASS_PROP = "dow2_ragdoll_body_mass"
RAGDOLL_BODY_FRICTION_PROP = "dow2_ragdoll_body_friction"
RAGDOLL_BODY_RESTITUTION_PROP = "dow2_ragdoll_body_restitution"
RAGDOLL_BODY_MOTION_TYPE_PROP = "dow2_ragdoll_body_motion_type"
RAGDOLL_BODY_LINEAR_DAMPING_PROP = "dow2_ragdoll_body_linear_damping"
RAGDOLL_BODY_ANGULAR_DAMPING_PROP = "dow2_ragdoll_body_angular_damping"
RAGDOLL_BODY_COLLISION_FILTER_PROP = "dow2_ragdoll_body_collision_filter_info"
RAGDOLL_BODY_QUALITY_TYPE_PROP = "dow2_ragdoll_body_quality_type"
RAGDOLL_CONSTRAINT_TYPE_PROP = "dow2_ragdoll_constraint_type"
RAGDOLL_TWIST_MIN_PROP = "dow2_ragdoll_twist_min"
RAGDOLL_TWIST_MAX_PROP = "dow2_ragdoll_twist_max"
RAGDOLL_CONE_ANGLE_PROP = "dow2_ragdoll_cone_angle"
RAGDOLL_PLANE_MIN_PROP = "dow2_ragdoll_plane_min"
RAGDOLL_PLANE_MAX_PROP = "dow2_ragdoll_plane_max"
RAGDOLL_HINGE_MIN_PROP = "dow2_ragdoll_hinge_min"
RAGDOLL_HINGE_MAX_PROP = "dow2_ragdoll_hinge_max"
RAGDOLL_FRICTION_TORQUE_PROP = "dow2_ragdoll_friction_torque"
RAGDOLL_PIVOT_A_PROP = "dow2_ragdoll_pivot_a"
RAGDOLL_PIVOT_B_PROP = "dow2_ragdoll_pivot_b"
RAGDOLL_TWIST_AXIS_A_PROP = "dow2_ragdoll_twist_axis_a"
RAGDOLL_TWIST_AXIS_B_PROP = "dow2_ragdoll_twist_axis_b"
RAGDOLL_PLANE_AXIS_A_PROP = "dow2_ragdoll_plane_axis_a"
RAGDOLL_PLANE_AXIS_B_PROP = "dow2_ragdoll_plane_axis_b"

BODY_SHAPE_ITEMS = [
    ("CAPSULE", "Capsule", "Create a capsule-style body preview aligned to the bone"),
]