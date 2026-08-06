import math

import bpy
import gpu
from bpy.props import StringProperty
from bpy.types import Operator
from gpu_extras.batch import batch_for_shader

from ...material.badges import (
    apply_badge_session_transform,
    badge_control,
    capture_badge_session,
    ensure_badge_preview_nodes,
    is_badge_material as is_badge_preview_material,
    resolve_texture_image,
    restore_badge_session,
)


def _target_area(context):
    if context.screen is None:
        return context.area
    image_area = next((area for area in context.screen.areas if area.type == 'IMAGE_EDITOR'), None)
    return image_area or context.area


def _find_area(screen, area_type: str):
    if screen is None:
        return None
    return next((area for area in screen.areas if area.type == area_type), None)


def _window_region(area):
    return next((region for region in area.regions if region.type == 'WINDOW'), None)


def _event_in_area_window(area, event) -> bool:
    region = _window_region(area)
    if region is None:
        return False
    local_x = event.mouse_x - (area.x + region.x)
    local_y = event.mouse_y - (area.y + region.y)
    return 0.0 <= local_x < region.width and 0.0 <= local_y < region.height


def _uv_to_region(area, uv):
    region = _window_region(area)
    if region is None:
        return None
    x, y = region.view2d.view_to_region(uv[0], uv[1], clip=False)
    return (float(x), float(y))


def _region_to_uv(area, x: float, y: float):
    region = _window_region(area)
    if region is None:
        return None
    return tuple(float(value) for value in region.view2d.region_to_view(x, y))


def _event_mouse_uv(area, event):
    region = _window_region(area)
    if region is None:
        return None
    local_x = event.mouse_x - (area.x + region.x)
    local_y = event.mouse_y - (area.y + region.y)
    return _region_to_uv(area, local_x, local_y)


def _pick_size_uv(area, min_pixels: float = 100.0):
    region = _window_region(area)
    if region is None:
        return (0.0, 0.0)
    origin_uv = _region_to_uv(area, 0.0, 0.0)
    offset_x_uv = _region_to_uv(area, min_pixels, 0.0)
    offset_y_uv = _region_to_uv(area, 0.0, min_pixels)
    if origin_uv is None or offset_x_uv is None or offset_y_uv is None:
        return (0.0, 0.0)
    return (
        abs(offset_x_uv[0] - origin_uv[0]),
        abs(offset_y_uv[1] - origin_uv[1]),
    )


def _set_area_sidebar_visible(area) -> None:
    if area is None:
        return
    area.show_menus = True
    for space in area.spaces:
        if hasattr(space, 'show_region_ui'):
            try:
                space.show_region_ui = True
            except Exception:
                pass
    area.tag_redraw()


def _set_view3d_shading(screen) -> None:
    view_area = _find_area(screen, 'VIEW_3D')
    if view_area is None:
        return
    for space in view_area.spaces:
        if space.type == 'VIEW_3D':
            try:
                space.shading.type = 'MATERIAL'
            except Exception:
                pass
            view_area.tag_redraw()
            return


def _set_object_mode(context, obj) -> None:
    if obj is None or getattr(obj, 'mode', 'OBJECT') == 'OBJECT':
        return
    screen = context.window.screen if context.window is not None else context.screen
    view_area = _find_area(screen, 'VIEW_3D')
    region = _window_region(view_area) if view_area is not None else None
    try:
        if context.view_layer is not None:
            context.view_layer.objects.active = obj
        if context.window is not None and view_area is not None and region is not None:
            with context.temp_override(window=context.window, area=view_area, region=region, active_object=obj, object=obj):
                bpy.ops.object.mode_set(mode='OBJECT')
        elif context.window is not None and getattr(context, 'area', None) is not None and getattr(context, 'region', None) is not None:
            with context.temp_override(window=context.window, area=context.area, region=context.region, active_object=obj, object=obj):
                bpy.ops.object.mode_set(mode='OBJECT')
        else:
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass


def _prepare_uv_editing_layout(context):
    if context.window is not None:
        uv_workspace = bpy.data.workspaces.get('UV Editing')
        if uv_workspace is not None:
            context.window.workspace = uv_workspace
    screen = context.window.screen if context.window is not None else context.screen
    image_area = _find_area(screen, 'IMAGE_EDITOR')
    if image_area is None:
        image_area = _target_area(context)
    if image_area is not None and image_area.type != 'IMAGE_EDITOR':
        image_area.type = 'IMAGE_EDITOR'
    if image_area is not None and hasattr(image_area, 'ui_type'):
        image_area.ui_type = 'UV'
    _set_area_sidebar_visible(image_area)
    _set_area_sidebar_visible(_find_area(screen, 'VIEW_3D'))
    _set_view3d_shading(screen)
    return image_area


def _snap_rotation_step(rotation: float, direction: int) -> float:
    quarter_turn = math.pi * 0.5
    snapped = round(rotation / quarter_turn) * quarter_turn
    if math.isclose(rotation, snapped, abs_tol=1e-6):
        return snapped + (direction * quarter_turn)
    return snapped


def _rotate(point, rotation: float):
    cos_theta = math.cos(rotation)
    sin_theta = math.sin(rotation)
    return (
        (point[0] * cos_theta) - (point[1] * sin_theta),
        (point[0] * sin_theta) + (point[1] * cos_theta),
    )


def _overlay_corners(center, size, rotation: float):
    half_u = size[0] * 0.5
    half_v = size[1] * 0.5
    corners = [(-half_u, -half_v), (half_u, -half_v), (half_u, half_v), (-half_u, half_v)]
    output = []
    for corner in corners:
        rotated = _rotate(corner, rotation)
        output.append((center[0] + rotated[0], center[1] + rotated[1]))
    return output


def _point_inside_overlay(area, point, center, size, rotation: float) -> bool:
    pick_size_u, pick_size_v = _pick_size_uv(area)
    hit_size = (
        max(size[0], pick_size_u),
        max(size[1], pick_size_v),
    )
    local_x = point[0] - center[0]
    local_y = point[1] - center[1]
    cos_theta = math.cos(-rotation)
    sin_theta = math.sin(-rotation)
    x = (local_x * cos_theta) - (local_y * sin_theta)
    y = (local_x * sin_theta) + (local_y * cos_theta)
    return abs(x) <= (hit_size[0] * 0.5) and abs(y) <= (hit_size[1] * 0.5)


class DOW2_OT_edit_badge_decal(Operator):
    bl_idname = "dow2.edit_badge_decal"
    bl_label = "Edit Badge Decal"
    bl_description = "Edit DoW2 badge placement directly on top of the diffuse UV layout"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty(name="Material", default="")
    badge_slot: StringProperty(name="Badge Slot", default="badge1")

    def _cleanup(self) -> None:
        timer = getattr(self, '_timer', None)
        window_manager = getattr(self, '_window_manager', None)
        if timer is not None and window_manager is not None:
            try:
                window_manager.event_timer_remove(timer)
            except Exception:
                pass
            self._timer = None
        if getattr(self, '_draw_handle', None) is not None:
            bpy.types.SpaceImageEditor.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
        if getattr(self, '_area', None) is not None:
            self._area.header_text_set(None)
            self._area.tag_redraw()

    def _draw_overlay(self) -> None:
        area = getattr(self, '_area', None)
        if area is None or bpy.context.area is None or bpy.context.area.as_pointer() != area.as_pointer():
            return

        corners_uv = _overlay_corners(self._current_center, self._current_size, self._rotation)
        corners_region = [_uv_to_region(area, corner) for corner in corners_uv]
        if any(corner is None for corner in corners_region):
            return

        coords = [(corner[0], corner[1]) for corner in corners_region if corner is not None]
        if len(coords) != 4:
            return

        if getattr(self, '_badge_image', None) is not None:
            shader = gpu.shader.from_builtin('IMAGE')
            texture = gpu.texture.from_image(self._badge_image)
            batch = batch_for_shader(
                shader,
                'TRI_FAN',
                {
                    'pos': coords,
                    'texCoord': ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
                },
            )
            gpu.state.blend_set('ALPHA')
            shader.bind()
            shader.uniform_sampler('image', texture)
            batch.draw(shader)

        line_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        line_batch = batch_for_shader(line_shader, 'LINE_LOOP', {'pos': coords})
        gpu.state.blend_set('ALPHA')
        line_shader.bind()
        line_shader.uniform_float('color', (1.0, 1.0, 1.0, 0.95))
        line_batch.draw(line_shader)

    def _apply_transform(self) -> None:
        if getattr(self, '_session', None) is None:
            return
        apply_badge_session_transform(
            self._session,
            current_center=self._current_center,
            current_size=self._current_size,
            rotation=self._rotation,
        )
        if getattr(self, '_area', None) is not None:
            self._area.tag_redraw()

    def _active_object(self):
        object_name = getattr(self, '_active_object_name', '')
        if not object_name:
            return None
        return bpy.data.objects.get(object_name)

    def _arm_editor(self, context):
        material = bpy.data.materials.get(self.material_name)
        if material is None:
            return False, 'Material not found'

        active_object = self._active_object()
        self._area = _prepare_uv_editing_layout(context)
        _set_object_mode(context, active_object)
        if active_object is not None and getattr(active_object, 'mode', 'OBJECT') != 'OBJECT':
            return False, 'Could not switch the active object back to Object Mode'

        ready, ready_message = ensure_badge_preview_nodes(context, material, self.badge_slot)
        if not ready:
            return False, ready_message or 'Could not prepare the badge preview graph'

        if self._area is None:
            self._area = _target_area(context)
        if self._area is None:
            return False, 'No editor area available'
        if self._area.type != 'IMAGE_EDITOR':
            self._area.type = 'IMAGE_EDITOR'
        if hasattr(self._area, 'ui_type'):
            self._area.ui_type = 'UV'
        _set_area_sidebar_visible(self._area)
        self._space = self._area.spaces.active

        _slot_name, _label, texture_key, _matrix_key, _translate_key = badge_control(self.badge_slot)
        base_image = resolve_texture_image(context, material, 'diffuseTex')
        self._badge_image = resolve_texture_image(context, material, texture_key)
        image_to_show = base_image or self._badge_image
        if image_to_show is not None and hasattr(self._space, 'image'):
            self._space.image = image_to_show

        self._session, session_message = capture_badge_session(
            material,
            self.badge_slot,
            self._badge_image or base_image or image_to_show,
        )
        if self._session is None:
            return False, session_message or 'Could not read the current badge placement'

        self._original_center = tuple(self._session['original_center'])
        self._original_size = tuple(self._session['original_size'])
        self._current_center = tuple(self._original_center)
        self._current_size = tuple(self._original_size)
        self._rotation = float(self._session.get('original_rotation', 0.0))
        self._dragging = False
        self._drag_anchor = (0.0, 0.0)
        self._drag_start_center = tuple(self._current_center)

        if getattr(self, '_draw_handle', None) is None:
            self._draw_handle = bpy.types.SpaceImageEditor.draw_handler_add(self._draw_overlay, (), 'WINDOW', 'POST_PIXEL')
        self._area.header_text_set('Drag to move. Mouse wheel to scale. Q/E to rotate. Ctrl+Q/E to rotate to closest axis. Enter to apply. Esc to cancel')
        self._area.tag_redraw()
        self._armed = True
        return True, session_message

    def invoke(self, context, _event):
        active_object = getattr(context, 'object', None)
        material = bpy.data.materials.get(self.material_name) if self.material_name else getattr(active_object, 'active_material', None)
        if material is None or not is_badge_preview_material(material):
            self.report({'ERROR'}, 'Active material is not a badge-capable DoW2 material')
            return {'CANCELLED'}

        _slot_name, label, texture_key, _matrix_key, _translate_key = badge_control(self.badge_slot)
        if not str(material.get(f'dow2_{texture_key}', '') or '').strip():
            self.report({'ERROR'}, f'{label} has no texture assigned')
            return {'CANCELLED'}

        self.material_name = material.name
        self._active_object_name = active_object.name if active_object is not None else ''
        if not self._active_object_name:
            self.report({'ERROR'}, 'No active object available for badge editing')
            return {'CANCELLED'}

        if context.window is None:
            self.report({'ERROR'}, 'A Blender window is required to start badge editing')
            return {'CANCELLED'}

        self._window_manager = context.window_manager
        self._timer = None
        self._draw_handle = None
        self._area = _prepare_uv_editing_layout(context)
        self._space = None
        self._badge_image = None
        self._session = None
        self._armed = False
        self._arming_attempts = 0
        self._dragging = False
        self._drag_anchor = (0.0, 0.0)
        self._drag_start_center = (0.0, 0.0)
        if self._area is not None:
            self._area.header_text_set('Preparing badge editor: switching to UV Editing, forcing Object Mode...')
            self._area.tag_redraw()

        self._timer = context.window_manager.event_timer_add(0.05, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            if getattr(self, '_session', None) is not None:
                restore_badge_session(self._session)
            self._cleanup()
            return {'CANCELLED'}

        if not getattr(self, '_armed', False):
            if event.type != 'TIMER':
                return {'PASS_THROUGH'}
            armed, message = self._arm_editor(context)
            if armed:
                if message:
                    self.report({'INFO'}, message)
                return {'RUNNING_MODAL'}
            self._arming_attempts += 1
            if self._arming_attempts >= 20:
                self.report({'ERROR'}, message or 'Could not start badge editing')
                self._cleanup()
                return {'CANCELLED'}
            if getattr(self, '_area', None) is not None:
                self._area.header_text_set('Preparing badge editor: forcing Object Mode...')
                self._area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type in {'RET', 'NUMPAD_ENTER', 'SPACE'} and event.value == 'PRESS':
            self._cleanup()
            return {'FINISHED'}

        if getattr(self, '_area', None) is None:
            self._cleanup()
            return {'CANCELLED'}

        event_in_uv_area = _event_in_area_window(self._area, event)
        mouse_uv = _event_mouse_uv(self._area, event) if event_in_uv_area else None

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and mouse_uv is not None:
            if _point_inside_overlay(self._area, mouse_uv, self._current_center, self._current_size, self._rotation):
                self._dragging = True
                self._drag_anchor = mouse_uv
                self._drag_start_center = tuple(self._current_center)
                return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if not self._dragging:
                return {'PASS_THROUGH'}
            self._dragging = False
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE' and self._dragging and mouse_uv is not None:
            delta_u = mouse_uv[0] - self._drag_anchor[0]
            delta_v = mouse_uv[1] - self._drag_anchor[1]
            self._current_center = (self._drag_start_center[0] + delta_u, self._drag_start_center[1] + delta_v)
            self._apply_transform()
            return {'RUNNING_MODAL'}

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and event.value == 'PRESS' and event_in_uv_area:
            factor = 1.05 if event.type == 'WHEELUPMOUSE' else (1.0 / 1.05)
            self._current_size = (max(1e-4, self._current_size[0] * factor), max(1e-4, self._current_size[1] * factor))
            self._apply_transform()
            return {'RUNNING_MODAL'}

        if event.type == 'Q' and event.value == 'PRESS' and event_in_uv_area:
            self._rotation = _snap_rotation_step(self._rotation, 1) if event.ctrl else self._rotation + math.radians(5.0)
            self._apply_transform()
            return {'RUNNING_MODAL'}

        if event.type == 'E' and event.value == 'PRESS' and event_in_uv_area:
            self._rotation = _snap_rotation_step(self._rotation, -1) if event.ctrl else self._rotation - math.radians(5.0)
            self._apply_transform()
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'} if self._dragging else {'PASS_THROUGH'}


__all__ = ["DOW2_OT_edit_badge_decal"]