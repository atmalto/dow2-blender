from bpy.types import Panel

from ..collision import utils as collision_utils


class DOW2_PT_collision_panel(Panel):
    """DoW2 Collision Import/Export Panel"""

    bl_label = "Collision"
    bl_idname = "DOW2_PT_collision_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_order = 60
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("import_scene.dow2_collision", text="Import", icon="IMPORT")
        row.operator("export_scene.dow2_collision", text="Export", icon="EXPORT")

        layout.separator()

        box = layout.box()
        box.label(text="Info", icon="INFO")

        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        box.label(text=f"Selected meshes: {len(selected_meshes)}")

        if context.object and context.object.type == 'MESH':
            obj = context.object
            state_id = obj.get("dow2_collision_state_id", obj.get("dow2_collision_type"))
            if state_id is not None:
                try:
                    state_id = int(state_id)
                except (TypeError, ValueError):
                    pass
                box.label(text=f"Collision state: {collision_utils.get_collision_state_name(state_id)} ({state_id})")
                mesh_type = obj.get("dow2_collision_mesh_type")
                if mesh_type is not None:
                    box.label(text=f"Mesh type: {mesh_type}")


class DOW2_PT_collision_collection_setup(Panel):
    """Create recognized DoW2 collision state collections"""

    bl_label = "Collision Export Setup"
    bl_idname = "DOW2_PT_collision_collection_setup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_parent_id = "DOW2_PT_collision_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(context.scene, "dow2_collision_state_count")
        col.operator("dow2.setup_collision_collections", icon="OUTLINER_COLLECTION")


class DOW2_PT_collision_generation(Panel):
    """Generate simplified collision meshes from selected geometry"""

    bl_label = "Collision Mesh Generation"
    bl_idname = "DOW2_PT_collision_generation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_parent_id = "DOW2_PT_collision_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        col.prop(scene, "dow2_collision_state_count")
        col.operator("dow2.setup_collision_collections", icon="OUTLINER_COLLECTION")
        col.separator()
        col.prop(scene, "dow2_collision_use_selected_faces")
        col.prop(scene, "dow2_collision_preview_type")

        if scene.dow2_collision_use_selected_faces:
            in_valid_mode = (
                context.mode == 'EDIT_MESH'
                and context.active_object is not None
                and context.active_object.type == 'MESH'
            )
            selected_faces = collision_utils.get_selected_face_count(context) if in_valid_mode else 0
            if not in_valid_mode:
                col.label(text="Use Edit Mode on a mesh object", icon='ERROR')
            elif selected_faces < 1:
                col.label(text="Select at least 1 face", icon='ERROR')
            else:
                col.label(text=f"Selected faces: {selected_faces}", icon='CHECKMARK')

        col.prop(scene, "dow2_collision_walkable")
        col.prop(scene, "dow2_collision_complex")
        if scene.dow2_collision_walkable and not scene.dow2_collision_complex:
            col.prop(scene, "dow2_collision_walkable_angle")
        if not scene.dow2_collision_complex:
            col.prop(scene, "dow2_collision_decimate")
        col.prop(scene, "dow2_collision_join_hulls")
        available_bucket_items = collision_utils.get_available_collision_state_items(scene, context)
        if available_bucket_items:
            col.prop(scene, "dow2_collision_generation_state")
        else:
            col.label(text="Generate collision buckets first", icon='ERROR')
        col.operator("dow2.generate_collision_mesh", icon="MOD_DECIM")


COLLISION_PANEL_CLASSES = [
    DOW2_PT_collision_panel,
    DOW2_PT_collision_generation,
]


__all__ = [
    "COLLISION_PANEL_CLASSES",
    "DOW2_PT_collision_generation",
    "DOW2_PT_collision_panel",
]