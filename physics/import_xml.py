# hkx -> assetcc -> xml -> blender
# assetcc goes into blender_hkx/BatchProcess/AssetCc/


from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .import_common import (
    coerce_float,
    coerce_int,
    extract_reference_ids,
    infer_lod_level,
    infer_state_name,
    normalize_motion_type,
    parse_float_sequence,
)
from .import_types import ImportedPhysicsScene, ImportedRigidBody, PhysicsImportError


PHYSICS_DATA_CLASSES = {"hkpPhysicsData", "hkPhysicsData"}
PHYSICS_SYSTEM_CLASSES = {"hkpPhysicsSystem", "hkPhysicsSystem"}
RIGID_BODY_CLASSES = {"hkpRigidBody", "hkRigidBody"}
CONVEX_SHAPE_CLASSES = {"hkpConvexVerticesShape", "hkConvexVerticesShape"}
TRANSLATE_SHAPE_CLASSES = {"hkpConvexTranslateShape", "hkConvexTranslateShape"}
TRANSFORM_SHAPE_CLASSES = {
    "hkpTransformShape",
    "hkTransformShape",
    "hkpConvexTransformShape",
    "hkConvexTransformShape",
}
LIST_SHAPE_CLASSES = {"hkpListShape", "hkListShape"}
CHILD_SHAPE_CLASSES = {"hkpMoppBvTreeShape", "hkMoppBvTreeShape"}


def parse_physics_xml(xml_path: str, source_format: str) -> ImportedPhysicsScene:
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        root = load_sanitized_xml_root(xml_path, exc)

    data_section = root.find(".//hksection[@name='__data__']")
    if data_section is None:
        raise PhysicsImportError("The selected file is not a supported Havok packfile XML")

    object_map = {
        element.get("name"): element
        for element in data_section.findall("./hkobject")
        if element.get("name")
    }
    if not object_map:
        raise PhysicsImportError("No Havok data objects were found in the selected file")

    physics_data = find_physics_data_object(data_section, object_map)
    system_refs = extract_reference_ids(get_param_text(physics_data, "systems"))
    if not system_refs:
        raise PhysicsImportError("The selected file does not contain any physics systems")

    scene = ImportedPhysicsScene(system_count=len(system_refs), source_format=source_format)

    for system_index, system_ref in enumerate(system_refs):
        system_obj = object_map.get(system_ref)
        if system_obj is None or system_obj.get("class") not in PHYSICS_SYSTEM_CLASSES:
            continue

        system_name = get_param_text(system_obj, "name") or f"Physics System {system_index + 1}"
        rigid_body_refs = extract_reference_ids(get_param_text(system_obj, "rigidBodies"))
        bodies = [parse_rigid_body(object_map, ref) for ref in rigid_body_refs]
        bodies = [body for body in bodies if body is not None]
        if not bodies:
            continue

        state_name = infer_state_name(system_name, [body[0] for body in bodies], len(system_refs), system_index)
        for body_name, motion_type, vertices, export_config in bodies:
            if not vertices:
                continue
            scene.rigid_bodies.append(
                ImportedRigidBody(
                    name=body_name,
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


def find_physics_data_object(data_section: ET.Element, object_map: Dict[str, ET.Element]) -> ET.Element:
    for container in data_section.findall("./hkobject[@class='hkRootLevelContainer']"):
        named_variants = container.find("./hkparam[@name='namedVariants']")
        if named_variants is None:
            continue
        for variant in named_variants.findall("./hkobject"):
            variant_name = (get_param_text(variant, "name") or "").strip().lower()
            class_name = (get_param_text(variant, "className") or get_param_text(variant, "class") or "").strip()
            if variant_name != "physics data" and class_name not in PHYSICS_DATA_CLASSES:
                continue
            variant_refs = extract_reference_ids(get_param_text(variant, "variant"))
            if variant_refs:
                physics_obj = object_map.get(variant_refs[0])
                if physics_obj is not None:
                    return physics_obj

    for physics_obj in data_section.findall("./hkobject"):
        if physics_obj.get("class") in PHYSICS_DATA_CLASSES:
            return physics_obj

    raise PhysicsImportError("The selected file is not a physics HKX/XML file")


def parse_rigid_body(
    object_map: Dict[str, ET.Element],
    rigid_body_ref: str,
) -> Optional[Tuple[str, str, List[List[float]], Dict[str, object]]]:
    rigid_body = object_map.get(rigid_body_ref)
    if rigid_body is None or rigid_body.get("class") not in RIGID_BODY_CLASSES:
        return None

    body_name = get_param_text(rigid_body, "name") or rigid_body_ref
    shape_ref = get_nested_param_text(rigid_body, ("collidable", "shape"))
    shape_refs = extract_reference_ids(shape_ref)
    if not shape_refs:
        return None

    motion_type = (get_nested_param_text(rigid_body, ("motion", "type")) or "MOTION_FIXED").strip()
    rigid_body_transform = parse_transform(get_nested_param_text(rigid_body, ("motion", "motionState", "transform")))
    vertices = collect_shape_vertices(object_map, shape_refs[0], visited=set())
    if rigid_body_transform is not None:
        vertices = [
            list(apply_transform((vertex[0], vertex[1], vertex[2]), rigid_body_transform))
            for vertex in vertices
        ]
    normalized_motion = normalize_motion_type(motion_type)
    return body_name, normalized_motion, vertices, parse_xml_export_config(object_map, rigid_body, shape_refs[0], normalized_motion)


def parse_xml_export_config(
    object_map: Dict[str, ET.Element],
    rigid_body: ET.Element,
    shape_ref: str,
    motion_type: str,
) -> Dict[str, object]:
    inertia_values = parse_float_sequence(get_nested_param_text(rigid_body, ("motion", "inertiaAndMassInv")))
    center_values = parse_float_sequence(get_nested_param_text(rigid_body, ("motion", "motionState", "sweptTransform", "centerOfMassLocal")))
    mass = None
    if len(inertia_values) >= 4 and abs(inertia_values[3]) > 1.0e-6:
        mass = 1.0 / inertia_values[3]

    config = {
        "motion_type": motion_type,
        "mass": mass,
        "allowed_penetration_depth": coerce_float(get_nested_param_text(rigid_body, ("collidable", "allowedPenetrationDepth"))),
        "friction": coerce_float(get_nested_param_text(rigid_body, ("material", "friction"))),
        "restitution": coerce_float(get_nested_param_text(rigid_body, ("material", "restitution"))),
        "quality_type": coerce_int(get_nested_param_text(rigid_body, ("collidable", "broadPhaseHandle", "objectQualityType"))),
        "process_contact_callback_delay": coerce_int(get_param_text(rigid_body, "processContactCallbackDelay")),
        "deactivation_class": coerce_int(get_nested_param_text(rigid_body, ("motion", "motionState", "deactivationClass"))),
        "deactivation_integrate_counter": coerce_int(get_nested_param_text(rigid_body, ("motion", "deactivationIntegrateCounter"))),
        "linear_damping": coerce_float(get_nested_param_text(rigid_body, ("motion", "motionState", "linearDamping"))),
        "angular_damping": coerce_float(get_nested_param_text(rigid_body, ("motion", "motionState", "angularDamping"))),
        "max_linear_velocity": coerce_float(get_nested_param_text(rigid_body, ("motion", "motionState", "maxLinearVelocity"))),
        "max_angular_velocity": coerce_float(get_nested_param_text(rigid_body, ("motion", "motionState", "maxAngularVelocity"))),
        "collision_filter_info": coerce_int(get_nested_param_text(rigid_body, ("collidable", "broadPhaseHandle", "collisionFilterInfo"))),
        "event_filter": coerce_int(get_nested_param_text(rigid_body, ("spuCollisionCallback", "eventFilter"))),
        "user_filter": coerce_int(get_nested_param_text(rigid_body, ("spuCollisionCallback", "userFilter"))),
        "center_of_mass_override": center_values[:3] if len(center_values) >= 3 else None,
        "shape_radius": coerce_float(get_shape_radius(object_map, shape_ref, visited=set())),
    }
    return {key: value for key, value in config.items() if value is not None}


def collect_shape_vertices(
    object_map: Dict[str, ET.Element],
    shape_ref: str,
    transform: Optional[Tuple[Tuple[float, float, float], ...]] = None,
    visited: Optional[Set[str]] = None,
) -> List[List[float]]:
    if visited is None:
        visited = set()
    if shape_ref in visited:
        return []

    visited.add(shape_ref)
    shape_obj = object_map.get(shape_ref)
    if shape_obj is None:
        return []

    class_name = shape_obj.get("class") or ""
    if class_name in CONVEX_SHAPE_CLASSES:
        return parse_shape_vertices(shape_obj, transform)

    if class_name in CHILD_SHAPE_CLASSES:
        child_refs = extract_reference_ids(get_param_text(shape_obj, "child"))
        if child_refs:
            return collect_shape_vertices(object_map, child_refs[0], transform, visited)
        return []

    if class_name in LIST_SHAPE_CLASSES:
        vertices: List[List[float]] = []
        for child_ref in extract_list_shape_children(shape_obj):
            vertices.extend(collect_shape_vertices(object_map, child_ref, transform, visited))
        return vertices

    if class_name in TRANSLATE_SHAPE_CLASSES:
        child_refs = extract_reference_ids(get_param_text(shape_obj, "childShape"))
        local_transform = compose_transform(transform, translation_transform(parse_translation(shape_obj, "translation")))
        if child_refs:
            return collect_shape_vertices(object_map, child_refs[0], local_transform, visited)
        return []

    if class_name in TRANSFORM_SHAPE_CLASSES:
        child_refs = extract_reference_ids(get_param_text(shape_obj, "childShape"))
        local_transform = compose_transform(transform, parse_shape_transform(shape_obj))
        if child_refs:
            return collect_shape_vertices(object_map, child_refs[0], local_transform, visited)
        return []

    return []


def parse_shape_vertices(shape_obj: ET.Element, transform: Optional[Tuple[Tuple[float, float, float], ...]]) -> List[List[float]]:
    rotated_vertices = shape_obj.find("./hkparam[@name='rotatedVertices']")
    if rotated_vertices is None:
        return []

    try:
        num_vertices = int((get_param_text(shape_obj, "numVertices") or "0").strip())
    except ValueError:
        num_vertices = 0

    vertices: List[List[float]] = []
    for group in rotated_vertices.findall("./hkobject"):
        xs = parse_float_sequence(get_param_text(group, "x"))
        ys = parse_float_sequence(get_param_text(group, "y"))
        zs = parse_float_sequence(get_param_text(group, "z"))
        group_size = min(len(xs), len(ys), len(zs), 4)
        for index in range(group_size):
            dx_vertex = (xs[index], ys[index], zs[index])
            transformed = apply_transform(dx_vertex, transform)
            vertices.append([transformed[0], transformed[1], transformed[2]])
            if num_vertices and len(vertices) >= num_vertices:
                return vertices

    if num_vertices:
        return vertices[:num_vertices]
    return vertices


def parse_transform(text: str) -> Optional[Tuple[Tuple[float, float, float], ...]]:
    values = parse_float_sequence(text)
    if len(values) < 12:
        return None

    return (
        (values[0], values[1], values[2]),
        (values[3], values[4], values[5]),
        (values[6], values[7], values[8]),
        (values[9], values[10], values[11]),
    )


def parse_translation(shape_obj: ET.Element, param_name: str) -> Optional[Tuple[float, float, float]]:
    values = parse_float_sequence(get_param_text(shape_obj, param_name))
    if len(values) < 3:
        return None
    return (values[0], values[1], values[2])


def parse_shape_transform(shape_obj: ET.Element) -> Optional[Tuple[Tuple[float, float, float], ...]]:
    for param_name in ("transform", "childTransform"):
        transform = parse_transform(get_param_text(shape_obj, param_name))
        if transform is not None:
            return transform

    translation = parse_translation(shape_obj, "translation")
    if translation is not None:
        return translation_transform(translation)
    return None


def translation_transform(translation: Optional[Tuple[float, float, float]]) -> Optional[Tuple[Tuple[float, float, float], ...]]:
    if translation is None:
        return None
    return (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        translation,
    )


def compose_transform(
    parent: Optional[Tuple[Tuple[float, float, float], ...]],
    child: Optional[Tuple[Tuple[float, float, float], ...]],
) -> Optional[Tuple[Tuple[float, float, float], ...]]:
    if parent is None:
        return child
    if child is None:
        return parent

    child_basis_x, child_basis_y, child_basis_z, child_translation = child
    return (
        apply_linear(child_basis_x, parent),
        apply_linear(child_basis_y, parent),
        apply_linear(child_basis_z, parent),
        apply_transform(child_translation, parent),
    )


def apply_linear(
    vertex: Tuple[float, float, float],
    transform: Tuple[Tuple[float, float, float], ...],
) -> Tuple[float, float, float]:
    basis_x, basis_y, basis_z, _translation = transform
    x, y, z = vertex
    world_x = basis_x[0] * x + basis_y[0] * y + basis_z[0] * z
    world_y = basis_x[1] * x + basis_y[1] * y + basis_z[1] * z
    world_z = basis_x[2] * x + basis_y[2] * y + basis_z[2] * z
    return world_x, world_y, world_z


def extract_list_shape_children(shape_obj: ET.Element) -> List[str]:
    for param_name in ("childInfo", "childShapes", "shapes"):
        refs = extract_reference_ids(get_param_text(shape_obj, param_name))
        if refs:
            return refs
    return []


def apply_transform(
    vertex: Tuple[float, float, float],
    transform: Optional[Tuple[Tuple[float, float, float], ...]],
) -> Tuple[float, float, float]:
    if transform is None:
        return vertex

    basis_x, basis_y, basis_z, translation = transform
    x, y, z = vertex
    world_x = basis_x[0] * x + basis_y[0] * y + basis_z[0] * z + translation[0]
    world_y = basis_x[1] * x + basis_y[1] * y + basis_z[1] * z + translation[1]
    world_z = basis_x[2] * x + basis_y[2] * y + basis_z[2] * z + translation[2]
    return world_x, world_y, world_z


def get_param_text(element: ET.Element, param_name: str) -> str:
    param = element.find(f"./hkparam[@name='{param_name}']")
    if param is None:
        return ""
    return "".join(param.itertext()).strip()


def get_nested_param_text(element: ET.Element, param_path: Sequence[str]) -> str:
    current = element
    for name in param_path:
        next_param = find_child_param(current, name)
        if next_param is None:
            return ""
        current = next_param
    return "".join(current.itertext()).strip()


def find_child_param(element: ET.Element, param_name: str) -> Optional[ET.Element]:
    candidates = (
        f"./hkparam[@name='{param_name}']",
        f"./hkobject/hkparam[@name='{param_name}']",
        f".//hkparam[@name='{param_name}']",
    )
    for candidate in candidates:
        found = element.find(candidate)
        if found is not None:
            return found
    return None


def load_sanitized_xml_root(xml_path: str, parse_error: ET.ParseError) -> ET.Element:
    with open(xml_path, "r", encoding="ascii", errors="ignore") as handle:
        xml_text = handle.read()

    sanitized_text = strip_invalid_xml_chars(xml_text)
    try:
        return ET.fromstring(sanitized_text)
    except ET.ParseError as sanitized_error:
        raise PhysicsImportError(f"Failed to parse Havok XML: {sanitized_error}") from parse_error


def strip_invalid_xml_chars(text: str) -> str:
    return "".join(
        character
        for character in text
        if character in "\t\n\r" or ord(character) >= 0x20
    )


def get_shape_radius(
    object_map: Dict[str, ET.Element],
    shape_ref: str,
    visited: Optional[Set[str]] = None,
) -> str:
    if visited is None:
        visited = set()
    if shape_ref in visited:
        return ""
    visited.add(shape_ref)

    shape_obj = object_map.get(shape_ref)
    if shape_obj is None:
        return ""

    radius_text = get_param_text(shape_obj, "radius")
    if radius_text:
        return radius_text

    class_name = shape_obj.get("class") or ""
    child_ref = ""
    if class_name in CHILD_SHAPE_CLASSES:
        child_refs = extract_reference_ids(get_param_text(shape_obj, "child"))
        child_ref = child_refs[0] if child_refs else ""
    elif class_name in TRANSLATE_SHAPE_CLASSES or class_name in TRANSFORM_SHAPE_CLASSES:
        child_refs = extract_reference_ids(get_param_text(shape_obj, "childShape"))
        child_ref = child_refs[0] if child_refs else ""
    elif class_name in LIST_SHAPE_CLASSES:
        child_refs = extract_list_shape_children(shape_obj)
        child_ref = child_refs[0] if child_refs else ""

    if child_ref:
        return get_shape_radius(object_map, child_ref, visited)
    return ""


__all__ = [
    "parse_physics_xml",
]