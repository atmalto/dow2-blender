from .badge_editor import DOW2_OT_edit_badge_decal
from .material_ops import (
    DOW2_OT_create_relic_material,
    DOW2_OT_load_shader,
    DOW2_OT_toggle_bool_param,
    get_or_create_default_material,
    is_relic_material,
)
from .palette_state import (
    DOW2_GlobalPaletteSettings,
    register_material_panel_state,
    unregister_material_panel_state,
)
from .panels_main import DOW2_PT_material_panel
from .panels_palettes import DOW2_PT_material_palettes
from .panels_params import DOW2_PT_material_params
from .panels_textures import DOW2_PT_material_textures
from .texture_ops import DOW2_OT_clear_texture, DOW2_OT_set_texture


MATERIAL_CLASSES = [
    DOW2_GlobalPaletteSettings,
    DOW2_OT_load_shader,
    DOW2_OT_set_texture,
    DOW2_OT_clear_texture,
    DOW2_OT_edit_badge_decal,
    DOW2_OT_create_relic_material,
    DOW2_OT_toggle_bool_param,
    DOW2_PT_material_panel,
    DOW2_PT_material_palettes,
    DOW2_PT_material_textures,
    DOW2_PT_material_params,
]


__all__ = [
    "MATERIAL_CLASSES",
    "DOW2_GlobalPaletteSettings",
    "DOW2_OT_clear_texture",
    "DOW2_OT_create_relic_material",
    "DOW2_OT_edit_badge_decal",
    "DOW2_OT_load_shader",
    "DOW2_OT_set_texture",
    "DOW2_OT_toggle_bool_param",
    "DOW2_PT_material_panel",
    "DOW2_PT_material_palettes",
    "DOW2_PT_material_params",
    "DOW2_PT_material_textures",
    "get_or_create_default_material",
    "is_relic_material",
    "register_material_panel_state",
    "unregister_material_panel_state",
]