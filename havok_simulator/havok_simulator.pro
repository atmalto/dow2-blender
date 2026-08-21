TEMPLATE = app
TARGET = havok_simulator

QT += core gui opengl
CONFIG += qt warn_on

# Shared engine core (Havok config + sim/io sources & headers).
include(sim_core.pri)

# --- GUI + render presentation layer (this target only) ----------------------
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
    src/render/capsule_render_utils.cpp \
    src/render/viewport_overlay_renderer.cpp \
    src/render/scene_body_renderer.cpp \
    src/render/ragdoll_preview_viewport.cpp \
    src/render/viewport_tool_controller.cpp \
    src/render/viewport_camera.cpp \
    src/render/viewport_widget.cpp

HEADERS += \
    include/app_theme.h \
    include/capsule_render_utils.h \
    include/main_window.h \
    include/main_window_ui_state.h \
    include/new_scene_dialog.h \
    include/physics_import_dialog.h \
    include/ragdoll_preview_viewport.h \
    include/ragdoll_preview_window.h \
    include/scene_file_commands.h \
    include/scene_body_renderer.h \
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