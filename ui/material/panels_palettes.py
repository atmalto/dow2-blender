from bpy.types import Panel


class DOW2_PT_material_palettes(Panel):
    """Global DoW2 team palette controls shared by all materials."""

    bl_label = "Team Palettes"
    bl_idname = "DOW2_PT_material_palettes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_parent_id = "DOW2_PT_material_panel"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def draw(self, context):
        layout = self.layout
        palette_settings = context.scene.dow2_global_palettes

        col = layout.column(align=True)
        col.prop(palette_settings, 'palette1')
        col.prop(palette_settings, 'palette2')
        col.prop(palette_settings, 'palette3')
        col.prop(palette_settings, 'palette4')


__all__ = ["DOW2_PT_material_palettes"]