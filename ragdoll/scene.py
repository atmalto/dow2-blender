import bpy


def import_model(filepath):
    result = bpy.ops.import_scene.dow2_model(
        filepath=filepath,
        import_meshes=True,
        import_materials=False,
        import_bones=True,
        import_markers=False,
        reset_scene=True,
    )
    return {"FINISHED"} if result == {"FINISHED"} else result


def get_armature():
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None