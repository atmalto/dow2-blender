import os
from typing import TYPE_CHECKING, List

import bpy

from . import utils as model_utils

if TYPE_CHECKING:
    from .exporter import DoW2ModelExporter


def export_bounding_box(exporter: "DoW2ModelExporter", box_type: str):
    """Export SIMBOX or COVERBOX dummy as .lua file."""
    scene = bpy.context.scene
    armature_obj = model_utils._primary_armature(scene)
    model_name = model_utils._resolve_model_name(scene, armature_obj) or os.path.splitext(os.path.basename(exporter.filepath))[0]
    obj = model_utils.find_bounding_box_object(scene, box_type, model_name)

    if obj is None:
        minimum, maximum = model_utils.mesh_bounds_local(scene, armature_obj)
        center = (minimum + maximum) * 0.5
        extents = (maximum - minimum) * 0.5
        extents.x = max(extents.x, 1e-4)
        extents.y = max(extents.y, 1e-4)
        extents.z = max(extents.z, 1e-4)
        loc = center
        scale = extents
        maintain_contour = True
    else:
        loc = obj.location.copy()
        scale = obj.scale.copy()
        maintain_contour = obj.get("maintain_contour", True)

    model_name = os.path.splitext(os.path.basename(exporter.filepath))[0]
    lua_path = os.path.join(exporter.data_path, f"{model_name}.{box_type}")

    print(f"Exporting {box_type}...")

    offset_x = -loc.x
    offset_y = loc.z
    offset_z = -loc.y

    scale_x = scale.x if abs(scale.x) > 0.001 else 1.0
    scale_y = scale.z if abs(scale.z) > 0.001 else 1.0
    scale_z = scale.y if abs(scale.y) > 0.001 else 1.0

    maintain_str = "true" if maintain_contour else "false"

    archive_path = exporter._get_archive_path()
    if exporter.data_path.startswith(archive_path):
        relative_path = os.path.relpath(lua_path, archive_path).replace("\\", "/")
    else:
        relative_path = f"{model_name}.{box_type}"

    with open(lua_path, "w", encoding="utf-8") as file:
        file.write(f"{box_type} =\n")
        file.write("{\n")
        file.write(f"    maintain_contour = {maintain_str},\n")
        file.write("    offset =\n")
        file.write("    {\n")
        file.write(f"\tx = {offset_x:.6g},\n")
        file.write(f"\ty = {offset_y:.6g},\n")
        file.write(f"\tz = {offset_z:.6g},\n")
        file.write("    },\n")
        file.write("    scale =\n")
        file.write("    {\n")
        file.write(f"\tx = {scale_x:.6g},\n")
        file.write(f"\ty = {scale_y:.6g},\n")
        file.write(f"\tz = {scale_z:.6g},\n")
        file.write("    },\n")
        file.write("}\n")
        file.write(f"{box_type}_states=" + "{}")

    print(f"  Exported {box_type} to: {lua_path}")


def get_archive_path(exporter: "DoW2ModelExporter") -> str:
    """Get the base archive path for relative texture paths."""
    path = exporter.data_path
    while path:
        if os.path.basename(path).lower() == "data":
            return path
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return exporter.data_path


def export_model_states(exporter: "DoW2ModelExporter", mesh_groups: List[str]):
    """Export model states matching MaxScript ExportModelStates."""
    damage_state_map = {
        "healthy": exporter.options.damage_state_healthy,
        "light_damage": exporter.options.damage_state_light_damage,
        "heavy_damage": exporter.options.damage_state_heavy_damage,
        "wreck": exporter.options.damage_state_wreck,
    }

    model_states = {}
    for damage_state, mesh_group_name in damage_state_map.items():
        if mesh_group_name not in model_states:
            actual_group = mesh_group_name if mesh_group_name in mesh_groups else None
            model_states[mesh_group_name] = {
                "mesh_group": actual_group,
                "conditions": [],
            }
        model_states[mesh_group_name]["conditions"].append(damage_state)

    msbp_header_pos = exporter.writer.file.tell()
    msbp_data_pos = exporter.writer.write_chunk_header("FOLD", "MSBP", 1, 0, None, 0)

    exporter.writer.write_chunk_header("DATA", "MSD ", 1, 4, None, -1)
    exporter.writer.write_long(len(model_states))

    for state_name, state_data in model_states.items():
        mesh_group = state_data["mesh_group"]
        conditions = state_data["conditions"]

        msd_size = 4 + len(state_name) + 4
        if mesh_group:
            msd_size += 4 + len(mesh_group)

        exporter.writer.write_chunk_header("DATA", "MSD ", 2, msd_size, None, 1)

        exporter.writer.write_long(len(state_name))
        exporter.writer.write_str(state_name)

        if mesh_group:
            exporter.writer.write_long(1)
            exporter.writer.write_long(len(mesh_group))
            exporter.writer.write_str(mesh_group)
        else:
            exporter.writer.write_long(0)

        cnbp_header_pos = exporter.writer.file.tell()
        cnbp_data_pos = exporter.writer.write_chunk_header("DATA", "CNBP", 3, 0, None, 2)

        if len(model_states) == 1:
            exporter.writer.write_long(0)
        else:
            exporter.writer.write_long(len(conditions))

            for condition in conditions:
                exporter.writer.write_long(2)
                exporter.writer.write_byte(0)

                var_name = "damage_state"
                exporter.writer.write_long(len(var_name))
                exporter.writer.write_str(var_name)

                exporter.writer.write_long(len(condition))
                exporter.writer.write_str(condition)

            for _ in range(len(conditions)):
                if len(conditions) > 1:
                    exporter.writer.write_long(1)
                else:
                    exporter.writer.write_long(0)

        exporter.writer.update_chunk_size(cnbp_header_pos, cnbp_data_pos)

    exporter.writer.update_chunk_size(msbp_header_pos, msbp_data_pos)


def export_data_templates(exporter: "DoW2ModelExporter"):
    """Export data templates matching MaxScript ExportDataTemplates."""
    dtbp_header_pos = exporter.writer.file.tell()
    dtbp_data_pos = exporter.writer.write_chunk_header("DATA", "DTBP", 3, 0, None, 2)

    exporter.writer.write_long(0)

    if exporter.options.export_damage_state_var:
        states = ["healthy", "light_damage", "heavy_damage", "wreck"]
        exporter.writer.write_long(1)

        exporter.writer.write_long(len("damage_state"))
        exporter.writer.write_str("damage_state")

        exporter.writer.write_long(len(states))
        for state in states:
            exporter.writer.write_long(len(state))
            exporter.writer.write_str(state)

        exporter.writer.write_long(len(states[0]))
        exporter.writer.write_str(states[0])
    else:
        exporter.writer.write_long(0)

    if exporter.options.export_health_var:
        exporter.writer.write_long(1)
        exporter.writer.write_long(len("health"))
        exporter.writer.write_str("health")
        exporter.writer.write_float(1.0)
        exporter.writer.write_float(0.0)
        exporter.writer.write_float(1.0)
        exporter.writer.write_byte(0)
    else:
        exporter.writer.write_long(0)

    exporter.writer.update_chunk_size(dtbp_header_pos, dtbp_data_pos)


__all__ = [
    "export_bounding_box",
    "export_data_templates",
    "export_model_states",
    "get_archive_path",
]