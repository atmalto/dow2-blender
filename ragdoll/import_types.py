from __future__ import annotations

from dataclasses import dataclass, field


class RagdollImportError(RuntimeError):
    pass


@dataclass
class ImportedTransform:
    pos: list[float] = field(default_factory=list)
    rot: list[float] = field(default_factory=list)
    scale: list[float] = field(default_factory=list)


@dataclass
class ImportedSkeleton:
    name: str
    bones: list[str] = field(default_factory=list)
    parent_indices: list[int] = field(default_factory=list)
    reference_pose: list[ImportedTransform] = field(default_factory=list)


@dataclass
class ImportedBoneMapping:
    ragdoll_bone: int
    anim_bone: int
    transform: ImportedTransform


@dataclass
class ImportedRigidBody:
    name: str
    bone_index: int
    shape_type: str
    radius: float
    shape_offset: list[float] = field(default_factory=list)
    vertex_a: list[float] = field(default_factory=list)
    vertex_b: list[float] = field(default_factory=list)
    half_extents: list[float] = field(default_factory=list)
    mass: float = 0.0
    friction: float = 0.0
    restitution: float = 0.0
    motion_type: str = ""
    position: list[float] = field(default_factory=list)
    rotation: list[float] = field(default_factory=list)
    linear_damping: float = 0.0
    angular_damping: float = 0.0
    collision_filter_info: int = 0
    quality_type: int = 0


@dataclass
class ImportedConstraint:
    name: str
    body_a_index: int
    body_b_index: int
    constraint_type: str
    pivot_a: list[float] = field(default_factory=list)
    pivot_b: list[float] = field(default_factory=list)
    twist_axis_a: list[float] = field(default_factory=list)
    twist_axis_b: list[float] = field(default_factory=list)
    plane_axis_a: list[float] = field(default_factory=list)
    plane_axis_b: list[float] = field(default_factory=list)
    twist_min: float = 0.0
    twist_max: float = 0.0
    cone_angle: float = 0.0
    plane_min: float = 0.0
    plane_max: float = 0.0
    hinge_min: float = 0.0
    hinge_max: float = 0.0
    friction_torque: float = 0.0


@dataclass
class ImportedRagdollScene:
    animation_skeleton: ImportedSkeleton
    ragdoll_skeleton: ImportedSkeleton
    bone_mappings: list[ImportedBoneMapping] = field(default_factory=list)
    rigid_bodies: list[ImportedRigidBody] = field(default_factory=list)
    constraints: list[ImportedConstraint] = field(default_factory=list)
    source_format: str = "hkx"


__all__ = [
    "ImportedBoneMapping",
    "ImportedConstraint",
    "ImportedRagdollScene",
    "ImportedRigidBody",
    "ImportedSkeleton",
    "ImportedTransform",
    "RagdollImportError",
]