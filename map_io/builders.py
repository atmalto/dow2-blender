from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from ..model import utils as model_utils
from ..utils import dx_to_blender_matrix, dx_to_blender_position
from .materials import build_nav_overlay_material, build_terrain_material
from .types import EntityData, TerrainData


def _scenario_dx_matrix(rows: list[tuple[float, float, float]]) -> Matrix:
    return Matrix(
        (
            (rows[0][0], rows[0][1], rows[0][2], rows[3][0]),
            (rows[1][0], rows[1][1], rows[1][2], rows[3][1]),
            (rows[2][0], rows[2][1], rows[2][2], rows[3][2]),
            (0.0, 0.0, 0.0, 1.0),
        )
    )


def _clear_collection_objects(collection: bpy.types.Collection):
    for child in list(collection.children):
        _clear_collection_objects(child)
        bpy.data.collections.remove(child)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def ensure_map_collection(scene: bpy.types.Scene, map_name: str) -> bpy.types.Collection:
    collection = model_utils.ensure_child_collection(scene.collection, f"DoW2 Map::{map_name}")
    _clear_collection_objects(collection)
    return collection


def create_terrain_mesh(
    parent_collection: bpy.types.Collection,
    map_name: str,
    terrain: TerrainData,
    tile_root: Path,
    *,
    with_textures: bool,
):
    mesh = bpy.data.meshes.new(f"DoW2Terrain::{map_name}")
    obj = bpy.data.objects.new(f"DoW2Terrain::{map_name}", mesh)
    parent_collection.objects.link(obj)
    obj["dow2_map_component"] = "terrain"
    obj["dow2_map_source"] = map_name

    half_width = (terrain.width - 1) / 2.0
    half_height = (terrain.height - 1) / 2.0
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    mask_uvs: list[tuple[float, float]] = []
    tile_uvs: list[tuple[float, float]] = []
    tile_scale = terrain.tile_world_scale if terrain.tile_world_scale > 0.0 else 8.0

    for z in range(terrain.height):
        for x in range(terrain.width):
            height_value = terrain.heights[z * terrain.width + x]
            dx_pos = Vector((x - half_width, height_value, z - half_height))
            pos = dx_to_blender_position(dx_pos)
            vertices.append((pos.x, pos.y, pos.z))
            mask_uvs.append(
                (
                    (x + 0.5) / max(1, terrain.width - 1),
                    (z + 0.5) / max(1, terrain.height - 1),
                )
            )
            tile_uvs.append((x / tile_scale, z / tile_scale))

    for z in range(terrain.height - 1):
        for x in range(terrain.width - 1):
            i0 = z * terrain.width + x
            i1 = i0 + 1
            i2 = i0 + terrain.width + 1
            i3 = i0 + terrain.width
            faces.append((i0, i1, i2, i3))

    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv_mask = mesh.uv_layers.new(name="TerrainMaskUV")
    uv_tile = mesh.uv_layers.new(name="TerrainTileUV")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            uv_mask.data[loop_index].uv = mask_uvs[vertex_index]
            uv_tile.data[loop_index].uv = tile_uvs[vertex_index]

    if with_textures and terrain.layer_paths and terrain.mask_payloads:
        material = build_terrain_material(
            name=f"DoW2TerrainMaterial::{map_name}",
            tile_root=tile_root,
            layer_paths=terrain.layer_paths,
            mask_payloads=terrain.mask_payloads,
            layer_usage_map=terrain.layer_usage_map,
            tile_world_scale=terrain.tile_world_scale,
        )
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
    return obj


def create_marker_objects(scene: bpy.types.Scene, parent_collection: bpy.types.Collection, marker_path: Path):
    from .bundle_reader import _import_working_maps_module

    marker_parser = _import_working_maps_module("marker_parser")
    report = marker_parser.parse_marker_file(marker_path)
    enabled_names = bool(getattr(scene, "dow2_show_bone_marker_names", False))
    for marker in report.get("markers", []):
        name = str(marker.get("name") or f"marker_{marker.get('marker_id', 0)}")
        empty = bpy.data.objects.new(name, None)
        empty["dow2_map_component"] = "marker"
        empty["dow2_is_marker"] = True
        empty["dow2_marker_type"] = str(marker.get("marker_type") or "")
        empty.show_name = enabled_names
        color = marker.get("display_color_rgb") or marker.get("vector_b") or (1.0, 1.0, 1.0)
        empty.color = (color[0], color[1], color[2], 1.0)
        shape_kind = marker.get("shape_kind") or "point"
        rows = list(
            marker.get("orientation_matrix3x3")
            or marker.get("basis_matrix3x3")
            or [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
        )
        rows.append(tuple(marker.get("position") or (0.0, 0.0, 0.0)))
        empty.matrix_world = dx_to_blender_matrix(_scenario_dx_matrix(rows))
        if shape_kind == "rectangle":
            empty.empty_display_type = 'CUBE'
            extents = marker.get("rectangle_extents_xy") or (1.0, 1.0)
            empty.scale = (max(extents[0], 0.1), max(extents[1], 0.1), 0.05)
        elif shape_kind == "radius":
            empty.empty_display_type = 'SPHERE'
            radius = float(marker.get("shape_scalar") or 1.0)
            empty.scale = (radius, radius, radius)
        else:
            empty.empty_display_type = 'PLAIN_AXES'
            empty.empty_display_size = 0.75
        parent_collection.objects.link(empty)


def _sample_terrain_height(terrain: TerrainData, dx_x: float, dx_z: float) -> float:
    half_width = (terrain.width - 1) / 2.0
    half_height = (terrain.height - 1) / 2.0
    grid_x = int(round(dx_x + half_width))
    grid_z = int(round(dx_z + half_height))
    grid_x = max(0, min(terrain.width - 1, grid_x))
    grid_z = max(0, min(terrain.height - 1, grid_z))
    return terrain.heights[grid_z * terrain.width + grid_x]


def create_nav_overlay(parent_collection: bpy.types.Collection, map_name: str, terrain: TerrainData, nav_grid: dict[str, object]):
    width = int(nav_grid["width"])
    height = int(nav_grid["height"])
    values = nav_grid["values"]
    half_width = (terrain.width - 1) / 2.0
    half_height = (terrain.height - 1) / 2.0
    cell_dx = (terrain.width - 1) / width
    cell_dz = (terrain.height - 1) / height

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    for z in range(height):
        for x in range(width):
            if values[z * width + x] == 0:
                continue
            x0 = -half_width + (x * cell_dx)
            x1 = x0 + cell_dx
            z0 = -half_height + (z * cell_dz)
            z1 = z0 + cell_dz
            corners = [
                (x0, _sample_terrain_height(terrain, x0, z0) + 0.15, z0),
                (x1, _sample_terrain_height(terrain, x1, z0) + 0.15, z0),
                (x1, _sample_terrain_height(terrain, x1, z1) + 0.15, z1),
                (x0, _sample_terrain_height(terrain, x0, z1) + 0.15, z1),
            ]
            start = len(vertices)
            for corner in corners:
                pos = dx_to_blender_position(Vector(corner))
                vertices.append((pos.x, pos.y, pos.z))
            faces.append((start, start + 1, start + 2, start + 3))

    if not faces:
        return None
    mesh = bpy.data.meshes.new(f"DoW2Nav::{map_name}")
    obj = bpy.data.objects.new(f"DoW2Nav::{map_name}", mesh)
    parent_collection.objects.link(obj)
    obj["dow2_map_component"] = "nav"
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    material = build_nav_overlay_material()
    obj.data.materials.append(material)
    return obj


def create_object_bounds(parent_collection: bpy.types.Collection, entities: list[EntityData]):
    cube_mesh = bpy.data.meshes.get("DoW2MapObjectBoundsMesh")
    if cube_mesh is None:
        cube_mesh = bpy.data.meshes.new("DoW2MapObjectBoundsMesh")
        cube_mesh.from_pydata(
            [
                (-0.5, -0.5, -0.5),
                (0.5, -0.5, -0.5),
                (0.5, 0.5, -0.5),
                (-0.5, 0.5, -0.5),
                (-0.5, -0.5, 0.5),
                (0.5, -0.5, 0.5),
                (0.5, 0.5, 0.5),
                (-0.5, 0.5, 0.5),
            ],
            [],
            [
                (0, 1, 2, 3),
                (4, 5, 6, 7),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            ],
        )
        cube_mesh.update()
    for entity in entities:
        name = Path(entity.blueprint_name).name or entity.blueprint_name
        obj = bpy.data.objects.new(name, cube_mesh)
        obj["dow2_map_component"] = "object_proxy"
        obj["dow2_blueprint_name"] = entity.blueprint_name
        obj.matrix_world = dx_to_blender_matrix(_scenario_dx_matrix(entity.matrix_rows))
        obj.scale = (1.0, 1.0, 1.0)
        obj.display_type = 'BOUNDS'
        obj.show_name = True
        parent_collection.objects.link(obj)


__all__ = [
    "create_marker_objects",
    "create_nav_overlay",
    "create_object_bounds",
    "create_terrain_mesh",
    "ensure_map_collection",
]