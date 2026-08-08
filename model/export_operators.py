import bpy
import os

from ..utils import load_persisted_settings, store_persisted_settings
from . import utils as model_utils
from .export_utils import (
    DAMAGE_STATE_ITEMS,
    ExportValidationError,
    assign_default_materials_to_missing_slots,
    export_options_from_dict,
    get_or_create_default_material,
    is_relic_material,
    validate_materials_for_export,
)


_PENDING_EXPORT_SCENE_KEYS = (
    "_dow2_export_filepath",
    "_dow2_export_mat_warnings",
    "_dow2_export_meshes_without_mats",
    "_dow2_export_options",
)
_MODEL_EXPORT_SETTINGS_ATTR = "model_export_settings_json"


def _get_exporter_class():
    from .exporter import DoW2ModelExporter

    return DoW2ModelExporter


def _build_export_options_payload(operator) -> dict:
    return {
        "export_materials": operator.export_materials,
        "export_bones": operator.export_bones,
        "export_markers": operator.export_markers,
        "export_rest_pose": operator.export_rest_pose,
        "apply_bone_limit": operator.apply_bone_limit,
        "combine_same_material_meshes": operator.combine_same_material_meshes,
        "apply_material_if_missing": operator.apply_material_if_missing,
        "damage_state_healthy": operator.damage_state_healthy,
        "damage_state_light_damage": operator.damage_state_light_damage,
        "damage_state_heavy_damage": operator.damage_state_heavy_damage,
        "damage_state_wreck": operator.damage_state_wreck,
        "export_damage_state_var": operator.export_damage_state_var,
        "export_health_var": operator.export_health_var,
        "export_simbox": operator.export_simbox,
        "export_coverbox": operator.export_coverbox,
        # "export_existing_bvols": operator.export_existing_bvols,
    }


def _run_export(filepath: str, options_dict: dict):
    exporter = _get_exporter_class()(filepath, export_options_from_dict(options_dict))
    return exporter.export_model()


def _run_export_with_reporting(operator, filepath: str, options_dict: dict):
    try:
        exporter = _get_exporter_class()(filepath, export_options_from_dict(options_dict))
        result = exporter.export_model()
        warnings = getattr(exporter, "warnings", [])
        if warnings:
            preview = "; ".join(warnings[:3])
            if len(warnings) > 3:
                preview += f"; ... {len(warnings) - 3} more"
            operator.report({'WARNING'}, preview)
        return result
    except ExportValidationError as exc:
        operator.report({'ERROR'}, str(exc))
        return {'CANCELLED'}


def _cleanup_pending_export(scene: bpy.types.Scene):
    for key in _PENDING_EXPORT_SCENE_KEYS:
        if key in scene:
            del scene[key]


def _apply_persisted_model_export_settings(operator, context) -> bool:
    operator._is_loading_persisted_model_export_settings = True
    try:
        payload = load_persisted_settings(context, _MODEL_EXPORT_SETTINGS_ATTR)
        for key, value in payload.items():
            if hasattr(operator, key):
                setattr(operator, key, value)
        return bool(payload)
    finally:
        operator._is_loading_persisted_model_export_settings = False


def _store_persisted_model_export_settings(operator, context):
    store_persisted_settings(context, _MODEL_EXPORT_SETTINGS_ATTR, _build_export_options_payload(operator))


def _persist_model_export_settings_update(operator, context):
    if getattr(operator, "_is_loading_persisted_model_export_settings", False):
        return
    _store_persisted_model_export_settings(operator, context)


class DOW2_OT_export_model(bpy.types.Operator):
    """Export Dawn of War 2 .Model"""

    bl_idname = "export_scene.dow2_model"
    bl_label = "Export DoW2 Model"
    bl_options = {"REGISTER"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.model", options={"HIDDEN"})
    export_materials: bpy.props.BoolProperty(name="Materials", default=True, update=_persist_model_export_settings_update)
    export_bones: bpy.props.BoolProperty(name="Bones", default=True, update=_persist_model_export_settings_update)
    export_markers: bpy.props.BoolProperty(name="Markers", default=True, update=_persist_model_export_settings_update)
    export_rest_pose: bpy.props.BoolProperty(
        name="Export in Rest Pose",
        description="Export bind/rest skeleton and undeformed mesh instead of the current posed frame",
        default=False,
        update=_persist_model_export_settings_update,
    )
    apply_bone_limit: bpy.props.BoolProperty(
        name="Apply 54 Bone Limit",
        description="Splits a mesh with more than 54 bones into multiple meshes to be compatible with DoW2's skin limits",
        default=True,
        update=_persist_model_export_settings_update,
    )
    combine_same_material_meshes: bpy.props.BoolProperty(
        name="Combine Same Material Meshes",
        description="Combine meshes that export identical DoW2 material properties without exceeding the 54-bone skin limit",
        default=False,
        update=_persist_model_export_settings_update,
    )
    apply_material_if_missing: bpy.props.BoolProperty(
        name="Apply Material If Missing",
        description="Assign a unique default DoW2 unit material to any mesh material slot that is empty before export",
        default=False,
        update=_persist_model_export_settings_update,
    )
    damage_state_healthy: bpy.props.EnumProperty(
        name="Healthy",
        description="Mesh group to use for healthy damage state",
        items=DAMAGE_STATE_ITEMS,
        default='healthy',
        update=_persist_model_export_settings_update,
    )
    damage_state_light_damage: bpy.props.EnumProperty(
        name="Light Damage",
        description="Mesh group to use for light_damage damage state",
        items=DAMAGE_STATE_ITEMS,
        default='light_damage',
        update=_persist_model_export_settings_update,
    )
    damage_state_heavy_damage: bpy.props.EnumProperty(
        name="Heavy Damage",
        description="Mesh group to use for heavy_damage damage state",
        items=DAMAGE_STATE_ITEMS,
        default='heavy_damage',
        update=_persist_model_export_settings_update,
    )
    damage_state_wreck: bpy.props.EnumProperty(
        name="Wreck",
        description="Mesh group to use for wreck damage state",
        items=DAMAGE_STATE_ITEMS,
        default='wreck',
        update=_persist_model_export_settings_update,
    )
    export_damage_state_var: bpy.props.BoolProperty(
        name="damage_state",
        description="Export damage_state state machine to data table",
        default=True,
        update=_persist_model_export_settings_update,
    )
    export_health_var: bpy.props.BoolProperty(
        name="health",
        description="Export health variable to data table",
        default=True,
        update=_persist_model_export_settings_update,
    )
    export_simbox: bpy.props.BoolProperty(
        name="Sim Box",
        description="Export SIMBOX dummy object as .simbox lua file",
        default=False,
        update=_persist_model_export_settings_update,
    )
    export_coverbox: bpy.props.BoolProperty(
        name="Cover Box",
        description="Export COVERBOX dummy object as .coverbox lua file",
        default=False,
        update=_persist_model_export_settings_update,
    )
    # export_existing_bvols: bpy.props.BoolProperty(
    #     name="Export Existing BVOLs",
    #     description="Export imported BVOL_ bounding volume objects instead of recomputing from mesh vertices",
    #     default=False,
    #     update=_persist_model_export_settings_update,
    # )
    check_existing: bpy.props.BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={'HIDDEN'},
    )

    def execute(self, context):
        _store_persisted_model_export_settings(self, context)

        if self.check_existing and self.filepath and os.path.exists(self.filepath):
            self.report({'WARNING'}, f"File already exists: {self.filepath}")
            return {'CANCELLED'}

        if self.apply_material_if_missing:
            assigned_count = assign_default_materials_to_missing_slots(unique_per_mesh=True)
            if assigned_count:
                self.report({'INFO'}, f"Assigned unique default material to {assigned_count} missing material slot(s)")

        if self.export_materials:
            warnings, meshes_without_mats = validate_materials_for_export()
            if warnings:
                context.scene["_dow2_export_filepath"] = self.filepath
                context.scene["_dow2_export_mat_warnings"] = warnings
                context.scene["_dow2_export_meshes_without_mats"] = [obj.name for obj in meshes_without_mats]
                context.scene["_dow2_export_options"] = _build_export_options_payload(self)
                bpy.ops.dow2.export_material_warning('INVOKE_DEFAULT')
                return {'CANCELLED'}

        return self._do_export(context)

    def _do_export(self, context):
        return _run_export_with_reporting(self, self.filepath, _build_export_options_payload(self))

    def invoke(self, context, event):
        has_persisted_settings = _apply_persisted_model_export_settings(self, context)

        model_name = str(context.scene.get("dow2_model_name") or "").strip()
        simbox = model_utils.find_bounding_box_object(context.scene, "simbox", model_name)
        coverbox = model_utils.find_bounding_box_object(context.scene, "coverbox", model_name)

        if not has_persisted_settings and simbox and simbox.type in {'EMPTY', 'MESH'}:
            self.export_simbox = True
        if not has_persisted_settings and coverbox and coverbox.type in {'EMPTY', 'MESH'}:
            self.export_coverbox = True

        scene = context.scene
        if not has_persisted_settings and "dow2_damage_states" in scene:
            damage_states = scene["dow2_damage_states"]
            if isinstance(damage_states, dict):
                if "healthy" in damage_states:
                    self.damage_state_healthy = damage_states["healthy"]
                if "light_damage" in damage_states:
                    self.damage_state_light_damage = damage_states["light_damage"]
                if "heavy_damage" in damage_states:
                    self.damage_state_heavy_damage = damage_states["heavy_damage"]
                if "wreck" in damage_states:
                    self.damage_state_wreck = damage_states["wreck"]

        if not has_persisted_settings and "dow2_export_damage_state" in scene:
            self.export_damage_state_var = scene["dow2_export_damage_state"]
        if not has_persisted_settings and "dow2_export_health" in scene:
            self.export_health_var = scene["dow2_export_health"]

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Damage States")
        col = box.column(align=True)
        col.prop(self, "damage_state_healthy")
        col.prop(self, "damage_state_light_damage")
        col.prop(self, "damage_state_heavy_damage")
        col.prop(self, "damage_state_wreck")

        row = layout.row()
        box1 = row.box()
        box1.label(text="Data Table")
        col1 = box1.column(align=True)
        col1.prop(self, "export_damage_state_var")
        col1.prop(self, "export_health_var")

        box2 = row.box()
        box2.label(text="Bounding Boxes")
        col2 = box2.column(align=True)

        model_name = str(context.scene.get("dow2_model_name") or "").strip()
        simbox = model_utils.find_bounding_box_object(context.scene, "simbox", model_name)
        coverbox = model_utils.find_bounding_box_object(context.scene, "coverbox", model_name)

        row_sim = col2.row()
        row_sim.prop(self, "export_simbox")
        row_sim.enabled = simbox is not None and simbox.type in {'EMPTY', 'MESH'}

        row_cover = col2.row()
        row_cover.prop(self, "export_coverbox")
        row_cover.enabled = coverbox is not None and coverbox.type in {'EMPTY', 'MESH'}

        # bvol_count = len([o for o in bpy.data.objects if o.name.startswith("BVOL_")])
        # row_bvol = col2.row()
        # row_bvol.prop(self, "export_existing_bvols")
        # if bvol_count == 0:
        #     row_bvol.enabled = False
        #     row_bvol.label(text="(no BVOL_ objects in scene)")

        box = layout.box()
        box.label(text="Export Options")
        col = box.column(align=True)
        col.prop(self, "export_materials")
        col.prop(self, "export_bones")
        col.prop(self, "export_markers")
        col.prop(self, "export_rest_pose")
        col.prop(self, "apply_bone_limit")
        col.prop(self, "combine_same_material_meshes")
        col.prop(self, "apply_material_if_missing")

    def check(self, context):
        return True


class DOW2_OT_export_material_warning(bpy.types.Operator):
    """Warning dialog for meshes without valid Relic materials."""

    bl_idname = "dow2.export_material_warning"
    bl_label = "Material Warning"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        return self._do_export(context, assign_defaults=True)

    def cancel(self, context):
        _cleanup_pending_export(context.scene)
        return {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        layout = self.layout

        warnings = context.scene.get("_dow2_export_mat_warnings", [])
        mesh_names = context.scene.get("_dow2_export_meshes_without_mats", [])

        row = layout.row()
        row.label(text="Material Warnings", icon='ERROR')

        box = layout.box()
        for warning in warnings[:10]:
            box.label(text=warning)
        if len(warnings) > 10:
            box.label(text=f"... and {len(warnings) - 10} more")

        layout.separator()
        layout.label(text=f"Found {len(mesh_names)} mesh(es) without valid Relic materials.")
        layout.label(text="Choose an action:")

        col = layout.column()
        col.label(text="- Click OK to assign default material and export")
        col.label(text="- Click Cancel to abort and fix materials manually")

        layout.separator()
        row = layout.row()
        row.operator("dow2.export_skip_materials", text="Export Anyway (Skip Material Validation)", icon='EXPORT')

    def _do_export(self, context, assign_defaults=False):
        filepath = context.scene.get("_dow2_export_filepath", "")
        options_dict = context.scene.get("_dow2_export_options", {})

        if not filepath:
            self.report({'ERROR'}, "No export path found")
            _cleanup_pending_export(context.scene)
            return {'CANCELLED'}

        if assign_defaults:
            mesh_names = context.scene.get("_dow2_export_meshes_without_mats", [])
            default_mat = get_or_create_default_material()
            assigned_count = 0
            for mesh_name in mesh_names:
                obj = bpy.data.objects.get(mesh_name)
                if obj and obj.type == 'MESH':
                    if not obj.data.materials:
                        obj.data.materials.append(default_mat)
                        assigned_count += 1
                    else:
                        for index, mat in enumerate(obj.data.materials):
                            if mat is None or not is_relic_material(mat):
                                obj.data.materials[index] = default_mat
                                assigned_count += 1
            self.report({'INFO'}, f"Assigned default material to {assigned_count} material slots")

        result = _run_export_with_reporting(self, filepath, options_dict)
        _cleanup_pending_export(context.scene)
        return result


class DOW2_OT_export_skip_materials(bpy.types.Operator):
    """Export without fixing material issues."""

    bl_idname = "dow2.export_skip_materials"
    bl_label = "Export Anyway"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        filepath = context.scene.get("_dow2_export_filepath", "")
        options_dict = context.scene.get("_dow2_export_options", {})

        if not filepath:
            self.report({'ERROR'}, "No export path found")
            return {'CANCELLED'}

        result = _run_export_with_reporting(self, filepath, options_dict)
        _cleanup_pending_export(context.scene)
        return result


class DOW2_OT_confirm_overwrite(bpy.types.Operator):
    """Confirm file overwrite."""

    bl_idname = "dow2.confirm_overwrite"
    bl_label = "Confirm Overwrite"
    bl_options = {'INTERNAL'}

    filepath: bpy.props.StringProperty()

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"File '{os.path.basename(self.filepath)}' already exists.")
        layout.label(text="Do you want to overwrite it?")


def menu_func_export(self, context):
    self.layout.operator(DOW2_OT_export_model.bl_idname, text="DoW2 Model (.model)")


def register():
    bpy.utils.register_class(DOW2_OT_export_model)
    bpy.utils.register_class(DOW2_OT_export_material_warning)
    bpy.utils.register_class(DOW2_OT_export_skip_materials)
    bpy.utils.register_class(DOW2_OT_confirm_overwrite)


def unregister():
    bpy.utils.unregister_class(DOW2_OT_confirm_overwrite)
    bpy.utils.unregister_class(DOW2_OT_export_skip_materials)
    bpy.utils.unregister_class(DOW2_OT_export_material_warning)
    bpy.utils.unregister_class(DOW2_OT_export_model)


__all__ = [
    "DOW2_OT_confirm_overwrite",
    "DOW2_OT_export_material_warning",
    "DOW2_OT_export_model",
    "DOW2_OT_export_skip_materials",
    "menu_func_export",
    "register",
    "unregister",
]