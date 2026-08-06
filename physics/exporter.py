from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import List

import bpy

from . import hull_properties, utils


ADDON_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ADDON_PATH, "blender_hkx")


def resolve_physics_exporter() -> str:
    return os.path.join(SCRIPTS_DIR, "havok_io_cli.exe")


PHYSICS_EXE = resolve_physics_exporter()


@dataclass
class ConvexHullData:
    name: str
    vertices: List[List[float]]
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])
    friction: float = 0.5
    restitution: float = 0.4
    motion_type: str = "FIXED"
    quality_type: int = 1
    allowed_penetration_depth: float = 0.0
    process_contact_callback_delay: int = 65535
    deactivation_class: int = 1
    deactivation_integrate_counter: int = 255
    linear_damping: float = 0.0
    angular_damping: float = 0.05
    max_linear_velocity: float = 200.0
    max_angular_velocity: float = 200.0
    collision_filter_info: int = 0
    event_filter: int = 0
    user_filter: int = 0
    mass: float = 0.0
    center_of_mass_mode: str = "ZERO"
    center_of_mass_override: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    shape_radius: float = 0.05
    response_type: str = "RESPONSE_SIMPLE_CONTACT"
    deactivator_present: bool = False


@dataclass
class PhysicsSystemData:
    name: str
    rigid_bodies: List[ConvexHullData] = field(default_factory=list)


def build_physics_systems(scene: bpy.types.Scene) -> List[PhysicsSystemData]:
    hulls_by_state = utils.collect_physics_hulls(scene)
    systems: List[PhysicsSystemData] = []

    for state_name in utils.STATE_NAMES:
        lod_map = hulls_by_state.get(state_name, {})
        rigid_bodies: List[ConvexHullData] = []
        for lod_level in sorted(lod_map.keys()):
            hull_objects = sorted(
                lod_map[lod_level],
                key=lambda obj: (utils.get_hull_body_name(obj).lower(), obj.name.lower()),
            )
            for hull_obj in hull_objects:
                hull_vertices = utils.hull_object_to_dx_vertices(hull_obj)
                if not hull_vertices:
                    continue
                config = hull_properties.resolve_export_settings(hull_obj)
                rigid_bodies.append(
                    ConvexHullData(
                        name=utils.get_hull_body_name(hull_obj),
                        vertices=hull_vertices,
                        friction=float(config["friction"]),
                        restitution=float(config["restitution"]),
                        motion_type=str(config["motion_type"]),
                        quality_type=int(config["quality_type"]),
                        allowed_penetration_depth=float(config["allowed_penetration_depth"]),
                        process_contact_callback_delay=int(config["process_contact_callback_delay"]),
                        deactivation_class=int(config["deactivation_class"]),
                        deactivation_integrate_counter=int(config["deactivation_integrate_counter"]),
                        linear_damping=float(config["linear_damping"]),
                        angular_damping=float(config["angular_damping"]),
                        max_linear_velocity=float(config["max_linear_velocity"]),
                        max_angular_velocity=float(config["max_angular_velocity"]),
                        collision_filter_info=int(config["collision_filter_info"]),
                        event_filter=int(config["event_filter"]),
                        user_filter=int(config["user_filter"]),
                        mass=float(config["mass"]),
                        center_of_mass_mode=str(config["center_of_mass_mode"]),
                        center_of_mass_override=list(config["center_of_mass_override"]),
                        shape_radius=float(config["shape_radius"]),
                        response_type=str(config["response_type"]),
                        deactivator_present=bool(config["deactivator_present"]),
                    )
                )

        if rigid_bodies:
            systems.append(PhysicsSystemData(name="Default Physics System", rigid_bodies=rigid_bodies))

    return systems


def export_physics_json(physics_systems: List[PhysicsSystemData], output_path: str) -> None:
    payload = {
        "version": "1.0",
        "physics_systems": [],
    }

    for system in physics_systems:
        payload["physics_systems"].append(
            {
                "name": system.name,
                "rigid_bodies": [
                    {
                        "name": body.name,
                        "vertices": body.vertices,
                        "position": body.position,
                        "rotation": body.rotation,
                        "friction": body.friction,
                        "restitution": body.restitution,
                        "motion_type": body.motion_type,
                        "quality_type": body.quality_type,
                        "allowed_penetration_depth": body.allowed_penetration_depth,
                        "process_contact_callback_delay": body.process_contact_callback_delay,
                        "deactivation_class": body.deactivation_class,
                        "deactivation_integrate_counter": body.deactivation_integrate_counter,
                        "linear_damping": body.linear_damping,
                        "angular_damping": body.angular_damping,
                        "max_linear_velocity": body.max_linear_velocity,
                        "max_angular_velocity": body.max_angular_velocity,
                        "collision_filter_info": body.collision_filter_info,
                        "event_filter": body.event_filter,
                        "user_filter": body.user_filter,
                        "mass": body.mass,
                        "center_of_mass_mode": body.center_of_mass_mode,
                        "center_of_mass_override": body.center_of_mass_override,
                        "shape_radius": body.shape_radius,
                        "response_type": body.response_type,
                        "deactivator_present": body.deactivator_present,
                    }
                    for body in system.rigid_bodies
                ],
            }
        )

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def run_physics_exporter(json_path: str, hkx_path: str) -> tuple[bool, str]:
    if not os.path.exists(PHYSICS_EXE):
        return False, f"Physics exporter not found: {PHYSICS_EXE}"

    completed = subprocess.run(
        [PHYSICS_EXE, "physics", "write", json_path, hkx_path],
        capture_output=True,
        text=True,
    )

    output = completed.stdout.strip()
    if completed.stderr.strip():
        output = f"{output}\n{completed.stderr.strip()}".strip()
    return completed.returncode == 0 and os.path.exists(hkx_path), output