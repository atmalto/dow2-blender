import bpy
from dataclasses import dataclass, field
from mathutils import Matrix, Vector
from typing import List, Optional, Tuple


def blender_to_dx_position(pos: Vector) -> Tuple[float, float, float]:
    """Convert position: Blender to DirectX."""
    return (-pos.x, pos.z, -pos.y)


def blender_to_dx_normal(normal: Vector) -> Tuple[float, float, float]:
    """Convert normal: Blender to DirectX."""
    return (-normal.y, normal.z, -normal.x)


def weights_to_bytes(weights: List[float]) -> bytes:
    """Convert float weights to packed bytes matching MaxScript WeightsToBytes."""
    bytes_out = [0, 0, 0, 0]
    bytes_out[0] = max(0, min(255, int(weights[2] * 255 + 0.5)))
    bytes_out[1] = max(0, min(255, int(weights[1] * 255 + 0.5)))
    bytes_out[2] = max(0, min(255, int(weights[0] * 255 + 0.5)))
    bytes_out[3] = max(0, min(255, int(weights[3] * 255 + 0.5)))

    total = sum(bytes_out)
    delta = total - 255
    bytes_out[0] = max(0, min(255, bytes_out[0] - delta))

    return bytes(bytes_out)


@dataclass
class ExportVertex:
    """Vertex data for export."""

    position: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
    blend_indices: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    blend_weights: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    normal: Vector = field(default_factory=lambda: Vector((0, 0, 1)))
    binormal: Vector = field(default_factory=lambda: Vector((1, 0, 0)))
    tangent: Vector = field(default_factory=lambda: Vector((0, 1, 0)))
    uv: List[Optional[Tuple[float, float]]] = field(default_factory=lambda: [None, None])


@dataclass
class ExportSkinBone:
    """Skin bone data for export."""

    name: str = ""
    matrix: Matrix = field(default_factory=Matrix)
    imatrix: Matrix = field(default_factory=Matrix)
    minimum: Optional[Vector] = None
    maximum: Optional[Vector] = None


@dataclass
class ExportSubMesh:
    """Sub-mesh data for export."""

    name: str = ""
    material_name: str = ""
    vertices: List[ExportVertex] = field(default_factory=list)
    faces: List[Tuple[int, int, int]] = field(default_factory=list)
    skin_bones: List[ExportSkinBone] = field(default_factory=list)
    has_skin: bool = False
    has_map: List[bool] = field(default_factory=lambda: [False, False])
    minimum: Optional[Vector] = None
    maximum: Optional[Vector] = None
    influencing_bone_names: Tuple[str, ...] = field(default_factory=tuple)


@dataclass
class ExportOptions:
    """Export configuration options matching MaxScript ST2ExportDialog."""

    export_materials: bool = True
    export_bones: bool = True
    export_markers: bool = True
    export_mesh: bool = True
    export_rest_pose: bool = False
    apply_bone_limit: bool = False
    combine_same_material_meshes: bool = False
    apply_material_if_missing: bool = False
    uv_channel: int = 1
    damage_state_healthy: str = "healthy"
    damage_state_light_damage: str = "light_damage"
    damage_state_heavy_damage: str = "heavy_damage"
    damage_state_wreck: str = "wreck"
    export_damage_state_var: bool = True
    export_health_var: bool = True
    export_simbox: bool = False
    export_coverbox: bool = False
    # export_existing_bvols: bool = False


DAMAGE_STATE_ITEMS = [
    ("healthy", "healthy", "Use healthy mesh group"),
    ("light_damage", "light_damage", "Use light_damage mesh group"),
    ("heavy_damage", "heavy_damage", "Use heavy_damage mesh group"),
    ("wreck", "wreck", "Use wreck mesh group"),
]


class ExportValidationError(RuntimeError):
    """Raised when export preconditions are not met."""


def export_options_from_dict(options_dict: dict) -> ExportOptions:
    """Build ExportOptions from a dict-like payload used by the operators."""
    return ExportOptions(
        export_materials=options_dict.get("export_materials", True),
        export_bones=options_dict.get("export_bones", True),
        export_markers=options_dict.get("export_markers", True),
        export_mesh=options_dict.get("export_mesh", True),
        export_rest_pose=options_dict.get("export_rest_pose", False),
        apply_bone_limit=options_dict.get("apply_bone_limit", False),
        combine_same_material_meshes=options_dict.get("combine_same_material_meshes", False),
        apply_material_if_missing=options_dict.get("apply_material_if_missing", False),
        uv_channel=options_dict.get("uv_channel", 1),
        damage_state_healthy=options_dict.get("damage_state_healthy", "healthy"),
        damage_state_light_damage=options_dict.get("damage_state_light_damage", "light_damage"),
        damage_state_heavy_damage=options_dict.get("damage_state_heavy_damage", "heavy_damage"),
        damage_state_wreck=options_dict.get("damage_state_wreck", "wreck"),
        export_damage_state_var=options_dict.get("export_damage_state_var", True),
        export_health_var=options_dict.get("export_health_var", True),
        export_simbox=options_dict.get("export_simbox", False),
        export_coverbox=options_dict.get("export_coverbox", False),
        # export_existing_bvols=options_dict.get("export_existing_bvols", False),
    )


def is_relic_material(mat: bpy.types.Material) -> bool:
    """Check if a material is a valid DoW2 Relic material."""
    if mat is None:
        return False
    return mat.get("dow2_is_relic_material", False) or "dow2_shader" in mat


def get_or_create_default_material() -> bpy.types.Material:
    """Get or create the default relic material for meshes without materials."""
    mat_name = "relic.material.default"
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        mat["dow2_is_relic_material"] = True
        mat["dow2_shader"] = "dow2_unit"
        mat["dow2_shader_path"] = ""
        mat["dow2_useLighting"] = True
        mat["dow2_useDepthTest"] = True
        mat["dow2_glossValue"] = 0.5
        mat["dow2_brightness"] = 1.0
    return mat


def get_or_create_unique_default_material(obj_name: str, slot_index: int = 0) -> bpy.types.Material:
    """Get or create a unique default material for missing-slot assignment."""
    mat_name = f"relic.material.default.auto.{obj_name}.{slot_index}"
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        template = get_or_create_default_material()
        mat = template.copy()
        mat.name = mat_name
        mat["dow2_force_unique_export_material"] = True
    return mat


def assign_default_materials_to_missing_slots(unique_per_mesh: bool = False) -> int:
    """Assign default materials to mesh slots that are empty or missing."""
    default_mat = None if unique_per_mesh else get_or_create_default_material()
    assigned_count = 0

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue

        if not obj.data.materials or len(obj.data.materials) == 0:
            mat = get_or_create_unique_default_material(obj.name, 0) if unique_per_mesh else default_mat
            obj.data.materials.append(mat)
            assigned_count += 1
            continue

        for index, mat in enumerate(obj.data.materials):
            if mat is not None:
                continue
            replacement = get_or_create_unique_default_material(obj.name, index) if unique_per_mesh else default_mat
            obj.data.materials[index] = replacement
            assigned_count += 1

    return assigned_count


def validate_materials_for_export() -> Tuple[List[str], List[bpy.types.Object]]:
    """Check all mesh objects for valid relic materials."""
    warnings = []
    meshes_without_materials = []

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue

        if not obj.data.materials or len(obj.data.materials) == 0:
            warnings.append(f"'{obj.name}' has no materials assigned")
            meshes_without_materials.append(obj)
            continue

        for index, mat in enumerate(obj.data.materials):
            if mat is None:
                warnings.append(f"'{obj.name}' has empty material slot {index}")
                if obj not in meshes_without_materials:
                    meshes_without_materials.append(obj)
            elif not is_relic_material(mat):
                warnings.append(f"'{obj.name}' material '{mat.name}' is not a Relic material")
                if obj not in meshes_without_materials:
                    meshes_without_materials.append(obj)

    return warnings, meshes_without_materials


__all__ = [
    "DAMAGE_STATE_ITEMS",
    "ExportValidationError",
    "ExportOptions",
    "ExportSkinBone",
    "ExportSubMesh",
    "ExportVertex",
    "assign_default_materials_to_missing_slots",
    "blender_to_dx_normal",
    "blender_to_dx_position",
    "export_options_from_dict",
    "get_or_create_default_material",
    "get_or_create_unique_default_material",
    "is_relic_material",
    "validate_materials_for_export",
    "weights_to_bytes",
]