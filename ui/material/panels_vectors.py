from bpy.types import Panel


class DOW2_PT_material_vectors(Panel):
    """DoW2 Material Vector Parameters Sub-Panel"""

    bl_label = "Vectors & Colors"
    bl_idname = "DOW2_PT_material_vectors"
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

        box = layout.box()
        box.label(text="Color", icon="COLOR")

        col3 = mat.get("dow2_colour", None)
        if col3:
            row = box.row()
            row.label(text="Colour (RGB)")
            row.label(text=f"({col3[0]:.2f}, {col3[1]:.2f}, {col3[2]:.2f})")

        box = layout.box()
        box.label(text="Vector4", icon="ORIENTATION_GLOBAL")

        vec4_params = [
            "badge1MatrixRow1Row2",
            "badge1Translate",
            "badge2MatrixRow1Row2",
            "badge2Translate",
            "WaterReflection_SurfaceOffset",
        ]

        for param in vec4_params:
            val = mat.get(f"dow2_{param}", None)
            if not val:
                continue

            row = box.row()
            row.label(text=param)
            if isinstance(val, (list, tuple)) and len(val) >= 4:
                row.label(text=f"({val[0]:.2f}, {val[1]:.2f}, {val[2]:.2f}, {val[3]:.2f})")

        box = layout.box()
        box.label(text="Vector2", icon="ORIENTATION_VIEW")

        wind = mat.get("dow2_WaterReflection_WindDirection", None)
        if wind:
            row = box.row()
            row.label(text="Wind Direction")
            if isinstance(wind, (list, tuple)) and len(wind) >= 2:
                row.label(text=f"({wind[0]:.2f}, {wind[1]:.2f})")

        world = mat.get("dow2_World", None)
        if world:
            box = layout.box()
            box.label(text="World Matrix", icon="EMPTY_AXIS")
            if isinstance(world, (list, tuple)) and len(world) >= 16:
                for index in range(4):
                    row = box.row()
                    for column in range(4):
                        row.label(text=f"{world[index * 4 + column]:.2f}")


__all__ = ["DOW2_PT_material_vectors"]