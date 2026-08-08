from __future__ import annotations

import os
from typing import Any, Optional, Tuple

import bpy

from .data import RelicMaterialData


class RelicMaterialCreator:
    """Facade for Relic material creation that delegates shader-specific logic."""

    def __init__(self, data_path: str):
        self.data_path = data_path
        self.game_data_path = self._find_data_root(data_path)
        from .shaders.layout import ShaderLayoutResolver
        from .shaders.registry import ShaderBuilderRegistry

        self._layout_resolver = ShaderLayoutResolver(self.game_data_path)
        self._shader_registry = ShaderBuilderRegistry(self._layout_resolver)

    def _find_data_root(self, path: str) -> str:
        """Find the game Data folder by walking upward until an art folder is found."""
        current = os.path.normpath(path)
        while current:
            if os.path.isdir(os.path.join(current, "art")):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return path

    def find_texture_file(self, tex_path: str) -> Optional[str]:
        """Find texture file on disk."""
        if not tex_path:
            return None

        full_path = os.path.join(self.game_data_path, tex_path)
        if not full_path.lower().endswith('.dds'):
            full_path += '.dds'

        if os.path.exists(full_path):
            return full_path

        full_path = full_path.replace('\\', '/')
        if os.path.exists(full_path):
            return full_path

        full_path = full_path.replace('/', '\\')
        if os.path.exists(full_path):
            return full_path

        return None

    def get_texture_uv_map(self, shader_name: str, texture_var_name: str) -> str:
        """Resolve UV map name for a texture variable using shader layout policy."""
        return self._layout_resolver.get_texture_uv_map(shader_name, texture_var_name)

    def create_image_node(
        self,
        nodes,
        links,
        tex_path: str,
        location: Tuple[float, float],
        label: str,
        non_color: bool = False,
        uv_map_name: str = "UVMap",
        extension: str = 'REPEAT',
    ) -> Optional[bpy.types.Node]:
        """Create an image texture node."""
        if not tex_path:
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.location = location
            tex_node.label = label
            if hasattr(tex_node, 'extension'):
                tex_node.extension = extension

            if uv_map_name:
                uv_node = nodes.new('ShaderNodeUVMap')
                uv_node.uv_map = uv_map_name
                uv_node.location = (location[0] - 220, location[1])
                uv_node.label = f"{label}_{uv_map_name}"
                links.new(uv_node.outputs['UV'], tex_node.inputs['Vector'])

            return tex_node

        file_path = self.find_texture_file(tex_path)
        if not file_path:
            print(f"[WARNING] Missing texture file: {tex_path}")
            return None

        try:
            img = bpy.data.images.load(file_path, check_existing=True)
            if non_color:
                img.colorspace_settings.name = 'Non-Color'

            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = img
            tex_node.location = location
            tex_node.label = label
            if hasattr(tex_node, 'extension'):
                tex_node.extension = extension

            if uv_map_name:
                uv_node = nodes.new('ShaderNodeUVMap')
                uv_node.uv_map = uv_map_name
                uv_node.location = (location[0] - 220, location[1])
                uv_node.label = f"{label}_{uv_map_name}"
                links.new(uv_node.outputs['UV'], tex_node.inputs['Vector'])

            return tex_node
        except Exception as error:
            print(f"Failed to load texture {file_path}: {error}")
            return None

    def create_material(self, mat_data: RelicMaterialData) -> bpy.types.Material:
        """Create a Blender material by delegating to shader-specific builder strategy."""
        builder = self._shader_registry.get_builder(mat_data.shader_name)
        return builder.build_material(self, mat_data)


_material_creator: Optional[RelicMaterialCreator] = None


def get_material_creator(data_path: str) -> RelicMaterialCreator:
    global _material_creator
    _material_creator = RelicMaterialCreator(data_path)
    return _material_creator


__all__ = ["RelicMaterialCreator", "get_material_creator"]