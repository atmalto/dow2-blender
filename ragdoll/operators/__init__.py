from __future__ import annotations

import bpy
from .authoring import (
    DOW2_OT_import_ragdoll_hkx,
    DOW2_OT_pick_ragdoll_import_path,
    DOW2_OT_pick_ragdoll_model_path,
    DOW2_OT_create_ragdoll_bodies,
    DOW2_OT_create_ragdoll_skeleton,
    DOW2_OT_export_ragdoll_hkx,
    DOW2_OT_set_active_ragdoll_body_shape,
    DOW2_OT_set_active_ragdoll_constraint_type,
)
from .shortcuts import DOW2_OT_adjust_active_ragdoll_body_dimension, register_keymaps as _register_keymaps, unregister_keymaps as _unregister_keymaps
from .templates import DOW2_OT_apply_ragdoll_template_category


classes = [
    DOW2_OT_pick_ragdoll_import_path,
    DOW2_OT_pick_ragdoll_model_path,
    DOW2_OT_import_ragdoll_hkx,
    DOW2_OT_create_ragdoll_skeleton,
    DOW2_OT_create_ragdoll_bodies,
    DOW2_OT_apply_ragdoll_template_category,
    DOW2_OT_set_active_ragdoll_body_shape,
    DOW2_OT_set_active_ragdoll_constraint_type,
    DOW2_OT_adjust_active_ragdoll_body_dimension,
    DOW2_OT_export_ragdoll_hkx,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    _register_keymaps()


def unregister():
    _unregister_keymaps()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)