from bpy.types import Panel


class DOW2_PT_material_panel(Panel):
    """DoW2 Material Editor - Main Panel"""

    bl_label = "Relic Material"
    bl_idname = "DOW2_PT_material_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_parent_id = "DOW2_PT_model_panel"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj.type == 'MESH':
            row = layout.row()
            row.template_list(
                "MATERIAL_UL_matslots",
                "",
                obj,
                "material_slots",
                obj,
                "active_material_index",
                rows=2,
            )
            col = row.column(align=True)
            col.operator("object.material_slot_add", icon='ADD', text="")
            col.operator("object.material_slot_remove", icon='REMOVE', text="")

        mat = obj.active_material if obj else None

        if not mat:
            layout.operator("dow2.create_relic_material", icon="ADD")
            return

        layout.prop(mat, "name", text="Name")

        box = layout.box()
        row = box.row()
        row.label(text="Shader:", icon="SHADING_RENDERED")
        shader = mat.get("dow2_shader", "None")
        row.label(text=shader if shader else "None")
        box.operator("dow2.load_shader", text="Load Shader...", icon="FILE_FOLDER")


__all__ = ["DOW2_PT_material_panel"]