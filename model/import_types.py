from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from mathutils import Matrix, Vector


@dataclass
class VertexElement:
    """Vertex element descriptor from mesh data"""

    element_type: int = 0
    version: int = 0
    data_type: int = 0


@dataclass
class ImportVertex:
    """Complete vertex data including all attributes"""

    position: Vector = field(default_factory=lambda: Vector((0, 0, 0)))
    blend_indices: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    blend_weights: List[float] = field(default_factory=lambda: [1.0, 0.0, 0.0, 0.0])
    normal: Vector = field(default_factory=lambda: Vector((0, 0, 1)))
    binormal: Vector = field(default_factory=lambda: Vector((0, 1, 0)))
    tangent: Vector = field(default_factory=lambda: Vector((1, 0, 0)))
    color: Tuple[float, float, float, float] = field(default_factory=lambda: (1.0, 1.0, 1.0, 1.0))
    uv: List[Tuple[float, float]] = field(default_factory=lambda: [(0.0, 0.0), (0.0, 0.0)])


@dataclass
class ImportBone:
    """Bone data from skeleton"""

    name: str = ""
    parent_index: int = -1
    matrix: Matrix = field(default_factory=Matrix)
    import_transform: Matrix = field(default_factory=Matrix)
    transform: Matrix = field(default_factory=Matrix)


@dataclass
class ImportMarker:
    """Marker/attachment point data"""

    name: str = ""
    parent: str = ""
    matrix: Matrix = field(default_factory=Matrix)
    params: Dict[str, str] = field(default_factory=dict)


@dataclass
class SkinBone:
    """Per-mesh skin bone data with world/inverse matrices"""

    name: str = ""
    world_matrix: Matrix = field(default_factory=Matrix)
    inverse_matrix: Matrix = field(default_factory=Matrix)


@dataclass
class ImportMesh:
    """Complete mesh data"""

    name: str = ""
    vertices: List[ImportVertex] = field(default_factory=list)
    faces: List[Tuple[int, int, int]] = field(default_factory=list)
    material_name: str = ""
    skin_bones: List[SkinBone] = field(default_factory=list)
    has_uv2: bool = False
    has_vertex_color: bool = False
    lod_level: int = 0
    mesh_group: str = ""


@dataclass
class ImportOptions:
    """Import configuration options - matches MaxScript ST2Import options"""

    import_meshes: bool = True
    import_materials: bool = True
    import_bones: bool = True
    import_markers: bool = True
    import_bounding_volumes: bool = False
    import_simbox: bool = False
    import_coverbox: bool = False
    smoothing: str = "NORMALS"
    reset_scene: bool = False
    save_scene: bool = False
    merge: bool = False
    group_meshes: bool = True
    weld_vertices: bool = False