from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

from .authoring.body_authoring import apply_body_data_to_object, create_or_update_body_for_bone
from .authoring.body_sync import suspend_body_sync
from .authoring.collections import ragdoll_collection_name, remove_collection_tree
from .authoring.constants import RAGDOLL_MAPPING_TRANSFORM_PROP
from .authoring.constraint_props import apply_constraint_data_to_bone
from .authoring.preview import sync_constraint_preview_objects
from .authoring.queries import find_source_armature
from .authoring.skeleton_authoring import (
    animation_collection_name,
    create_scene_animation_skeleton,
    create_scene_ragdoll_skeleton,
)
from .import_types import ImportedConstraint, ImportedRagdollScene, ImportedRigidBody, ImportedTransform, RagdollImportError
from .importer import load_ragdoll_scene
from .scene import import_model


class RagdollImporter:
    def import_scene(
        self,
        context: bpy.types.Context,
        ragdoll_path: str,
        model_path: str | None = None,
        ragdoll_name: str | None = None,
    ) -> bpy.types.Object:
        scene_data = load_ragdoll_scene(ragdoll_path)
        self._validate_scene_data(scene_data)
        target_name = (ragdoll_name or Path(ragdoll_path).stem or "ragdoll").strip() or "ragdoll"

        if model_path:
            self.import_model_source_armature(context, model_path)

        animation_object = create_scene_animation_skeleton(
            context,
            target_name,
            self._animation_skeleton_payload(scene_data),
        )
        return self.apply_to_source_armature(
            context,
            animation_object,
            scene_data,
            ragdoll_name=target_name,
            prefer_reference_pose_display=False,
        )

    def import_model_source_armature(
        self,
        context: bpy.types.Context,
        model_path: str,
    ) -> bpy.types.Object:
        existing_armature_names = {
            obj.name
            for obj in bpy.data.objects
            if obj.type == "ARMATURE"
        }

        result = import_model(model_path, reset_scene=False)
        if "FINISHED" not in result:
            raise RagdollImportError(f"Model import failed: {result}")

        new_armatures = [
            obj
            for obj in bpy.data.objects
            if obj.type == "ARMATURE" and obj.name not in existing_armature_names
        ]
        if len(new_armatures) == 1:
            return new_armatures[0]

        active_object = context.view_layer.objects.active
        if active_object is not None and active_object in new_armatures:
            return active_object

        source_armature = find_source_armature(context)
        if source_armature is not None and source_armature.name not in existing_armature_names:
            return source_armature

        if len(new_armatures) > 1:
            raise RagdollImportError(
                "Model import produced multiple armatures and the ragdoll importer could not resolve the new source armature"
            )

        if active_object is not None and active_object.type == "ARMATURE" and active_object.name not in existing_armature_names:
            return active_object

        if source_armature is None or source_armature.type != "ARMATURE":
            raise RagdollImportError("Model import did not produce a usable source armature")
        raise RagdollImportError(
            "Model import did not produce a new source armature without resetting the current scene"
        )

    def apply_to_source_armature(
        self,
        context: bpy.types.Context,
        source_armature: bpy.types.Object,
        scene_data: ImportedRagdollScene,
        ragdoll_name: str | None = None,
        prefer_reference_pose_display: bool = False,
    ) -> bpy.types.Object:
        if source_armature.type != "ARMATURE":
            raise RagdollImportError("Ragdoll import requires an armature source object")

        self._validate_scene_data(scene_data)
        source_bone_map = self._resolve_source_bone_map(source_armature, scene_data)
        target_name = (ragdoll_name or source_armature.name or "ragdoll").strip() or "ragdoll"
        collection_name = ragdoll_collection_name(target_name)

        try:
            skeleton_object = create_scene_ragdoll_skeleton(
                context,
                source_armature,
                target_name,
                ragdoll_skeleton_data=self._ragdoll_skeleton_payload(scene_data),
                ragdoll_bone_map=source_bone_map,
                prefer_reference_pose_display=prefer_reference_pose_display,
            )
            # Keep the live capsule sync from firing while we place bodies at their
            # authoritative Havok joint origins; otherwise depsgraph updates from
            # building the body meshes recenter them off their joints before the
            # per-body joint-origin flag is set.
            with suspend_body_sync():
                self._apply_rigid_bodies(skeleton_object, scene_data)
                self._apply_constraints(skeleton_object, scene_data)
            self._store_bone_mapping_transforms(skeleton_object, scene_data)
            sync_constraint_preview_objects()
            self._select_imported_skeleton(context, skeleton_object)
            return skeleton_object
        except Exception:
            partial_collection = context.scene.collection.children.get(collection_name)
            if partial_collection is not None:
                remove_collection_tree(partial_collection)
            raise

    def _validate_scene_data(self, scene_data: ImportedRagdollScene) -> None:
        ragdoll_bone_count = len(scene_data.ragdoll_skeleton.bones)
        if len(scene_data.rigid_bodies) != ragdoll_bone_count:
            raise RagdollImportError(
                "Imported ragdoll data must contain exactly one rigid body for each ragdoll bone"
            )

        seen_constraint_children: set[int] = set()
        for constraint in scene_data.constraints:
            _parent_bone_index, child_bone_index = self._resolve_constraint_bones(scene_data, constraint)
            if child_bone_index in seen_constraint_children:
                raise RagdollImportError(
                    f"Multiple constraints target ragdoll bone index {child_bone_index}"
                )
            seen_constraint_children.add(child_bone_index)

    def _resolve_constraint_bones(
        self,
        scene_data: ImportedRagdollScene,
        constraint: ImportedConstraint,
    ) -> tuple[int, int]:
        body_a = scene_data.rigid_bodies[constraint.body_a_index]
        body_b = scene_data.rigid_bodies[constraint.body_b_index]
        parent_indices = scene_data.ragdoll_skeleton.parent_indices

        if parent_indices[body_b.bone_index] == body_a.bone_index:
            return body_a.bone_index, body_b.bone_index
        if parent_indices[body_a.bone_index] == body_b.bone_index:
            return body_b.bone_index, body_a.bone_index

        raise RagdollImportError(
            f"Constraint {constraint.name} does not match the imported ragdoll hierarchy"
        )

    def _resolve_source_bone_map(
        self,
        source_armature: bpy.types.Object,
        scene_data: ImportedRagdollScene,
    ) -> dict[str, str]:
        source_bones_by_lower = {
            bone.name.lower(): bone.name
            for bone in source_armature.data.bones
        }
        ragdoll_names = scene_data.ragdoll_skeleton.bones
        animation_names = scene_data.animation_skeleton.bones
        ragdoll_to_source: dict[str, str] = {}
        missing_animation_bones: list[str] = []

        for mapping in scene_data.bone_mappings:
            ragdoll_name = ragdoll_names[mapping.ragdoll_bone]
            animation_name = animation_names[mapping.anim_bone]
            source_bone_name = source_bones_by_lower.get(animation_name.lower())
            if source_bone_name is None:
                missing_animation_bones.append(animation_name)
                continue
            ragdoll_to_source[ragdoll_name] = source_bone_name

        if missing_animation_bones:
            preview = ", ".join(sorted(set(missing_animation_bones))[:8])
            if len(set(missing_animation_bones)) > 8:
                preview = f"{preview}, ..."
            raise RagdollImportError(
                "Model armature is missing animation bones required by the imported ragdoll: "
                f"{preview}"
            )

        missing_ragdoll_bones = [
            bone_name
            for bone_name in ragdoll_names
            if bone_name not in ragdoll_to_source
        ]
        if missing_ragdoll_bones:
            preview = ", ".join(missing_ragdoll_bones[:8])
            if len(missing_ragdoll_bones) > 8:
                preview = f"{preview}, ..."
            raise RagdollImportError(
                "Imported ragdoll bones are missing animation-to-model mappings: "
                f"{preview}"
            )

        return ragdoll_to_source

    def _store_bone_mapping_transforms(
        self,
        skeleton_object: bpy.types.Object,
        scene_data: ImportedRagdollScene,
    ) -> None:
        # Persist the ragdoll->animation mapping transform (pos+rot+scale) read
        # from the shipped .hkx onto each ragdoll bone so export can re-emit it
        # instead of collapsing every mapping to identity.
        ragdoll_names = scene_data.ragdoll_skeleton.bones
        bones = skeleton_object.data.bones
        for mapping in scene_data.bone_mappings:
            ragdoll_name = ragdoll_names[mapping.ragdoll_bone]
            bone = bones.get(ragdoll_name)
            if bone is None:
                continue
            transform = mapping.transform
            bone[RAGDOLL_MAPPING_TRANSFORM_PROP] = [
                float(transform.pos[0]), float(transform.pos[1]), float(transform.pos[2]),
                float(transform.rot[0]), float(transform.rot[1]), float(transform.rot[2]), float(transform.rot[3]),
                float(transform.scale[0]), float(transform.scale[1]), float(transform.scale[2]),
            ]

    def _ragdoll_skeleton_payload(self, scene_data: ImportedRagdollScene) -> dict[str, object]:
        return {
            "name": scene_data.ragdoll_skeleton.name,
            "bones": list(scene_data.ragdoll_skeleton.bones),
            "parent_indices": list(scene_data.ragdoll_skeleton.parent_indices),
            "reference_pose": [self._transform_payload(transform) for transform in scene_data.ragdoll_skeleton.reference_pose],
        }

    def _animation_skeleton_payload(self, scene_data: ImportedRagdollScene) -> dict[str, object]:
        return {
            "name": scene_data.animation_skeleton.name,
            "bones": list(scene_data.animation_skeleton.bones),
            "parent_indices": list(scene_data.animation_skeleton.parent_indices),
            "reference_pose": [self._transform_payload(transform) for transform in scene_data.animation_skeleton.reference_pose],
        }

    def _transform_payload(self, transform: ImportedTransform) -> dict[str, list[float]]:
        return {
            "pos": list(transform.pos),
            "rot": list(transform.rot),
            "scale": list(transform.scale),
        }

    def _body_payload(self, rigid_body: ImportedRigidBody) -> dict[str, object]:
        payload = {
            "name": rigid_body.name,
            "bone_index": rigid_body.bone_index,
            "shape_type": rigid_body.shape_type,
            "radius": rigid_body.radius,
            "vertex_a": list(rigid_body.vertex_a),
            "vertex_b": list(rigid_body.vertex_b),
            "half_extents": list(rigid_body.half_extents),
            "mass": rigid_body.mass,
            "friction": rigid_body.friction,
            "restitution": rigid_body.restitution,
            "motion_type": rigid_body.motion_type,
            "position": list(rigid_body.position),
            "rotation": list(rigid_body.rotation),
            "linear_damping": rigid_body.linear_damping,
            "angular_damping": rigid_body.angular_damping,
            "collision_filter_info": rigid_body.collision_filter_info,
            "quality_type": rigid_body.quality_type,
        }

        # Keep the shipped Havok convention: body origin at the joint with the
        # capsule vertices offset asymmetrically toward the limb. Do NOT recenter
        # onto the geometric midpoint here — the constraint pivots are stored
        # relative to this joint origin, so moving the body origin without moving
        # the pivots desyncs them and the exported ragdoll explodes. The imported
        # bodies are flagged joint-origin so the live capsule sync leaves them put.
        return payload

    def _constraint_payload(self, constraint: ImportedConstraint) -> dict[str, object]:
        return {
            "name": constraint.name,
            "body_a_index": constraint.body_a_index,
            "body_b_index": constraint.body_b_index,
            "constraint_type": constraint.constraint_type,
            "pivot_a": list(constraint.pivot_a),
            "pivot_b": list(constraint.pivot_b),
            "twist_axis_a": list(constraint.twist_axis_a),
            "twist_axis_b": list(constraint.twist_axis_b),
            "plane_axis_a": list(constraint.plane_axis_a),
            "plane_axis_b": list(constraint.plane_axis_b),
            "twist_min": constraint.twist_min,
            "twist_max": constraint.twist_max,
            "cone_angle": constraint.cone_angle,
            "plane_min": constraint.plane_min,
            "plane_max": constraint.plane_max,
            "hinge_min": constraint.hinge_min,
            "hinge_max": constraint.hinge_max,
            "friction_torque": constraint.friction_torque,
        }

    def _apply_rigid_bodies(
        self,
        skeleton_object: bpy.types.Object,
        scene_data: ImportedRagdollScene,
    ) -> None:
        bodies_by_bone_index = {body.bone_index: body for body in scene_data.rigid_bodies}
        for bone_index, bone_name in enumerate(scene_data.ragdoll_skeleton.bones):
            rigid_body = bodies_by_bone_index.get(bone_index)
            if rigid_body is None:
                raise RagdollImportError(f"Imported ragdoll bone {bone_name} is missing a rigid body")

            length = max(abs(rigid_body.vertex_b[1] - rigid_body.vertex_a[1]), rigid_body.half_extents[1] * 2.0, 0.001)
            height = max(rigid_body.radius * 2.0, rigid_body.half_extents[2] * 2.0, 0.001)
            body_object = create_or_update_body_for_bone(
                skeleton_object,
                bone_name,
                rigid_body.shape_type.upper(),
                max(rigid_body.radius, 0.001),
                height,
                length,
            )
            apply_body_data_to_object(body_object, self._body_payload(rigid_body), apply_world_transform=True)

    def _apply_constraints(
        self,
        skeleton_object: bpy.types.Object,
        scene_data: ImportedRagdollScene,
    ) -> None:
        bones_by_name = {bone.name: bone for bone in skeleton_object.data.bones}
        ragdoll_bone_names = scene_data.ragdoll_skeleton.bones
        for constraint in scene_data.constraints:
            _parent_bone_index, child_bone_index = self._resolve_constraint_bones(scene_data, constraint)
            bone_name = ragdoll_bone_names[child_bone_index]
            bone = bones_by_name.get(bone_name)
            if bone is None:
                raise RagdollImportError(f"Ragdoll bone {bone_name} was not created during import")
            apply_constraint_data_to_bone(bone, self._constraint_payload(constraint))

    def _select_imported_skeleton(
        self,
        context: bpy.types.Context,
        skeleton_object: bpy.types.Object,
    ) -> None:
        if context.mode != "OBJECT" and bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        skeleton_object.select_set(True)
        context.view_layer.objects.active = skeleton_object


def import_ragdoll_scene(
    context: bpy.types.Context,
    ragdoll_path: str,
    model_path: str,
    ragdoll_name: str | None = None,
) -> bpy.types.Object:
    return RagdollImporter().import_scene(
        context,
        ragdoll_path,
        model_path,
        ragdoll_name=ragdoll_name,
    )


__all__ = [
    "RagdollImporter",
    "import_ragdoll_scene",
]