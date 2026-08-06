# Animation package
from .importer import (
    DOW2_OT_import_animation,
    DOW2_OT_batch_import_animations,
)
from .exporter import (
    EXPORT_OT_dow2_animation,
    DOW2_OT_batch_import_anims,
    DOW2_OT_batch_export_anims,
)


def register():
    from .importer import register as register_importer
    from .exporter import register as register_exporter
    register_importer()
    register_exporter()


def unregister():
    from .importer import unregister as unregister_importer
    from .exporter import unregister as unregister_exporter
    unregister_exporter()
    unregister_importer()
