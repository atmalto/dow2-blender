import csv
import os

import bpy


CSV_HEADER = ("bone_name", "rig", "track")


def _unique_names(names):
    seen = set()
    unique = []
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        unique.append(name)
    return unique


def get_armature_bones_in_export_order(armature_obj):
    """Return armature bones in canonical export order."""
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        return []

    ordered_bones = []

    def visit_bone(bone):
        ordered_bones.append(bone)
        for child in sorted(bone.children, key=lambda child: child.name.lower()):
            visit_bone(child)

    root_bones = sorted(
        (bone for bone in armature_obj.data.bones if bone.parent is None),
        key=lambda bone: bone.name.lower(),
    )
    for root_bone in root_bones:
        visit_bone(root_bone)

    return ordered_bones


def get_armature_bone_names(armature_obj):
    """Return armature bone names in canonical export order."""
    return [bone.name for bone in get_armature_bones_in_export_order(armature_obj)]


def get_action_track_bone_names(action):
    """Return bones that have keyed pose channels in an action."""
    if action is None:
        return []

    track_names = []
    for fcurve in action.fcurves:
        data_path = fcurve.data_path or ""
        if not data_path.startswith('pose.bones["'):
            continue
        parts = data_path.split('"')
        if len(parts) > 1:
            track_names.append(parts[1])
    return _unique_names(track_names)


def find_scene_armature(scene: bpy.types.Scene):
    """Return the first armature found in the scene."""
    if scene is None:
        return None

    for obj in scene.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def find_context_armature(context):
    """Prefer selected or active armatures, then fall back to the scene armature."""
    if context is None:
        return None

    for obj in context.selected_objects:
        if obj.type == 'ARMATURE':
            return obj

    active_object = context.active_object
    if active_object and active_object.type == 'ARMATURE':
        return active_object

    return find_scene_armature(context.scene)


def build_rig_track_rows(bone_names, track_names):
    """Build rig/track CSV rows using a master bone list and keyed track names."""
    track_name_set = {name.lower() for name in _unique_names(track_names)}
    rows = []
    for bone_name in _unique_names(bone_names):
        rows.append({
            "bone_name": bone_name,
            "rig": True,
            "track": bone_name.lower() in track_name_set,
        })
    return rows


def write_rig_track_csv(csv_path: str, rows):
    """Write rig/track rows to a CSV file."""
    if not csv_path:
        return ""

    with open(csv_path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow([row["bone_name"], int(row["rig"]), int(row["track"])])
    return csv_path


def _populate_scene_rig_track_items(scene: bpy.types.Scene, rows):
    scene.dow2_rig_track_items.clear()
    for row in rows:
        item = scene.dow2_rig_track_items.add()
        item.bone_name = row["bone_name"]
        item.rig_enabled = bool(row["rig"])
        item.track_enabled = bool(row["track"])


def get_scene_export_name_sets(scene: bpy.types.Scene, context=None, armature_obj=None):
    """Derive rig and track selections directly from the current scene state."""
    if armature_obj is None:
        if context is not None:
            armature_obj = find_context_armature(context)
        else:
            armature_obj = find_scene_armature(scene)

    if armature_obj is None:
        return None, None, "No armature found in the scene"

    action = None
    if armature_obj.animation_data:
        action = armature_obj.animation_data.action
    if action is None:
        return None, None, f"Armature '{armature_obj.name}' has no active action"

    rig_names = get_armature_bone_names(armature_obj)
    track_names = get_action_track_bone_names(action)
    return rig_names, track_names, ""


def build_scene_rig_track_rows(scene: bpy.types.Scene, context=None, bone_names=None):
    """Build rig/track rows for a scene, optionally using a provided master bone list."""
    rig_names, track_names, error_message = get_scene_export_name_sets(scene, context=context)
    if rig_names is None or track_names is None:
        return None, error_message

    row_bone_names = bone_names if bone_names is not None else rig_names
    return build_rig_track_rows(row_bone_names, track_names), ""


def generate_scene_rig_track_settings(scene: bpy.types.Scene, context=None):
    """Generate and save a scene CSV based on current bones and keyed tracks."""
    if not bpy.data.filepath:
        return "", "Save the .blend file first to generate rig/track settings"

    rows, error_message = build_scene_rig_track_rows(scene, context=context)
    if rows is None:
        return "", error_message

    csv_path = write_rig_track_csv(get_scene_csv_path(), rows)
    _populate_scene_rig_track_items(scene, rows)
    scene.dow2_rig_track_loaded_csv_path = csv_path
    return csv_path, ""


def get_scene_csv_path() -> str:
    """Return the CSV path matching the current blend file name."""
    blend_path = bpy.data.filepath
    if not blend_path:
        return ""

    blend_dir = os.path.dirname(blend_path)
    blend_name = os.path.splitext(os.path.basename(blend_path))[0]
    candidate_paths = [os.path.join(blend_dir, f"{blend_name}.csv")]

    active_action_name = ""
    scene = bpy.context.scene if bpy.context else None
    if scene is not None:
        for obj in scene.objects:
            if obj.type != 'ARMATURE':
                continue
            if obj.animation_data and obj.animation_data.action:
                active_action_name = obj.animation_data.action.name
                break

    if active_action_name and active_action_name != blend_name:
        candidate_paths.append(os.path.join(blend_dir, f"{active_action_name}.csv"))

    for candidate_path in candidate_paths:
        if os.path.exists(candidate_path):
            return candidate_path

    return candidate_paths[0]


def get_scene_name() -> str:
    """Return the current blend file name without extension."""
    blend_path = bpy.data.filepath
    if not blend_path:
        return ""
    return os.path.splitext(os.path.basename(blend_path))[0]


def _parse_flag(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_csv_path_for_blend(blend_path: str) -> str:
    """Return the CSV path matching a .blend file name."""
    if not blend_path:
        return ""
    blend_dir = os.path.dirname(blend_path)
    blend_name = os.path.splitext(os.path.basename(blend_path))[0]
    return os.path.join(blend_dir, f"{blend_name}.csv")


def parse_bone_name_file(file_path: str):
    """Parse comma- or newline-separated bone names from a text file."""
    if not file_path or not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as handle:
        content = handle.read()

    tokens = []
    for raw_part in content.replace('\r', '\n').replace(',', '\n').split('\n'):
        bone_name = raw_part.strip()
        if bone_name:
            tokens.append(bone_name)
    return _unique_names(tokens)


def parse_rig_track_csv(csv_path: str):
    """Parse rig and track bone selections from a CSV file."""
    if not csv_path or not os.path.exists(csv_path):
        return None, None

    rig_names = []
    track_names = []
    with open(csv_path, newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            bone_name = (row.get("bone_name") or "").strip()
            if not bone_name:
                continue
            if _parse_flag(row.get("rig", "1")):
                rig_names.append(bone_name)
            if _parse_flag(row.get("track", "1")):
                track_names.append(bone_name)

    return _unique_names(rig_names), _unique_names(track_names)


def resolve_bone_names_for_armature(armature_obj, selected_names):
    """Resolve selected bone names to exact armature bone names, case-insensitively."""
    if selected_names is None:
        return None, []

    armature_names = {bone.name.lower(): bone.name for bone in armature_obj.data.bones}
    resolved = []
    missing = []
    for name in selected_names:
        exact_name = armature_names.get(name.lower())
        if exact_name is None:
            missing.append(name)
            continue
        resolved.append(exact_name)

    return _unique_names(resolved), _unique_names(missing)


def load_scene_rig_track_settings(scene: bpy.types.Scene) -> bool:
    """Load per-bone rig/track settings from the current scene CSV."""
    csv_path = get_scene_csv_path()
    scene.dow2_rig_track_items.clear()
    scene.dow2_rig_track_loaded_csv_path = csv_path

    if not csv_path or not os.path.exists(csv_path):
        return False

    with open(csv_path, newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            bone_name = (row.get("bone_name") or "").strip()
            if not bone_name:
                continue

            rows.append({
                "bone_name": bone_name,
                "rig": _parse_flag(row.get("rig", "1")),
                "track": _parse_flag(row.get("track", "1")),
            })

    _populate_scene_rig_track_items(scene, rows)

    return True


def save_scene_rig_track_settings(scene: bpy.types.Scene) -> str:
    """Save the current rig/track UI state back to the scene CSV."""
    csv_path = get_scene_csv_path()
    if not csv_path:
        return ""

    rows = []
    for item in scene.dow2_rig_track_items:
        rows.append({
            "bone_name": item.bone_name,
            "rig": item.rig_enabled,
            "track": item.track_enabled,
        })
    write_rig_track_csv(csv_path, rows)

    scene.dow2_rig_track_loaded_csv_path = csv_path
    return csv_path


def reset_scene_rig_track_settings(scene: bpy.types.Scene):
    """Reset all rig/track settings to enabled without saving."""
    set_scene_rig_track_flags(scene, rig_enabled=True, track_enabled=True)


def set_scene_rig_track_flags(scene: bpy.types.Scene, rig_enabled=None, track_enabled=None):
    """Update rig/track flags in the UI without saving."""
    for item in scene.dow2_rig_track_items:
        if rig_enabled is not None:
            item.rig_enabled = bool(rig_enabled)
        if track_enabled is not None:
            item.track_enabled = bool(track_enabled)


def sync_scene_rig_track_settings(scene: bpy.types.Scene):
    """Reload settings when the active blend file changes."""
    csv_path = get_scene_csv_path()
    if scene.dow2_rig_track_loaded_csv_path != csv_path:
        load_scene_rig_track_settings(scene)