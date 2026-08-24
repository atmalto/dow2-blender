"""Blender -> Havok simulator sync bridge (add-on package).

Transport (:mod:`protocol`, :mod:`client`) is pure stdlib and importable without
Blender for unit tests. The Blender-facing pieces (:mod:`operators`, :mod:`ui`)
are only imported inside :func:`register` so importing this package outside
Blender (e.g. in the transport tests) does not require ``bpy``.
"""

from . import client, protocol

__all__ = ["client", "protocol", "register", "unregister"]


def register():
    from . import operators, properties, ui

    properties.register()
    operators.register()
    ui.register()


def unregister():
    from . import operators, properties, ui

    ui.unregister()
    operators.unregister()
    properties.unregister()
