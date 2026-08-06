import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from . import presets


WORKFLOW_ITEMS = [
    (
        "BONE_INFLUENCES",
        "Bone Influences",
        "Create rigid body hulls from existing owner-bone vertex partitions. I.e. create hull from each bone's vertex group influences.",
    ),
    (
        "MESH_OBJECTS",
        "Mesh Objects",
        "Create one generated bone and one rigid body hull per source mesh. I.e. select a mesh, generate a hull and a respective bone for it that influences all of its vertices.",
    ),
]


class DOW2_PhysicsSettings(PropertyGroup):
    import_filepath: StringProperty(
        name="Physics File",
        description="Path to a DoW2 physics HKX file to import. XML is also accepted for development and debugging",
        subtype="FILE_PATH",
        default="",
    )

    workflow: EnumProperty(
        name="Workflow",
        description="Physics hull generation workflow. They both create valid physics systems, but with different use cases. ",
        #   \
        # "Bone Influences: is more automatic and creates hulls based on your existing bone vertex group weights. This assumes you " \
        # "have your vertices weighted with physics descruction in mind, i.e. a single solid object does not have two bones influencing it." \
        # "Mesh Objects: is for meshes that dont yet have a rig and are built with physics in mind first, it will create one hull per mesh, and " \
        # "a bone for each hull that influences all of its vertices under DoW2_Armature.",
        items=WORKFLOW_ITEMS,
        default="BONE_INFLUENCES",
    )

    use_selected_only: BoolProperty(
        name="Selected Only",
        description="Use only selected bones in Bone Influences mode, or selected meshes in Mesh Objects mode",
        default=False,
    )

    generation_preset: EnumProperty(
        name="Default Hull Preset",
        description="Preset assigned to newly generated hulls. This replaces the old static/dynamic toggle with the three corpus-backed motion presets.",
        items=presets.PRESET_ITEMS,
        default=presets.BUILDING_STATIC,
    )


classes = [
    DOW2_PhysicsSettings,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.dow2_physics_settings = PointerProperty(type=DOW2_PhysicsSettings)


def unregister():
    if hasattr(bpy.types.Scene, "dow2_physics_settings"):
        del bpy.types.Scene.dow2_physics_settings

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
