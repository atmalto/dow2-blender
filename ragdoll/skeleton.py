from mathutils import Quaternion

try:
    from dow2_tools.utils import blender_to_dx_matrix
except ModuleNotFoundError:
    from utils import blender_to_dx_matrix

from .constants import DEFAULT_RAGDOLL_BONE_ORDER
from .naming import canonicalize_bone_name, to_title_case


def build_animation_skeleton_from_armature(armature):
    arm_data = armature.data
    bones_ordered = []
    bone_name_to_idx = {}

    def add_bone_recursive(bone, parent_idx=-1):
        idx = len(bones_ordered)
        bone_name_to_idx[bone.name.lower()] = idx
        bones_ordered.append((bone, parent_idx))
        for child in bone.children:
            add_bone_recursive(child, idx)

    for bone in arm_data.bones:
        if bone.parent is None:
            add_bone_recursive(bone)

    animation_skeleton = {
        "name": to_title_case(arm_data.bones[0].name) if arm_data.bones else "Skeleton",
        "bones": [to_title_case(bone.name) for bone, _ in bones_ordered],
        "parent_indices": [parent_idx for _, parent_idx in bones_ordered],
        "reference_pose": [bone_to_transform(bone, armature) for bone, _ in bones_ordered],
    }
    return animation_skeleton, bone_name_to_idx


def infer_ragdoll_bone_map(armature, ragdoll_bone_order):
    canonical_lookup = {}
    lower_lookup = {bone.name.lower(): bone for bone in armature.data.bones}

    for bone in armature.data.bones:
        canonical = canonicalize_bone_name(bone.name)
        canonical_lookup.setdefault(canonical, bone.name.lower())

    ragdoll_bone_map = {}
    missing = []
    for rag_name in ragdoll_bone_order:
        anim_name = canonical_lookup.get(canonicalize_bone_name(rag_name))
        if anim_name is None:
            missing.append(rag_name)
            continue
        ragdoll_bone_map[rag_name] = anim_name

    if missing:
        raise ValueError(f"Could not map ragdoll bones to animation bones: {missing}")

    return ragdoll_bone_map


def infer_ragdoll_hierarchy(armature, ragdoll_bone_order, ragdoll_bone_map):
    bone_lookup = {bone.name.lower(): bone for bone in armature.data.bones}
    anim_to_ragdoll = {anim_name: rag_name for rag_name, anim_name in ragdoll_bone_map.items()}
    ragdoll_hierarchy = {}

    for rag_name in ragdoll_bone_order:
        anim_name = ragdoll_bone_map.get(rag_name)
        bone = bone_lookup.get(anim_name)
        parent_rag_name = None

        if bone is not None:
            current_parent = bone.parent
            while current_parent is not None:
                parent_anim_name = current_parent.name.lower()
                if parent_anim_name in anim_to_ragdoll and anim_to_ragdoll[parent_anim_name] != rag_name:
                    parent_rag_name = anim_to_ragdoll[parent_anim_name]
                    break
                current_parent = current_parent.parent

        ragdoll_hierarchy[rag_name] = parent_rag_name

    if ragdoll_bone_order:
        ragdoll_hierarchy[ragdoll_bone_order[0]] = None
    return ragdoll_hierarchy


def order_ragdoll_bones_parent_first(ragdoll_bone_order, ragdoll_hierarchy):
    original_index = {rag_name: index for index, rag_name in enumerate(ragdoll_bone_order)}
    ordered = []
    visiting = set()
    visited = set()

    def visit(rag_name):
        if rag_name in visited:
            return
        if rag_name in visiting:
            raise ValueError(f"Cycle detected while ordering ragdoll hierarchy at {rag_name}")

        visiting.add(rag_name)
        parent_name = ragdoll_hierarchy.get(rag_name)
        if parent_name in original_index:
            visit(parent_name)
        visiting.remove(rag_name)
        visited.add(rag_name)
        ordered.append(rag_name)

    for rag_name in sorted(ragdoll_bone_order, key=original_index.get):
        visit(rag_name)
    return ordered


def get_bone_world_transforms_from_blender(armature):
    result = {}
    for bone in armature.data.bones:
        world_mat_dx = blender_to_dx_matrix(bone.matrix_local)
        world_pos, world_rot, world_scale = world_mat_dx.decompose()
        result[bone.name.lower()] = {
            "world_pos": world_pos,
            "world_rot": world_rot,
            "world_scale": world_scale,
        }
    return result


def compute_ragdoll_skeleton_transforms(armature, ragdoll_bone_order, ragdoll_bone_map, ragdoll_hierarchy):
    bone_data = get_bone_world_transforms_from_blender(armature)
    ragdoll_world_transforms = {}
    local_transform_by_name = {}
    active_stack = set()

    def compute_transform_for_bone(rag_name):
        if rag_name in local_transform_by_name:
            return local_transform_by_name[rag_name]
        if rag_name in active_stack:
            raise ValueError(f"Cycle detected in inferred ragdoll hierarchy at {rag_name}")

        active_stack.add(rag_name)
        anim_bone_name = ragdoll_bone_map.get(rag_name)
        parent_rag_name = ragdoll_hierarchy.get(rag_name)

        if not anim_bone_name or anim_bone_name.lower() not in bone_data:
            local_transform = {
                "pos": [0.0, 0.0, 0.0],
                "rot": [0.0, 0.0, 0.0, 1.0],
                "scale": [1.0, 1.0, 1.0],
            }
            ragdoll_world_transforms[rag_name] = (None, None)
            local_transform_by_name[rag_name] = local_transform
            active_stack.remove(rag_name)
            return local_transform

        anim_bone = bone_data[anim_bone_name.lower()]
        anim_world_pos = anim_bone["world_pos"]
        anim_world_rot = anim_bone["world_rot"]

        if parent_rag_name is None or parent_rag_name not in ragdoll_bone_map:
            local_pos = anim_world_pos
            local_rot = anim_world_rot
        else:
            if parent_rag_name not in ragdoll_world_transforms:
                compute_transform_for_bone(parent_rag_name)

            parent_world_pos, parent_world_rot = ragdoll_world_transforms.get(parent_rag_name, (None, None))
            if parent_world_pos is None or parent_world_rot is None:
                local_pos = anim_world_pos
                local_rot = anim_world_rot
            else:
                parent_rot_inv = parent_world_rot.inverted()
                local_pos = parent_rot_inv @ (anim_world_pos - parent_world_pos)
                local_rot = parent_rot_inv @ anim_world_rot

        ragdoll_world_transforms[rag_name] = (anim_world_pos.copy(), anim_world_rot.copy())
        local_transform = {
            "pos": [local_pos.x, local_pos.y, local_pos.z],
            "rot": [local_rot.x, local_rot.y, local_rot.z, local_rot.w],
            "scale": [1.0, 1.0, 1.0],
        }
        local_transform_by_name[rag_name] = local_transform
        active_stack.remove(rag_name)
        return local_transform

    for rag_name in ragdoll_bone_order:
        compute_transform_for_bone(rag_name)

    return [local_transform_by_name[rag_name] for rag_name in ragdoll_bone_order]


def bone_to_transform(bone, armature, parent_bone=None, use_world_space=False, is_ragdoll_root=False):
    if use_world_space:
        local_mat = bone.matrix_local
    elif parent_bone is not None:
        local_mat = parent_bone.matrix_local.inverted() @ bone.matrix_local
    elif bone.parent:
        local_mat = bone.parent.matrix_local.inverted() @ bone.matrix_local
    else:
        local_mat = bone.matrix_local

    local_mat = blender_to_dx_matrix(local_mat)
    loc, rot, scale = local_mat.decompose()

    if is_ragdoll_root:
        rot = Quaternion((0.706046, 0.038731, 0.706045, 0.038731))

    return {
        "pos": [loc.x, loc.y, loc.z],
        "rot": [rot.x, rot.y, rot.z, rot.w],
        "scale": [scale.x, scale.y, scale.z],
    }


def create_ragdoll_skeleton_from_armature(armature, ragdoll_bone_order=None):
    ragdoll_bone_order = list(ragdoll_bone_order or DEFAULT_RAGDOLL_BONE_ORDER)
    animation_skeleton, bone_name_to_idx = build_animation_skeleton_from_armature(armature)
    ragdoll_bone_map = infer_ragdoll_bone_map(armature, ragdoll_bone_order)
    ragdoll_hierarchy = infer_ragdoll_hierarchy(armature, ragdoll_bone_order, ragdoll_bone_map)
    ragdoll_bone_order = order_ragdoll_bones_parent_first(ragdoll_bone_order, ragdoll_hierarchy)
    ragdoll_bone_to_idx = {rag_name: index for index, rag_name in enumerate(ragdoll_bone_order)}

    ragdoll_parent_indices = []
    for rag_name in ragdoll_bone_order:
        parent_name = ragdoll_hierarchy.get(rag_name)
        if parent_name not in ragdoll_bone_to_idx:
            parent_name = None
        ragdoll_parent_indices.append(-1 if parent_name is None else ragdoll_bone_to_idx[parent_name])

    ragdoll_pose = compute_ragdoll_skeleton_transforms(
        armature, ragdoll_bone_order, ragdoll_bone_map, ragdoll_hierarchy
    )

    bone_mappings = []
    for index, rag_name in enumerate(ragdoll_bone_order):
        anim_bone_name = ragdoll_bone_map.get(rag_name)
        if anim_bone_name and anim_bone_name in bone_name_to_idx:
            bone_mappings.append(
                {
                    "ragdoll_bone": index,
                    "anim_bone": bone_name_to_idx[anim_bone_name],
                    "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "scale": [1, 1, 1]},
                }
            )

    ragdoll_skeleton = {
        "name": ragdoll_bone_order[0] if ragdoll_bone_order else "Ragdoll_Bip01",
        "bones": ragdoll_bone_order,
        "parent_indices": ragdoll_parent_indices,
        "reference_pose": ragdoll_pose,
    }

    return animation_skeleton, ragdoll_skeleton, bone_mappings, ragdoll_bone_map