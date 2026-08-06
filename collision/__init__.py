"""
DoW2 Collision module - Import/Export for .collision files.

This module provides:
- collision_io: Core read/write functions for collision files
- importer: Blender operator to import .collision files
- exporter: Blender operator to export collision files from mesh objects
"""

from . import importer
from . import exporter


def register():
    """Register collision import/export operators."""
    importer.register()
    exporter.register()


def unregister():
    """Unregister collision import/export operators."""
    exporter.unregister()
    importer.unregister()
