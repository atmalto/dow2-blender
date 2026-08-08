"""
DoW2 Collision Exporter - Blender operator for exporting .collision files.

Creates collision files from selected Blender mesh objects.
"""

import bpy
import os
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from .collision_io import write_collision, CollisionData, CollisionMesh
from . import utils as collision_utils
from ..utils import blender_to_dx_position


class DOW2_OT_export_collision(Operator, ExportHelper):
    """Export Dawn of War 2 collision file (.collision)"""
    bl_idname = "export_scene.dow2_collision"
    bl_label = "Export DoW2 Collision"
    bl_options = {'REGISTER', 'PRESET'}
    
    # File browser settings
    filename_ext = ".collision"
    filter_glob: StringProperty(
        default="*.collision",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    # Export options
    use_selection: BoolProperty(
        name="Selected Only",
        description="Export only selected mesh objects. "
                    "When disabled, exports all visible mesh objects",
        default=True,
    )
    
    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers to meshes before exporting. "
                    "Recommended for accurate collision geometry",
        default=True,
    )
    
    def execute(self, context):
        grouped_objects = collision_utils.collect_collision_state_meshes(context.scene)
        export_groups = []
        for state_id, objects in sorted(grouped_objects.items()):
            if self.use_selection:
                filtered_objects = [obj for obj in objects if obj in context.selected_objects]
            else:
                filtered_objects = [obj for obj in objects if obj.visible_get()]
            if filtered_objects:
                export_groups.append((state_id, sorted(filtered_objects, key=lambda item: item.name.lower())))

        if not export_groups:
            self.report({'ERROR'}, "No recognized collision meshes to export from Collision::... collections")
            return {'CANCELLED'}
        
        collision_data = CollisionData(collision_type=1, meshes=[])
        
        for state_id, objects in export_groups:
            for obj in objects:
                col_mesh = self._object_to_collision_mesh(context, obj, state_id)
                if col_mesh:
                    collision_data.meshes.append(col_mesh)
        
        if not collision_data.meshes:
            self.report({'ERROR'}, "No valid meshes to export")
            return {'CANCELLED'}

        collision_data.collision_type = collision_data.meshes[0].state_id
        
        # Write collision file
        try:
            write_collision(collision_data, self.filepath)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to write collision file: {e}")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"Exported {len(collision_data.meshes)} collision mesh(es) to '{os.path.basename(self.filepath)}'")
        return {'FINISHED'}
    
    def _object_to_collision_mesh(self, context, obj: bpy.types.Object, state_id: int) -> CollisionMesh:
        """Convert a Blender object to a CollisionMesh."""
        if self.apply_modifiers:
            depsgraph = context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)
            mesh = obj_eval.to_mesh()
            cleanup_eval_mesh = True
        else:
            mesh = obj.data.copy()
            cleanup_eval_mesh = False
        
        # Triangulate if needed (collision requires triangles only)
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(mesh)
        bm.free()
        
        # Get world-space vertices and convert to DirectX coordinate system
        world_matrix = obj.matrix_world
        vertices = []
        for vert in mesh.vertices:
            world_co = world_matrix @ vert.co
            vertices.append(blender_to_dx_position(world_co))
        
        # Get face indices
        faces = []
        for poly in mesh.polygons:
            if len(poly.vertices) == 3:
                faces.append((poly.vertices[0], poly.vertices[1], poly.vertices[2]))
        
        if self.apply_modifiers:
            obj_eval.to_mesh_clear()
        else:
            bpy.data.meshes.remove(mesh)
        
        stored_mesh_type = obj.get("dow2_collision_mesh_type", 4)
        stored_header = obj.get("dow2_collision_header", None)
        
        if stored_header:
            header_fields = list(stored_header)
        else:
            header_fields = [0, stored_mesh_type]
            for i in range(stored_mesh_type):
                header_fields.append(i)
        
        return CollisionMesh(
            name=obj.name,
            state_id=state_id,
            mesh_type=stored_mesh_type,
            vertices=vertices,
            faces=faces,
            header_fields=header_fields
        )
    
    def draw(self, context):
        layout = self.layout
        
        # Export options box
        box = layout.box()
        box.label(text="Export Options", icon="EXPORT")
        
        box.prop(self, "use_selection")
        box.prop(self, "apply_modifiers")
        
        collision_state_meshes = collision_utils.collect_collision_state_meshes(context.scene)
        if self.use_selection:
            selected_meshes = sum(1 for meshes in collision_state_meshes.values() for obj in meshes if obj in context.selected_objects)
        else:
            selected_meshes = sum(1 for meshes in collision_state_meshes.values() for obj in meshes if obj.visible_get())
        
        box = layout.box()
        box.label(text=f"Meshes to export: {selected_meshes}", icon="INFO")
        box.label(text="Source: recognized Collision::... collections", icon="OUTLINER_COLLECTION")


def menu_func_export(self, context):
    self.layout.operator(DOW2_OT_export_collision.bl_idname, text="DoW2 Collision (.collision)")


def register():
    bpy.utils.register_class(DOW2_OT_export_collision)


def unregister():
    try:
        bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    except (RuntimeError, ValueError):
        pass
    bpy.utils.unregister_class(DOW2_OT_export_collision)
