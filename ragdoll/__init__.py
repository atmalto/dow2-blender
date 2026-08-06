from .constants import DEFAULT_RAGDOLL_BONE_ORDER
from .field_specs import EXPOSED_FIELD_SPECS, LOCKED_BACKEND_FIELDS, TEMPLATE_DRIVEN_FIELDS
from .templates import load_template_library, list_template_tree


def create_ragdoll_skeleton_from_armature(*args, **kwargs):
    from .skeleton import create_ragdoll_skeleton_from_armature as implementation

    return implementation(*args, **kwargs)


def export_ragdoll_json(*args, **kwargs):
    from .exporter import export_ragdoll_json as implementation

    return implementation(*args, **kwargs)


def export_ragdoll_hkx(*args, **kwargs):
    from .exporter import export_ragdoll_hkx as implementation

    return implementation(*args, **kwargs)


def build_ragdoll_data(*args, **kwargs):
    from .exporter import build_ragdoll_data as implementation

    return implementation(*args, **kwargs)


def get_armature(*args, **kwargs):
    from .scene import get_armature as implementation

    return implementation(*args, **kwargs)


def import_model(*args, **kwargs):
    from .scene import import_model as implementation

    return implementation(*args, **kwargs)

__all__ = [
    "DEFAULT_RAGDOLL_BONE_ORDER",
    "EXPOSED_FIELD_SPECS",
    "LOCKED_BACKEND_FIELDS",
    "TEMPLATE_DRIVEN_FIELDS",
    "build_ragdoll_data",
    "create_ragdoll_skeleton_from_armature",
    "export_ragdoll_hkx",
    "export_ragdoll_json",
    "get_armature",
    "import_model",
    "list_template_tree",
    "load_template_library",
]