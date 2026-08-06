import bpy
from bpy.types import Panel

from ..physics import hull_properties, presets, utils


def _draw_quick_float_row(layout, hull_obj, label, property_name, quick_values):
    settings = hull_obj.dow2_physics_hull_settings
    row = layout.row(align=True)
    row.label(text=label)
    for value in quick_values:
        button = row.operator("dow2.set_selected_hull_physics_value", text="Max" if value >= presets.HK_REAL_MAX else f"{value:g}")
        button.property_name = property_name
        button.value = float(value)
    row.prop(settings, property_name, text="")


def _draw_filter_preset_row(layout, settings, label, preset_property_name, override_property_name):
    row = layout.row(align=True)
    row.prop(settings, preset_property_name, text=label)
    row.prop(settings, override_property_name, text="Override", slider=True)


def _draw_selected_hull_section(layout, context):
    header, body = layout.panel("dow2_physics_selected_hull", default_closed=False)
    header.label(text="Selected Hull Physics", icon="PROPERTIES")
    if body is None:
        return

    active_obj = context.active_object
    if active_obj is None or not utils.is_physics_hull_object(active_obj):
        body.label(text="Select a generated hull to edit its export settings", icon="INFO")
        return

    settings = active_obj.dow2_physics_hull_settings
    selected_hull_count = sum(1 for obj in context.selected_objects if utils.is_physics_hull_object(obj))

    info_box = body.box()
    info_box.label(text=f"Body: {utils.get_hull_body_name(active_obj)}", icon="MESH_ICOSPHERE")
    info_box.label(text=f"State: {active_obj.get(utils.STATE_PROP, 'unknown')}   LoD: {active_obj.get(utils.LOD_PROP, 0)}")
    if selected_hull_count > 1:
        info_box.label(text=f"Applying edits to all {selected_hull_count} selected hulls", icon="RESTRICT_SELECT_OFF")

    basic_box = body.box()
    basic_box.label(text="Basic", icon="SETTINGS")
    basic_box.prop(settings, "preset")

    mass_row = basic_box.row(align=True)
    mass_row.label(text="Mass")
    mass_row.prop(settings, "mass_preset", text="")
    mass_row.prop(settings, "mass", text="", slider=True)

    _draw_quick_float_row(basic_box, active_obj, "Penetration", "allowed_penetration_depth", presets.PENETRATION_QUICK_VALUES)
    _draw_quick_float_row(basic_box, active_obj, "Friction", "friction", presets.FRICTION_QUICK_VALUES)
    _draw_quick_float_row(basic_box, active_obj, "Restitution", "restitution", presets.RESTITUTION_QUICK_VALUES)

    advanced_box = body.box()
    advanced_box.label(text="Advanced", icon="PREFERENCES")
    advanced_box.prop(settings, "quality_type")
    advanced_box.prop(settings, "process_contact_callback_delay")
    advanced_box.prop(settings, "deactivation_class")
    advanced_box.prop(settings, "deactivation_integrate_counter")
    advanced_box.prop(settings, "linear_damping")
    advanced_box.prop(settings, "angular_damping")
    velocity_row = advanced_box.row(align=True)
    velocity_row.prop(settings, "max_linear_velocity")
    velocity_row.prop(settings, "max_angular_velocity")
    advanced_box.prop(settings, "collision_filter_info")
    _draw_filter_preset_row(advanced_box, settings, "Event Filter", "event_filter_preset", "event_filter")
    _draw_filter_preset_row(advanced_box, settings, "User Filter", "user_filter_preset", "user_filter")
    advanced_box.prop(settings, "center_of_mass_mode")
    if settings.center_of_mass_mode == "CUSTOM":
        advanced_box.prop(settings, "center_of_mass_override")
    advanced_box.prop(settings, "shape_radius")

    effective = hull_properties.resolve_export_settings(active_obj)
    effective_box = body.box()
    effective_box.label(text="Effective Export Values", icon="INFO")
    effective_box.label(text=f"Motion: {effective['motion_type']}")
    effective_box.label(text=f"Quality: {effective['quality_type']}   Deactivator: {effective['deactivator_present']}")
    effective_box.label(text=f"Mass: {effective['mass']:.3f}   Shape Radius: {effective['shape_radius']:.3f}")
    effective_box.label(text=f"Response: {effective['response_type']}   Collision Filter: {effective['collision_filter_info']}")


class DOW2_PT_physics_panel(Panel):
    """DoW2 destruction physics generation and export"""

    bl_label = "Physics (Experimental)"
    bl_idname = "DOW2_PT_physics_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_order = 55
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.dow2_physics_settings

        import_header, import_body = layout.panel("dow2_physics_import", default_closed=False)
        import_header.label(text="Import", icon="IMPORT")
        if import_body is not None:
            import_row = import_body.row(align=True)
            split = import_row.split(factor=0.8, align=True)
            split.prop(settings, "import_filepath", text="")
            split.operator("dow2.import_physics_hulls", text="Import Hulls", icon="IMPORT")

        export_header, export_body = layout.panel("dow2_physics_export", default_closed=False)
        export_header.label(text="Export", icon="EXPORT")
        if export_body is not None:
            settings_box = export_body.box()
            settings_box.label(text="Workflow", icon="PHYSICS")
            settings_box.prop(settings, "workflow", text="")
            settings_box.prop(settings, "generation_preset")

            selection_label = "Selected Bones Only" if settings.workflow == "BONE_INFLUENCES" else "Selected Meshes Only"
            settings_box.prop(settings, "use_selected_only", text=selection_label)

            description_box = export_body.box()
            if settings.workflow == "BONE_INFLUENCES":
                description_box.label(text="Generate one hull per owner bone per state/LoD bin", icon="BONE_DATA")
            else:
                description_box.label(text="Generate one hull and one centered bone per source mesh", icon="MESH_DATA")

            generate_row = export_body.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)
            generate_row.operator("dow2.generate_physics_hulls", icon="MESH_ICOSPHERE")
            generate_row.operator("dow2.export_physics_hulls", icon="EXPORT")

            visibility_row = export_body.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=True, align=True)
            visibility_row.operator("dow2.clear_physics_hulls", text="Clear Hulls", icon="TRASH")
            visibility_row.operator("dow2.isolate_physics_hulls", text="Show Hulls", icon="HIDE_OFF")
            visibility_row.operator("dow2.hide_physics_hulls", text="Hide Hulls", icon="HIDE_ON")

        _draw_selected_hull_section(layout, context)

        header, body = layout.panel("dow2_physics_bins", default_closed=True)
        header.label(text="Physics Bins", icon="OUTLINER_COLLECTION")
        if body is None:
            return

        hull_map = utils.collect_physics_hulls(context.scene)

        total_states = 0
        total_hulls = 0
        for state_name in utils.STATE_NAMES:
            lod_map = hull_map.get(state_name, {})
            state_hull_count = sum(len(items) for items in lod_map.values())
            total_hulls += state_hull_count
            if state_hull_count:
                total_states += 1

            state_box = body.box()
            state_box.label(text=f"{state_name} ({state_hull_count} hulls)", icon="OUTLINER_COLLECTION")
            if not lod_map:
                state_box.label(text="none", icon="INFO")
                continue

            for lod_level in sorted(lod_map.keys()):
                lod_box = state_box.box()
                lod_box.label(text=f"lod{lod_level}", icon="OUTLINER_COLLECTION")
                hull_objects = sorted(
                    lod_map[lod_level],
                    key=lambda obj: (utils.get_hull_body_name(obj).lower(), obj.name.lower()),
                )
                for hull_obj in hull_objects:
                    lod_box.label(text=utils.get_hull_body_name(hull_obj), icon="MESH_ICOSPHERE")

        footer = body.box()
        footer.label(text=f"Populated physics states: {total_states}")
        footer.label(text=f"Generated hulls total: {total_hulls}")


PHYSICS_PANEL_CLASSES = [
    DOW2_PT_physics_panel,
]


__all__ = [
    "DOW2_PT_physics_panel",
    "PHYSICS_PANEL_CLASSES",
]