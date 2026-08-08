# ===========
# ADDON INFO
# ===========
bl_info = {
    "name": "DoW2 Tools",
    "author": "Converted from Santos Tools 2",
    "version": (0, 1, 1),
    "blender": (4, 3, 0),
    "location": "File > Import/Export, View3D > Sidebar > DoW2",
    "description": "Import and export Dawn of War 2 model files (.model)",
    "category": "Import-Export",
}

import bpy
import importlib
import os
import sys
import traceback

from . import preferences as preferences_module


_RUNTIME_MODULE_PATHS = [
    ".modules",
    ".model.importer",
    ".model.exporter",
    ".animation.importer",
    ".animation.exporter",
    ".collision.importer",
    ".collision.exporter",
    ".physics",
    ".ragdoll.addon",
    ".ui.panels",
]

_runtime_modules = []
_dev_hot_reload_enabled = False
_dev_hot_reload_interval = 1.0
_module_mtimes = {}
_is_reloading = False


class DOW2_OT_ReloadAddon(bpy.types.Operator):
    """Manually reload the DoW2 Tools addon"""
    bl_idname = "dow2.reload_addon"
    bl_label = "Reload DoW2 Tools"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        _run_dev_hot_reload()
        self.report({'INFO'}, "DoW2 Tools Reloaded")
        return {'FINISHED'}


def _addon_root() -> str:
    return os.path.dirname(__file__)


def _should_enable_dev_hot_reload() -> bool:
    env_override = os.environ.get("DOW2_DEV_HOT_RELOAD", "").strip().lower()
    if env_override in {"1", "true", "yes", "on"}:
        return True
    
    # Force disable for standard users to prevent UI stutter/freezing
    return False


def _scan_module_mtimes() -> dict:
    mtimes = {}
    for root, _, files in os.walk(_addon_root()):
        for file_name in files:
            if not file_name.endswith(".py"):
                continue
            path = os.path.join(root, file_name)
            try:
                mtimes[path] = os.path.getmtime(path)
            except OSError:
                continue
    return mtimes


def _import_runtime_modules():
    global _runtime_modules
    _runtime_modules = [importlib.import_module(module_path, __name__) for module_path in _RUNTIME_MODULE_PATHS]


def _register_runtime_modules():
    for module in _runtime_modules:
        register_fn = getattr(module, "register", None)
        if callable(register_fn):
            register_fn()


def _unregister_runtime_modules():
    for module in reversed(_runtime_modules):
        unregister_fn = getattr(module, "unregister", None)
        if callable(unregister_fn):
            try:
                unregister_fn()
            except Exception:
                traceback.print_exc()


def _reload_package_submodules():
    module_names = [
        name for name in sys.modules.keys()
        if name.startswith(__name__ + ".")
    ]
    module_names.sort(key=lambda item: item.count("."), reverse=True)

    for name in module_names:
        module = sys.modules.get(name)
        if module is None:
            continue
        try:
            importlib.reload(module)
        except Exception:
            traceback.print_exc()


def _run_dev_hot_reload():
    global _is_reloading, _module_mtimes
    if _is_reloading:
        return

    _is_reloading = True
    try:
        _unregister_runtime_modules()
        _reload_package_submodules()
        _import_runtime_modules()
        _register_runtime_modules()
        _module_mtimes = _scan_module_mtimes()
        print("[DoW2 Tools] Hot reload completed")
    except Exception:
        traceback.print_exc()
    finally:
        _is_reloading = False


def _dev_hot_reload_timer():
    global _module_mtimes

    if not _dev_hot_reload_enabled:
        return None

    current = _scan_module_mtimes()
    changed = any(_module_mtimes.get(path) != mtime for path, mtime in current.items())

    if changed and not _is_reloading:
        print("[DoW2 Tools] Source change detected, reloading modules...")
        _run_dev_hot_reload()

    return _dev_hot_reload_interval


def _start_dev_hot_reload():
    global _module_mtimes
    _module_mtimes = _scan_module_mtimes()
    if not bpy.app.timers.is_registered(_dev_hot_reload_timer):
        bpy.app.timers.register(_dev_hot_reload_timer, first_interval=_dev_hot_reload_interval)


def _stop_dev_hot_reload():
    if bpy.app.timers.is_registered(_dev_hot_reload_timer):
        bpy.app.timers.unregister(_dev_hot_reload_timer)


def register():
    global _dev_hot_reload_enabled
    preferences_module.register()
    bpy.utils.register_class(DOW2_OT_ReloadAddon)
    _import_runtime_modules()
    _register_runtime_modules()

    _dev_hot_reload_enabled = _should_enable_dev_hot_reload()
    if _dev_hot_reload_enabled:
        _start_dev_hot_reload()


def unregister():
    _stop_dev_hot_reload()
    _unregister_runtime_modules()
    _runtime_modules.clear()
    if hasattr(bpy.types, DOW2_OT_ReloadAddon.__name__):
        bpy.utils.unregister_class(DOW2_OT_ReloadAddon)
    preferences_module.unregister()


__all__ = [
    "DOW2_OT_ReloadAddon",
    "register",
    "unregister",
]


# if __name__ == "__main__":
#     register()
