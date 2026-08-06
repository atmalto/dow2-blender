from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MapImportOptions:
    import_mesh: bool = True
    import_markers: bool = True
    import_nav_plane: bool = True
    import_textures: bool = True
    import_objects: bool = True


@dataclass(slots=True)
class TerrainData:
    width: int
    height: int
    heights: list[float]
    min_height: float
    max_height: float
    tile_world_scale: float
    layer_paths: list[tuple[str, str]]
    mask_payloads: list[tuple[str, int, int, bytes]]
    layer_usage_map: tuple[int, int, bytes] | None = None


@dataclass(slots=True)
class EntityData:
    blueprint_name: str
    matrix_rows: list[tuple[float, float, float]]


@dataclass(slots=True)
class MapImportResult:
    map_name: str
    collection_name: str
    terrain_object_name: str | None
    marker_count: int
    nav_object_name: str | None
    object_count: int


__all__ = [
    "EntityData",
    "MapImportOptions",
    "MapImportResult",
    "TerrainData",
]