"""DoW2 map I/O package.

STATUS: WIP. 
Scenario map import is no where near complete, it will likely fail or produce
partial results on some maps. It's tile textures are especially broken at this point. 
This is an experimental feature developed to import map scene to render cinematics...
"""

from .importer import MapImportOptions, MapImportResult, import_scenario_map

__all__ = [
    "MapImportOptions",
    "MapImportResult",
    "import_scenario_map",
]