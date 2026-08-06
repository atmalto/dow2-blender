from __future__ import annotations

from pathlib import Path

import bpy

from ..model import utils as model_utils
from .builders import (
    create_marker_objects,
    create_nav_overlay,
    create_object_bounds,
    create_terrain_mesh,
    ensure_map_collection,
)
from .bundle_reader import load_bundle_data, parse_entities, parse_nav_grid, parse_terrain, resolve_data_root
from .types import MapImportOptions, MapImportResult


def import_scenario_map(context: bpy.types.Context, scenario_path: str, options: MapImportOptions):
    path = Path(scenario_path)
    if not path.exists():
        raise FileNotFoundError(path)

    data, terr_root, smeg_root = load_bundle_data(path)
    terrain = parse_terrain(terr_root, data)
    entities = parse_entities(smeg_root, data) if options.import_objects else []
    nav_grid = parse_nav_grid(smeg_root, data) if options.import_nav_plane else None
    data_root = resolve_data_root(path)
    tile_root = data_root / "art" / "terrain_textures" / "tiles"

    map_collection = ensure_map_collection(context.scene, path.stem)
    terrain_collection = model_utils.ensure_child_collection(map_collection, "Terrain")
    marker_collection = model_utils.ensure_child_collection(map_collection, "Markers")
    nav_collection = model_utils.ensure_child_collection(map_collection, "Nav")
    object_collection = model_utils.ensure_child_collection(map_collection, "Objects")

    terrain_obj = None
    marker_count = 0
    nav_obj = None
    if options.import_mesh:
        terrain_obj = create_terrain_mesh(
            terrain_collection,
            path.stem,
            terrain,
            tile_root,
            with_textures=options.import_textures,
        )
    if options.import_markers:
        marker_path = path.with_suffix(".scenariomarker")
        if marker_path.exists():
            create_marker_objects(context.scene, marker_collection, marker_path)
            marker_count = len(marker_collection.objects)
    if options.import_nav_plane and nav_grid is not None:
        nav_obj = create_nav_overlay(nav_collection, path.stem, terrain, nav_grid)
    if options.import_objects:
        create_object_bounds(object_collection, entities)
    return MapImportResult(
        map_name=path.stem,
        collection_name=map_collection.name,
        terrain_object_name=terrain_obj.name if terrain_obj is not None else None,
        marker_count=marker_count,
        nav_object_name=nav_obj.name if nav_obj is not None else None,
        object_count=len(object_collection.objects),
    )


__all__ = [
    "MapImportOptions",
    "MapImportResult",
    "import_scenario_map",
]