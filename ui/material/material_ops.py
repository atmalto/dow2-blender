import os

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator

from ...material.definitions import DEFAULT_MATERIAL_NAME
from ...material.presets import SHADER_PRESETS, SHADER_PRESET_CONFIG, SHADER_PRESET_LABELS
from ...material.service import configure_relic_material, is_relic_material


class DOW2_OT_load_shader(Operator):
    """Load a DoW2 shader file"""

    bl_idname = "dow2.load_shader"
    bl_label = "Load Shader"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(
        name="Shader Path",
        description="Path to .shader file",
        subtype='FILE_PATH',
    )

    filter_glob: StringProperty(
        default="*.shader",
        options={'HIDDEN'},
    )

    def execute(self, context):
        mat = context.object.active_material
        if not mat:
            self.report({'ERROR'}, "No material selected")
            return {'CANCELLED'}

        shader_vars = self.parse_shader(self.filepath)

        configure_relic_material(
            context,
            mat,
            shader_name=os.path.splitext(os.path.basename(self.filepath))[0],
            shader_path=self.filepath,
            shader_vars=shader_vars,
        )

        self.report({'INFO'}, f"Loaded shader with {len(shader_vars)} variables")
        return {'FINISHED'}

    def invoke(self, context, event):
        prefs = context.preferences.addons.get('dow2_tools')
        if prefs:
            dow2_path = prefs.preferences.dow2_path
            shaders_path = os.path.join(dow2_path, "Codex", "Data", "shaders")
            if os.path.exists(shaders_path):
                self.filepath = shaders_path + os.sep

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def parse_shader(self, filepath):
        variables = []
        if not os.path.exists(filepath):
            return variables

        try:
            with open(filepath, 'r') as handle:
                name = None
                var_type = None
                for line in handle:
                    line = line.strip()
                    if '=' not in line:
                        continue

                    parts = line.split('=', 1)
                    key = parts[0].strip().strip('"')
                    value = parts[1].strip().strip('",')

                    if key == "name":
                        name = value
                    elif key == "type":
                        var_type = value

                    if name and var_type:
                        variables.append(name)
                        name = None
                        var_type = None
        except Exception as exc:
            print(f"Error parsing shader: {exc}")

        return variables


class DOW2_OT_create_relic_material(Operator):
    """Create a new DoW2 Relic Material with shader preset"""

    bl_idname = "dow2.create_relic_material"
    bl_label = "Create Relic Material"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty(
        name="Material Name",
        default="relic.material.new_material",
    )

    shader_preset: EnumProperty(
        name="Shader",
        description="Select a shader preset to auto-populate material properties",
        items=SHADER_PRESETS,
        default="NONE",
    )

    def execute(self, context):
        mat = bpy.data.materials.new(name=self.material_name)
        shader_name = self.shader_preset if self.shader_preset != "NONE" else ""
        shader_vars = []
        param_overrides = {}
        if self.shader_preset in SHADER_PRESET_CONFIG:
            config = SHADER_PRESET_CONFIG[self.shader_preset]
            shader_vars = list(config.get("textures", []))
            param_overrides.update(config.get("params", {}))

        configure_relic_material(
            context,
            mat,
            shader_name=shader_name,
            shader_path="",
            shader_vars=shader_vars,
            param_overrides=param_overrides,
        )

        if context.object and context.object.type == 'MESH':
            if context.object.data.materials:
                context.object.data.materials[0] = mat
            else:
                context.object.data.materials.append(mat)

        preset_name = SHADER_PRESET_LABELS.get(self.shader_preset, "custom")
        self.report({'INFO'}, f"Created material: {self.material_name} ({preset_name})")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "material_name")
        layout.prop(self, "shader_preset")

        if self.shader_preset in SHADER_PRESET_CONFIG:
            config = SHADER_PRESET_CONFIG[self.shader_preset]
            box = layout.box()
            box.label(text="Preset includes:", icon="INFO")

            textures = config.get("textures", [])
            if textures:
                box.label(text=f"Textures: {', '.join(textures[:4])}")
                if len(textures) > 4:
                    box.label(text=f"          {', '.join(textures[4:])}")


class DOW2_OT_toggle_bool_param(Operator):
    """Toggle a boolean parameter"""

    bl_idname = "dow2.toggle_bool_param"
    bl_label = "Toggle Parameter"
    bl_options = {'REGISTER', 'UNDO'}

    param_name: StringProperty()

    def execute(self, context):
        mat = context.object.active_material
        if mat:
            prop_name = f"dow2_{self.param_name}"
            current = mat.get(prop_name, False)
            mat[prop_name] = not current
        return {'FINISHED'}


def get_or_create_default_material() -> bpy.types.Material:
    mat = bpy.data.materials.get(DEFAULT_MATERIAL_NAME)
    if mat is None:
        mat = bpy.data.materials.new(name=DEFAULT_MATERIAL_NAME)
        configure_relic_material(
            bpy.context,
            mat,
            shader_name="dow2_unit",
            shader_path="",
            shader_vars=SHADER_PRESET_CONFIG.get("dow2_unit", {}).get("textures", []),
            param_overrides={
                "useLighting": True,
                "useDepthTest": True,
                "glossValue": 0.5,
            },
        )

    return mat


__all__ = [
    "DOW2_OT_create_relic_material",
    "DOW2_OT_load_shader",
    "DOW2_OT_toggle_bool_param",
    "get_or_create_default_material",
    "is_relic_material",
]