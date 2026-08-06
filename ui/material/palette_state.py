import time

import bpy
from bpy.props import FloatVectorProperty, PointerProperty
from bpy.types import PropertyGroup

from ...material.definitions import (
    DEFAULT_PALETTE_1,
    DEFAULT_PALETTE_2,
    DEFAULT_PALETTE_3,
    DEFAULT_PALETTE_4,
)
from ...material.shaders.node_passes import BaseColorNodePasses


_PALETTE_SYNC_DELAY_SECONDS = 0.12
_palette_sync_timer_registered = False
_palette_sync_deadline = 0.0


def _run_deferred_dow2_palette_sync():
    global _palette_sync_timer_registered

    remaining = _palette_sync_deadline - time.perf_counter()
    if remaining > 0.0:
        return max(remaining, 0.01)

    scene = getattr(bpy.context, 'scene', None)
    if scene is not None:
        BaseColorNodePasses.sync_global_palette_nodes(scene)

    _palette_sync_timer_registered = False
    return None


def _schedule_dow2_palette_sync() -> None:
    global _palette_sync_deadline, _palette_sync_timer_registered

    _palette_sync_deadline = time.perf_counter() + _PALETTE_SYNC_DELAY_SECONDS
    if _palette_sync_timer_registered:
        return

    bpy.app.timers.register(_run_deferred_dow2_palette_sync, first_interval=_PALETTE_SYNC_DELAY_SECONDS)
    _palette_sync_timer_registered = True


def _sync_dow2_global_palettes(_self, context):
    scene = getattr(context, 'scene', None)
    if scene is None:
        return
    _schedule_dow2_palette_sync()


class DOW2_GlobalPaletteSettings(PropertyGroup):
    palette1: FloatVectorProperty(
        name='Palette 1',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=DEFAULT_PALETTE_1,
        update=_sync_dow2_global_palettes,
    )
    palette2: FloatVectorProperty(
        name='Palette 2',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=DEFAULT_PALETTE_2,
        update=_sync_dow2_global_palettes,
    )
    palette3: FloatVectorProperty(
        name='Palette 3',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=DEFAULT_PALETTE_3,
        update=_sync_dow2_global_palettes,
    )
    palette4: FloatVectorProperty(
        name='Palette 4',
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=DEFAULT_PALETTE_4,
        update=_sync_dow2_global_palettes,
    )


def register_material_panel_state() -> None:
    bpy.types.Scene.dow2_global_palettes = PointerProperty(type=DOW2_GlobalPaletteSettings)
    scene = getattr(bpy.context, 'scene', None)
    if scene is not None:
        BaseColorNodePasses.sync_global_palette_nodes(scene)


def unregister_material_panel_state() -> None:
    global _palette_sync_timer_registered

    if _palette_sync_timer_registered and bpy.app.timers.is_registered(_run_deferred_dow2_palette_sync):
        bpy.app.timers.unregister(_run_deferred_dow2_palette_sync)
    _palette_sync_timer_registered = False

    if hasattr(bpy.types.Scene, 'dow2_global_palettes'):
        del bpy.types.Scene.dow2_global_palettes


__all__ = [
    "DOW2_GlobalPaletteSettings",
    "register_material_panel_state",
    "unregister_material_panel_state",
]