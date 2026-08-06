# hkx -> json -> blender
# This is the primary import path for physics data, as C++ physics backend
# can exports to json vs xml that needs licensed AssetCc. The importer 
# will attempt to parse the HKX file directly as JSON first, and if that 
# fails, it will fall back to converting the HKX to XML using the physics 
# tool and parsing the XML instead. XML may be removed in the future if C++
# backend is completely tested and stable

from __future__ import annotations

import json
from typing import Dict, List, Tuple

from .import_common import (
    coerce_float,
    coerce_int,
    infer_lod_level,
    infer_state_name,
    normalize_motion_type,
    parse_vector3_data,
)
from .import_types import ImportedPhysicsScene, ImportedRigidBody, PhysicsImportError


def parse_physics_json(json_path: str, source_format: str) -> ImportedPhysicsScene:
    try:
        with open(json_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as exc:
        raise PhysicsImportError(f"Failed to read physics JSON: {exc}") from exc
    except ValueError as exc:
        raise PhysicsImportError(f"Failed to parse physics JSON: {exc}") from exc

    systems = payload.get("physics_systems")
    if not isinstance(systems, list) or not systems:
        raise PhysicsImportError(
            "The physics JSON does not contain any physics systems"
        )

    scene = ImportedPhysicsScene(
        system_count=len(systems),
        source_format=str(payload.get("source_format") or source_format),
    )

    for system_index, system_data in enumerate(systems):
        if not isinstance(system_data, dict):
            continue

        system_name = str(
            system_data.get("name") or f"Physics System {system_index + 1}"
        )
        bodies_data = system_data.get("rigid_bodies")
        if not isinstance(bodies_data, list):
            continue

        bodies: List[Tuple[str, str, List[List[float]], Dict[str, object]]] = []
        for body_data in bodies_data:
            if not isinstance(body_data, dict):
                continue
            body_name = str(body_data.get("name") or "")
            motion_type = normalize_motion_type(
                str(body_data.get("motion_type") or "FIXED")
            )
            vertices = parse_json_vertices(body_data.get("vertices"))
            if not vertices:
                continue
            bodies.append(
                (
                    body_name,
                    motion_type,
                    vertices,
                    parse_json_export_config(body_data, motion_type),
                )
            )

        if not bodies:
            continue

        state_name = infer_state_name(
            system_name, [body[0] for body in bodies], len(systems), system_index
        )
        for body_name, motion_type, vertices, export_config in bodies:
            scene.rigid_bodies.append(
                ImportedRigidBody(
                    name=body_name or f"RigidBody {len(scene.rigid_bodies) + 1}",
                    vertices=vertices,
                    motion_type=motion_type,
                    state_name=state_name,
                    lod_level=infer_lod_level(body_name),
                    system_index=system_index,
                    system_name=system_name,
                    export_config=export_config,
                )
            )

    if not scene.rigid_bodies:
        raise PhysicsImportError(
            "The selected file does not contain any convex-hull rigid bodies that can be imported"
        )

    return scene


def parse_json_vertices(vertices_data: object) -> List[List[float]]:
    if not isinstance(vertices_data, list):
        return []

    vertices: List[List[float]] = []
    for vertex_data in vertices_data:
        if not isinstance(vertex_data, (list, tuple)) or len(vertex_data) < 3:
            continue
        try:
            vertices.append(
                [float(vertex_data[0]), float(vertex_data[1]), float(vertex_data[2])]
            )
        except (TypeError, ValueError):
            continue
    return vertices


def parse_json_export_config(
    body_data: Dict[str, object], motion_type: str
) -> Dict[str, object]:
    mass = coerce_float(body_data.get("mass"))
    if mass is None:
        inverse_mass = coerce_float(body_data.get("inverse_mass"))
        if inverse_mass not in (None, 0.0):
            mass = 1.0 / inverse_mass

    config = {
        "motion_type": motion_type,
        "mass": mass,
        "allowed_penetration_depth": coerce_float(
            body_data.get("allowed_penetration_depth")
        ),
        "friction": coerce_float(body_data.get("friction")),
        "restitution": coerce_float(body_data.get("restitution")),
        "quality_type": coerce_int(body_data.get("quality_type")),
        "process_contact_callback_delay": coerce_int(
            body_data.get("process_contact_callback_delay")
        ),
        "deactivation_class": coerce_int(body_data.get("deactivation_class")),
        "deactivation_integrate_counter": coerce_int(
            body_data.get("deactivation_integrate_counter")
        ),
        "linear_damping": coerce_float(body_data.get("linear_damping")),
        "angular_damping": coerce_float(body_data.get("angular_damping")),
        "max_linear_velocity": coerce_float(body_data.get("max_linear_velocity")),
        "max_angular_velocity": coerce_float(body_data.get("max_angular_velocity")),
        "collision_filter_info": coerce_int(body_data.get("collision_filter_info")),
        "event_filter": coerce_int(body_data.get("event_filter")),
        "user_filter": coerce_int(body_data.get("user_filter")),
        "center_of_mass_override": parse_vector3_data(
            body_data.get("center_of_mass_override")
        ),
        "shape_radius": coerce_float(body_data.get("shape_radius")),
    }
    return {key: value for key, value in config.items() if value is not None}


__all__ = [
    "parse_json_export_config",
    "parse_physics_json",
]
