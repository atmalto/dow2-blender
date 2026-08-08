import textwrap

from bpy.types import Panel

from ..utils import get_addon_preferences


class DOW2_PT_header_panel(Panel):
    """DoW2 tools header banner"""

    bl_label = "DoW 2 Tools"
    bl_idname = "DOW2_PT_header_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"

    def draw(self, context):
        layout = self.layout
        column = layout.column()
        column.scale_y = 1.5

        text = (
            "Dawn of War 2 Blender Tools\n"
            "Import/Export: Models, Animations, Physics, Collision\n"
            "Utilities: Create collision, rigid bodies, simbox/ coverbox, \n"
            "collections, team color viz, badges placement, key DoW2 shader\n" 
            "replicas, parallel export workers and more"

        )

        for line in text.split("\n"):
            wrapped = textwrap.wrap(line.strip(), width=70) or [""]
            for subline in wrapped:
                column.label(text=subline)


class DOW2_PT_model_panel(Panel):
    """DoW2 Model Import/Export Panel"""

    bl_label = "Model"
    bl_idname = "DOW2_PT_model_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_order = 30

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("import_scene.dow2_model", text="Import", icon="IMPORT")
        row.operator("export_scene.dow2_model", text="Export", icon="EXPORT")


class DOW2_PT_mod_folder_panel(Panel):
    """DoW2 mod folder selection"""

    bl_label = "Mod Folder"
    bl_idname = "DOW2_PT_mod_folder_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_order = 20

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        if prefs is None:
            layout.label(text="Addon preferences unavailable", icon='ERROR')
            return

        layout.prop(prefs, "module_path", text="")


class DOW2_PT_collection_setup(Panel):
    """Create standard DoW2 model hierarchy collections"""

    bl_label = "Model Export Setup"
    bl_idname = "DOW2_PT_collection_setup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_parent_id = "DOW2_PT_model_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        col.prop(scene, "dow2_model_lod_count")
        col.prop(scene, "dow2_model_damage_template")
        col.operator("dow2.setup_collections", icon="OUTLINER_COLLECTION")


class DOW2_PT_bones_markers(Panel):
    """DoW2 bone and marker controls"""

    bl_label = "Bones and Markers"
    bl_idname = "DOW2_PT_bones_markers"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_parent_id = "DOW2_PT_model_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(context.scene, "dow2_intercept_apply_transform", text="Intercept Apply Transform")
        col.prop(context.scene, "dow2_show_bone_marker_names", text="Show Bone and Marker Names")


class DOW2_PT_simbox_coverbox(Panel):
    """DoW2 simbox and coverbox controls"""

    bl_label = "Simbox and Coverbox"
    bl_idname = "DOW2_PT_simbox_coverbox"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_parent_id = "DOW2_PT_model_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, _context):
        layout = self.layout
        row = layout.row(align=True)
        simbox = row.operator("dow2.create_bounding_box", text="Create Simbox", icon="SHADING_BBOX")
        simbox.box_type = "simbox"
        coverbox = row.operator("dow2.create_bounding_box", text="Create Coverbox", icon="CUBE")
        coverbox.box_type = "coverbox"


class DOW2_PT_object_panel(Panel):
    """DoW2 Object Properties Panel"""

    bl_label = "Object Info"
    bl_idname = "DOW2_PT_object_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_parent_id = "DOW2_PT_model_panel"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        obj = context.object

        row = layout.row()
        row.label(text="Type:", icon="OBJECT_DATA")
        row.label(text=obj.type)

        if obj.type == 'MESH' and obj.data:
            mesh = obj.data
            col = layout.column()
            col.label(text=f"Vertices: {len(mesh.vertices)}")
            col.label(text=f"Faces: {len(mesh.polygons)}")
            col.label(text=f"Materials: {len(obj.material_slots)}")

            if mesh.uv_layers:
                col.label(text=f"UV Layers: {len(mesh.uv_layers)}")

            if obj.vertex_groups:
                col.label(text=f"Skin Bones: {len(obj.vertex_groups)}")

        elif obj.type == 'ARMATURE' and obj.data:
            armature = obj.data
            col = layout.column()
            col.label(text=f"Bones: {len(armature.bones)}")

        elif obj.type == 'EMPTY':
            col = layout.column()
            col.label(text="Marker/Helper")
            if obj.parent:
                col.label(text=f"Parent: {obj.parent.name}")


MODEL_PANEL_CLASSES = [
    DOW2_PT_header_panel,
    DOW2_PT_mod_folder_panel,
    DOW2_PT_model_panel,
    DOW2_PT_collection_setup,
    DOW2_PT_bones_markers,
    DOW2_PT_simbox_coverbox,
    DOW2_PT_object_panel,
]


__all__ = [
    "DOW2_PT_collection_setup",
    "DOW2_PT_bones_markers",
    "DOW2_PT_header_panel",
    "DOW2_PT_mod_folder_panel",
    "DOW2_PT_model_panel",
    "DOW2_PT_object_panel",
    "DOW2_PT_simbox_coverbox",
    "MODEL_PANEL_CLASSES",
]