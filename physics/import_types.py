from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


class PhysicsImportError(RuntimeError):
    pass


@dataclass
class ImportedRigidBody:
    name: str
    vertices: List[List[float]]
    motion_type: str
    state_name: str
    lod_level: int
    system_index: int
    system_name: str = ""
    export_config: Dict[str, object] = field(default_factory=dict)


@dataclass
class ImportedPhysicsScene:
    rigid_bodies: List[ImportedRigidBody] = field(default_factory=list)
    system_count: int = 0
    source_format: str = "hkx"


__all__ = [
    "ImportedPhysicsScene",
    "ImportedRigidBody",
    "PhysicsImportError",
]