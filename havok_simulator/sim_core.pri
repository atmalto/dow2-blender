# sim_core.pri
#
# Shared engine core for the Havok simulator. Included by BOTH the GUI target
# (havok_simulator.pro) and the headless CLI target (havok_sim_cli.pro) so they
# compile the identical sim/io sources with the identical Havok configuration.
#
# This file contributes NO Qt GUI/OpenGL dependency: the sim/ layer links Qt=core
# only (scene_persistence.cpp uses QtCore for XML; nothing here touches QtGui/OpenGL).
# Each including .pro decides its own QT modules and adds its own presentation layer.

INCLUDEPATH += $$PWD/include

# --- Havok 5.5 SDK resolution (shared) ---------------------------------------
HAVOK_SDK_ROOT = $$(HAVOK_SDK_ROOT)
isEmpty(HAVOK_SDK_ROOT) {
    USERPROFILE_PATH = $$(USERPROFILE)
    !isEmpty(USERPROFILE_PATH) {
        USERPROFILE_PATH = $$replace(USERPROFILE_PATH, \\, /)
        HAVOK_SDK_ROOT = $$USERPROFILE_PATH/Desktop/Reverse Engineering/DoW2_Mod_tools/dow2_tools_working/working/havok_sdk_5_5_x
    }
}

isEmpty(HAVOK_SDK_ROOT) {
    error(HAVOK_SDK_ROOT is not set. Set the environment variable or pass the SDK path to the build script.)
}

HAVOK_LIB_FLAVOR = $$(HAVOK_LIB_FLAVOR)
isEmpty(HAVOK_LIB_FLAVOR) {
    HAVOK_LIB_FLAVOR = debug_multithreaded
}

HAVOK_LIB_DIR = $$HAVOK_SDK_ROOT/Lib/win32_net_8-0/$$HAVOK_LIB_FLAVOR

INCLUDEPATH += $$quote($$HAVOK_SDK_ROOT/Source)
DEPENDPATH += $$quote($$HAVOK_SDK_ROOT/Source)

LIBS += -L$$quote($$HAVOK_LIB_DIR)
LIBS += -lhkBase -lhkCompat -lhkpCollide -lhkpConstraintSolver -lhkpDynamics -lhkpInternal -lhkpUtilities -lhkSceneData -lhkSerialize -lhkVisualize -lhkaAnimation -lhkaInternal -lhkaRagdoll

# --- Engine core sources (GUI-agnostic) --------------------------------------
SOURCES += \
    src/sim/ragdoll_runtime_manager.cpp \
    src/sim/ragdoll_runtime.cpp \
    src/sim/ragdoll_runtime_controller.cpp \
    src/sim/scene_presets.cpp \
    src/sim/havok_serialize_registry.cpp \
    src/sim/ragdoll_preview_data.cpp \
    src/sim/scene_document.cpp \
    src/sim/simulation_controller.cpp \
    src/sim/simulation_controller_core.cpp \
    src/sim/simulation_controller_scene.cpp \
    src/sim/simulation_controller_entities.cpp \
    src/sim/simulation_controller_ragdoll.cpp \
    src/sim/simulation_controller_selection.cpp \
    src/sim/simulation_world.cpp \
    src/sim/transform_session_controller.cpp \
    src/sim/simulation_settings.cpp \
    src/io/physics_import.cpp \
    src/io/scene_persistence.cpp

HEADERS += \
    include/body_render_state.h \
    include/physics_import.h \
    include/ragdoll_preview_data.h \
    include/ragdoll_runtime_diagnostics.h \
    include/ragdoll_runtime.h \
    include/ragdoll_runtime_controller.h \
    include/ragdoll_runtime_manager.h \
    include/scene_document.h \
    include/scene_entity.h \
    include/scene_persistence.h \
    include/scene_presets.h \
    include/simulation_controller.h \
    src/sim/simulation_controller_internal.h \
    include/simulation_world.h \
    include/simulation_settings.h \
    include/transform_session_controller.h
