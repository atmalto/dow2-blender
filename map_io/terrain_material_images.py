from __future__ import annotations

from pathlib import Path

import bpy

from .terrain_material_types import TerrainTextureSet


MAX_TERRAIN_IMAGE_SAMPLERS = 28


def ensure_image_from_rgba(name: str, width: int, height: int, rgba_bytes: bytes) -> bpy.types.Image:
    image = bpy.data.images.get(name)
    if image is None:
        image = bpy.data.images.new(name, width=width, height=height, alpha=True)
    else:
        image.scale(width, height)
    image.colorspace_settings.name = "Non-Color"
    image.alpha_mode = 'CHANNEL_PACKED'
    pixels = [component / 255.0 for component in rgba_bytes]
    image.pixels.foreach_set(pixels)
    image.pack()
    return image


def load_tile_image(tile_root: Path, texture_path: str, suffix: str) -> bpy.types.Image | None:
    file_path = tile_root / f"{texture_path}_{suffix}.dds"
    if not file_path.exists():
        return None
    existing = bpy.data.images.get(file_path.name)
    if existing is not None:
        return existing
    image = bpy.data.images.load(str(file_path), check_existing=True)
    image.colorspace_settings.name = "Non-Color" if suffix != "dif" else "sRGB"
    return image


def build_usage_mask_payloads(
    mask_payloads: list[tuple[str, int, int, bytes]],
    layer_usage_map: tuple[int, int, bytes] | None,
) -> list[tuple[str, int, int, bytes]]:
    if layer_usage_map is None or not mask_payloads:
        return []
    usage_width, usage_height, usage_values = layer_usage_map
    if usage_width <= 0 or usage_height <= 0 or len(usage_values) != usage_width * usage_height:
        return []
    mask_width = mask_payloads[0][1]
    mask_height = mask_payloads[0][2]
    image_payloads = [bytearray(mask_width * mask_height * 4) for _ in range(2)]

    for y in range(mask_height):
        usage_y = min(usage_height - 1, (y * usage_height) // max(1, mask_height))
        for x in range(mask_width):
            usage_x = min(usage_width - 1, (x * usage_width) // max(1, mask_width))
            active_mask = usage_values[(usage_y * usage_width) + usage_x]
            pixel_offset = ((y * mask_width) + x) * 4
            for layer_index in range(8):
                if not (active_mask & (1 << layer_index)):
                    continue
                image_index = layer_index // 4
                channel_index = layer_index % 4
                image_payloads[image_index][pixel_offset + channel_index] = 255

    return [
        (
            f"DoW2_TerrainUsageMask_{mask_index}",
            mask_width,
            mask_height,
            bytes(payload),
        )
        for mask_index, payload in enumerate(image_payloads)
    ]


def build_texture_sets(
    *,
    tile_root: Path,
    layer_paths: list[tuple[str, str]],
    initial_sampler_count: int,
) -> tuple[list[TerrainTextureSet], int, int]:
    texture_sets: list[TerrainTextureSet] = []
    sampler_count = initial_sampler_count
    max_candidate_layers = min(len(layer_paths), 8)

    for layer_index, pair in enumerate(layer_paths[:max_candidate_layers]):
        surface_path = pair[0] or pair[1]
        cliff_path = pair[1] or pair[0]
        if not surface_path:
            continue

        surface_diffuse = load_tile_image(tile_root, surface_path, "dif")
        cliff_diffuse = load_tile_image(tile_root, cliff_path, "dif")
        surface_normal = None
        cliff_normal = None
        surface_spec = None
        cliff_spec = None
        layer_sampler_count = sum(
            image is not None
            for image in (
                surface_diffuse,
                cliff_diffuse,
            )
        )
        if layer_sampler_count == 0:
            continue
        if texture_sets and sampler_count + layer_sampler_count > MAX_TERRAIN_IMAGE_SAMPLERS:
            break

        texture_sets.append(
            TerrainTextureSet(
                layer_index=layer_index,
                surface_path=surface_path,
                cliff_path=cliff_path,
                surface_diffuse=surface_diffuse,
                cliff_diffuse=cliff_diffuse,
                surface_normal=surface_normal,
                cliff_normal=cliff_normal,
                surface_spec=surface_spec,
                cliff_spec=cliff_spec,
            )
        )
        sampler_count += layer_sampler_count

    for texture_set in texture_sets:
        if sampler_count >= MAX_TERRAIN_IMAGE_SAMPLERS:
            break
        surface_spec = load_tile_image(tile_root, texture_set.surface_path, "spc")
        if surface_spec is None:
            continue
        texture_set.surface_spec = surface_spec
        sampler_count += 1

    truncated_layer_count = max(0, max_candidate_layers - len(texture_sets))
    return texture_sets, sampler_count, truncated_layer_count


__all__ = [
    "MAX_TERRAIN_IMAGE_SAMPLERS",
    "build_usage_mask_payloads",
    "build_texture_sets",
    "ensure_image_from_rgba",
    "load_tile_image",
]