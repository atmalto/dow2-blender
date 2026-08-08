from bpy.types import Panel

from ...material.definitions import VAR_TYPE_BOOL, VAR_TYPE_FLOAT, VAR_TYPE_INT
from ...material.schema import (
    scalar_schema_variables,
    shader_param_label,
    shader_schema_for_material,
)
from ...material.service import resolve_dow2_data_path


class DOW2_PT_material_params(Panel):
    """DoW2 Material Parameters Sub-Panel"""

    bl_label = "Parameters"
    bl_idname = "DOW2_PT_material_params"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_parent_id = "DOW2_PT_material_panel"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.active_material

    def draw(self, context):
        layout = self.layout
        mat = context.object.active_material
        schema = shader_schema_for_material(mat, resolve_dow2_data_path(context, ""))

        if not schema.variables:
            layout.label(text="No shader schema found", icon="ERROR")
            return

        box = layout.box()
        box.label(text="Boolean")
        for var in scalar_schema_variables(schema, VAR_TYPE_BOOL):
            prop_name = f"dow2_{var.name}"
            if prop_name not in mat:
                continue
            row = box.row()
            row.prop(mat, f'["{prop_name}"]', text=shader_param_label(var.name))

        box = layout.box()
        box.label(text="Integer")
        for var in scalar_schema_variables(schema, VAR_TYPE_INT):
            prop_name = f"dow2_{var.name}"
            if prop_name not in mat:
                continue
            row = box.row()
            row.prop(mat, f'["{prop_name}"]', text=shader_param_label(var.name))

        box = layout.box()
        box.label(text="Float")
        for var in scalar_schema_variables(schema, VAR_TYPE_FLOAT):
            prop_name = f"dow2_{var.name}"
            if prop_name not in mat:
                continue
            row = box.row()
            row.prop(mat, f'["{prop_name}"]', text=shader_param_label(var.name))


__all__ = ["DOW2_PT_material_params"]