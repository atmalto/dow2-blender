from bpy.types import Panel

from ...material.definitions import BOOL_PARAMS, FLOAT_PARAMS, INT_PARAMS


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
        shader_vars = mat.get("dow2_shader_vars", "").split(",") if mat.get("dow2_shader_vars") else []

        box = layout.box()
        box.label(text="Boolean", icon="CHECKBOX_HLT")
        for param, label in BOOL_PARAMS:
            enabled = not shader_vars or param in shader_vars or not mat.get("dow2_shader")
            row = box.row()
            row.enabled = enabled

            prop_name = f"dow2_{param}"
            current = mat.get(prop_name, False)
            icon = 'CHECKBOX_HLT' if current else 'CHECKBOX_DEHLT'
            op = row.operator("dow2.toggle_bool_param", text=label, icon=icon, depress=current)
            op.param_name = param

        box = layout.box()
        box.label(text="Integer", icon="LINENUMBERS_ON")
        for param, label in INT_PARAMS:
            enabled = not shader_vars or param in shader_vars or not mat.get("dow2_shader")
            row = box.row()
            row.enabled = enabled
            row.label(text=label)

            prop_name = f"dow2_{param}"
            current = mat.get(prop_name, 0)
            row.label(text=str(current))

        box = layout.box()
        box.label(text="Float", icon="DRIVER_DISTANCE")
        for param, label, default in FLOAT_PARAMS:
            enabled = not shader_vars or param in shader_vars or not mat.get("dow2_shader")
            row = box.row()
            row.enabled = enabled
            row.label(text=label)

            prop_name = f"dow2_{param}"
            current = mat.get(prop_name, default)
            row.label(text=f"{current:.3f}")


__all__ = ["DOW2_PT_material_params"]