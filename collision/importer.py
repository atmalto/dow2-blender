"""
DoW2 Collision Importer - Blender operator for importing .collision files.

Creates Blender mesh objects from collision data.
"""

import bpy
import os
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector

from .collision_io import read_collision, CollisionData, CollisionMesh
from . import utils as collision_utils
from ..utils import dx_to_blender_position


class DOW2_OT_import_collision(Operator, ImportHelper):
    """Import Dawn of War 2 collision file (.collision)"""
    bl_idname = "import_scene.dow2_collision"
    bl_label = "Import DoW2 Collision"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}
    
    # File browser filter
    filename_ext = ".collision"
    filter_glob: StringProperty(
        default="*.collision",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    # Import options
    import_as_separate: BoolProperty(
        name="Import as Separate Objects",
        description="Import each collision mesh as a separate Blender object. "
                    "When disabled, all meshes are combined into a single object",
        default=True,
    )
    
    create_collection: BoolProperty(
        name="Create State Collections",
        description="Place imported collision meshes into recognized Collision::... state collections",
        default=True,
    )
    
    display_type: EnumProperty(
        name="Display Type",
        description="How to display the collision meshes in the viewport",
        items=[
            ('SOLID', "Solid", "Display as solid objects"),
            ('WIRE', "Wire", "Display as wireframe (recommended for collision)"),
            ('BOUNDS', "Bounds", "Display as bounding box only"),
        ],
        default='WIRE',
    )
    
    def execute(self, context):
        # Read the collision file
        try:
            collision_data = read_collision(self.filepath)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to read collision file: {e}")
            return {'CANCELLED'}
        
        # Get base name for objects/collection
        base_name = os.path.splitext(os.path.basename(self.filepath))[0]
        
        # Import meshes
        created_objects = []
        
        if self.import_as_separate:
            for col_mesh in collision_data.meshes:
                obj = self._create_mesh_object(col_mesh, f"{base_name}_{col_mesh.name}")
                if self.create_collection:
                    collection = collision_utils.ensure_collision_state_collection(context.scene, col_mesh.state_id)
                else:
                    collection = context.scene.collection
                collection.objects.link(obj)
                created_objects.append(obj)
                
                # Store collision metadata
                obj["dow2_collision_type"] = col_mesh.state_id
                obj["dow2_collision_state_id"] = col_mesh.state_id
                obj["dow2_collision_state_name"] = collision_utils.get_collision_state_name(col_mesh.state_id)
                obj["dow2_collision_mesh_type"] = col_mesh.mesh_type
                obj["dow2_collision_header"] = list(col_mesh.header_fields)
        else:
            meshes_by_state = {}
            for col_mesh in collision_data.meshes:
                meshes_by_state.setdefault(col_mesh.state_id, []).append(col_mesh)

            for state_id, meshes in sorted(meshes_by_state.items()):
                combined_verts = []
                combined_faces = []
                vert_offset = 0

                for col_mesh in meshes:
                    converted_verts = [dx_to_blender_position(Vector(v)) for v in col_mesh.vertices]
                    combined_verts.extend(converted_verts)
                    for face in col_mesh.faces:
                        combined_faces.append((
                            face[0] + vert_offset,
                            face[1] + vert_offset,
                            face[2] + vert_offset
                        ))
                    vert_offset += len(col_mesh.vertices)

                mesh = bpy.data.meshes.new(f"{base_name}_{collision_utils.get_collision_state_name(state_id)}_mesh")
                mesh.from_pydata(combined_verts, [], combined_faces)
                mesh.update()

                obj = bpy.data.objects.new(f"{base_name}_{collision_utils.get_collision_state_name(state_id)}", mesh)
                if self.create_collection:
                    collection = collision_utils.ensure_collision_state_collection(context.scene, state_id)
                else:
                    collection = context.scene.collection
                collection.objects.link(obj)
                created_objects.append(obj)

                obj["dow2_collision_type"] = state_id
                obj["dow2_collision_state_id"] = state_id
                obj["dow2_collision_state_name"] = collision_utils.get_collision_state_name(state_id)
                obj["dow2_collision_meshes"] = len(meshes)
        
        # Set display properties
        for obj in created_objects:
            obj.display_type = self.display_type
            
            # Add collision material for visibility
            mat = self._get_or_create_collision_material()
            obj.data.materials.append(mat)
        
        # Select imported objects
        bpy.ops.object.select_all(action='DESELECT')
        for obj in created_objects:
            obj.select_set(True)
        if created_objects:
            context.view_layer.objects.active = created_objects[0]
        
        self.report({'INFO'}, f"Imported {len(collision_data.meshes)} collision mesh(es) from '{base_name}'")
        return {'FINISHED'}
    
    def _create_mesh_object(self, col_mesh: CollisionMesh, name: str) -> bpy.types.Object:
        """Create a Blender mesh object from a CollisionMesh."""
        mesh = bpy.data.meshes.new(f"{name}_mesh")
        verts = [dx_to_blender_position(Vector(v)) for v in col_mesh.vertices]
        mesh.from_pydata(verts, [], col_mesh.faces)
        mesh.update()
        
        obj = bpy.data.objects.new(name, mesh)
        return obj
    
    def _get_or_create_collision_material(self) -> bpy.types.Material:
        """Get or create a semi-transparent material for collision visualization."""
        mat_name = "dow2_collision_material"
        mat = bpy.data.materials.get(mat_name)
        
        if mat is None:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            mat.blend_method = 'BLEND'
            
            # Set up principled BSDF for collision visualization
            nodes = mat.node_tree.nodes
            bsdf = nodes.get("Principled BSDF")
            if bsdf:
                # Green semi-transparent color for collision
                bsdf.inputs["Base Color"].default_value = (0.2, 0.8, 0.2, 1.0)
                bsdf.inputs["Alpha"].default_value = 0.3
                bsdf.inputs["Roughness"].default_value = 1.0
        
        return mat
    
    def draw(self, context):
        layout = self.layout
        
        # Import options box
        box = layout.box()
        box.label(text="Import Options", icon="IMPORT")
        
        box.prop(self, "import_as_separate")
        box.prop(self, "create_collection")
        box.prop(self, "display_type")


def menu_func_import(self, context):
    self.layout.operator(DOW2_OT_import_collision.bl_idname, text="DoW2 Collision (.collision)")


def register():
    bpy.utils.register_class(DOW2_OT_import_collision)


def unregister():
    try:
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    except (RuntimeError, ValueError):
        pass
    bpy.utils.unregister_class(DOW2_OT_import_collision)
