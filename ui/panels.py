import bpy

from ..collision import utils as collision_utils
from ..model import utils as model_utils
from .animation_panels import (
    ANIMATION_PANEL_CLASSES,
    DOW2_OT_generate_rig_track_settings,
    DOW2_OT_refresh_rig_track_settings,
    DOW2_OT_reset_rig_track_settings,
    DOW2_OT_save_rig_track_settings,
    DOW2_PT_animation_panel,
    DOW2_RigTrackSettingItem,
    register_animation_panel_state,
    unregister_animation_panel_state,
)
from .collision_panels import (
    COLLISION_PANEL_CLASSES,
    DOW2_PT_collision_generation,
    DOW2_PT_collision_panel,
)
from .material.registry import (
    MATERIAL_CLASSES,
    register_material_panel_state,
    unregister_material_panel_state,
)
from .model_panels import (
    MODEL_PANEL_CLASSES,
    DOW2_PT_collection_setup,
    DOW2_PT_header_panel,
    DOW2_PT_model_panel,
    DOW2_PT_object_panel,
)
from ..material.definitions import (
    BOOL_PARAMS,
    DEFAULT_MATERIAL_NAME,
    FLOAT_PARAMS,
    INT_PARAMS,
    TEXTURE_SLOTS,
)
from ..material.presets import (
    SHADER_PRESETS,
    SHADER_PRESET_CONFIG,
    SHADER_PRESET_LABELS,
)
from .physics_panels import (
    PHYSICS_PANEL_CLASSES,
    DOW2_PT_physics_panel,
)
from .ragdoll_panels import (
    RAGDOLL_PANEL_CLASSES,
    DOW2_PT_ragdoll_panel,
)
from .scene_graph_panels import (
    DOW2_OT_clear_scene_graph_scene,
    DOW2_OT_scene_graph_import_map,
    DOW2_OT_scene_graph_pick_map_path,
    DOW2_OT_scene_graph_select_material,
    DOW2_OT_scene_graph_select_object,
    DOW2_PT_scene_graph,
    SCENE_GRAPH_CLASSES,
    register_scene_graph_state,
    unregister_scene_graph_state,
)


classes = [
    *MODEL_PANEL_CLASSES,
    *MATERIAL_CLASSES,
    *ANIMATION_PANEL_CLASSES,
    *PHYSICS_PANEL_CLASSES,
    *RAGDOLL_PANEL_CLASSES,
    *COLLISION_PANEL_CLASSES,
    *SCENE_GRAPH_CLASSES,
]


def register():
    model_utils.register()
    collision_utils.register()
    register_scene_graph_state()
    for cls in classes:
        bpy.utils.register_class(cls)
    register_material_panel_state()
    register_animation_panel_state()


def unregister():
    unregister_animation_panel_state()
    unregister_material_panel_state()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    unregister_scene_graph_state()
    collision_utils.unregister()
    model_utils.unregister()


__all__ = [
    "BOOL_PARAMS",
    "DEFAULT_MATERIAL_NAME",
    "DOW2_OT_clear_scene_graph_scene",
    "DOW2_OT_generate_rig_track_settings",
    "DOW2_OT_refresh_rig_track_settings",
    "DOW2_OT_reset_rig_track_settings",
    "DOW2_OT_save_rig_track_settings",
    "DOW2_OT_scene_graph_import_map",
    "DOW2_OT_scene_graph_pick_map_path",
    "DOW2_OT_scene_graph_select_material",
    "DOW2_OT_scene_graph_select_object",
    "DOW2_PT_animation_panel",
    "DOW2_PT_collection_setup",
    "DOW2_PT_collision_generation",
    "DOW2_PT_collision_panel",
    "DOW2_PT_header_panel",
    "DOW2_PT_model_panel",
    "DOW2_PT_object_panel",
    "DOW2_PT_physics_panel",
    "DOW2_PT_ragdoll_panel",
    "DOW2_PT_scene_graph",
    "DOW2_RigTrackSettingItem",
    "FLOAT_PARAMS",
    "INT_PARAMS",
    "SHADER_PRESETS",
    "SHADER_PRESET_CONFIG",
    "SHADER_PRESET_LABELS",
    "TEXTURE_SLOTS",
    "classes",
    "register",
    "unregister",
]