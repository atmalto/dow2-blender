from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from .definitions import VAR_TYPE_TEXTURE


@dataclass
class MaterialVariable:
    """A material shader variable."""

    name: str
    var_type: int
    value: Any


@dataclass
class RelicMaterialData:
    """Parsed Relic material data used by readers, builders, and exporters."""

    name: str
    shader_name: str = ""
    shader_path: str = ""
    variables: List[MaterialVariable] = field(default_factory=list)

    def get_variable(self, name: str) -> Optional[MaterialVariable]:
        for var in self.variables:
            if var.name == name:
                return var
        return None

    def get_texture(self, name: str) -> Optional[str]:
        var = self.get_variable(name)
        if var and var.var_type == VAR_TYPE_TEXTURE:
            return var.value
        return None


__all__ = ["MaterialVariable", "RelicMaterialData"]