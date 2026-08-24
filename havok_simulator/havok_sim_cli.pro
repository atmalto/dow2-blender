TEMPLATE = app
TARGET = havok_sim_cli

# Console-only: no GUI, no OpenGL. QtCore is required because the shared engine
# core (scene_persistence.cpp) uses QtCore for scene XML I/O.
QT = core
CONFIG += console warn_on
CONFIG -= app_bundle

# Shared engine core (Havok config + sim/io sources & headers).
include(sim_core.pri)

# --- CLI driver (this target only) -------------------------------------------
SOURCES += \
    src/cli/main.cpp \
    src/cli/command_dispatch.cpp \
    src/cli/command_dispatch_common.cpp \
    src/cli/command_dispatch_scene.cpp \
    src/cli/command_dispatch_entities.cpp \
    src/cli/command_dispatch_imports.cpp \
    src/cli/command_dispatch_query.cpp \
    src/cli/json_value.cpp

HEADERS += \
    src/cli/command_dispatch.h \
    src/cli/command_dispatch_internal.h \
    src/cli/json_value.h

OBJECTS_DIR = .build_cli/obj
MOC_DIR = .build_cli/moc
RCC_DIR = .build_cli/rcc
UI_DIR = .build_cli/ui

CONFIG(release, debug|release) {
    DESTDIR = release
}
else {
    DESTDIR = build
}
