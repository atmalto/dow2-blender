import importlib.util
import os

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator, Panel

from ..map_io.importer import MapImportOptions, import_scenario_map
from ..utils import clear_scene


_SCENE_GRAPH_HELPERS = None


def _get_scene_graph_helpers():
    global _SCENE_GRAPH_HELPERS
    if _SCENE_GRAPH_HELPERS is not None:
        return _SCENE_GRAPH_HELPERS

    addon_root = os.path.dirname(os.path.dirname(__file__))
    helper_path = os.path.join(addon_root, "utils", "scene_graph.py")
    if not os.path.exists(helper_path):
        return None

    spec = importlib.util.spec_from_file_location("dow2_scene_graph_helpers", helper_path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _SCENE_GRAPH_HELPERS = module
    return _SCENE_GRAPH_HELPERS


def _available_properties_contexts(area: bpy.types.Area) -> set:
    spaces = getattr(area, "spaces", None)
    if spaces is None or spaces.active is None:
        return set()

    context_property = spaces.active.bl_rna.properties.get("context")
    if context_property is None:
        return set()

    return {item.identifier for item in context_property.enum_items}


def _set_properties_context(context, target_context: str, fallback_contexts=()):
    screen = getattr(context, "screen", None)
    if screen is None:
        return False

    for area in screen.areas:
        if area.type != 'PROPERTIES':
            continue

        available = _available_properties_contexts(area)
        for candidate in (target_context, *fallback_contexts):
            if candidate not in available:
                continue
            try:
                area.spaces.active.context = candidate
                return True
            except (TypeError, ValueError):
                continue
        return False

    return False


def _defer_properties_context(target_context: str, fallback_contexts=()):
    def _apply():
        _set_properties_context(bpy.context, target_context, fallback_contexts)
        return None

    bpy.app.timers.register(_apply, first_interval=0.01)


def _get_object_properties_context(obj: bpy.types.Object):
    if obj.type == 'ARMATURE':
        return 'DATA', ('OBJECT', 'CONSTRAINT')
    if obj.type == 'MESH':
        return 'MODIFIER', ('OBJECT', 'DATA')
    return 'OBJECT', ('DATA',)


class DOW2_OT_scene_graph_select_object(Operator):
    """Select an object from the DoW2 scene graph"""

    bl_idname = "dow2.scene_graph_select_object"
    bl_label = "Select Scene Graph Object"
    bl_options = {'REGISTER', 'UNDO'}

    object_name: StringProperty()

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if obj is None:
            self.report({'ERROR'}, f"Object not found: {self.object_name}")
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        target_context, fallback_contexts = _get_object_properties_context(obj)
        _set_properties_context(context, target_context, fallback_contexts)
        _defer_properties_context(target_context, fallback_contexts)
        return {'FINISHED'}


class DOW2_OT_scene_graph_select_material(Operator):
    """Select object and focus one relic material"""

    bl_idname = "dow2.scene_graph_select_material"
    bl_label = "Select Scene Graph Material"
    bl_options = {'REGISTER', 'UNDO'}

    object_name: StringProperty()
    material_index: IntProperty(default=0)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Material owner mesh not found")
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        obj.active_material_index = max(0, min(self.material_index, max(0, len(obj.material_slots) - 1)))
        _set_properties_context(context, 'MATERIAL', ('DATA', 'OBJECT'))
        _defer_properties_context('MATERIAL', ('DATA', 'OBJECT'))
        return {'FINISHED'}


class DOW2_OT_clear_scene_graph_scene(Operator):
    """Clear scene objects and orphaned data"""

    bl_idname = "dow2.clear_scene_graph_scene"
    bl_label = "Clear Scene"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.scene is not None

    def execute(self, context):
        clear_scene(include_collections=True)
        self.report({'INFO'}, "Scene cleared")
        return {'FINISHED'}


class DOW2_OT_scene_graph_pick_map_path(Operator, ImportHelper):
    """Select a DoW2 scenario file for map import"""

    bl_idname = "dow2.scene_graph_pick_map_path"
    bl_label = "Select Scenario"
    bl_options = {'REGISTER'}

    filename_ext = ".scenario"
    filter_glob: StringProperty(default="*.scenario", options={'HIDDEN'})

    def execute(self, context):
        context.scene.dow2_map_import_path = self.filepath
        return {'FINISHED'}


class DOW2_OT_scene_graph_import_map(Operator):
    """Import a DoW2 scenario map into the current scene"""

    bl_idname = "dow2.scene_graph_import_map"
    bl_label = "Import Scenario Map"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.scene is not None

    def execute(self, context):
        scene = context.scene
        path = str(getattr(scene, "dow2_map_import_path", "")).strip()
        if not path:
            self.report({'ERROR'}, "Choose a .scenario file first")
            return {'CANCELLED'}
        try:
            result = import_scenario_map(
                context,
                path,
                MapImportOptions(
                    import_mesh=bool(scene.dow2_map_import_mesh),
                    import_markers=bool(scene.dow2_map_import_markers),
                    import_nav_plane=bool(scene.dow2_map_import_nav_plane),
                    import_textures=bool(scene.dow2_map_import_textures),
                    import_objects=bool(scene.dow2_map_import_objects),
                ),
            )
        except Exception as exc:
            self.report({'ERROR'}, f"Map import failed: {exc}")
            return {'CANCELLED'}
        scene.dow2_map_last_import_name = result.map_name
        scene.dow2_map_last_import_collection = result.collection_name
        scene.dow2_map_last_import_has_terrain = bool(result.terrain_object_name)
        scene.dow2_map_last_import_terrain_object = result.terrain_object_name or ""
        scene.dow2_map_last_import_marker_count = int(result.marker_count)
        scene.dow2_map_last_import_has_nav = bool(result.nav_object_name)
        scene.dow2_map_last_import_nav_object = result.nav_object_name or ""
        scene.dow2_map_last_import_object_count = int(result.object_count)
        self.report(
            {'INFO'},
            f"Imported {result.map_name}: markers={result.marker_count}, objects={result.object_count}, nav={'yes' if result.nav_object_name else 'no'}",
        )
        return {'FINISHED'}


class DOW2_PT_map_io(Panel):
    """DoW2 scenario map import (experimental)"""

    bl_label = "Map I/O (Experimental)"
    bl_idname = "DOW2_PT_map_io"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_order = 65
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "dow2_map_import_path", text="Scenario")
        row = layout.row(align=True)
        row.operator("dow2.scene_graph_pick_map_path", icon='FILE_FOLDER')
        row.operator("dow2.scene_graph_import_map", icon='IMPORT')

        options = layout.box()
        options.label(text="Import Selection")
        col = options.column(align=True)
        col.prop(scene, "dow2_map_import_mesh")
        col.prop(scene, "dow2_map_import_markers")
        col.prop(scene, "dow2_map_import_nav_plane")
        col.prop(scene, "dow2_map_import_textures")
        col.prop(scene, "dow2_map_import_objects")

        last_map = str(getattr(scene, "dow2_map_last_import_name", "")).strip()
        if last_map:
            summary = layout.box()
            summary.label(text="Last Import", icon='INFO')
            summary.label(text=f"Map: {last_map}")
            summary.label(text=f"Collection: {scene.dow2_map_last_import_collection}")
            summary.label(text=f"Terrain: {'yes' if scene.dow2_map_last_import_has_terrain else 'no'}")
            terrain_name = str(getattr(scene, "dow2_map_last_import_terrain_object", "")).strip()
            if terrain_name:
                terrain_op = summary.operator("dow2.scene_graph_select_object", text="Select Terrain", icon='MESH_GRID')
                terrain_op.object_name = terrain_name
            summary.label(text=f"Markers: {scene.dow2_map_last_import_marker_count}")
            summary.label(text=f"Nav: {'yes' if scene.dow2_map_last_import_has_nav else 'no'}")
            nav_name = str(getattr(scene, "dow2_map_last_import_nav_object", "")).strip()
            if nav_name:
                nav_op = summary.operator("dow2.scene_graph_select_object", text="Select Nav", icon='MESH_PLANE')
                nav_op.object_name = nav_name
            summary.label(text=f"Object Proxies: {scene.dow2_map_last_import_object_count}")


class DOW2_PT_scene_graph(Panel):
    """DoW2-aware hierarchy summary"""

    bl_label = "DoW2 Scene Graph"
    bl_idname = "DOW2_PT_scene_graph"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_order = 70
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        helpers = _get_scene_graph_helpers()

        if helpers is None:
            layout.label(text="Scene graph helpers unavailable", icon='ERROR')
            return

        layout.operator("dow2.clear_scene_graph_scene", icon='TRASH')

        header, body = layout.panel("dow2_scene_graph_skeleton", default_closed=False)
        header.label(text="Skeleton", icon='ARMATURE_DATA')
        if body is not None:
            armature = helpers.find_active_armature(context.scene)
            if armature is None:
                body.label(text="No armature found", icon='INFO')
            else:
                op = body.operator("dow2.scene_graph_select_object", text=armature.name, icon='ARMATURE_DATA')
                op.object_name = armature.name
                for bone in armature.data.bones:
                    bone_row = body.row()
                    bone_row.label(text=bone.name, icon='BONE_DATA')

        header, body = layout.panel("dow2_scene_graph_geometry", default_closed=False)
        header.label(text="Meshes, Materials", icon='MESH_DATA')
        if body is not None:
            grouped = helpers.collect_meshes_by_damage_state(context.scene)
            has_geometry = False
            for state_name in helpers.DAMAGE_STATES:
                lod_map = grouped.get(state_name, {})
                if not lod_map:
                    continue
                has_geometry = True
                state_box = body.box()
                state_box.label(text=state_name)
                for lod_name, meshes in lod_map.items():
                    lod_box = state_box.box()
                    lod_box.label(text=lod_name, icon='OUTLINER_COLLECTION')
                    for obj in sorted(meshes, key=lambda item: item.name.lower()):
                        row = lod_box.row(align=True)
                        op = row.operator("dow2.scene_graph_select_object", text=obj.name, icon='MESH_DATA')
                        op.object_name = obj.name

                        has_relic = False
                        for index, slot in enumerate(obj.material_slots):
                            mat = slot.material
                            if not helpers.is_relic_material(mat):
                                continue
                            has_relic = True
                            shader = helpers.get_material_shader(mat)
                            mat_row = lod_box.row(align=True)
                            mat_op = mat_row.operator(
                                "dow2.scene_graph_select_material",
                                text=f"{mat.name} [{shader}]" if shader else mat.name,
                                icon='MATERIAL',
                            )
                            mat_op.object_name = obj.name
                            mat_op.material_index = index

                        if not has_relic:
                            row.label(text="", icon='ERROR')

            if not has_geometry:
                body.label(text="No mesh hierarchy found", icon='INFO')

        header, body = layout.panel("dow2_scene_graph_markers", default_closed=True)
        header.label(text="Markers, Cover", icon='EMPTY_AXIS')
        if body is not None:
            markers = helpers.collect_markers_and_cover(context.scene)
            if not markers:
                body.label(text="No markers or cover objects", icon='INFO')
            for marker in markers:
                op = body.operator("dow2.scene_graph_select_object", text=marker.name, icon='EMPTY_AXIS')
                op.object_name = marker.name

        header, body = layout.panel("dow2_scene_graph_physics", default_closed=True)
        header.label(text="Physics Hulls", icon='MESH_ICOSPHERE')
        if body is not None:
            physics_hulls = helpers.collect_physics_hulls(context.scene)
            has_hulls = False
            for state_name in helpers.DAMAGE_STATES:
                lod_map = physics_hulls.get(state_name, {})
                if not lod_map:
                    continue
                has_hulls = True
                state_box = body.box()
                state_box.label(text=state_name)
                for lod_name, meshes in lod_map.items():
                    lod_box = state_box.box()
                    lod_box.label(text=lod_name, icon='OUTLINER_COLLECTION')
                    for obj in sorted(meshes, key=lambda item: item.name.lower()):
                        row = lod_box.row(align=True)
                        op = row.operator("dow2.scene_graph_select_object", text=obj.name, icon='MESH_ICOSPHERE')
                        op.object_name = obj.name
                        row.label(text=obj.get("dow2_physics_body_name", obj.name))

            if not has_hulls:
                body.label(text="No generated physics hulls", icon='INFO')

        header, body = layout.panel("dow2_scene_graph_collision", default_closed=True)
        header.label(text="Collision Meshes", icon='MESH_CUBE')
        if body is not None:
            collisions = helpers.collect_collision_meshes(context.scene)
            if not collisions:
                body.label(text="No collision collections", icon='INFO')
            for collection_name, meshes in sorted(collisions.items(), key=lambda item: item[0].lower()):
                box = body.box()
                box.label(text=collection_name, icon='OUTLINER_COLLECTION')
                for obj in sorted(meshes, key=lambda item: item.name.lower()):
                    op = box.operator("dow2.scene_graph_select_object", text=obj.name, icon='MESH_CUBE')
                    op.object_name = obj.name


SCENE_GRAPH_CLASSES = [
    DOW2_OT_scene_graph_select_object,
    DOW2_OT_scene_graph_select_material,
    DOW2_OT_clear_scene_graph_scene,
    DOW2_OT_scene_graph_pick_map_path,
    DOW2_OT_scene_graph_import_map,
    DOW2_PT_map_io,
    DOW2_PT_scene_graph,
]


def register_scene_graph_state():
    bpy.types.Scene.dow2_map_import_path = StringProperty(
        name="Scenario Path",
        description="Path to the .scenario file to import",
        subtype='FILE_PATH',
        default="",
    )
    bpy.types.Scene.dow2_map_import_mesh = BoolProperty(name="Mesh", default=True)
    bpy.types.Scene.dow2_map_import_markers = BoolProperty(name="Markers", default=True)
    bpy.types.Scene.dow2_map_import_nav_plane = BoolProperty(name="Nav Plane", default=True)
    bpy.types.Scene.dow2_map_import_textures = BoolProperty(name="Textures", default=True)
    bpy.types.Scene.dow2_map_import_objects = BoolProperty(name="Objects", default=True)
    bpy.types.Scene.dow2_map_last_import_name = StringProperty(name="Last Imported Map", default="")
    bpy.types.Scene.dow2_map_last_import_collection = StringProperty(name="Last Imported Collection", default="")
    bpy.types.Scene.dow2_map_last_import_has_terrain = BoolProperty(name="Last Import Terrain", default=False)
    bpy.types.Scene.dow2_map_last_import_terrain_object = StringProperty(name="Last Import Terrain Object", default="")
    bpy.types.Scene.dow2_map_last_import_marker_count = IntProperty(name="Last Import Marker Count", default=0)
    bpy.types.Scene.dow2_map_last_import_has_nav = BoolProperty(name="Last Import Nav", default=False)
    bpy.types.Scene.dow2_map_last_import_nav_object = StringProperty(name="Last Import Nav Object", default="")
    bpy.types.Scene.dow2_map_last_import_object_count = IntProperty(name="Last Import Object Count", default=0)


def unregister_scene_graph_state():
    for attr in (
        "dow2_map_import_path",
        "dow2_map_import_mesh",
        "dow2_map_import_markers",
        "dow2_map_import_nav_plane",
        "dow2_map_import_textures",
        "dow2_map_import_objects",
        "dow2_map_last_import_name",
        "dow2_map_last_import_collection",
        "dow2_map_last_import_has_terrain",
        "dow2_map_last_import_terrain_object",
        "dow2_map_last_import_marker_count",
        "dow2_map_last_import_has_nav",
        "dow2_map_last_import_nav_object",
        "dow2_map_last_import_object_count",
    ):
        if hasattr(bpy.types.Scene, attr):
            delattr(bpy.types.Scene, attr)


__all__ = [
    "DOW2_OT_clear_scene_graph_scene",
    "DOW2_OT_scene_graph_import_map",
    "DOW2_OT_scene_graph_pick_map_path",
    "DOW2_OT_scene_graph_select_material",
    "DOW2_OT_scene_graph_select_object",
    "DOW2_PT_map_io",
    "DOW2_PT_scene_graph",
    "SCENE_GRAPH_CLASSES",
    "register_scene_graph_state",
    "unregister_scene_graph_state",
]