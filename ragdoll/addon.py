from . import operators, properties
from .authoring import register_body_sync_handlers, unregister_body_sync_handlers


def register():
    properties.register()
    operators.register()
    register_body_sync_handlers()


def unregister():
    unregister_body_sync_handlers()
    operators.unregister()
    properties.unregister()