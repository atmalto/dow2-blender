import bpy
import bmesh
from math import radians
from mathutils import Vector
from bpy.types import Operator
from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty


_BLENDER_NAME_MAX_BYTES = 63
_COLLISION_SUFFIX = "_collision"

COLLISION_STATE_DEFINITIONS = (
    (1, "Healthy_LOD", "healthy"),
    (2, "Light_LOD", "light_damage"),
    (3, "HeavyDMG_LOD", "heavy_damage"),
    (4, "Wreck_LOD", "wreck"),
)

COLLISION_STATE_NAMES = {state_id: state_name for state_id, state_name, _ in COLLISION_STATE_DEFINITIONS}
MODEL_STATE_TO_COLLISION_STATE_ID = {model_state: state_id for state_id, _state_name, model_state in COLLISION_STATE_DEFINITIONS}


def _selected_mesh_objects(context):
    return [obj for obj in context.selected_objects if obj.type == 'MESH']


def _update_collision_walkable(scene, _context):
    if scene.dow2_collision_walkable and scene.dow2_collision_complex:
        scene.dow2_collision_complex = False


def _update_collision_complex(scene, _context):
    if scene.dow2_collision_complex and scene.dow2_collision_walkable:
        scene.dow2_collision_walkable = False


def _strip_collection_suffix(name: str) -> str:
    return name.split(".")[0]


def iter_collision_states(limit: int | None = None):
    state_limit = max(0, min(limit or len(COLLISION_STATE_DEFINITIONS), len(COLLISION_STATE_DEFINITIONS)))
    return COLLISION_STATE_DEFINITIONS[:state_limit]


def get_collision_state_name(state_id: int) -> str:
    return COLLISION_STATE_NAMES.get(int(state_id), f"State{state_id}")


def get_collision_collection_name(state_id: int) -> str:
    return f"Collision::{get_collision_state_name(state_id)}"


def is_recognized_collision_collection_name(name: str) -> bool:
    base_name = _strip_collection_suffix(name)
    return any(base_name == get_collision_collection_name(state_id) for state_id, _state_name, _model_state in COLLISION_STATE_DEFINITIONS)


def ensure_collision_state_collection(scene, state_id: int) -> bpy.types.Collection:
    collection_name = get_collision_collection_name(state_id)
    existing = bpy.data.collections.get(collection_name)
    if existing:
        return existing

    collection = bpy.data.collections.new(collection_name)
    scene.collection.children.link(collection)
    return collection


def get_available_collision_state_items(_scene=None, _context=None):
    items = []
    for state_id, _state_name, _model_state in COLLISION_STATE_DEFINITIONS:
        collection_name = get_collision_collection_name(state_id)
        if bpy.data.collections.get(collection_name) is None:
            continue
        items.append((str(state_id), collection_name, f"Place generated collision meshes into {collection_name}"))
    return items


def get_selected_generation_state_id(scene) -> int | None:
    items = get_available_collision_state_items(scene)
    if not items:
        return None

    selected = str(getattr(scene, "dow2_collision_generation_state", "") or "")
    valid_ids = {item[0] for item in items}
    if selected in valid_ids:
        return int(selected)
    return int(items[0][0])


def collect_collision_state_meshes(scene) -> dict[int, list[bpy.types.Object]]:
    grouped = {}
    for state_id, _state_name, _model_state in COLLISION_STATE_DEFINITIONS:
        collection = bpy.data.collections.get(get_collision_collection_name(state_id))
        if collection is None:
            continue
        meshes = [obj for obj in collection.objects if obj.type == 'MESH']
        if meshes:
            grouped[state_id] = meshes
    return grouped


def infer_collision_state_id_from_object(obj: bpy.types.Object, default: int = 1) -> int:
    stored_state_id = obj.get("dow2_collision_state_id")
    if stored_state_id is not None:
        try:
            state_id = int(stored_state_id)
            if state_id in COLLISION_STATE_NAMES:
                return state_id
        except (TypeError, ValueError):
            pass

    for collection in obj.users_collection:
        base_name = _strip_collection_suffix(collection.name)
        for state_id, _state_name, _model_state in COLLISION_STATE_DEFINITIONS:
            if base_name == get_collision_collection_name(state_id):
                return state_id

    model_state = str(obj.get("dow2_group", "") or "")
    if model_state in MODEL_STATE_TO_COLLISION_STATE_ID:
        return MODEL_STATE_TO_COLLISION_STATE_ID[model_state]

    for collection in obj.users_collection:
        base_name = _strip_collection_suffix(collection.name)
        if base_name in MODEL_STATE_TO_COLLISION_STATE_ID:
            return MODEL_STATE_TO_COLLISION_STATE_ID[base_name]

    return default


def get_selected_face_count(context) -> int:
    if context.mode != 'EDIT_MESH':
        return 0

    obj = context.active_object
    if obj is None or obj.type != 'MESH':
        return 0

    bm = bmesh.from_edit_mesh(obj.data)
    return sum(1 for face in bm.faces if face.select)


def _duplicate_selected_meshes(context, selected_meshes):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selected_meshes:
        obj.select_set(True)
    context.view_layer.objects.active = selected_meshes[0]
    bpy.ops.object.duplicate(linked=False)
    duplicates = [obj for obj in context.selected_objects if obj.type == 'MESH']
    return duplicates


def _truncate_base_with_suffix(base_name: str, suffix: str) -> str:
    if not base_name:
        base_name = "collision"

    while base_name and len((base_name + suffix).encode("utf-8")) > _BLENDER_NAME_MAX_BYTES:
        base_name = base_name[:-1]

    if not base_name:
        suffix_bytes = suffix.encode("utf-8")
        return suffix_bytes[:_BLENDER_NAME_MAX_BYTES].decode("utf-8", errors="ignore")

    return f"{base_name}{suffix}"


def _build_collision_name(source_name: str) -> str:
    return _truncate_base_with_suffix(source_name, _COLLISION_SUFFIX)


def _build_collision_collection_name(base_name: str) -> str:
    return _truncate_base_with_suffix(base_name, _COLLISION_SUFFIX)


def _ensure_collision_collection(scene, base_name: str) -> bpy.types.Collection:
    collection_name = _build_collision_collection_name(base_name)
    existing = bpy.data.collections.get(collection_name)
    if existing:
        return existing
    collection = bpy.data.collections.new(collection_name)
    scene.collection.children.link(collection)
    return collection


def _resolve_generation_target_collection(scene, fallback_base_name: str) -> bpy.types.Collection:
    state_id = get_selected_generation_state_id(scene)
    if state_id in COLLISION_STATE_NAMES:
        return ensure_collision_state_collection(scene, state_id)
    return _ensure_collision_collection(scene, fallback_base_name)


def _unlink_from_all_collections(obj: bpy.types.Object):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)


def _build_convex_hull(obj: bpy.types.Object):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.convex_hull()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def _create_object_from_selected_faces(context, source_obj: bpy.types.Object):
    bm_src = bmesh.from_edit_mesh(source_obj.data)
    selected_faces = [face for face in bm_src.faces if face.select]
    if not selected_faces:
        return None

    bm_new = bmesh.new()
    vertex_map = {}

    for face in selected_faces:
        face_verts = []
        for vert in face.verts:
            mapped = vertex_map.get(vert.index)
            if mapped is None:
                mapped = bm_new.verts.new(vert.co.copy())
                vertex_map[vert.index] = mapped
            face_verts.append(mapped)

        try:
            bm_new.faces.new(face_verts)
        except ValueError:
            continue

    if not bm_new.faces:
        bm_new.free()
        return None

    bm_new.normal_update()
    mesh = bpy.data.meshes.new(name=f"{source_obj.name}_selected_faces")
    bm_new.to_mesh(mesh)
    bm_new.free()

    obj = bpy.data.objects.new(mesh.name, mesh)
    obj.matrix_world = source_obj.matrix_world.copy()

    target_collection = source_obj.users_collection[0] if source_obj.users_collection else context.scene.collection
    target_collection.objects.link(obj)
    return obj


def _filter_walkable_faces(obj: bpy.types.Object, max_angle_degrees: int) -> int:
    up = Vector((0.0, 0.0, 1.0))
    threshold = radians(max_angle_degrees)

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    faces_to_delete = []
    normal_matrix = obj.matrix_world.to_3x3()

    for face in bm.faces:
        world_normal = (normal_matrix @ face.normal).normalized()
        angle = world_normal.angle(up)
        if angle > threshold:
            faces_to_delete.append(face)

    deleted_count = len(faces_to_delete)
    if faces_to_delete:
        bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return deleted_count


def _apply_decimate(obj: bpy.types.Object, ratio: float):
    if ratio >= 0.999:
        return

    modifier = obj.modifiers.new(name="DoW2Decimate", type='DECIMATE')
    modifier.decimate_type = 'COLLAPSE'
    modifier.ratio = max(0.0, min(1.0, ratio))

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def _get_or_create_collision_material() -> bpy.types.Material:
    mat_name = "dow2_collision_material"
    mat = bpy.data.materials.get(mat_name)

    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        mat.blend_method = 'BLEND'

        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.2, 0.8, 0.2, 1.0)
            bsdf.inputs["Alpha"].default_value = 0.3
            bsdf.inputs["Roughness"].default_value = 1.0

    return mat


def _apply_preview_style(obj: bpy.types.Object, display_type: str):
    obj.display_type = display_type
    if obj.type == 'MESH' and obj.data is not None:
        material = _get_or_create_collision_material()
        if material.name not in [slot.name for slot in obj.data.materials if slot is not None]:
            obj.data.materials.append(material)


class DOW2_OT_generate_collision_mesh(Operator):
    """Generate convex-hull collision mesh from selected objects"""

    bl_idname = "dow2.generate_collision_mesh"
    bl_label = "Apply"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'OBJECT':
            return len(context.selected_objects) > 0
        if context.mode == 'EDIT_MESH':
            return context.active_object is not None and context.active_object.type == 'MESH'
        return False

    def execute(self, context):
        scene = context.scene
        use_selected_faces = scene.dow2_collision_use_selected_faces
        use_complex_collision = scene.dow2_collision_complex
        generation_state_id = get_selected_generation_state_id(scene)

        if generation_state_id is None:
            self.report({'ERROR'}, "Generate collision buckets first")
            return {'CANCELLED'}

        selected_meshes = []
        non_mesh_selected = []
        source_for_name = None

        if use_selected_faces:
            if context.mode != 'EDIT_MESH':
                self.report({'ERROR'}, "Enable Edit Mode and select at least 1 face")
                return {'CANCELLED'}

            source_obj = context.active_object
            if source_obj is None or source_obj.type != 'MESH':
                self.report({'ERROR'}, "Active object must be a mesh in Edit Mode")
                return {'CANCELLED'}

            if get_selected_face_count(context) < 1:
                self.report({'ERROR'}, "Select at least 1 face before generating collision")
                return {'CANCELLED'}

            source_for_name = source_obj
            selected_face_obj = _create_object_from_selected_faces(context, source_obj)
            if selected_face_obj is None:
                self.report({'ERROR'}, "Could not build a mesh from selected faces")
                return {'CANCELLED'}

            bpy.ops.object.mode_set(mode='OBJECT')
            selected_meshes = [selected_face_obj]
        else:
            if context.mode != 'OBJECT':
                self.report({'ERROR'}, "Switch to Object Mode or enable 'Use Selected Faces'")
                return {'CANCELLED'}

            selected_meshes = _selected_mesh_objects(context)
            non_mesh_selected = [obj for obj in context.selected_objects if obj.type != 'MESH']

        if not selected_meshes:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        if non_mesh_selected:
            self.report({'WARNING'}, f"Skipped {len(non_mesh_selected)} non-mesh object(s)")

        duplicates = selected_meshes if use_selected_faces else _duplicate_selected_meshes(context, selected_meshes)
        if not duplicates:
            self.report({'ERROR'}, "Could not duplicate selected meshes")
            return {'CANCELLED'}

        working_objects = []
        if scene.dow2_collision_join_hulls and len(duplicates) > 1:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in duplicates:
                obj.select_set(True)
            context.view_layer.objects.active = duplicates[0]
            bpy.ops.object.join()
            if context.active_object and context.active_object.type == 'MESH':
                working_objects = [context.active_object]
        else:
            working_objects = duplicates

        if not working_objects:
            self.report({'ERROR'}, "Failed to create working collision mesh")
            return {'CANCELLED'}

        deleted_faces_total = 0

        for index, obj in enumerate(working_objects):
            if not use_complex_collision:
                _build_convex_hull(obj)

                if scene.dow2_collision_walkable:
                    deleted_faces_total += _filter_walkable_faces(obj, scene.dow2_collision_walkable_angle)

                _apply_decimate(obj, scene.dow2_collision_decimate)

            if len(working_objects) == 1 and scene.dow2_collision_join_hulls:
                joined_source_name = source_for_name.name if source_for_name is not None else selected_meshes[0].name
                obj.name = _build_collision_name(f"{joined_source_name}_joined")
                collection_base_name = f"{joined_source_name}_joined"
                source_obj = source_for_name if source_for_name is not None else selected_meshes[0]
            else:
                if source_for_name is not None:
                    source_name = source_for_name.name
                    source_obj = source_for_name
                else:
                    source_name = selected_meshes[min(index, len(selected_meshes) - 1)].name
                    source_obj = selected_meshes[min(index, len(selected_meshes) - 1)]
                obj.name = _build_collision_name(source_name)
                collection_base_name = source_name

            target_collection = _resolve_generation_target_collection(scene, collection_base_name)
            _unlink_from_all_collections(obj)
            target_collection.objects.link(obj)
            obj["dow2_collision_state_id"] = generation_state_id
            _apply_preview_style(obj, scene.dow2_collision_preview_type)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in working_objects:
            obj.select_set(True)
        context.view_layer.objects.active = working_objects[0]

        if use_complex_collision:
            info = f"Generated {len(working_objects)} complex collision mesh(es)"
        elif scene.dow2_collision_walkable:
            info = f"Generated {len(working_objects)} walkable collision mesh(es)"
        else:
            info = f"Generated {len(working_objects)} collision mesh(es)"
        if scene.dow2_collision_walkable:
            info += f", removed {deleted_faces_total} non-walkable face(s)"
        self.report({'INFO'}, info)
        return {'FINISHED'}


class DOW2_OT_setup_collision_collections(Operator):
    """Create recognized collision state collections"""

    bl_idname = "dow2.setup_collision_collections"
    bl_label = "Setup"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.scene is not None and context.scene.collection is not None

    def execute(self, context):
        state_count = int(context.scene.dow2_collision_state_count)
        created = 0
        for state_id, _state_name, _model_state in iter_collision_states(state_count):
            collection_name = get_collision_collection_name(state_id)
            if bpy.data.collections.get(collection_name) is None:
                ensure_collision_state_collection(context.scene, state_id)
                created += 1

        self.report({'INFO'}, f"Collision state collections ready: {state_count} state(s), created {created} collection(s)")
        return {'FINISHED'}


classes = [
    DOW2_OT_setup_collision_collections,
    DOW2_OT_generate_collision_mesh,
]


def register():
    bpy.types.Scene.dow2_collision_state_count = IntProperty(
        name="Number of Health States",
        description="Number of collision health-state collections to create",
        default=4,
        min=1,
        max=4,
    )
    bpy.types.Scene.dow2_collision_walkable = BoolProperty(
        name="Walkable",
        description="Keep only faces whose world normal angle to up-vector is within threshold (use for walkable surfaces like stairs and bridges, don't use for full object collision like buildings or walls)",
        default=False,
        update=_update_collision_walkable,
    )
    bpy.types.Scene.dow2_collision_complex = BoolProperty(
        name="Complex",
        description="Used to recreate collision out of the object's detailed geometry. This is used mainly for DoW2's garrisonable buildings",
        default=False,
        update=_update_collision_complex,
    )
    bpy.types.Scene.dow2_collision_walkable_angle = IntProperty(
        name="Walkable Angle",
        description="Maximum slope angle from world up-axis (ex: stairs ~ 45 degrees)",
        default=45,
        min=0,
        max=90,
    )
    bpy.types.Scene.dow2_collision_decimate = FloatProperty(
        name="Decimate",
        description="Decimation ratio - i.e. how much of the mesh's detail to preserve (0.1 keeps minimal detail, 1.0 keeps full detail)",
        default=1.0,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )
    bpy.types.Scene.dow2_collision_join_hulls = BoolProperty(
        name="Join Into One Hull",
        description="Join selected meshes into one temporary mesh before hull generation. I.e. create one hull outof multiple non contiguous geomety (faces, meshes, etc).",
        default=False,
    )
    bpy.types.Scene.dow2_collision_use_selected_faces = BoolProperty(
        name="Use Selected Faces",
        description="Build collision from selected edit-mode faces on the active mesh. Go into edit mode, select some faces, and Apply to generate a collision mesh using only those faces.",
        default=False,
    )
    bpy.types.Scene.dow2_collision_preview_type = EnumProperty(
        name="Display Type",
        description="How to display generated collision meshes in the viewport",
        items=[
            ('WIRE', "Wire", "Display as wireframe (recommended for collision)"),
            ('SOLID', "Solid", "Display as solid objects"),
        ],
        default='WIRE',
    )
    bpy.types.Scene.dow2_collision_generation_state = EnumProperty(
        name="Target Bucket",
        description="Recognized collision bucket that generated meshes will be moved into",
        items=get_available_collision_state_items,
    )

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    if hasattr(bpy.types.Scene, "dow2_collision_state_count"):
        del bpy.types.Scene.dow2_collision_state_count
    if hasattr(bpy.types.Scene, "dow2_collision_walkable"):
        del bpy.types.Scene.dow2_collision_walkable
    if hasattr(bpy.types.Scene, "dow2_collision_complex"):
        del bpy.types.Scene.dow2_collision_complex
    if hasattr(bpy.types.Scene, "dow2_collision_walkable_angle"):
        del bpy.types.Scene.dow2_collision_walkable_angle
    if hasattr(bpy.types.Scene, "dow2_collision_decimate"):
        del bpy.types.Scene.dow2_collision_decimate
    if hasattr(bpy.types.Scene, "dow2_collision_join_hulls"):
        del bpy.types.Scene.dow2_collision_join_hulls
    if hasattr(bpy.types.Scene, "dow2_collision_use_selected_faces"):
        del bpy.types.Scene.dow2_collision_use_selected_faces
    if hasattr(bpy.types.Scene, "dow2_collision_preview_type"):
        del bpy.types.Scene.dow2_collision_preview_type
    if hasattr(bpy.types.Scene, "dow2_collision_generation_state"):
        del bpy.types.Scene.dow2_collision_generation_state
