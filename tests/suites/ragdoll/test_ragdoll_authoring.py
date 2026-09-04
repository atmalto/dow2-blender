from __future__ import annotations

CATEGORY = "ragdoll/authoring"

_TOL = 1.0e-4


def _rounded(values):
    return [round(float(value), 4) for value in values]


def _assert_close(actual, expected, label: str, problems: list[str]) -> None:
    if len(actual) != len(expected):
        problems.append(f"{label} length {len(actual)} != {len(expected)}")
        return
    if any(abs(float(a) - float(b)) > _TOL for a, b in zip(actual, expected)):
        problems.append(f"{label} {_rounded(actual)} != {_rounded(expected)}")


def _assert_rotation_close(actual, expected, label: str, problems: list[str]) -> None:
    angle = float(actual.rotation_difference(expected).angle)
    if angle > _TOL:
        problems.append(f"{label} angle delta {round(angle, 4)} > {_TOL}")


def _make_source_armature():
    import bpy  # type: ignore

    bpy.ops.object.armature_add(location=(0.0, 0.0, 0.0))
    armature = bpy.context.active_object
    armature.name = "ragdoll_authoring_source"
    bpy.ops.object.mode_set(mode='EDIT')
    root = armature.data.edit_bones[0]
    root.name = "root"
    root.head = (0.0, 0.0, 0.0)
    root.tail = (0.0, 0.0, 1.0)
    child = armature.data.edit_bones.new("child")
    child.parent = root
    child.head = (0.0, 0.0, 1.0)
    child.tail = (0.0, 0.0, 2.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    return armature


def _make_oriented_source_armature():
    import bpy  # type: ignore

    bpy.ops.object.armature_add(location=(0.0, 0.0, 0.0))
    armature = bpy.context.active_object
    armature.name = "ragdoll_authoring_oriented_source"
    bpy.ops.object.mode_set(mode='EDIT')
    root = armature.data.edit_bones[0]
    root.name = "root"
    root.head = (0.0, 0.0, 0.0)
    root.tail = (0.25, 0.15, 1.0)
    root.roll = 0.45
    child = armature.data.edit_bones.new("child")
    child.parent = root
    child.head = tuple(root.tail)
    child.tail = (1.0, 0.7, 1.8)
    child.roll = -0.6
    bpy.ops.object.mode_set(mode='OBJECT')
    return armature


def _make_multi_edit_source_armature():
    import bpy  # type: ignore

    bpy.ops.object.armature_add(location=(0.0, 0.0, 0.0))
    armature = bpy.context.active_object
    armature.name = "ragdoll_authoring_multi_edit_source"
    bpy.ops.object.mode_set(mode='EDIT')
    root = armature.data.edit_bones[0]
    root.name = "root"
    root.head = (0.0, 0.0, 0.0)
    root.tail = (0.0, 0.0, 1.0)
    upper = armature.data.edit_bones.new("upper")
    upper.parent = root
    upper.head = (0.0, 0.0, 1.0)
    upper.tail = (0.25, 0.0, 1.8)
    lower = armature.data.edit_bones.new("lower")
    lower.parent = upper
    lower.head = tuple(upper.tail)
    lower.tail = (0.55, 0.1, 2.45)
    hand = armature.data.edit_bones.new("hand")
    hand.parent = lower
    hand.head = tuple(lower.tail)
    hand.tail = (0.8, 0.15, 2.8)
    bpy.ops.object.mode_set(mode='OBJECT')
    return armature


def _make_named_ragdoll(source_armature, bone_order):
    import bpy  # type: ignore

    from dow2_tools.ragdoll.authoring import create_scene_ragdoll_skeleton  # type: ignore

    return create_scene_ragdoll_skeleton(
        bpy.context,
        source_armature,
        "authoring_shapes",
        ragdoll_bone_order=list(bone_order),
    )


def _make_ragdoll(source_armature):
    import bpy  # type: ignore

    from dow2_tools.ragdoll.authoring import create_scene_ragdoll_skeleton  # type: ignore

    return create_scene_ragdoll_skeleton(
        bpy.context,
        source_armature,
        "authoring_shapes",
        ragdoll_bone_order=["root", "child"],
    )


def _body_by_name(exported: dict, name: str) -> dict:
    for body in exported["rigid_bodies"]:
        if body.get("name") == name:
            return body
    raise AssertionError(f"rigid body not found: {name}")


def _identity_transform(pos):
    from dow2_tools.ragdoll.import_types import ImportedTransform  # type: ignore

    return ImportedTransform(pos=list(pos), rot=[0.0, 0.0, 0.0, 1.0], scale=[1.0, 1.0, 1.0])


def _make_import_scene_with_offset(source_armature):
    from mathutils import Matrix

    from dow2_tools.ragdoll.import_types import (  # type: ignore
        ImportedBoneMapping,
        ImportedConstraint,
        ImportedRagdollScene,
        ImportedRigidBody,
        ImportedSkeleton,
    )
    from dow2_tools.utils import blender_to_dx_matrix  # type: ignore

    root_head = source_armature.matrix_world @ source_armature.data.bones["root"].head_local
    child_head = source_armature.matrix_world @ source_armature.data.bones["child"].head_local
    root_pos = blender_to_dx_matrix(Matrix.Translation(root_head)).decompose()[0]
    child_pos = blender_to_dx_matrix(Matrix.Translation(child_head)).decompose()[0]

    animation_skeleton = ImportedSkeleton(
        name="offset_test_anim",
        bones=["root", "child"],
        parent_indices=[-1, 0],
        reference_pose=[_identity_transform([0.0, 0.0, 0.0]), _identity_transform([0.0, 1.0, 0.0])],
    )
    ragdoll_skeleton = ImportedSkeleton(
        name="offset_test_ragdoll",
        bones=["root", "child"],
        parent_indices=[-1, 0],
        reference_pose=[_identity_transform([0.0, 0.0, 0.0]), _identity_transform([0.0, 1.0, 0.0])],
    )
    return ImportedRagdollScene(
        animation_skeleton=animation_skeleton,
        ragdoll_skeleton=ragdoll_skeleton,
        bone_mappings=[
            ImportedBoneMapping(ragdoll_bone=0, anim_bone=0, transform=_identity_transform([0.0, 0.0, 0.0])),
            ImportedBoneMapping(ragdoll_bone=1, anim_bone=1, transform=_identity_transform([0.0, 0.0, 0.0])),
        ],
        rigid_bodies=[
            ImportedRigidBody(
                name="root",
                bone_index=0,
                shape_type="capsule",
                radius=0.12,
                shape_offset=[0.0, 0.0, 0.0],
                vertex_a=[0.0, -0.25, 0.0],
                vertex_b=[0.0, 0.25, 0.0],
                half_extents=[0.12, 0.25, 0.12],
                mass=5.0,
                friction=1.0,
                restitution=0.0,
                motion_type="MOTION_BOX_INERTIA",
                position=[root_pos.x, root_pos.y, root_pos.z],
                rotation=[0.0, 0.0, 0.0, 1.0],
                linear_damping=1.0,
                angular_damping=3.0,
                collision_filter_info=65984,
                quality_type=4,
            ),
            ImportedRigidBody(
                name="child",
                bone_index=1,
                shape_type="box",
                radius=0.0,
                shape_offset=[0.15, -0.05, 0.1],
                vertex_a=[0.0, 0.0, 0.0],
                vertex_b=[0.0, 0.0, 0.0],
                half_extents=[0.2, 0.3, 0.4],
                mass=8.0,
                friction=1.0,
                restitution=0.0,
                motion_type="MOTION_BOX_INERTIA",
                position=[child_pos.x, child_pos.y, child_pos.z],
                rotation=[0.0, 0.0, 0.0, 1.0],
                linear_damping=1.0,
                angular_damping=3.0,
                collision_filter_info=65984,
                quality_type=4,
            ),
        ],
        constraints=[
            ImportedConstraint(
                name="child",
                body_a_index=1,
                body_b_index=0,
                constraint_type="limited_hinge",
                pivot_a=[0.0, 0.0, 0.0],
                pivot_b=[0.0, 0.0, 0.0],
                twist_axis_a=[1.0, 0.0, 0.0],
                twist_axis_b=[1.0, 0.0, 0.0],
                plane_axis_a=[0.0, 1.0, 0.0],
                plane_axis_b=[0.0, 1.0, 0.0],
                hinge_min=-0.5,
                hinge_max=0.5,
                friction_torque=0.0,
            ),
        ],
        source_format="json",
    )


def test_ragdoll_body_creation_supports_box_and_sphere(ctx):
    import bpy  # type: ignore

    from dow2_tools.ragdoll.authoring import (  # type: ignore
        create_or_update_body_for_bone,
        sync_ragdoll_body_object,
    )
    from dow2_tools.ragdoll.authoring.export_builder import build_authored_ragdoll_data  # type: ignore
    from framework import blender_env

    blender_env.reset_scene()
    source_armature = _make_source_armature()
    ragdoll = _make_ragdoll(source_armature)

    problems: list[str] = []

    sphere_body = create_or_update_body_for_bone(ragdoll, "root", "SPHERE", 0.17, 0.34, 0.34)
    box_body = create_or_update_body_for_bone(ragdoll, "child", "BOX", 0.25, 0.8, 0.6)
    sync_ragdoll_body_object(sphere_body, force=True)
    sync_ragdoll_body_object(box_body, force=True)

    if str(sphere_body.get("dow2_ragdoll_body_shape", "")) != "SPHERE":
        problems.append("sphere body shape prop not set to SPHERE")
    if str(box_body.get("dow2_ragdoll_body_shape", "")) != "BOX":
        problems.append("box body shape prop not set to BOX")
    _assert_close(list(sphere_body.get("dow2_ragdoll_body_half_extents", [])), [0.17, 0.17, 0.17], "sphere half extents", problems)
    _assert_close(list(box_body.get("dow2_ragdoll_body_half_extents", [])), [0.25, 0.3, 0.4], "box half extents", problems)

    exported = build_authored_ragdoll_data(source_armature, ragdoll)
    exported_sphere = _body_by_name(exported, "root")
    exported_box = _body_by_name(exported, "child")
    if exported_sphere.get("shape_type") != "sphere":
        problems.append(f"exported sphere shape_type {exported_sphere.get('shape_type')} != sphere")
    if exported_box.get("shape_type") != "box":
        problems.append(f"exported box shape_type {exported_box.get('shape_type')} != box")
    _assert_close(exported_sphere.get("half_extents", []), [0.17, 0.17, 0.17], "exported sphere half extents", problems)
    _assert_close(exported_box.get("half_extents", []), [0.25, 0.3, 0.4], "exported box half extents", problems)

    if problems:
        ctx.fail(" | ".join(problems))


def test_ragdoll_body_shape_switch_operator_rebuilds_shape_state(ctx):
    import bpy  # type: ignore

    from dow2_tools.ragdoll.authoring import create_or_update_body_for_bone  # type: ignore
    from framework import blender_env

    blender_env.reset_scene()
    source_armature = _make_source_armature()
    ragdoll = _make_ragdoll(source_armature)
    body = create_or_update_body_for_bone(ragdoll, "child", "CAPSULE", 0.12, 0.24, 0.7)

    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body

    problems: list[str] = []
    starting_radius = float(body.get("dow2_ragdoll_body_radius", 0.0))
    starting_height = float(body.get("dow2_ragdoll_body_height", 0.0))
    starting_length = float(body.get("dow2_ragdoll_body_length", 0.0))

    result = bpy.ops.dow2.set_active_ragdoll_body_shape(shape="BOX")
    if "FINISHED" not in result:
        problems.append(f"switch to BOX failed: {result}")
    if str(body.get("dow2_ragdoll_body_shape", "")) != "BOX":
        problems.append("body shape prop not updated to BOX")
    _assert_close(
        list(body.get("dow2_ragdoll_body_half_extents", [])),
        [starting_radius, starting_length * 0.5, starting_height * 0.5],
        "box switch half extents",
        problems,
    )
    if any(bool(child.get("dow2_ragdoll_capsule_handle", False)) for child in body.children):
        problems.append("capsule handles were not removed after switching to BOX")

    result = bpy.ops.dow2.set_active_ragdoll_body_shape(shape="SPHERE")
    if "FINISHED" not in result:
        problems.append(f"switch to SPHERE failed: {result}")
    if str(body.get("dow2_ragdoll_body_shape", "")) != "SPHERE":
        problems.append("body shape prop not updated to SPHERE")
    _assert_close(list(body.get("dow2_ragdoll_body_half_extents", [])), [starting_radius, starting_radius, starting_radius], "sphere switch half extents", problems)

    result = bpy.ops.dow2.set_active_ragdoll_body_shape(shape="CAPSULE")
    if "FINISHED" not in result:
        problems.append(f"switch to CAPSULE failed: {result}")
    if str(body.get("dow2_ragdoll_body_shape", "")) != "CAPSULE":
        problems.append("body shape prop not updated to CAPSULE")
    if sum(1 for child in body.children if bool(child.get("dow2_ragdoll_capsule_handle", False))) != 2:
        problems.append("capsule handles were not restored after switching back to CAPSULE")

    if problems:
        ctx.fail(" | ".join(problems))


def test_ragdoll_box_height_shortcut_updates_third_dimension(ctx):
    import bpy  # type: ignore

    from dow2_tools.ragdoll.authoring import create_or_update_body_for_bone  # type: ignore
    from dow2_tools.ragdoll.operators.shortcuts import _adjust_active_body_dimension  # type: ignore
    from framework import blender_env

    del ctx
    blender_env.reset_scene()
    source_armature = _make_source_armature()
    ragdoll = _make_ragdoll(source_armature)
    body = create_or_update_body_for_bone(ragdoll, "child", "BOX", 0.2, 0.6, 0.5)

    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body

    start_height = float(body.get("dow2_ragdoll_body_height", 0.0))
    success, message = _adjust_active_body_dimension(bpy.context, "height", 0.05)
    if not success:
        raise AssertionError(message)
    end_height = float(body.get("dow2_ragdoll_body_height", 0.0))
    if end_height <= start_height:
        raise AssertionError(f"box height shortcut did not increase height: {start_height} -> {end_height}")


def test_ragdoll_capsule_creation_uses_joint_origin(ctx):
    from mathutils import Vector

    from dow2_tools.ragdoll.authoring import create_or_update_body_for_bone, sync_ragdoll_body_object  # type: ignore
    from framework import blender_env

    blender_env.reset_scene()
    source_armature = _make_source_armature()
    ragdoll = _make_ragdoll(source_armature)
    body = create_or_update_body_for_bone(ragdoll, "child", "CAPSULE", 0.12, 0.24, 0.7)
    sync_ragdoll_body_object(body, force=True)

    problems: list[str] = []
    bone_head = ragdoll.matrix_world @ ragdoll.data.bones["child"].head_local
    _assert_close(
        [body.matrix_world.translation.x, body.matrix_world.translation.y, body.matrix_world.translation.z],
        [bone_head.x, bone_head.y, bone_head.z],
        "capsule body origin",
        problems,
    )

    if not bool(body.get("dow2_ragdoll_body_joint_origin", False)):
        problems.append("capsule body was not flagged as joint-origin anchored")

    if list(body.get("dow2_ragdoll_body_shape_offset", [1.0, 1.0, 1.0])) != [0.0, 0.0, 0.0]:
        problems.append(f"fresh capsule shape_offset is not zero: {list(body.get('dow2_ragdoll_body_shape_offset', []))}")

    vertex_a = list(body.get("dow2_ragdoll_body_vertex_a", []))
    vertex_b = list(body.get("dow2_ragdoll_body_vertex_b", []))
    if len(vertex_a) != 3 or len(vertex_b) != 3:
        problems.append("capsule vertices missing after creation")
    else:
        if vertex_a[1] < -_TOL:
            problems.append(f"joint-origin capsule vertex_a should not sit behind the origin: {vertex_a}")
        if vertex_b[1] <= vertex_a[1]:
            problems.append(f"joint-origin capsule vertex ordering invalid: {vertex_a} -> {vertex_b}")

    if body.data.vertices:
        centroid = sum((vertex.co for vertex in body.data.vertices), Vector((0.0, 0.0, 0.0))) / len(body.data.vertices)
        if centroid.y <= _TOL:
            problems.append(f"joint-origin capsule centroid should lie forward from the origin, got {tuple(centroid)}")

    if problems:
        ctx.fail(" | ".join(problems))


def test_ragdoll_created_capsule_uses_joint_frame_rotation(ctx):
    from dow2_tools.ragdoll.authoring import create_or_update_body_for_bone, sync_ragdoll_body_object  # type: ignore
    from dow2_tools.model.skeleton_space import get_export_node_world_matrix  # type: ignore
    from framework import blender_env

    blender_env.reset_scene()
    source_armature = _make_oriented_source_armature()
    ragdoll = _make_ragdoll(source_armature)
    body = create_or_update_body_for_bone(ragdoll, "child", "CAPSULE", 0.12, 0.24, 0.7)
    sync_ragdoll_body_object(body, force=True)

    problems: list[str] = []
    expected_rotation = get_export_node_world_matrix(ragdoll.data.bones["child"], ragdoll).to_quaternion()
    _assert_rotation_close(body.matrix_world.to_quaternion(), expected_rotation, "capsule export-frame rotation", problems)

    if problems:
        ctx.fail(" | ".join(problems))


def test_ragdoll_multi_selection_edits_filter_body_and_constraint_compatibility(ctx):
    import bpy  # type: ignore

    from dow2_tools.ragdoll.authoring import (  # type: ignore
        RAGDOLL_BODY_HEIGHT_PROP,
        RAGDOLL_BODY_SHAPE_PROP,
        RAGDOLL_CONSTRAINT_TYPE_PROP,
        RAGDOLL_HINGE_MIN_PROP,
        apply_body_shape_to_selected,
        apply_constraint_type_to_selected,
        apply_constraint_data_to_bone,
        create_or_update_body_for_bone,
        propagate_selected_ragdoll_edits,
        sync_ragdoll_body_object,
    )
    from framework import blender_env

    blender_env.reset_scene()
    source_armature = _make_multi_edit_source_armature()
    ragdoll = _make_named_ragdoll(source_armature, ["root", "upper", "lower", "hand"])

    active_box = create_or_update_body_for_bone(ragdoll, "upper", "BOX", 0.2, 0.6, 0.4)
    hinge_sphere = create_or_update_body_for_bone(ragdoll, "lower", "SPHERE", 0.16, 0.32, 0.32)
    ragdoll_box = create_or_update_body_for_bone(ragdoll, "hand", "BOX", 0.14, 0.5, 0.3)
    for body in (active_box, hinge_sphere, ragdoll_box):
        sync_ragdoll_body_object(body, force=True)

    apply_constraint_data_to_bone(ragdoll.data.bones["upper"], {"constraint_type": "limited_hinge", "hinge_min": -0.4, "hinge_max": 0.4})
    apply_constraint_data_to_bone(ragdoll.data.bones["lower"], {"constraint_type": "limited_hinge", "hinge_min": -0.25, "hinge_max": 0.25})
    apply_constraint_data_to_bone(ragdoll.data.bones["hand"], {"constraint_type": "ragdoll", "twist_min": -0.2, "twist_max": 0.2})

    bpy.ops.object.select_all(action='DESELECT')
    for body in (active_box, hinge_sphere, ragdoll_box):
        body.select_set(True)
    bpy.context.view_layer.objects.active = active_box

    propagate_selected_ragdoll_edits(bpy.context)

    active_box[RAGDOLL_BODY_HEIGHT_PROP] = 1.1
    propagate_selected_ragdoll_edits(bpy.context)

    problems: list[str] = []
    if str(ragdoll_box.get(RAGDOLL_BODY_SHAPE_PROP, "")) != "BOX":
        problems.append("ragdoll box shape changed unexpectedly before body propagation check")
    if abs(float(ragdoll_box.get(RAGDOLL_BODY_HEIGHT_PROP, 0.0)) - 1.1) > _TOL:
        problems.append(f"box body edit did not propagate across differing constraint type: {float(ragdoll_box.get(RAGDOLL_BODY_HEIGHT_PROP, 0.0))}")
    if abs(float(hinge_sphere.get(RAGDOLL_BODY_HEIGHT_PROP, 0.0)) - 0.32) > _TOL:
        problems.append(f"sphere body should have ignored box height edit: {float(hinge_sphere.get(RAGDOLL_BODY_HEIGHT_PROP, 0.0))}")

    propagate_selected_ragdoll_edits(bpy.context)
    ragdoll.data.bones["upper"][RAGDOLL_HINGE_MIN_PROP] = -1.05
    propagate_selected_ragdoll_edits(bpy.context)

    if str(ragdoll.data.bones["lower"].get(RAGDOLL_CONSTRAINT_TYPE_PROP, "")) != "limited_hinge":
        problems.append("limited hinge target lost its constraint type unexpectedly")
    if abs(float(ragdoll.data.bones["lower"].get(RAGDOLL_HINGE_MIN_PROP, 0.0)) - (-1.05)) > _TOL:
        problems.append(f"hinge edit did not propagate across differing body shape: {float(ragdoll.data.bones['lower'].get(RAGDOLL_HINGE_MIN_PROP, 0.0))}")
    if abs(float(ragdoll.data.bones["hand"].get(RAGDOLL_HINGE_MIN_PROP, 0.0)) - (-3.141592653589793)) > _TOL:
        problems.append(f"ragdoll constraint should have ignored hinge edit: {float(ragdoll.data.bones['hand'].get(RAGDOLL_HINGE_MIN_PROP, 0.0))}")

    changed_shapes = apply_body_shape_to_selected(bpy.context, "CAPSULE")
    if len(changed_shapes) != 2:
        problems.append(f"shape switch should have affected exactly the two selected boxes, got {len(changed_shapes)}")
    if str(active_box.get(RAGDOLL_BODY_SHAPE_PROP, "")) != "CAPSULE":
        problems.append("active box did not switch shape")
    if str(ragdoll_box.get(RAGDOLL_BODY_SHAPE_PROP, "")) != "CAPSULE":
        problems.append("matching selected box did not switch shape")
    if str(hinge_sphere.get(RAGDOLL_BODY_SHAPE_PROP, "")) != "SPHERE":
        problems.append("sphere should have ignored box-driven shape switch")

    changed_constraints = apply_constraint_type_to_selected(bpy.context, "ragdoll")
    if len(changed_constraints) != 2:
        problems.append(f"constraint type switch should have affected exactly the two selected limited hinges, got {len(changed_constraints)}")
    if str(ragdoll.data.bones["upper"].get(RAGDOLL_CONSTRAINT_TYPE_PROP, "")) != "ragdoll":
        problems.append("active hinge did not switch constraint type")
    if str(ragdoll.data.bones["lower"].get(RAGDOLL_CONSTRAINT_TYPE_PROP, "")) != "ragdoll":
        problems.append("matching selected hinge did not switch constraint type")

    if problems:
        ctx.fail(" | ".join(problems))


def test_ragdoll_shape_offset_import_and_export_roundtrip(ctx):
    import bpy  # type: ignore
    from mathutils import Vector

    from dow2_tools.ragdoll.authoring.export_builder import build_authored_ragdoll_data  # type: ignore
    from dow2_tools.ragdoll.authoring.geometry import _dx_vector_to_blender_local  # type: ignore
    from dow2_tools.ragdoll.authoring.queries import find_ragdoll_body_for_bone  # type: ignore
    from dow2_tools.ragdoll.scene_importer import RagdollImporter  # type: ignore
    from framework import blender_env

    blender_env.reset_scene()
    source_armature = _make_source_armature()
    scene_data = _make_import_scene_with_offset(source_armature)
    skeleton = RagdollImporter().apply_to_source_armature(
        bpy.context,
        source_armature,
        scene_data,
        ragdoll_name="offset_authoring",
        prefer_reference_pose_display=False,
    )

    body = find_ragdoll_body_for_bone(skeleton, "child")
    if body is None:
        ctx.fail("offset test body was not created")
        return

    problems: list[str] = []
    expected_offset = _dx_vector_to_blender_local([0.15, -0.05, 0.1])
    _assert_close(list(body.get("dow2_ragdoll_body_shape_offset", [])), expected_offset, "shape offset prop", problems)

    bone_world = skeleton.matrix_world @ skeleton.data.bones["child"].head_local
    actual_origin = [body.matrix_world.translation.x, body.matrix_world.translation.y, body.matrix_world.translation.z]
    _assert_close(actual_origin, [bone_world.x, bone_world.y, bone_world.z], "body origin stays on joint", problems)

    if not body.data.vertices:
        problems.append("offset body mesh has no vertices")
    else:
        centroid = sum((vertex.co for vertex in body.data.vertices), Vector((0.0, 0.0, 0.0))) / len(body.data.vertices)
        _assert_close([centroid.x, centroid.y, centroid.z], expected_offset, "mesh centroid offset", problems)

    exported = build_authored_ragdoll_data(source_armature, skeleton, auto_generate_missing_bodies=False)
    exported_body = _body_by_name(exported, "child")
    _assert_close(exported_body.get("shape_offset", []), [0.15, -0.05, 0.1], "exported shape_offset", problems)
    _assert_close(exported_body.get("position", []), scene_data.rigid_bodies[1].position, "exported body position", problems)

    if problems:
        ctx.fail(" | ".join(problems))


def test_ragdoll_capsule_shape_offset_resets_cleanly(ctx):
    from mathutils import Vector

    from dow2_tools.ragdoll.authoring import create_or_update_body_for_bone, sync_ragdoll_body_object  # type: ignore
    from dow2_tools.ragdoll.authoring.body_sync import _capsule_handle_local_positions  # type: ignore
    from framework import blender_env

    blender_env.reset_scene()
    source_armature = _make_source_armature()
    ragdoll = _make_ragdoll(source_armature)
    body = create_or_update_body_for_bone(ragdoll, "child", "CAPSULE", 0.12, 0.24, 0.7)
    sync_ragdoll_body_object(body, force=True)

    problems: list[str] = []
    expected_vertex_a = list(body.get("dow2_ragdoll_body_vertex_a", []))
    expected_vertex_b = list(body.get("dow2_ragdoll_body_vertex_b", []))
    _assert_close(list(body.get("dow2_ragdoll_body_vertex_a", [])), expected_vertex_a, "initial vertex_a", problems)
    _assert_close(list(body.get("dow2_ragdoll_body_vertex_b", [])), expected_vertex_b, "initial vertex_b", problems)
    expected_centroid = None
    if body.data.vertices:
        centroid = sum((vertex.co for vertex in body.data.vertices), Vector((0.0, 0.0, 0.0))) / len(body.data.vertices)
        expected_centroid = [centroid.x, centroid.y, centroid.z]

    body["dow2_ragdoll_body_shape_offset"] = [0.2, 0.0, 0.1]
    sync_ragdoll_body_object(body)
    handle_a, handle_b = _capsule_handle_local_positions(body)
    if handle_a is None or handle_b is None:
        problems.append("capsule handles missing after applying shape offset")
    else:
        _assert_close(list(handle_a), [expected_vertex_a[0] + 0.2, expected_vertex_a[1], expected_vertex_a[2] + 0.1], "offset handle_a", problems)
        _assert_close(list(handle_b), [expected_vertex_b[0] + 0.2, expected_vertex_b[1], expected_vertex_b[2] + 0.1], "offset handle_b", problems)

    body["dow2_ragdoll_body_shape_offset"] = [0.0, 0.0, 0.0]
    sync_ragdoll_body_object(body)

    _assert_close(list(body.get("dow2_ragdoll_body_vertex_a", [])), expected_vertex_a, "reset vertex_a", problems)
    _assert_close(list(body.get("dow2_ragdoll_body_vertex_b", [])), expected_vertex_b, "reset vertex_b", problems)
    handle_a, handle_b = _capsule_handle_local_positions(body)
    if handle_a is None or handle_b is None:
        problems.append("capsule handles missing after resetting shape offset")
    else:
        _assert_close(list(handle_a), expected_vertex_a, "reset handle_a", problems)
        _assert_close(list(handle_b), expected_vertex_b, "reset handle_b", problems)

    if body.data.vertices and expected_centroid is not None:
        centroid = sum((vertex.co for vertex in body.data.vertices), Vector((0.0, 0.0, 0.0))) / len(body.data.vertices)
        _assert_close([centroid.x, centroid.y, centroid.z], expected_centroid, "reset mesh centroid", problems)

    if problems:
        ctx.fail(" | ".join(problems))


def test_ragdoll_capsule_shape_offset_resize_is_not_cumulative(ctx):
    from mathutils import Vector

    from dow2_tools.ragdoll.authoring import create_or_update_body_for_bone, sync_ragdoll_body_object  # type: ignore
    from dow2_tools.ragdoll.authoring.body_sync import _capsule_handle_local_positions  # type: ignore
    from framework import blender_env

    blender_env.reset_scene()
    source_armature = _make_source_armature()
    ragdoll = _make_ragdoll(source_armature)
    body = create_or_update_body_for_bone(ragdoll, "child", "CAPSULE", 0.12, 0.24, 0.7)
    sync_ragdoll_body_object(body, force=True)

    problems: list[str] = []
    offset = [0.2, 0.0, 0.1]
    body["dow2_ragdoll_body_shape_offset"] = offset
    sync_ragdoll_body_object(body)

    expected_centroid = None
    if body.data.vertices:
        centroid = sum((vertex.co for vertex in body.data.vertices), Vector((0.0, 0.0, 0.0))) / len(body.data.vertices)
        expected_centroid = [centroid.x, centroid.y, centroid.z]

    body["dow2_ragdoll_body_length"] = 1.0
    sync_ragdoll_body_object(body)
    body["dow2_ragdoll_body_radius"] = 0.18
    sync_ragdoll_body_object(body)

    vertex_a = list(body.get("dow2_ragdoll_body_vertex_a", []))
    vertex_b = list(body.get("dow2_ragdoll_body_vertex_b", []))
    handle_a, handle_b = _capsule_handle_local_positions(body)
    if handle_a is None or handle_b is None:
        problems.append("capsule handles missing after offseted resize")
    else:
        _assert_close(list(handle_a), [vertex_a[0] + offset[0], vertex_a[1] + offset[1], vertex_a[2] + offset[2]], "resized handle_a", problems)
        _assert_close(list(handle_b), [vertex_b[0] + offset[0], vertex_b[1] + offset[1], vertex_b[2] + offset[2]], "resized handle_b", problems)

    if body.data.vertices and expected_centroid is not None:
        centroid = sum((vertex.co for vertex in body.data.vertices), Vector((0.0, 0.0, 0.0))) / len(body.data.vertices)
        _assert_close([centroid.x - expected_centroid[0], centroid.y - expected_centroid[1], centroid.z - expected_centroid[2]], [0.0, 0.0, 0.0], "resized mesh centroid drift", problems)

    if problems:
        ctx.fail(" | ".join(problems))
