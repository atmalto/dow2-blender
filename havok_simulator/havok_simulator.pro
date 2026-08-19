TEMPLATE = app
TARGET = havok_simulator

QT += core gui opengl
CONFIG += qt warn_on

INCLUDEPATH += include

HAVOK_SDK_ROOT = $$(HAVOK_SDK_ROOT)
isEmpty(HAVOK_SDK_ROOT) {
    USERPROFILE_PATH = $$(USERPROFILE)
    !isEmpty(USERPROFILE_PATH) {
        USERPROFILE_PATH = $$replace(USERPROFILE_PATH, \\, /)
        HAVOK_SDK_ROOT = $$USERPROFILE_PATH/Desktop/Reverse Engineering/DoW2_Mod_tools/dow2_tools_working/working/havok_sdk_5_5_x
    }
}

isEmpty(HAVOK_SDK_ROOT) {
    error(HAVOK_SDK_ROOT is not set. Set the environment variable or pass the SDK path to build.sh.)
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

SOURCES += \
    src/app/add_force_dialog.cpp \
    src/app/add_object_dialog.cpp \
    src/app/app_theme.cpp \
    src/app/dialog_form_utils.cpp \
    src/app/main.cpp \
    src/app/main_window.cpp \
    src/app/main_window_ui_state.cpp \
    src/app/new_scene_dialog.cpp \
    src/app/physics_import_dialog.cpp \
    src/app/ragdoll_preview_window.cpp \
    src/app/ragdoll_properties_dialog.cpp \
    src/app/scene_file_commands.cpp \
    src/app/simulation_settings_dialog.cpp \
    src/io/physics_import.cpp \
    src/io/scene_persistence.cpp \
    src/render/capsule_render_utils.cpp \
    src/render/viewport_overlay_renderer.cpp \
    src/render/scene_body_renderer.cpp \
    src/render/ragdoll_preview_viewport.cpp \
    src/render/viewport_tool_controller.cpp \
    src/render/viewport_camera.cpp \
    src/sim/ragdoll_runtime_manager.cpp \
    src/sim/ragdoll_runtime.cpp \
    src/sim/ragdoll_runtime_controller.cpp \
    src/sim/scene_presets.cpp \
    src/sim/havok_serialize_registry.cpp \
    src/sim/ragdoll_preview_data.cpp \
    src/sim/scene_document.cpp \
    src/sim/simulation_controller.cpp \
    src/sim/simulation_world.cpp \
    src/sim/transform_session_controller.cpp \
    src/sim/simulation_settings.cpp \
    src/render/viewport_widget.cpp

HEADERS += \
    include/app_theme.h \
    include/body_render_state.h \
    include/capsule_render_utils.h \
    include/main_window.h \
    include/main_window_ui_state.h \
    include/new_scene_dialog.h \
    include/physics_import.h \
    include/physics_import_dialog.h \
    include/ragdoll_preview_data.h \
    include/ragdoll_runtime_diagnostics.h \
    include/ragdoll_runtime.h \
    include/ragdoll_runtime_controller.h \
    include/ragdoll_preview_viewport.h \
    include/ragdoll_preview_window.h \
    include/ragdoll_runtime_manager.h \
    include/scene_file_commands.h \
    include/scene_body_renderer.h \
    include/scene_document.h \
    include/scene_entity.h \
    include/scene_persistence.h \
    include/scene_presets.h \
    include/simulation_controller.h \
    include/simulation_world.h \
    include/simulation_settings.h \
    include/transform_session_controller.h \
    include/tool_dialogs.h \
    include/viewport_camera.h \
    include/viewport_overlay_renderer.h \
    include/viewport_tool_controller.h \
    include/viewport_widget.h

OBJECTS_DIR = .build/obj
MOC_DIR = .build/moc
RCC_DIR = .build/rcc
UI_DIR = .build/ui

CONFIG(release, debug|release) {
    DESTDIR = release
}
else {
    DESTDIR = build
}