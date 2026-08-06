from __future__ import annotations

from typing import Optional

import bpy

from .affine import coerce_sequence
from .defs import BADGE_SLOTS


def is_badge_material(material: Optional[bpy.types.Material]) -> bool:
    if material is None:
        return False

    shader_name = str(material.get("dow2_shader", "") or "").strip().lower()
    shader_profile = str(material.get("dow2_shader_profile", "") or "").strip().lower()
    shader_vars = {
        item.strip().lower()
        for item in str(material.get("dow2_shader_vars", "") or "").split(",")
        if item.strip()
    }
    has_badge_texture = any(
        str(material.get(f'dow2_{texture_key}', '') or '').strip()
        for _slot_name, _label, texture_key, _matrix_key, _translate_key in BADGE_SLOTS
    )
    has_badge_transform = any(
        coerce_sequence(material.get(f'dow2_{matrix_key}')) or coerce_sequence(material.get(f'dow2_{translate_key}'))
        for _slot_name, _label, _texture_key, matrix_key, translate_key in BADGE_SLOTS
    )

    if has_badge_texture or has_badge_transform:
        return True
    if shader_profile in {"unit", "wargear"} and bool({"badge1tex", "badge2tex"} & shader_vars):
        return True
    if (shader_name.startswith("dow2_unit") or shader_name.startswith("dow2_wargear")) and bool({"badge1tex", "badge2tex"} & shader_vars):
        return True
    return bool({"badge1tex", "badge2tex"} & shader_vars)


__all__ = ["is_badge_material"]