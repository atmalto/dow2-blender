# Definition of hull physics properties, presets, and related utilities.
# The hull physics properties were derived from DoW2 World objects corpus, Havok 5.5 documentation and SDK, and some educated guesses
# An effort was made for UX friendliness, especially with defining commonly observed presets and exposing most material properties, while others remain hardcoded in the backend
# 1. DOW2_PhysicsHullSettings: a PropertyGroup defining all export-relevant physics properties for a convex hull; added update callbacks to propagate changes to all selected hulls
# 2. apply_preset_to_settings: applies a preset configuration to an instance of settings
# 3. snapshot_hull_settings: captures the current settings of a hull into a dictionary snapshot.
# 4. initialize_hull_settings: initializes a hull's settings based on a preset, with optional overrides from a snapshot or imported config
# 5. apply_imported_config: applies an imported physics config (e.g. from JSON) to the settings, inferring preset and handling center of mass logic
# 6. resolve_export_settings: computes the final export configuration for a hull based on its settings and preset defaults, ready for use by the exporter
# Together these hopefully provide multiple layers of default, override and validation logic for managing hull physics properties in a way that matches the observed patterns in the DoW2 data corpus

# Here's what each property intuitively represents in terms of the physics behavior of the hull:
# - mass: the actual mass value used by the exporter; for static bodies this is typically set to 0, while for dynamic bodies it can vary widely but common values are around 2-20
# - allowed_penetration_depth: how much interpenetration havok allows before it considers it a collision; static building bodies typically use a very large value (HK_REAL_MAX) to effectively disable penetration checks, while dynamic rubble bodies often use a small value like 0.1
#   - Docs: Havok describes this as a hint to the engine for how much CPU to spend preventing penetration, with a default of 0.05 and a good range of about 5% to 20% of the smallest object diameter (Havok Documentation 5.5.x.md, 3.2.3.1).
# - friction: how much resistance the hull has to sliding against other surfaces; building bodies often use 0.5, while rubble bodies can be 0.5 or 0.1
#   - Docs: friction is the initial surface-smoothness value for an hkpRigidBody, affecting how easily it slides, with a typical default of 0.5 and general range of 0 to 1 (Havok Documentation 5.5.x.md, 3.2.3.1).
# - restitution: how bouncy the hull is; building bodies often use 0.4, while rubble bodies can be 0.4 or 0.1
#   - Docs: restitution is the initial bounciness of an hkpRigidBody; 1 returns all energy, 0 stops completely, the default is 0.4, and Havok notes a hard limit of 1.99 (Havok Documentation 5.5.x.md, 3.2.3.1).
# - quality_type: a havok property that affects collision detection quality; building bodies often use 1 (fixed), while rubble bodies use 4 (moving)
#   - Docs: the rigid body's quality type controls how it interacts with other objects, is stored on the collidable, and is resolved per pair by the collision dispatcher (Havok Documentation 5.5.x.md, 3.2.3.1).
# - process_contact_callback_delay: a havok property that affects how often contact callbacks are processed; all analyzed bodies use 65535 which is the maximum value, effectively disabling the delay
#   - Docs: this sets how often process contact events are sent, and the default 65535 means the callback runs on the first collision and then only every 65535 frames until bodies leave collision tolerance (Havok Documentation 5.5.x.md, 3.2.3.1).
# - deactivation_class: a havok property that affects how the physics engine deactivates bodies that come to rest; building bodies often use 1 (never deactivate), while rubble bodies use 2 (deactivate when at rest)
#   - Docs: Havok deactivation is driven by each body having a deactivator; bodies can be kept awake with DEACTIVATOR_NEVER or deactivated via the spatial deactivation system once they settle (Havok Documentation 5.5.x.md, 3.2.3.6).
# - deactivation_integrate_counter: a havok property that works with deactivation_class to determine when a body should be deactivated; building bodies often use 255 (maximum), while rubble bodies use 15
#   - Docs: Havok uses high-frequency and low-frequency deactivation checks, roughly around 20 and 80 frames, with the counters reset whenever the body leaves the deactivation sphere (Havok Documentation 5.5.x.md, 3.2.3.6).
# - linear_damping: how much  hull's linear velocity is reduced over time; all analyzed bodies use 0.0
#   - Docs: linear damping is the initial linear slowdown for an hkpRigidBody, with Havok describing the default as 0.0 and stating it reduces motion over time (Havok Documentation 5.5.x.md, 3.2.3.1).
# - angular_damping: how much the hull's angular velocity is reduced over time; all analyzed bodies use 0.05
#   - Docs: angular damping is the rotational counterpart to linear damping, with Havok describing the default as 0.05 and noting it reduces angular motion over time (Havok Documentation 5.5.x.md, 3.2.3.1).
# - max_linear_velocity: maximum linear velocity the hull can have; all analyzed bodies use 200
#   - Docs: Havok treats max linear velocity as a hard limit built into the integrator, with a default limit of 200 m/s and a note that damping is better for gameplay-limited speed control (Havok Documentation 5.5.x.md, 3.2.3.1).
# - max_angular_velocity: maximum angular velocity the hull can have; all analyzed bodies use 200
#   - Docs: Havok treats max angular velocity as a hard limit as well, with angular velocity also clipped by a per-frame limit in the integrator (Havok Documentation 5.5.x.md, 3.2.3.1).
# - collision_filter_info: a Havok property that can be used to control collision filtering; all analyzed bodies use 0
# - collision_filter_info: a Havok property that can be used to control collision filtering; all analyzed bodies use 0
#   - Docs: collision filters use this value to identify an entity, such as assigning a collision group, and the default is 0 (Havok Documentation 5.5.x.md, 3.3.7).
# - event_filter: a havok property that can be used to control which events the body generates; corpus values are noisy so this is an advanced manual field
#   - Docs: the manual documents collision filtering around mcollisionFilterInfo, but does not give a stable standalone meaning for this byte, so this addon leaves it as a manual advanced field (Havok Documentation 5.5.x.md, 3.3.7).
# - user_filter: a Havok property that can be used for custom filtering; corpus values are noisy so this is an advanced manual field
#   - Docs: Havok documents collision filters as entity identifiers and collision-group selectors, but not a separate corpus-stable meaning for this byte, so this addon keeps it manual (Havok Documentation 5.5.x.md, 3.3.7).
# - center_of_mass_mode: controls how the exporter writes the center of mass; building bodies typically use ZERO, while rubble bodies default to COMPUTE_FROM_SHAPE
#   - Docs: the center of mass is stored in body local space, defaults to the local origin, and changing it does not move the rigid body itself (Havok Documentation 5.5.x.md, 3.2.3.1).
# - center_of_mass_override: custom center of mass vector that is used when center_of_mass_mode is set to CUSTOM; the exporter will write this value directly, but if the values are all close to zero, it will switch to ZERO mode to avoid precision issues
#   - Docs: Havok describes center of mass as a local-space property, often at the shape center for boxes and spheres, and explicitly notes that changing it does not change body position (Havok Documentation 5.5.x.md, 3.2.3.1).
# - shape_radius: the collision margin for the convex hull; all analyzed bodies use 0.05
#   - Docs: convex shapes can add a radius shell around the shape, the default radius is 0.05, and the shell becomes the collision surface for better convex-collision performance (Havok Documentation 5.5.x.md, 3.3.10.3).

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict

import bpy
from bpy.props import EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, PointerProperty
from bpy.types import PropertyGroup

from . import filter_presets, presets


_SUSPENDED_SETTINGS: set[int] = set()
RUBBLE_FIT_SCALE = 9.854851048671641
RUBBLE_FIT_EXPONENT = 0.2836330288405142
RUBBLE_AUTO_MASS_BINS = (3.0, 5.0, 10.0, 20.0)

HULL_SETTINGS_FIELDS = (
    "preset",
    "mass_preset",
    "mass",
    "allowed_penetration_depth",
    "friction",
    "restitution",
    "quality_type",
    "process_contact_callback_delay",
    "deactivation_class",
    "deactivation_integrate_counter",
    "linear_damping",
    "angular_damping",
    "max_linear_velocity",
    "max_angular_velocity",
    "collision_filter_info",
    "event_filter_preset",
    "event_filter",
    "user_filter_preset",
    "user_filter",
    "center_of_mass_mode",
    "center_of_mass_override",
    "shape_radius",
)

_INT_ENUM_FIELDS = {
    "quality_type",
    "deactivation_class",
}

_STRING_ENUM_FIELDS = {
    "preset",
    "mass_preset",
    "event_filter_preset",
    "user_filter_preset",
    "center_of_mass_mode",
}

_VECTOR_FIELDS = {
    "center_of_mass_override",
}


def _settings_key(settings: PropertyGroup) -> int:
    return settings.as_pointer()


@contextmanager
def suspend_updates(settings: PropertyGroup):
    key = _settings_key(settings)
    _SUSPENDED_SETTINGS.add(key)
    try:
        yield
    finally:
        _SUSPENDED_SETTINGS.discard(key)


def _is_suspended(settings: PropertyGroup) -> bool:
    return _settings_key(settings) in _SUSPENDED_SETTINGS


def _normalize_field_value(field_name: str, value: Any) -> Any:
    if field_name in _INT_ENUM_FIELDS:
        return str(int(value))
    if field_name in _STRING_ENUM_FIELDS:
        return str(value)
    if field_name in _VECTOR_FIELDS:
        return [float(component) for component in value]
    return value


def _apply_settings_data(settings: PropertyGroup, data: Dict[str, Any]) -> None:
    with suspend_updates(settings):
        for field_name in HULL_SETTINGS_FIELDS:
            if field_name not in data:
                continue
            setattr(settings, field_name, _normalize_field_value(field_name, data[field_name]))
        _sync_filter_preset_fields(settings)


def _owner_object(settings: PropertyGroup) -> bpy.types.Object | None:
    owner = getattr(settings, "id_data", None)
    return owner if isinstance(owner, bpy.types.Object) else None


def _copy_field_value(settings: PropertyGroup, field_name: str) -> Any:
    value = getattr(settings, field_name)
    if field_name == "center_of_mass_override":
        return list(value)
    return value


def _propagate_fields_to_selected(settings: PropertyGroup, context: bpy.types.Context, field_names: tuple[str, ...]) -> None:
    owner = _owner_object(settings)
    if owner is None or context is None:
        return

    payload = {field_name: _copy_field_value(settings, field_name) for field_name in field_names}
    for obj in context.selected_objects:
        if obj == owner or not obj.get("dow2_physics_hull", False) or not hasattr(obj, "dow2_physics_hull_settings"):
            continue
        _apply_settings_data(obj.dow2_physics_hull_settings, payload)


def _sync_filter_preset_field(
    settings: PropertyGroup,
    *,
    preset_field_name: str,
    value_field_name: str,
    filter_kind: str,
) -> None:
    raw_value = int(getattr(settings, value_field_name))
    setattr(settings, preset_field_name, filter_presets.preset_id_for_value(filter_kind, raw_value))


def _sync_filter_preset_fields(settings: PropertyGroup) -> None:
    _sync_filter_preset_field(
        settings,
        preset_field_name="event_filter_preset",
        value_field_name="event_filter",
        filter_kind=filter_presets.EVENT_FILTER_KIND,
    )
    _sync_filter_preset_field(
        settings,
        preset_field_name="user_filter_preset",
        value_field_name="user_filter",
        filter_kind=filter_presets.USER_FILTER_KIND,
    )


def _make_selected_field_update(*field_names: str):
    def _update(self: PropertyGroup, context: bpy.types.Context) -> None:
        if _is_suspended(self):
            return
        _propagate_fields_to_selected(self, context, field_names)

    return _update


def _on_preset_changed(self: PropertyGroup, context: bpy.types.Context) -> None:
    if _is_suspended(self):
        return
    apply_preset_to_settings(self, self.preset)
    _propagate_fields_to_selected(self, context, HULL_SETTINGS_FIELDS)


def _on_mass_preset_changed(self: PropertyGroup, context: bpy.types.Context) -> None:
    if _is_suspended(self):
        return
    preset_value = presets.mass_value_from_preset(self.mass_preset)
    if preset_value is None:
        return
    with suspend_updates(self):
        self.mass = preset_value
    _propagate_fields_to_selected(self, context, ("mass_preset", "mass"))


def _on_mass_changed(self: PropertyGroup, context: bpy.types.Context) -> None:
    if _is_suspended(self):
        return
    with suspend_updates(self):
        self.mass_preset = presets.mass_preset_for_value(self.mass)
    _propagate_fields_to_selected(self, context, ("mass", "mass_preset"))


def _filter_preset_items(filter_kind: str):
    def _items(self: PropertyGroup, context: bpy.types.Context):
        try:
            return filter_presets.enum_items_for_filter_kind(filter_kind)
        except Exception:
            return [
                (
                    filter_presets.CUSTOM_PRESET_ID,
                    "Library Load Failed",
                    "The frozen physics filter preset library could not be loaded. Use the raw override field.",
                )
            ]

    return _items


def _on_filter_preset_changed(
    self: PropertyGroup,
    context: bpy.types.Context,
    *,
    preset_field_name: str,
    value_field_name: str,
    filter_kind: str,
) -> None:
    if _is_suspended(self):
        return
    raw_value = filter_presets.value_from_preset(filter_kind, getattr(self, preset_field_name))
    if raw_value is not None:
        with suspend_updates(self):
            setattr(self, value_field_name, int(raw_value))
    _propagate_fields_to_selected(self, context, (preset_field_name, value_field_name))


def _on_filter_value_changed(
    self: PropertyGroup,
    context: bpy.types.Context,
    *,
    preset_field_name: str,
    value_field_name: str,
    filter_kind: str,
) -> None:
    if _is_suspended(self):
        return
    with suspend_updates(self):
        _sync_filter_preset_field(
            self,
            preset_field_name=preset_field_name,
            value_field_name=value_field_name,
            filter_kind=filter_kind,
        )
    _propagate_fields_to_selected(self, context, (preset_field_name, value_field_name))


def _on_event_filter_preset_changed(self: PropertyGroup, context: bpy.types.Context) -> None:
    _on_filter_preset_changed(
        self,
        context,
        preset_field_name="event_filter_preset",
        value_field_name="event_filter",
        filter_kind=filter_presets.EVENT_FILTER_KIND,
    )


def _on_event_filter_changed(self: PropertyGroup, context: bpy.types.Context) -> None:
    _on_filter_value_changed(
        self,
        context,
        preset_field_name="event_filter_preset",
        value_field_name="event_filter",
        filter_kind=filter_presets.EVENT_FILTER_KIND,
    )


def _on_user_filter_preset_changed(self: PropertyGroup, context: bpy.types.Context) -> None:
    _on_filter_preset_changed(
        self,
        context,
        preset_field_name="user_filter_preset",
        value_field_name="user_filter",
        filter_kind=filter_presets.USER_FILTER_KIND,
    )


def _on_user_filter_changed(self: PropertyGroup, context: bpy.types.Context) -> None:
    _on_filter_value_changed(
        self,
        context,
        preset_field_name="user_filter_preset",
        value_field_name="user_filter",
        filter_kind=filter_presets.USER_FILTER_KIND,
    )


class DOW2_PhysicsHullSettings(PropertyGroup):
    preset: EnumProperty(
        name="Preset",
        description="Semantic meaning: the main starting profile for a hull, so you can begin from a static building setup or one of the common dynamic rubble setups instead of filling every field by hand. Corpus use: Static Objects matches the building corpus, while the two rubble presets match the dominant dynamic debris families.",
        items=presets.PRESET_ITEMS,
        default=presets.BUILDING_STATIC,
        update=_on_preset_changed,
    )

    mass_preset: EnumProperty(
        name="Common Mass",
        description="Semantic meaning: a quick picker for common authored mass values, so you can land on a shipped-style weight before fine-tuning the raw mass number. Corpus use: the most frequent inferred rubble masses were 5, 3, 2, 10, 20, 7, and 15.",
        items=presets.MASS_PRESET_ITEMS,
        default="MASS_5",
        update=_on_mass_preset_changed,
    )

    mass: FloatProperty(
        name="Mass",
        description="Semantic meaning: how heavy the rigid body is when it moves, which strongly affects how hard it is to push and how much force it carries into impacts. Corpus use: common authored dynamic masses include 5, 3, 2, 10, 20, 7, 15, 4, 6, 8, and 12, while static building bodies resolve to zero mass.",
        default=5.0,
        min=0.0,
        soft_max=100.0,
        precision=3,
        update=_on_mass_changed,
    )

    allowed_penetration_depth: FloatProperty(
        name="Penetration",
        description="Semantic meaning: how much overlap Havok tolerates before it spends effort pushing bodies apart, so bigger values are looser and smaller values are stricter. Corpus use: building bodies usually use HK_REAL_MAX, while rubble is usually 0.1 with a few smaller authored values.",
        default=presets.HK_REAL_MAX,
        min=0.0,
        precision=6,
        update=_make_selected_field_update("allowed_penetration_depth"),
    )

    friction: FloatProperty(
        name="Friction",
        description="Semantic meaning: how strongly the hull resists sliding across other surfaces, so higher values grip more and lower values slip more. Corpus use: building bodies use 0.5, while rubble is mostly 0.5 or 0.1 with rarer 0.2 and 0.3.",
        default=0.5,
        min=0.0,
        soft_max=1.0,
        precision=3,
        update=_make_selected_field_update("friction"),
    )

    restitution: FloatProperty(
        name="Restitution",
        description="Semantic meaning: how bouncy the hull is when it hits something, so higher values keep more bounce and lower values die out faster. Corpus use: building bodies are almost always 0.4, while rubble is mainly 0.4 or 0.1 with rare 0.2, 0.3, and 0.0.",
        default=0.4,
        min=0.0,
        max=1.0,
        precision=3,
        update=_make_selected_field_update("restitution"),
    )

    quality_type: EnumProperty(
        name="Quality Type",
        description="Semantic meaning: the Havok collision-quality mode, which tells the solver whether this body behaves like a fixed object or a moving one. Corpus use: building bodies use quality type 1, while rubble bodies use quality type 4.",
        items=presets.QUALITY_TYPE_ITEMS,
        default="1",
        update=_make_selected_field_update("quality_type"),
    )

    process_contact_callback_delay: IntProperty(
        name="Contact Callback Delay",
        description="Semantic meaning: a rate limiter for process-contact callbacks, so larger values make that repeated callback happen less often after the first hit. Corpus use: all analyzed building and rubble bodies use 65535.",
        default=65535,
        min=0,
        max=65535,
        update=_make_selected_field_update("process_contact_callback_delay"),
    )

    deactivation_class: EnumProperty(
        name="Deactivation Class",
        description="Semantic meaning: whether the body behaves like something that stays awake forever or something that is allowed to go to sleep when it settles. Corpus use: building bodies use deactivation class 1, while rubble bodies use deactivation class 2.",
        items=presets.DEACTIVATION_CLASS_ITEMS,
        default="1",
        update=_make_selected_field_update("deactivation_class"),
    )

    deactivation_integrate_counter: IntProperty(
        name="Deactivation Counter",
        description="Semantic meaning: the motion-state sleep counter that works with the deactivation class to decide how long a moving body keeps integrating before it can settle down. Corpus use: building bodies use 255, while rubble bodies use 15.",
        default=255,
        min=0,
        max=255,
        update=_make_selected_field_update("deactivation_integrate_counter"),
    )

    linear_damping: FloatProperty(
        name="Linear Damping",
        description="Semantic meaning: how much straight-line motion is slowly drained away over time, so higher values make a body lose travel speed faster. Corpus use: all analyzed building and rubble bodies use 0.0.",
        default=0.0,
        min=0.0,
        precision=4,
        update=_make_selected_field_update("linear_damping"),
    )

    angular_damping: FloatProperty(
        name="Angular Damping",
        description="Semantic meaning: how much spin is slowly drained away over time, so higher values make a body stop rotating faster. Corpus use: all analyzed building and rubble bodies use 0.05.",
        default=0.05,
        min=0.0,
        precision=4,
        update=_make_selected_field_update("angular_damping"),
    )

    max_linear_velocity: FloatProperty(
        name="Max Linear Velocity",
        description="Semantic meaning: a hard cap on straight-line speed, so the body cannot move faster than this even if forces try to push it harder. Corpus use: all analyzed building and rubble bodies use 200.",
        default=200.0,
        min=0.0,
        precision=3,
        update=_make_selected_field_update("max_linear_velocity"),
    )

    max_angular_velocity: FloatProperty(
        name="Max Angular Velocity",
        description="Semantic meaning: a hard cap on spin speed, so the body cannot rotate faster than this even if forces try to spin it harder. Corpus use: all analyzed building and rubble bodies use 200.",
        default=200.0,
        min=0.0,
        precision=3,
        update=_make_selected_field_update("max_angular_velocity"),
    )

    collision_filter_info: IntProperty(
        name="Collision Filter Info",
        description="Semantic meaning: the separate Havok collision-layer or collision-group integer used by collision filters, which is not the same thing as the callback filter bytes below. Corpus use: all analyzed building and rubble bodies use 0.",
        default=0,
        min=0,
        max=2147483647,
        update=_make_selected_field_update("collision_filter_info"),
    )

    event_filter_preset: EnumProperty(
        name="Event Filter Preset",
        description="Choose a shipped event_filter byte from the frozen preset library. Corpus use: labels show representative HKX names and raw values, while the override control is there for rare authored bytes that are not in the lean preset set.",
        items=_filter_preset_items(filter_presets.EVENT_FILTER_KIND),
        update=_on_event_filter_preset_changed,
    )

    event_filter: IntProperty(
        name="Event Filter",
        description="Known behavior: this is the raw callback-event byte, where the low bits are the documented Havok contact event bits and the higher bits behave like unresolved extension flags. Corpus use: the world-object corpus uses many authored values here, so start from a preset and only override the raw byte when matching a specific shipped body.",
        default=0,
        min=0,
        max=255,
        update=_on_event_filter_changed,
    )

    user_filter_preset: EnumProperty(
        name="User Filter Preset",
        description="Choose a shipped user_filter byte from the frozen preset library. Corpus use: the curated list focuses on repeated values such as 0, 14, 62, 63, 190, and 191, while the override control remains available for rarer authored masks.",
        items=_filter_preset_items(filter_presets.USER_FILTER_KIND),
        update=_on_user_filter_preset_changed,
    )

    user_filter: IntProperty(
        name="User Filter",
        description="Known behavior: this is the raw shared-bit callback-family byte rather than a unique object ID, but the exact game-specific names for the bits are still not fully recovered. Corpus use: most shipped bodies cluster around 0, 14, 62, 63, 190, and 191, so use a preset first and reserve manual overrides for rare authored masks.",
        default=0,
        min=0,
        max=255,
        update=_on_user_filter_changed,
    )

    center_of_mass_mode: EnumProperty(
        name="Center Of Mass",
        description="Semantic meaning: how the exporter decides the hull's local center of mass, so you can force zero, compute it from the hull shape, or write a custom value. Corpus use: building-style exports use Zero, while rubble defaults to Compute From Shape.",
        items=presets.CENTER_OF_MASS_MODE_ITEMS,
        default="ZERO",
        update=_make_selected_field_update("center_of_mass_mode"),
    )

    center_of_mass_override: FloatVectorProperty(
        name="Center Of Mass Override",
        description="Semantic meaning: the exact local-space center of mass vector written by the exporter when Center Of Mass mode is set to Custom Override. Corpus use: this is mainly for matching authored Havok data exactly, not the common building or rubble defaults.",
        default=(0.0, 0.0, 0.0),
        size=3,
        precision=6,
        update=_make_selected_field_update("center_of_mass_override"),
    )

    shape_radius: FloatProperty(
        name="Shape Radius",
        description="Semantic meaning: the convex-hull collision shell or margin wrapped around the shape, which helps Havok handle convex collisions more robustly. Corpus use: analyzed building and rubble convex hulls use 0.05.",
        default=0.05,
        min=0.0,
        precision=4,
        update=_make_selected_field_update("shape_radius"),
    )


def apply_preset_to_settings(settings: PropertyGroup, preset_id: str) -> None:
    defaults = presets.get_preset_defaults(preset_id)
    _apply_settings_data(settings, defaults)


def _nearest_rubble_mass_bin(value: float) -> float:
    return min(RUBBLE_AUTO_MASS_BINS, key=lambda candidate: (abs(candidate - value), candidate))


def _predict_rubble_mass_from_volume(volume: float) -> float:
    clamped_volume = max(float(volume), 1.0e-6)
    predicted_mass = RUBBLE_FIT_SCALE * (clamped_volume ** RUBBLE_FIT_EXPONENT)
    return _nearest_rubble_mass_bin(predicted_mass)


def apply_generated_rubble_mass_fit(settings: PropertyGroup, preset_id: str, generated_volume: float | None) -> None:
    if preset_id not in {presets.RUBBLE_BOX, presets.RUBBLE_SPHERE}:
        return
    if generated_volume is None or generated_volume <= 0.0:
        return
    fitted_mass = _predict_rubble_mass_from_volume(generated_volume)
    _apply_settings_data(
        settings,
        {
            "mass": fitted_mass,
            "mass_preset": presets.mass_preset_for_value(fitted_mass),
        },
    )


def snapshot_hull_settings(obj: bpy.types.Object | None) -> Dict[str, Any] | None:
    if obj is None or not hasattr(obj, "dow2_physics_hull_settings"):
        return None
    settings = obj.dow2_physics_hull_settings
    snapshot: Dict[str, Any] = {}
    for field_name in HULL_SETTINGS_FIELDS:
        value = getattr(settings, field_name)
        if field_name == "center_of_mass_override":
            snapshot[field_name] = list(value)
        else:
            snapshot[field_name] = value
    return snapshot


def initialize_hull_settings(
    obj: bpy.types.Object,
    default_preset: str,
    snapshot: Dict[str, Any] | None = None,
    imported_config: Dict[str, Any] | None = None,
) -> None:
    settings = obj.dow2_physics_hull_settings
    if imported_config:
        apply_imported_config(settings, imported_config)
        return
    if snapshot:
        _apply_settings_data(settings, snapshot)
        return
    apply_preset_to_settings(settings, default_preset)


def apply_imported_config(settings: PropertyGroup, imported_config: Dict[str, Any]) -> None:
    preset_id = presets.infer_preset_from_motion_type(str(imported_config.get("motion_type") or "FIXED"))
    merged = presets.get_preset_defaults(preset_id)
    merged["preset"] = preset_id

    if "mass" in imported_config and imported_config["mass"] is not None:
        merged["mass"] = float(imported_config["mass"])
        merged["mass_preset"] = presets.mass_preset_for_value(float(imported_config["mass"]))

    for field_name in HULL_SETTINGS_FIELDS:
        if field_name in {"preset", "mass", "mass_preset"}:
            continue
        if field_name in imported_config and imported_config[field_name] is not None:
            merged[field_name] = imported_config[field_name]

    center = imported_config.get("center_of_mass_override")
    if center is not None:
        if all(abs(float(value)) <= 1.0e-6 for value in center[:3]):
            merged["center_of_mass_mode"] = "ZERO"
            merged["center_of_mass_override"] = [0.0, 0.0, 0.0]
        else:
            merged["center_of_mass_mode"] = "CUSTOM"
            merged["center_of_mass_override"] = list(center[:3])

    _apply_settings_data(settings, merged)


def resolve_export_settings(obj: bpy.types.Object) -> Dict[str, Any]:
    settings = obj.dow2_physics_hull_settings
    preset_id = settings.preset or presets.BUILDING_STATIC
    config = presets.get_preset_defaults(preset_id)

    config.update(
        {
            "preset": preset_id,
            "motion_type": presets.motion_type_for_preset(preset_id),
            "mass": float(settings.mass),
            "allowed_penetration_depth": float(settings.allowed_penetration_depth),
            "friction": float(settings.friction),
            "restitution": float(settings.restitution),
            "quality_type": int(settings.quality_type),
            "process_contact_callback_delay": int(settings.process_contact_callback_delay),
            "deactivation_class": int(settings.deactivation_class),
            "deactivation_integrate_counter": int(settings.deactivation_integrate_counter),
            "linear_damping": float(settings.linear_damping),
            "angular_damping": float(settings.angular_damping),
            "max_linear_velocity": float(settings.max_linear_velocity),
            "max_angular_velocity": float(settings.max_angular_velocity),
            "collision_filter_info": int(settings.collision_filter_info),
            "event_filter": int(settings.event_filter),
            "user_filter": int(settings.user_filter),
            "center_of_mass_mode": settings.center_of_mass_mode,
            "center_of_mass_override": [float(value) for value in settings.center_of_mass_override],
            "shape_radius": float(settings.shape_radius),
            "response_type": "RESPONSE_SIMPLE_CONTACT",
            "deactivator_present": presets.deactivator_present_for_preset(preset_id),
        }
    )

    if preset_id == presets.BUILDING_STATIC:
        config["mass"] = 0.0
        config["center_of_mass_mode"] = "ZERO"
        config["center_of_mass_override"] = [0.0, 0.0, 0.0]
    elif config["center_of_mass_mode"] == "ZERO":
        config["center_of_mass_override"] = [0.0, 0.0, 0.0]

    return config


classes = [
    DOW2_PhysicsHullSettings,
]


def register() -> None:
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.dow2_physics_hull_settings = PointerProperty(type=DOW2_PhysicsHullSettings)


def unregister() -> None:
    if hasattr(bpy.types.Object, "dow2_physics_hull_settings"):
        del bpy.types.Object.dow2_physics_hull_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


__all__ = [
    "DOW2_PhysicsHullSettings",
    "HULL_SETTINGS_FIELDS",
    "apply_generated_rubble_mass_fit",
    "apply_imported_config",
    "apply_preset_to_settings",
    "initialize_hull_settings",
    "register",
    "resolve_export_settings",
    "snapshot_hull_settings",
    "unregister",
]