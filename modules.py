# DoW2 Module Manager
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DoW2Module:
    name: str
    description: str = ""
    dll_name: str = ""
    mod_folder: str = ""
    mod_version: str = ""
    playable: bool = False
    archive_list: List[str] = field(default_factory=list)
    required_mods: List[str] = field(default_factory=list)
    data_folder: str = ""
    mod_path: str = ""


class DoW2ModuleManager:
    def __init__(self):
        self.modules: Dict[str, DoW2Module] = {}
        self.dow2_path: str = ""
        self.data_path: str = ""
    
    def set_paths(self, dow2_path: str, module_path: str = ""):
        self.dow2_path = dow2_path
        if module_path:
            self.data_path = module_path
        else:
            self.data_path = os.path.join(dow2_path, "Codex", "Data")
    
    def get_data_path(self, module_name: str = "") -> str:
        if module_name and module_name in self.modules:
            module = self.modules[module_name]
            if module.data_folder:
                return os.path.join(module.mod_path, module.data_folder)
        return self.data_path
    
    def make_relative(self, filepath: str, module_name: str = "") -> str:
        data_path = self.get_data_path(module_name)
        if filepath.lower().startswith(data_path.lower()):
            return filepath[len(data_path):].lstrip(os.sep).lstrip('/')
        return filepath
    
    def make_absolute(self, relative_path: str, module_name: str = "") -> str:
        data_path = self.get_data_path(module_name)
        return os.path.join(data_path, relative_path)


module_manager = DoW2ModuleManager()


def register():
    import bpy
    prefs = bpy.context.preferences.addons.get('dow2_tools')
    if prefs:
        prefs = prefs.preferences
        module_manager.set_paths(prefs.dow2_path, prefs.module_path)


def unregister():
    module_manager.modules.clear()
