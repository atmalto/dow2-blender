import bpy
from bpy.types import Operator
from bpy.props import IntProperty, EnumProperty, BoolProperty
from mathutils import Vector


DAMAGE_STATE_TEMPLATES = {
    "SINGLE": ["healthy"],
    "SIMPLE": ["healthy", "wreck"],
    "FULL": ["healthy", "light_damage", "heavy_damage", "wreck"],
}


DAMAGE_STATE_ITEMS = [
    ("SINGLE", "Single (Healthy)", "Create only healthy damage state"),
    ("SIMPLE", "Simple (Healthy, Wreck)", "Create healthy and wreck damage states"),
    ("FULL", "Full (Healthy, Light, Heavy, Wreck)", "Create all damage states"),
]


_ORIGINAL_VIEW3D_MT_OBJECT_APPLY_DRAW = None
BOUNDING_BOX_TYPE_PROP = "dow2_bounding_box_type"
BOUNDING_BOX_MODEL_PROP = "dow2_bounding_box_model_name"
BOUNDING_BOX_SOURCE_PROP = "dow2_bounding_box_source"
BOUNDING_BOX_PREFIXES = {
    "simbox": "DoW2_Simbox::",
    "coverbox": "DoW2_Coverbox::",
}
BOUNDING_BOX_COLORS = {
    "simbox": (0.2, 0.45, 1.0, 1.0),
    "coverbox": (1.0, 0.25, 0.25, 1.0),
}


def _find_child_collection(parent: bpy.types.Collection, name: str):
    for child in parent.children:
        if child.name == name or child.name.split(".")[0] == name:
            return child
    return None


def ensure_child_collection(parent: bpy.types.Collection, name: str) -> bpy.types.Collection:
    existing = _find_child_collection(parent, name)
    if existing:
        return existing
    collection = bpy.data.collections.new(name)
    parent.children.link(collection)
    return collection


def iter_armature_markers(armature_obj: bpy.types.Object):
    for obj in bpy.data.objects:
        if obj.type != 'EMPTY':
            continue
        if obj.parent != armature_obj:
            continue
        if obj.parent_type != 'BONE' or not obj.parent_bone:
            continue
        yield obj


def _iter_dow2_armatures(scene: bpy.types.Scene):
    named = bpy.data.objects.get("DoW2_Armature")
    if named is not None and named.type == 'ARMATURE' and named.name in scene.objects:
        yield named
        return

    for obj in scene.objects:
        if obj.type == 'ARMATURE':
            yield obj


def _iter_dow2_marker_like_objects(scene: bpy.types.Scene):
    for obj in scene.objects:
        if obj.type != 'EMPTY':
            continue
        if bool(obj.get("dow2_is_marker", False)):
            yield obj
            continue
        upper = obj.name.upper()
        if "MARKER" in upper or "MRKR" in upper or "COVER" in upper or upper in {"SIMBOX", "COVERBOX"}:
            yield obj


def _bounding_box_prefix(box_type: str) -> str:
    return BOUNDING_BOX_PREFIXES[box_type]


def bounding_box_object_name(box_type: str, model_name: str = "") -> str:
    suffix = str(model_name or "Bounds").strip() or "Bounds"
    return f"{_bounding_box_prefix(box_type)}{suffix}"


def is_bounding_box_object(obj: bpy.types.Object, box_type: str | None = None) -> bool:
    stored_type = str(obj.get(BOUNDING_BOX_TYPE_PROP) or "").strip().lower()
    if box_type is not None:
        if stored_type == box_type:
            return True
        return obj.name.startswith(_bounding_box_prefix(box_type)) or obj.name.lower() in {box_type, box_type.upper().lower()}
    if stored_type in BOUNDING_BOX_PREFIXES:
        return True
    return any(obj.name.startswith(prefix) for prefix in BOUNDING_BOX_PREFIXES.values()) or obj.name.upper() in {"SIMBOX", "COVERBOX"}


def _primary_armature(scene: bpy.types.Scene):
    return next(_iter_dow2_armatures(scene), None)


def _resolve_model_name(scene: bpy.types.Scene, armature_obj: bpy.types.Object | None = None) -> str:
    if armature_obj is not None:
        armature_name = str(armature_obj.get("dow2_model_name") or "").strip()
        if armature_name:
            return armature_name
    scene_name = str(scene.get("dow2_model_name") or "").strip()
    if scene_name:
        return scene_name
    return ""


def find_bounding_box_object(scene: bpy.types.Scene, box_type: str, model_name: str = ""):
    expected_name = bounding_box_object_name(box_type, model_name) if model_name else ""
    for obj in scene.objects:
        if obj.type not in {'MESH', 'EMPTY'}:
            continue
        if expected_name and obj.name == expected_name:
            return obj
        if str(obj.get(BOUNDING_BOX_TYPE_PROP) or "").strip().lower() != box_type:
            continue
        stored_model_name = str(obj.get(BOUNDING_BOX_MODEL_PROP) or "").strip()
        if not model_name or not stored_model_name or stored_model_name == model_name:
            return obj

    legacy_name = box_type.upper()
    return bpy.data.objects.get(legacy_name) or bpy.data.objects.get(box_type)


def _ensure_bounding_box_mesh(name: str) -> bpy.types.Mesh:
    mesh = bpy.data.meshes.get(name)
    if mesh is None:
        mesh = bpy.data.meshes.new(name)
    else:
        mesh.clear_geometry()
    mesh.from_pydata(
        [
            (-1.0, -1.0, -1.0),
            (-1.0, -1.0, 1.0),
            (-1.0, 1.0, -1.0),
            (-1.0, 1.0, 1.0),
            (1.0, -1.0, -1.0),
            (1.0, -1.0, 1.0),
            (1.0, 1.0, -1.0),
            (1.0, 1.0, 1.0),
        ],
        [
            (0, 1), (0, 2), (0, 4),
            (1, 3), (1, 5),
            (2, 3), (2, 6),
            (3, 7),
            (4, 5), (4, 6),
            (5, 7),
            (6, 7),
        ],
        [],
    )
    return mesh


def _ensure_bounding_box_material(box_type: str) -> bpy.types.Material:
    material_name = f"DoW2_{box_type.title()}Material"
    material = bpy.data.materials.get(material_name)
    if material is None:
        material = bpy.data.materials.new(name=material_name)
        material.use_nodes = True
        material.diffuse_color = BOUNDING_BOX_COLORS[box_type]
        if material.node_tree is not None:
            principled = material.node_tree.nodes.get("Principled BSDF")
            if principled is not None:
                principled.inputs["Base Color"].default_value = BOUNDING_BOX_COLORS[box_type]
                principled.inputs["Roughness"].default_value = 1.0
    return material


def _link_bounding_box_object(scene: bpy.types.Scene, obj: bpy.types.Object, armature_obj: bpy.types.Object | None) -> None:
    target_collection = scene.collection
    if armature_obj is not None and armature_obj.users_collection:
        target_collection = armature_obj.users_collection[0]
    if target_collection not in obj.users_collection:
        target_collection.objects.link(obj)


def create_or_update_bounding_box_object(
    scene: bpy.types.Scene,
    box_type: str,
    *,
    model_name: str,
    location: Vector,
    scale: Vector,
    maintain_contour: bool,
    armature_obj: bpy.types.Object | None = None,
    source_path: str = "",
):
    existing = find_bounding_box_object(scene, box_type, model_name)
    object_name = bounding_box_object_name(box_type, model_name)
    mesh_name = f"{object_name}::Mesh"
    mesh = _ensure_bounding_box_mesh(mesh_name)

    if existing is not None and existing.type != 'MESH':
        bpy.data.objects.remove(existing, do_unlink=True)
        existing = None

    obj = existing
    if obj is None:
        obj = bpy.data.objects.new(object_name, mesh)
    else:
        obj.name = object_name
        obj.data = mesh

    _link_bounding_box_object(scene, obj, armature_obj)
    obj.display_type = 'WIRE'
    obj.show_in_front = True
    obj.color = BOUNDING_BOX_COLORS[box_type]
    obj.show_wire = True
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = scale
    material = _ensure_bounding_box_material(box_type)
    if obj.data is not None:
        obj.data.materials.clear()
        obj.data.materials.append(material)
    obj[BOUNDING_BOX_TYPE_PROP] = box_type
    obj[BOUNDING_BOX_MODEL_PROP] = model_name
    obj[BOUNDING_BOX_SOURCE_PROP] = source_path
    obj["maintain_contour"] = maintain_contour
    obj.parent = armature_obj
    obj.parent_type = 'OBJECT' if armature_obj is not None else 'OBJECT'
    return obj


def _iter_meshes_for_bounds(scene: bpy.types.Scene):
    for obj in scene.objects:
        if obj.type != 'MESH':
            continue
        if is_bounding_box_object(obj):
            continue
        yield obj


def mesh_bounds_local(scene: bpy.types.Scene, armature_obj: bpy.types.Object | None = None):
    meshes = list(_iter_meshes_for_bounds(scene))
    if not meshes:
        raise ValueError("no mesh geometry found to fit bounding box")

    inverse = armature_obj.matrix_world.inverted() if armature_obj is not None else None
    minimum = None
    maximum = None
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        for corner in evaluated.bound_box:
            world_corner = evaluated.matrix_world @ Vector(corner)
            local_corner = inverse @ world_corner if inverse is not None else world_corner
            if minimum is None:
                minimum = local_corner.copy()
                maximum = local_corner.copy()
                continue
            minimum.x = min(minimum.x, local_corner.x)
            minimum.y = min(minimum.y, local_corner.y)
            minimum.z = min(minimum.z, local_corner.z)
            maximum.x = max(maximum.x, local_corner.x)
            maximum.y = max(maximum.y, local_corner.y)
            maximum.z = max(maximum.z, local_corner.z)

    if minimum is None or maximum is None:
        raise ValueError("unable to resolve mesh bounds")
    return minimum, maximum


class DOW2_OT_create_bounding_box(Operator):
    """Create or update a DoW2 simbox/coverbox fitted to scene geometry"""

    bl_idname = "dow2.create_bounding_box"
    bl_label = "Create DoW2 Bounding Box"
    bl_options = {'REGISTER', 'UNDO'}

    box_type: EnumProperty(
        name="Bounding Box Type",
        items=[
            ("simbox", "Simbox", "Create or update the DoW2 simbox"),
            ("coverbox", "Coverbox", "Create or update the DoW2 coverbox"),
        ],
        default="simbox",
    )

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' and not is_bounding_box_object(obj) for obj in context.scene.objects)

    def execute(self, context):
        armature_obj = _primary_armature(context.scene)
        model_name = _resolve_model_name(context.scene, armature_obj) or context.scene.name
        minimum, maximum = mesh_bounds_local(context.scene, armature_obj)
        center = (minimum + maximum) * 0.5
        extents = (maximum - minimum) * 0.5
        extents.x = max(extents.x, 1e-4)
        extents.y = max(extents.y, 1e-4)
        extents.z = max(extents.z, 1e-4)

        box_obj = create_or_update_bounding_box_object(
            context.scene,
            self.box_type,
            model_name=model_name,
            location=center,
            scale=extents,
            maintain_contour=True,
            armature_obj=armature_obj,
            source_path=f"generated:{self.box_type}",
        )
        self.report({'INFO'}, f"Updated {box_obj.name}")
        return {'FINISHED'}


def apply_bone_marker_name_visibility(scene: bpy.types.Scene):
    enabled = bool(getattr(scene, "dow2_show_bone_marker_names", False))

    for armature_obj in _iter_dow2_armatures(scene):
        armature_data = getattr(armature_obj, "data", None)
        if armature_data is not None:
            armature_data.show_names = enabled

    for marker_obj in _iter_dow2_marker_like_objects(scene):
        marker_obj.show_name = enabled


def _update_bone_marker_name_visibility(self, context):
    if context.scene is not None:
        apply_bone_marker_name_visibility(context.scene)


def snapshot_armature_marker_worlds(armature_obj: bpy.types.Object):
    return [(marker, marker.matrix_world.copy()) for marker in iter_armature_markers(armature_obj)]


def restore_armature_marker_worlds(marker_snapshots):
    for marker, matrix_world in marker_snapshots:
        if marker.name not in bpy.data.objects:
            continue
        marker.matrix_world = matrix_world
    bpy.context.view_layer.update()


def _snapshot_selected_armature_marker_worlds(context: bpy.types.Context):
    snapshots = []
    for obj in context.selected_objects:
        if obj.type != 'ARMATURE':
            continue
        snapshots.extend(snapshot_armature_marker_worlds(obj))
    return snapshots


def apply_transform_preserve_markers(
    context: bpy.types.Context,
    *,
    location: bool,
    rotation: bool,
    scale: bool,
):
    marker_snapshots = []
    if getattr(context.scene, "dow2_intercept_apply_transform", True):
        marker_snapshots = _snapshot_selected_armature_marker_worlds(context)

    result = bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale)
    if 'FINISHED' not in result:
        return result, 0

    if marker_snapshots:
        restore_armature_marker_worlds(marker_snapshots)

    return result, len(marker_snapshots)


def _draw_intercepted_object_apply_menu(self, context):
    if not getattr(context.scene, "dow2_intercept_apply_transform", True):
        if _ORIGINAL_VIEW3D_MT_OBJECT_APPLY_DRAW is not None:
            _ORIGINAL_VIEW3D_MT_OBJECT_APPLY_DRAW(self, context)
        return

    layout = self.layout

    op = layout.operator("dow2.apply_armature_transform_preserve_markers", text="Location")
    op.location = True
    op.rotation = False
    op.scale = False

    op = layout.operator("dow2.apply_armature_transform_preserve_markers", text="Rotation")
    op.location = False
    op.rotation = True
    op.scale = False

    op = layout.operator("dow2.apply_armature_transform_preserve_markers", text="Scale")
    op.location = False
    op.rotation = False
    op.scale = True

    op = layout.operator("dow2.apply_armature_transform_preserve_markers", text="Rotation & Scale")
    op.location = False
    op.rotation = True
    op.scale = True

    op = layout.operator("dow2.apply_armature_transform_preserve_markers", text="All Transforms")
    op.location = True
    op.rotation = True
    op.scale = True

    layout.separator()
    layout.operator("object.visual_transform_apply", text="Visual Transform")
    layout.operator("object.duplicates_make_real", text="Make Instances Real")


class DOW2_OT_setup_collections(Operator):
    """Create DoW2 damage-state and LoD collection hierarchy"""

    bl_idname = "dow2.setup_collections"
    bl_label = "Setup"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.scene is not None and context.scene.collection is not None

    def execute(self, context):
        scene = context.scene
        root_collection = scene.collection

        lod_count = int(scene.dow2_model_lod_count)
        template = scene.dow2_model_damage_template
        states = DAMAGE_STATE_TEMPLATES.get(template, ["healthy"])

        created_state_count = 0
        created_lod_count = 0

        for state_name in states:
            state_col = _find_child_collection(root_collection, state_name)
            if state_col is None:
                state_col = ensure_child_collection(root_collection, state_name)
                created_state_count += 1

            for lod_index in range(lod_count):
                lod_name = f"lod{lod_index}"
                lod_col = _find_child_collection(state_col, lod_name)
                if lod_col is None:
                    ensure_child_collection(state_col, lod_name)
                    created_lod_count += 1

        self.report(
            {'INFO'},
            f"Model hierarchy ready: {len(states)} state(s), {lod_count} LoD(s), created {created_state_count} state and {created_lod_count} LoD collection(s)"
        )
        return {'FINISHED'}


class DOW2_OT_apply_armature_transform_preserve_markers(Operator):
    """Apply transforms while preserving DoW2 bone-marker world placement"""

    bl_idname = "dow2.apply_armature_transform_preserve_markers"
    bl_label = "Apply Transform"
    bl_options = {'REGISTER', 'UNDO'}

    location: BoolProperty(name="Location", default=False)
    rotation: BoolProperty(name="Rotation", default=False)
    scale: BoolProperty(name="Scale", default=True)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and context.mode == 'OBJECT'

    def execute(self, context):
        if not (self.location or self.rotation or self.scale):
            self.report({'WARNING'}, "Enable at least one transform component")
            return {'CANCELLED'}

        result, marker_count = apply_transform_preserve_markers(
            context,
            location=self.location,
            rotation=self.rotation,
            scale=self.scale,
        )
        if 'FINISHED' not in result:
            return {'CANCELLED'}

        if marker_count > 0:
            self.report({'INFO'}, "Applied custom transform")
        return {'FINISHED'}


classes = [
    DOW2_OT_setup_collections,
    DOW2_OT_apply_armature_transform_preserve_markers,
    DOW2_OT_create_bounding_box,
]


def register():
    global _ORIGINAL_VIEW3D_MT_OBJECT_APPLY_DRAW

    bpy.types.Scene.dow2_model_lod_count = IntProperty(
        name="Number of LoDs",
        description="Number of LoD collections to create per damage state",
        default=1,
        min=1,
        max=4,
    )
    bpy.types.Scene.dow2_model_damage_template = EnumProperty(
        name="Damage State Template",
        description="Damage state template for model hierarchy",
        items=DAMAGE_STATE_ITEMS,
        default="SINGLE",
    )
    bpy.types.Scene.dow2_intercept_apply_transform = BoolProperty(
        name="Intercept Apply Transform",
        description="Use the DoW2 custom apply transform wrapper to preserve marker offsets on armatures",
        default=True,
    )
    bpy.types.Scene.dow2_show_bone_marker_names = BoolProperty(
        name="Show Bone and Marker Names",
        description="Show DoW2 armature bone names and marker names in the viewport",
        default=False,
        update=_update_bone_marker_name_visibility,
    )

    for cls in classes:
        bpy.utils.register_class(cls)

    apply_menu = getattr(bpy.types, "VIEW3D_MT_object_apply", None)
    if apply_menu is not None and _ORIGINAL_VIEW3D_MT_OBJECT_APPLY_DRAW is None:
        _ORIGINAL_VIEW3D_MT_OBJECT_APPLY_DRAW = apply_menu.draw
        apply_menu.draw = _draw_intercepted_object_apply_menu


def unregister():
    global _ORIGINAL_VIEW3D_MT_OBJECT_APPLY_DRAW

    apply_menu = getattr(bpy.types, "VIEW3D_MT_object_apply", None)
    if apply_menu is not None and _ORIGINAL_VIEW3D_MT_OBJECT_APPLY_DRAW is not None:
        apply_menu.draw = _ORIGINAL_VIEW3D_MT_OBJECT_APPLY_DRAW
        _ORIGINAL_VIEW3D_MT_OBJECT_APPLY_DRAW = None

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    if hasattr(bpy.types.Scene, "dow2_model_lod_count"):
        del bpy.types.Scene.dow2_model_lod_count
    if hasattr(bpy.types.Scene, "dow2_model_damage_template"):
        del bpy.types.Scene.dow2_model_damage_template
    if hasattr(bpy.types.Scene, "dow2_intercept_apply_transform"):
        del bpy.types.Scene.dow2_intercept_apply_transform
    if hasattr(bpy.types.Scene, "dow2_show_bone_marker_names"):
        del bpy.types.Scene.dow2_show_bone_marker_names
