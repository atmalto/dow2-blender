from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, List

import bpy
from mathutils import Vector

from ..chunk_lib import RelicChunk, get_chunk
from . import utils as model_utils

if TYPE_CHECKING:
    from .importer import DoW2ModelImporter


def import_bounding_box(importer: DoW2ModelImporter, box_type: str):
    """Import simbox or coverbox from a sidecar lua file."""

    lua_path = os.path.join(importer.data_path, f"{importer.model_name}.{box_type}")
    if not os.path.exists(lua_path):
        print(f"No {box_type} found at: {lua_path}")
        return

    print(f"Importing {box_type}...")

    try:
        with open(lua_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        maintain_contour = True
        offset = Vector((0, 0, 0))
        scale = Vector((1, 1, 1))
        lower_content = content.lower()

        if "maintain_contour = true" in lower_content:
            maintain_contour = True
        elif "maintain_contour = false" in lower_content:
            maintain_contour = False

        offset_match = re.search(r"offset\s*=\s*\{([^}]+)\}", content, re.DOTALL)
        if offset_match:
            _fill_vector_from_lua_block(offset, offset_match.group(1))

        scale_match = re.search(r"scale\s*=\s*\{([^}]+)\}", content, re.DOTALL)
        if scale_match:
            _fill_vector_from_lua_block(scale, scale_match.group(1))

        print(f"    Parsed: offset={offset}, scale={scale}")

        bl_offset = Vector((-offset.x, -offset.z, offset.y))
        bl_scale = Vector((scale.x, scale.z, scale.y))

        model_utils.create_or_update_bounding_box_object(
            bpy.context.scene,
            box_type,
            model_name=importer.model_name,
            location=bl_offset,
            scale=bl_scale,
            maintain_contour=maintain_contour,
            armature_obj=importer.armature,
            source_path=lua_path,
        )
        print(f"  Imported {box_type}")

    except Exception as exc:
        print(f"Failed to import {box_type}: {exc}")


def import_model_states(importer: DoW2ModelImporter, chunks: List[RelicChunk]):
    """Import model states from the MSBP chunk."""

    msbp_chunk = get_chunk("MSBP", chunks)
    if not msbp_chunk:
        print("No model states found")
        return

    print("Importing model states...")
    scene = bpy.context.scene
    if "dow2_damage_states" not in scene:
        scene["dow2_damage_states"] = {}

    damage_states = {
        "healthy": "healthy",
        "light_damage": "light_damage",
        "heavy_damage": "heavy_damage",
        "wreck": "wreck",
    }

    try:
        if not msbp_chunk.children:
            return

        first_msd = msbp_chunk.children[0]
        importer.reader.seek_chunk(first_msd)
        num_states = importer.reader.read_long()
        print(f"  Found {num_states} model states")

        child_idx = 1
        for _ in range(num_states):
            if child_idx >= len(msbp_chunk.children):
                break

            msd_chunk = msbp_chunk.children[child_idx]
            importer.reader.seek_chunk(msd_chunk)

            state_name_len = importer.reader.read_long()
            state_name = importer.reader.read_str(state_name_len) if state_name_len > 0 else ""

            mesh_group_name = None
            has_mesh_group = importer.reader.read_long()
            if has_mesh_group > 0:
                group_name_len = importer.reader.read_long()
                mesh_group_name = importer.reader.read_str(group_name_len) if group_name_len > 0 else None

            child_idx += 1
            if child_idx >= len(msbp_chunk.children):
                break

            cnbp_chunk = msbp_chunk.children[child_idx]
            importer.reader.seek_chunk(cnbp_chunk)
            num_conditions = importer.reader.read_long()

            if num_conditions == 0:
                for damage_state in damage_states:
                    damage_states[damage_state] = state_name
            else:
                for _ in range(num_conditions):
                    cond_type = importer.reader.read_long()
                    importer.reader.read_byte()

                    if cond_type != 5:
                        var_name_len = importer.reader.read_long()
                        if var_name_len > 0:
                            importer.reader.read_str(var_name_len)

                    if cond_type == 2:
                        value_len = importer.reader.read_long()
                        condition_value = importer.reader.read_str(value_len) if value_len > 0 else ""
                        if condition_value in damage_states:
                            damage_states[condition_value] = state_name
                    elif cond_type == 3:
                        importer.reader.read_float()
                        importer.reader.read_long()
                    elif cond_type == 4:
                        importer.reader.read_float()
                        importer.reader.read_float()
                    elif cond_type == 5:
                        importer.reader.read_float()

                for _ in range(num_conditions):
                    importer.reader.read_long()

            child_idx += 1
            print(f"  State '{state_name}' -> mesh group '{mesh_group_name}'")

        scene["dow2_damage_states"] = damage_states
        print(f"  Damage state mapping: {damage_states}")

    except Exception as exc:
        print(f"Error importing model states: {exc}")


def import_data_templates(importer: DoW2ModelImporter, chunks: List[RelicChunk]):
    """Import data templates from the DTBP chunk."""

    dtbp_chunk = get_chunk("DTBP", chunks)
    if not dtbp_chunk:
        print("No data templates found")
        return

    print("Importing data templates...")
    scene = bpy.context.scene

    try:
        importer.reader.seek_chunk(dtbp_chunk)

        num_events = importer.reader.read_long()
        for _ in range(num_events):
            event_len = importer.reader.read_long()
            if event_len > 0:
                importer.reader.read_str(event_len)

        scene["dow2_export_damage_state"] = False
        num_state_machines = importer.reader.read_long()
        for _ in range(num_state_machines):
            name_len = importer.reader.read_long()
            state_machine_name = importer.reader.read_str(name_len) if name_len > 0 else ""

            num_states = importer.reader.read_long()
            for _ in range(num_states):
                state_len = importer.reader.read_long()
                if state_len > 0:
                    importer.reader.read_str(state_len)

            default_len = importer.reader.read_long()
            if default_len > 0:
                importer.reader.read_str(default_len)

            if state_machine_name == "damage_state":
                scene["dow2_export_damage_state"] = True
                print("  Found damage_state state machine")

        scene["dow2_export_health"] = False
        num_vars = importer.reader.read_long()
        for _ in range(num_vars):
            var_len = importer.reader.read_long()
            var_name = importer.reader.read_str(var_len) if var_len > 0 else ""
            importer.reader.read_float()
            importer.reader.read_float()
            importer.reader.read_float()

            if var_name == "health":
                scene["dow2_export_health"] = True
                print("  Found health variable")

        for _ in range(num_vars):
            importer.reader.read_byte()

    except Exception as exc:
        print(f"Error importing data templates: {exc}")


def _fill_vector_from_lua_block(target: Vector, block: str):
    x_match = re.search(r"x\s*=\s*([+-]?[\d.]+)", block)
    y_match = re.search(r"y\s*=\s*([+-]?[\d.]+)", block)
    z_match = re.search(r"z\s*=\s*([+-]?[\d.]+)", block)

    if x_match:
        target.x = float(x_match.group(1))
    if y_match:
        target.y = float(y_match.group(1))
    if z_match:
        target.z = float(z_match.group(1))