from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


@dataclass
class MaterialBuildContext:
    mat: Any
    nodes: Any
    links: Any
    output: Any
    principled: Any


@dataclass
class MaterialBuildState:
    tex_x: int
    tex_y: int
    tex_y_step: int
    diffuse_tex_node: Optional[Any] = None
    emissive_tex_node: Optional[Any] = None
    ao_tex_node: Optional[Any] = None
    team_tex_node: Optional[Any] = None
    specular_tex_node: Optional[Any] = None
    specular_color_socket: Optional[Any] = None
    metallic_socket: Optional[Any] = None
    normal_socket: Optional[Any] = None
    texture_nodes: Dict[str, Any] = None

    def __post_init__(self):
        if self.texture_nodes is None:
            self.texture_nodes = {}

    def next_texture_row(self) -> None:
        self.tex_y += self.tex_y_step


class ShaderLayoutPolicy(Protocol):
    def get_texture_uv_map(self, shader_name: str, texture_var_name: str) -> str:
        ...


class ShaderMaterialBuilder(Protocol):
    def build_material(self, creator: Any, mat_data: Any) -> Any:
        ...


class TextureSlotHandler(Protocol):
    def can_handle(self, var_name_lower: str) -> bool:
        ...

    def handle(self, creator: Any, ctx: MaterialBuildContext, state: MaterialBuildState, mat_data: Any, var: Any) -> bool:
        ...


class ShaderBuilderRegistry(Protocol):
    def get_builder(self, shader_name: Optional[str]) -> ShaderMaterialBuilder:
        ...
