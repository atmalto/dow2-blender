#!/usr/bin/env bash
# Build the headless havok_sim_cli test driver (Qt 4.8.7 + VS2008 + Havok 5.5).
# Mirrors build.sh but targets havok_sim_cli.pro in a separate build dir and only
# ships QtCore (no GUI/OpenGL DLLs).
set -euo pipefail

BUILD_MODE="${1:-debug}"
SDK_ROOT_OVERRIDE="${2:-}"

VSROOT='/c/Program Files (x86)/Microsoft Visual Studio 9.0/VC'
VSIDE='/c/Program Files (x86)/Microsoft Visual Studio 9.0/Common7/IDE'
SDKROOT='/c/Program Files/Microsoft SDKs/Windows/v6.0A'
QTROOT='/c/Qt/4.8.7'
BUILD_DIR='build_cli'

case "$BUILD_MODE" in
	debug)
		export HAVOK_LIB_FLAVOR='debug_multithreaded'
		QMAKE_CONFIG=(CONFIG+=debug CONFIG-=release)
		NMAKE_TARGET='debug'
		OUTPUT_DIR='build'
		QT_DLLS=(QtCored4.dll)
		;;
	release)
		export HAVOK_LIB_FLAVOR='release_multithreaded'
		QMAKE_CONFIG=(CONFIG+=release CONFIG-=debug)
		NMAKE_TARGET='release'
		OUTPUT_DIR='release'
		QT_DLLS=(QtCore4.dll)
		;;
	*)
		echo "Usage: $0 [debug|release]" >&2
		exit 1
		;;
esac

export PATH="$QTROOT/bin:$VSROOT/bin:$VSIDE:$SDKROOT/bin:$PATH"
export INCLUDE="$(cygpath -w "$VSROOT/include");$(cygpath -w "$SDKROOT/include")"
export LIB="$(cygpath -w "$VSROOT/lib");$(cygpath -w "$SDKROOT/lib")"
export LIBPATH="$(cygpath -w "$VSROOT/lib")"

if [[ -n "$SDK_ROOT_OVERRIDE" ]]; then
	export HAVOK_SDK_ROOT="$(cygpath -m "$SDK_ROOT_OVERRIDE")"
elif [[ -z "${HAVOK_SDK_ROOT:-}" && -n "${USERPROFILE:-}" ]]; then
	export HAVOK_SDK_ROOT="$(cygpath -m "$USERPROFILE")/Desktop/Reverse Engineering/DoW2_Mod_tools/dow2_tools_working/working/havok_sdk_5_5_x"
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

qmake.exe ../havok_sim_cli.pro -spec win32-msvc2008 "${QMAKE_CONFIG[@]}"
nmake.exe clean || true
nmake.exe "$NMAKE_TARGET"

mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/QtCore4.dll "$OUTPUT_DIR"/QtCored4.dll

for qt_dll in "${QT_DLLS[@]}"; do
	cp "$QTROOT/bin/$qt_dll" "$OUTPUT_DIR/"
done
