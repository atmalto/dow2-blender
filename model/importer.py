import os
from typing import Dict, List, Optional

import bpy

from ..chunk_lib import ChunkReader, RelicChunk, get_chunk
from .import_types import ImportBone, ImportMesh, ImportOptions
from .import_operators import DOW2_OT_import_model, menu_func_import, register, unregister
from .importer_materials import import_materials
from .importer_meshes import create_blender_mesh, get_or_create_group_collection, get_or_create_lod_collection, import_meshes, import_submesh
from .importer_scene import import_bounding_box, import_data_templates, import_model_states
from .importer_skeleton import import_bones, import_markers


class DoW2ModelImporter:
    """Complete DoW2 model importer with all features"""
    
    def __init__(self, filepath: str, options: ImportOptions):
        self.filepath = filepath
        self.options = options
        self.reader: Optional[ChunkReader] = None
        self.bones: List[ImportBone] = []
        self.bone_map: Dict[str, int] = {}  # bone name -> index
        self.materials: Dict[str, bpy.types.Material] = {}
        self.armature: Optional[bpy.types.Object] = None
        self.data_path = ""
        self.model_name = ""  # Model filename without extension
        self.mesh_groups: Dict[str, List[ImportMesh]] = {}
    
    def import_model(self):
        """Main import entry point"""
        print(f"Importing: {self.filepath}")
        
        # Reset scene if requested (clear all objects and collections)
        if self.options.reset_scene:
            print("Resetting scene...")
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete()
            # Remove all collections (except master scene collection)
            for col in list(bpy.data.collections):
                bpy.data.collections.remove(col)
            # Also remove orphan data
            for mesh in bpy.data.meshes:
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
            for mat in bpy.data.materials:
                if mat.users == 0:
                    bpy.data.materials.remove(mat)
            for arm in bpy.data.armatures:
                if arm.users == 0:
                    bpy.data.armatures.remove(arm)
        
        self.data_path = os.path.dirname(self.filepath)
        self.model_name = os.path.splitext(os.path.basename(self.filepath))[0]
        bpy.context.scene["dow2_model_name"] = self.model_name
        
        with open(self.filepath, "rb") as file:
            self.reader = ChunkReader(file)
            if not self.reader.read_relic_chunky():
                print("Invalid Relic Chunky file")
                return {"CANCELLED"}
            
            self.reader.read_chunks()
            chunks = self.reader.root_chunks
            
            # Get MODL chunk
            modl = get_chunk("MODL", chunks)
            if not modl:
                print("No MODL chunk found")
                return {"CANCELLED"}
            
            # Import in order: materials, bones, meshes, markers
            if self.options.import_materials:
                self._import_materials(modl.children)
            
            if self.options.import_bones:
                self._import_bones(modl.children)
            
            if self.options.import_meshes:
                self._import_meshes(modl.children)
            
            if self.options.import_markers:
                self._import_markers(modl.children)
            
            # Import model states (damage states) and data templates
            self._import_model_states(modl.children)
            self._import_data_templates(modl.children)

        if self.armature is not None:
            self.armature["dow2_model_name"] = self.model_name
        
        # Import bounding boxes from lua files (outside model file)
        if self.options.import_simbox:
            self._import_bounding_box("simbox")
        
        if self.options.import_coverbox:
            self._import_bounding_box("coverbox")
        
        print("Import complete")
        return {"FINISHED"}

    def _import_bounding_box(self, box_type: str):
        import_bounding_box(self, box_type)

    def _import_model_states(self, chunks: List[RelicChunk]):
        import_model_states(self, chunks)

    def _import_data_templates(self, chunks: List[RelicChunk]):
        import_data_templates(self, chunks)

    def _import_materials(self, chunks: List[RelicChunk]):
        import_materials(self, chunks)

    def _import_bones(self, chunks: List[RelicChunk]):
        import_bones(self, chunks)

    def _import_markers(self, chunks: List[RelicChunk]):
        import_markers(self, chunks)

    def _import_meshes(self, chunks: List[RelicChunk]):
        import_meshes(self, chunks)

    def _get_or_create_group_collection(self, group_name: str):
        return get_or_create_group_collection(self, group_name)

    def _get_or_create_lod_collection(self, group_name: str, lod_level: int, parent_collection):
        return get_or_create_lod_collection(self, group_name, lod_level, parent_collection)

    def _import_submesh(self, mesh_chunk: RelicChunk, group_name: str, lod_level: int, lod_collection=None):
        import_submesh(self, mesh_chunk, group_name, lod_level, lod_collection)

    def _create_blender_mesh(
        self,
        name,
        vertices,
        faces,
        mat_name,
        skin_bones,
        has_uv2,
        has_vertex_color,
        group_name,
        lod_level,
    ):
        create_blender_mesh(
            self,
            name,
            vertices,
            faces,
            mat_name,
            skin_bones,
            has_uv2,
            has_vertex_color,
            group_name,
            lod_level,
        )
