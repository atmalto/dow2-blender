import os

import bpy

from ..utils import load_persisted_settings, set_file_browser_start, store_persisted_settings
from .import_types import ImportOptions


_MODEL_IMPORT_SETTINGS_ATTR = "model_import_settings_json"


def _get_importer_class():
    from .importer import DoW2ModelImporter

    return DoW2ModelImporter


def _build_import_options(operator) -> ImportOptions:
    return ImportOptions(
        import_meshes=operator.import_meshes,
        import_materials=operator.import_materials,
        import_bones=operator.import_bones,
        import_markers=operator.import_markers,
        import_bounding_volumes=operator.import_bounding_volumes,
        import_simbox=operator.import_simbox,
        import_coverbox=operator.import_coverbox,
        smoothing=operator.smoothing,
        reset_scene=operator.reset_scene,
        save_scene=operator.save_scene,
        merge=operator.merge,
        group_meshes=operator.group_meshes,
        weld_vertices=operator.weld_vertices,
    )


def _build_import_settings_payload(operator) -> dict:
    return {
        "import_meshes": operator.import_meshes,
        "import_materials": operator.import_materials,
        "import_bones": operator.import_bones,
        "import_markers": operator.import_markers,
        "import_bounding_volumes": operator.import_bounding_volumes,
        "import_simbox": operator.import_simbox,
        "import_coverbox": operator.import_coverbox,
        "smoothing": operator.smoothing,
        "reset_scene": operator.reset_scene,
        "save_scene": operator.save_scene,
        "merge": operator.merge,
        "group_meshes": operator.group_meshes,
        "weld_vertices": operator.weld_vertices,
    }


def _apply_persisted_model_import_settings(operator, context):
    operator._is_loading_persisted_model_import_settings = True
    try:
        payload = load_persisted_settings(context, _MODEL_IMPORT_SETTINGS_ATTR)
        for key, value in payload.items():
            if hasattr(operator, key):
                setattr(operator, key, value)
    finally:
        operator._is_loading_persisted_model_import_settings = False


def _store_persisted_model_import_settings(operator, context):
    store_persisted_settings(context, _MODEL_IMPORT_SETTINGS_ATTR, _build_import_settings_payload(operator))


def _persist_model_import_settings_update(operator, context):
    if getattr(operator, "_is_loading_persisted_model_import_settings", False):
        return
    _store_persisted_model_import_settings(operator, context)


class DOW2_OT_import_model(bpy.types.Operator):
    """Import Dawn of War 2 .Model"""

    bl_idname = "import_scene.dow2_model"
    bl_label = "Import DoW2 Model"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.model", options={"HIDDEN"})
    import_meshes: bpy.props.BoolProperty(
        name="Meshes",
        description="Import mesh geometry",
        default=True,
        update=_persist_model_import_settings_update,
    )
    import_materials: bpy.props.BoolProperty(
        name="Materials",
        description="Import materials with textures",
        default=True,
        update=_persist_model_import_settings_update,
    )
    import_bones: bpy.props.BoolProperty(
        name="Bones",
        description="Import bone skeleton",
        default=True,
        update=_persist_model_import_settings_update,
    )
    import_markers: bpy.props.BoolProperty(
        name="Markers",
        description="Import attachment points/markers",
        default=True,
        update=_persist_model_import_settings_update,
    )
    import_bounding_volumes: bpy.props.BoolProperty(
        name="Bounding Volumes",
        description="Import mesh bounding volumes",
        default=False,
        update=_persist_model_import_settings_update,
    )
    import_simbox: bpy.props.BoolProperty(
        name="SimBox",
        description="Import simulation bounding box from .simbox file",
        default=False,
        update=_persist_model_import_settings_update,
    )
    import_coverbox: bpy.props.BoolProperty(
        name="CoverBox",
        description="Import cover bounding box from .coverbox file",
        default=False,
        update=_persist_model_import_settings_update,
    )
    smoothing: bpy.props.EnumProperty(
        name="Smoothing",
        description="How to handle mesh smoothing",
        items=[
            ("NONE", "None", "No smoothing - flat shaded"),
            ("SMOOTH_GROUPS", "Smoothing Groups", "Apply smoothing groups from model data"),
            ("NORMALS", "Normals", "Import and apply custom normals from model"),
        ],
        default="NORMALS",
        update=_persist_model_import_settings_update,
    )
    reset_scene: bpy.props.BoolProperty(
        name="Reset Scene",
        description="Clear scene before importing",
        default=False,
        update=_persist_model_import_settings_update,
    )
    save_scene: bpy.props.BoolProperty(
        name="Save Scene",
        description="Save scene after importing",
        default=False,
        update=_persist_model_import_settings_update,
    )
    merge: bpy.props.BoolProperty(
        name="Merge",
        description="Merge with existing skeleton and meshes",
        default=False,
        update=_persist_model_import_settings_update,
    )
    group_meshes: bpy.props.BoolProperty(
        name="Group Meshes",
        description="Group meshes by mesh group and LOD level",
        default=True,
        update=_persist_model_import_settings_update,
    )
    weld_vertices: bpy.props.BoolProperty(
        name="Weld Vertices",
        description="Weld vertices at same position",
        default=False,
        update=_persist_model_import_settings_update,
    )

    def execute(self, context):
        _store_persisted_model_import_settings(self, context)
        importer = _get_importer_class()(self.filepath, _build_import_options(self))
        result = importer.import_model()

        if self.save_scene and result == {"FINISHED"}:
            blend_path = os.path.splitext(self.filepath)[0] + ".blend"
            bpy.ops.wm.save_as_mainfile(filepath=blend_path)

        return result

    def invoke(self, context, event):
        _apply_persisted_model_import_settings(self, context)
        set_file_browser_start(self, context)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Import:", icon="IMPORT")
        col = box.column(align=True)
        col.prop(self, "import_meshes")
        col.prop(self, "import_materials")
        col.prop(self, "import_bones")
        col.prop(self, "import_markers")
        col.prop(self, "import_bounding_volumes")
        col.prop(self, "import_simbox")
        col.prop(self, "import_coverbox")

        box = layout.box()
        box.label(text="Smoothing:", icon="MOD_SMOOTH")
        box.prop(self, "smoothing", text="")

        box = layout.box()
        box.label(text="Options:", icon="PREFERENCES")
        col = box.column(align=True)
        col.prop(self, "reset_scene")
        col.prop(self, "save_scene")
        col.prop(self, "merge")
        col.prop(self, "group_meshes")
        col.prop(self, "weld_vertices")


def menu_func_import(self, context):
    self.layout.operator(DOW2_OT_import_model.bl_idname, text="DoW2 Model (.model)")


def register():
    bpy.utils.register_class(DOW2_OT_import_model)


def unregister():
    bpy.utils.unregister_class(DOW2_OT_import_model)


__all__ = [
    "DOW2_OT_import_model",
    "menu_func_import",
    "register",
    "unregister",
]