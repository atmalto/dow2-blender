from __future__ import annotations

from pathlib import Path
import importlib
import struct
import sys
import zlib

from .types import EntityData, TerrainData


_WORKING_MAPS_READY = False


def _ensure_working_maps_modules():
    global _WORKING_MAPS_READY
    if _WORKING_MAPS_READY:
        return
    working_maps = Path(__file__).resolve().parents[1] / "working" / "maps"
    working_maps_str = str(working_maps)
    if working_maps_str not in sys.path:
        sys.path.insert(0, working_maps_str)
    _WORKING_MAPS_READY = True


def _import_working_maps_module(name: str):
    _ensure_working_maps_modules()
    return importlib.import_module(name)


def _parse_height_values(folder, data: bytes):
    chunky = _import_working_maps_module("chunky")
    head = chunky.find_child_chunk(folder, "HEAD")
    vals = chunky.find_child_chunk(folder, "VALS")
    head_payload = chunky.chunk_payload(data, head)
    width, height, _ = struct.unpack_from("<III", head_payload, 0)
    decoded = zlib.decompress(chunky.chunk_payload(data, vals))
    values = list(struct.unpack("<" + "f" * (width * height), decoded))
    return width, height, values


def parse_terrain(terrain_root, data: bytes) -> TerrainData:
    chunky = _import_working_maps_module("chunky")
    hman = chunky.find_child_chunk(terrain_root, "HMAN")
    hite = chunky.find_child_chunk(hman, "HITE")
    hval = chunky.find_child_chunk(hite, "HVAL")
    width, height, heights = _parse_height_values(hval, data)

    ttex = chunky.find_child_chunk(terrain_root, "TTEX")
    ttex_data = chunky.find_child_chunk(ttex, "DATA")
    tile_world_scale = 8.0
    if ttex_data is not None:
        cursor = chunky.ByteCursor(chunky.chunk_payload(data, ttex_data))
        cursor.read_u32()
        cursor.read_u32()
        cursor.read_f32()
        cursor.read_u32()
        cursor.read_u32()
        parsed_tile_world_scale = cursor.read_f32()
        if parsed_tile_world_scale > 0.0:
            tile_world_scale = parsed_tile_world_scale

    layer_paths: list[tuple[str, str]] = []
    mask_payloads: list[tuple[str, int, int, bytes]] = []
    layer_usage_map: tuple[int, int, bytes] | None = None
    comp = chunky.find_child_chunk(ttex, "COMP")
    rcti = chunky.find_child_chunk(comp, "RCTI") if comp is not None else None
    if rcti is not None:
        layr = chunky.find_child_chunk(rcti, "LAYR")
        if layr is not None:
            cursor_cls = chunky.ByteCursor
            for index, child in enumerate(layr.children):
                payload = chunky.chunk_payload(data, child)
                cursor = cursor_cls(payload)
                strings: list[str] = []
                while cursor._offset < len(payload):
                    strings.append(cursor.read_string())
                if len(strings) >= 2:
                    layer_paths.append((strings[0], strings[1]))
                elif len(strings) == 1:
                    layer_paths.append((strings[0], strings[0]))
                else:
                    layer_paths.append((f"layer_{index}", f"layer_{index}"))
        mask = chunky.find_child_chunk(rcti, "MASK")
        if mask is not None:
            for mask_index, image in enumerate(mask.children):
                attr = chunky.find_child_chunk(image, "ATTR")
                image_data = chunky.find_child_chunk(image, "DATA")
                if attr is None or image_data is None:
                    continue
                attr_payload = chunky.chunk_payload(data, attr)
                attr_words = [int.from_bytes(attr_payload[i : i + 4], "little") for i in range(0, len(attr_payload), 4)]
                if len(attr_words) < 3:
                    continue
                width_px = attr_words[1]
                height_px = attr_words[2]
                mask_payloads.append(
                    (
                        f"DoW2_TerrainMask_{mask_index}",
                        width_px,
                        height_px,
                        chunky.chunk_payload(data, image_data),
                    )
                )
        usag = chunky.find_child_chunk(rcti, "USAG")
        if usag is not None:
            usage_payload = chunky.chunk_payload(data, usag)
            if len(usage_payload) >= 8:
                usage_width, usage_height = struct.unpack_from("<II", usage_payload, 0)
                usage_values = usage_payload[8 : 8 + (usage_width * usage_height)]
                if len(usage_values) == usage_width * usage_height:
                    layer_usage_map = (usage_width, usage_height, usage_values)

    return TerrainData(
        width=width,
        height=height,
        heights=heights,
        min_height=min(heights) if heights else 0.0,
        max_height=max(heights) if heights else 0.0,
        tile_world_scale=tile_world_scale,
        layer_paths=layer_paths,
        mask_payloads=mask_payloads,
        layer_usage_map=layer_usage_map,
    )


def parse_entities(smeg_root, data: bytes) -> list[EntityData]:
    chunky = _import_working_maps_module("chunky")
    ebpt = chunky.find_child_chunk(smeg_root, "EBPT")
    entl = chunky.find_child_chunk(smeg_root, "ENTL")
    blueprints: list[str] = []
    if ebpt is not None:
        cursor = chunky.ByteCursor(chunky.chunk_payload(data, ebpt))
        count = cursor.read_u32()
        blueprints = [cursor.read_string() for _ in range(count)]
    entities: list[EntityData] = []
    if entl is None:
        return entities
    for folder in entl.children:
        if folder.chunk_type != "ENTY":
            continue
        enti = chunky.find_child_chunk(folder, "ENTI")
        if enti is None:
            continue
        cursor = chunky.ByteCursor(chunky.chunk_payload(data, enti))
        cursor.read_u32()
        blueprint_index = cursor.read_i32()
        rows = [cursor.read_vec3() for _ in range(4)]
        blueprint_name = blueprints[blueprint_index] if 0 <= blueprint_index < len(blueprints) else f"entity_{len(entities)}"
        entities.append(EntityData(blueprint_name=blueprint_name, matrix_rows=rows))
    return entities


def parse_nav_grid(smeg_root, data: bytes):
    chunky = _import_working_maps_module("chunky")
    wrld = chunky.find_child_chunk(smeg_root, "WRLD")
    wldi = chunky.find_child_chunk(wrld, "WLDI") if wrld is not None else None
    pfdr = chunky.find_child_chunk(wldi, "PFDR") if wldi is not None else None
    prmp = chunky.find_child_chunk(pfdr, "PRMP") if pfdr is not None else None
    if prmp is None:
        return None
    payload = chunky.chunk_payload(data, prmp)
    width, height, layer_count = struct.unpack_from("<III", payload, 0)
    layer_size = width * height
    if layer_count < 1 or len(payload) < 12 + layer_size:
        return None
    return {
        "width": width,
        "height": height,
        "values": payload[12 : 12 + layer_size],
    }


def load_bundle_data(scenario_path: Path):
    chunky = _import_working_maps_module("chunky")
    data, roots = chunky.parse_chunky_file(scenario_path)
    scen = chunky.find_first_chunk(roots, "SCEN")
    gewd = chunky.find_child_chunk(scen, "GEWD")
    terr = chunky.find_child_chunk(gewd, "TERR")
    smeg = chunky.find_child_chunk(gewd, "SMEG")
    return data, terr, smeg


def resolve_data_root(scenario_path: Path) -> Path:
    for parent in scenario_path.parents:
        if parent.name.lower() == "data":
            return parent
    return scenario_path.parent


__all__ = [
    "load_bundle_data",
    "parse_entities",
    "parse_nav_grid",
    "parse_terrain",
    "resolve_data_root",
]