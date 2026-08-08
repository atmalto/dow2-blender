import os

from bpy.props import StringProperty
from bpy.types import Operator

from ...material.badges import clear_badge_preview, is_badge_material as is_badge_preview_material
from ...material.service import rebuild_dow2_material_graph
from ...utils import get_active_data_root, set_file_browser_start


class DOW2_OT_set_texture(Operator):
    """Set a texture path for DoW2 material"""

    bl_idname = "dow2.set_texture"
    bl_label = "Set Texture"
    bl_options = {'REGISTER', 'UNDO'}

    texture_slot: StringProperty(name="Texture Slot")

    filepath: StringProperty(
        name="Texture Path",
        description="Path to texture file",
        subtype='FILE_PATH',
    )

    filter_glob: StringProperty(
        default="*.dds;*.tga;*.png",
        options={'HIDDEN'},
    )

    def execute(self, context):
        mat = context.object.active_material
        if not mat:
            self.report({'ERROR'}, "No material selected")
            return {'CANCELLED'}

        tex_path = self.filepath
        data_path = get_active_data_root(context)
        if data_path and tex_path.lower().startswith(data_path.lower()):
            tex_path = tex_path[len(data_path):].lstrip(os.sep).lstrip('/')
            if tex_path.lower().endswith('.dds'):
                tex_path = tex_path[:-4]

        mat[f"dow2_{self.texture_slot}"] = tex_path
        self.update_material_nodes(context, mat)

        self.report({'INFO'}, f"Set {self.texture_slot}")
        return {'FINISHED'}

    def invoke(self, context, event):
        set_file_browser_start(self, context)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def update_material_nodes(self, context, mat):
        if not mat.use_nodes:
            return
        rebuild_dow2_material_graph(context, mat, str(mat.get("dow2_shader_path", "") or ""))


class DOW2_OT_clear_texture(Operator):
    """Clear a texture slot"""

    bl_idname = "dow2.clear_texture"
    bl_label = "Clear Texture"
    bl_options = {'REGISTER', 'UNDO'}

    texture_slot: StringProperty(name="Texture Slot")

    def execute(self, context):
        mat = context.object.active_material
        if mat is None:
            return {'FINISHED'}

        prop_name = f"dow2_{self.texture_slot}"
        if prop_name in mat:
            del mat[prop_name]

        if mat.use_nodes and mat.node_tree is not None:
            tex_node = mat.node_tree.nodes.get(f"dow2_{self.texture_slot}")
            if tex_node is not None and getattr(tex_node, 'type', None) == 'TEX_IMAGE':
                tex_node.image = None

        if self.texture_slot in {'badge1Tex', 'badge2Tex'} and is_badge_preview_material(mat):
            clear_badge_preview(mat, 'badge1' if self.texture_slot == 'badge1Tex' else 'badge2')
        return {'FINISHED'}


__all__ = [
    "DOW2_OT_clear_texture",
    "DOW2_OT_set_texture",
]