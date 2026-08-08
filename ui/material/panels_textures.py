from bpy.types import Panel

from ...material.badges import is_badge_material as is_badge_preview_material
from ...material.definitions import TEXTURE_SLOTS
from ...material.schema import is_texture_variable, shader_schema_for_material
from ...material.service import resolve_dow2_data_path


class DOW2_PT_material_textures(Panel):
    """DoW2 Material Textures Sub-Panel"""

    bl_label = "Textures"
    bl_idname = "DOW2_PT_material_textures"
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
        schema_textures = {var.name for var in schema.variables if is_texture_variable(var)}

        for slot_name, label in TEXTURE_SLOTS:
            enabled = not schema.variables or slot_name in schema_textures

            box = layout.box()
            box.enabled = enabled

            row = box.row()
            row.label(text=label)

            tex_value = mat.get(f"dow2_{slot_name}", "")
            if tex_value:
                row = box.row()
                display_path = tex_value if len(tex_value) <= 35 else "..." + tex_value[-32:]
                row.label(text=display_path)

                row = box.row()
                op = row.operator("dow2.set_texture", text="Change", icon="FILE_IMAGE")
                op.texture_slot = slot_name
                if slot_name in {"badge1Tex", "badge2Tex"} and is_badge_preview_material(mat):
                    edit_op = row.operator("dow2.edit_badge_decal", text="Edit", icon="UV")
                    edit_op.material_name = mat.name
                    edit_op.badge_slot = "badge1" if slot_name == "badge1Tex" else "badge2"
                op = row.operator("dow2.clear_texture", text="Clear", icon="X")
                op.texture_slot = slot_name
            else:
                op = box.operator("dow2.set_texture", text="Set Texture", icon="FILE_IMAGE")
                op.texture_slot = slot_name


__all__ = ["DOW2_PT_material_textures"]