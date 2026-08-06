@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "BUILD_ROOT=%SCRIPT_DIR%.build"
set "OBJ_ROOT=%BUILD_ROOT%\obj"

set "VSINSTALLDIR=C:\Program Files (x86)\Microsoft Visual Studio 9.0"
set "VCINSTALLDIR=%VSINSTALLDIR%\VC"
set "FrameworkDir=C:\Windows\Microsoft.NET\Framework"
set "FrameworkVersion=v2.0.50727"
set "Framework35Version=v3.5"

set "PATH=%VCINSTALLDIR%\bin;%VSINSTALLDIR%\Common7\IDE;%FrameworkDir%\%Framework35Version%;%FrameworkDir%\%FrameworkVersion%;%PATH%"
set "INCLUDE=%VCINSTALLDIR%\include;C:\Program Files\Microsoft SDKs\Windows\v6.0A\Include;%INCLUDE%"
set "LIB=%VCINSTALLDIR%\lib;C:\Program Files\Microsoft SDKs\Windows\v6.0A\Lib;%LIB%"

if defined HAVOK_SDK_ROOT (
	set "HAVOK_SDK=%HAVOK_SDK_ROOT%"
) else if exist "C:\Users\Moham\Desktop\Reverse Engineering\DoW2_Mod_tools\dow2_tools_working\working\havok_sdk_5_5_x\Source" (
	set "HAVOK_SDK=C:\Users\Moham\Desktop\Reverse Engineering\DoW2_Mod_tools\dow2_tools_working\working\havok_sdk_5_5_x"
) else (
	set "HAVOK_SDK=%SCRIPT_DIR%..\working\havok_sdk_5_5_x"
)

set "HAVOK_INC=%HAVOK_SDK%\Source"
set "HAVOK_LIB=%HAVOK_SDK%\Lib\win32_net_8-0\release_multithreaded"

set CL_FLAGS=/nologo /EHsc /MT /O2 /W3 /D "WIN32" /D "NDEBUG" /D "_CONSOLE" /D "_UNICODE" /D "UNICODE" /D "_CRT_SECURE_NO_WARNINGS"
set COMMON_INCLUDES=/I"include" /I"src\core" /I"src\animation" /I"src\physics" /I"src\ragdoll" /I"src\hkanim" /I"%HAVOK_INC%" /I"%HAVOK_INC%\Common" /I"%HAVOK_INC%\Animation" /I"%HAVOK_INC%\Physics"
set HAVOK_LIBS=hkBase.lib hkSerialize.lib hkCompat.lib hkaAnimation.lib hkaInternal.lib hkaRagdoll.lib hkpCollide.lib hkpConstraintSolver.lib hkpDynamics.lib hkpUtilities.lib hkpInternal.lib hkSceneData.lib hkpVehicle.lib

set CORE_SOURCES="src\core\havok_runtime.cpp" "src\core\havok_registry.cpp" "src\core\havok_io_api.cpp"
set ANIMATION_SOURCES="src\animation\animation_scene_builder.cpp" "src\animation\hkx_451_reader.cpp" "src\animation\hkx_451_writer.cpp" "src\animation\json_animation_input.cpp" "src\animation\json_animation_output.cpp" "src\animation\mod_studio_animation_bridge.cpp"
set PHYSICS_SOURCES="src\physics\hkx_451r_reader.cpp" "src\physics\hkx_55_writer.cpp" "src\physics\json_physics_input.cpp" "src\physics\json_physics_output.cpp" "src\physics\physics_scene_builder.cpp"
set RAGDOLL_SOURCES="src\ragdoll\hkx_451_writer.cpp" "src\ragdoll\json_ragdoll_input.cpp" "src\ragdoll\ragdoll_scene_builder.cpp"
set HKANIM_SOURCES="src\hkanim\hkanim_packer.cpp" "src\hkanim\hkanim_unpacker.cpp"

if not exist "%OBJ_ROOT%\core" mkdir "%OBJ_ROOT%\core"
if not exist "%OBJ_ROOT%\animation" mkdir "%OBJ_ROOT%\animation"
if not exist "%OBJ_ROOT%\physics" mkdir "%OBJ_ROOT%\physics"
if not exist "%OBJ_ROOT%\ragdoll" mkdir "%OBJ_ROOT%\ragdoll"
if not exist "%OBJ_ROOT%\hkanim" mkdir "%OBJ_ROOT%\hkanim"
if not exist "%OBJ_ROOT%\tools" mkdir "%OBJ_ROOT%\tools"

pushd "%SCRIPT_DIR%"

echo.
echo Building havok_io.dll and havok_io_cli.exe...
echo Havok SDK: %HAVOK_SDK%
echo.

cl %CL_FLAGS% %COMMON_INCLUDES% /D "HAVOK_IO_EXPORTS" /c /Fo".build\obj\core\\" %CORE_SOURCES%
if errorlevel 1 goto :fail

cl %CL_FLAGS% %COMMON_INCLUDES% /c /Fo".build\obj\animation\\" %ANIMATION_SOURCES%
if errorlevel 1 goto :fail

cl %CL_FLAGS% %COMMON_INCLUDES% /c /Fo".build\obj\physics\\" %PHYSICS_SOURCES%
if errorlevel 1 goto :fail

cl %CL_FLAGS% %COMMON_INCLUDES% /c /Fo".build\obj\ragdoll\\" %RAGDOLL_SOURCES%
if errorlevel 1 goto :fail

cl %CL_FLAGS% /I"src\hkanim" /c /Fo".build\obj\hkanim\\" %HKANIM_SOURCES%
if errorlevel 1 goto :fail

link /NOLOGO /DLL /OUT:"havok_io.dll" /IMPLIB:"havok_io.lib" /LIBPATH:"%HAVOK_LIB%" ".build\obj\core\*.obj" ".build\obj\animation\*.obj" ".build\obj\physics\*.obj" ".build\obj\ragdoll\*.obj" ".build\obj\hkanim\*.obj" %HAVOK_LIBS%
if errorlevel 1 goto :fail

cl %CL_FLAGS% /I"include" /c /Fo".build\obj\tools\\" "tools\havok_io_cli_main.cpp"
if errorlevel 1 goto :fail

link /NOLOGO /OUT:"havok_io_cli.exe" /LIBPATH:"." ".build\obj\tools\havok_io_cli_main.obj" havok_io.lib
if errorlevel 1 goto :fail

del /f /q "havok_io.exp" "havok_io.lib" >nul 2>nul
if exist "%BUILD_ROOT%" rmdir /s /q "%BUILD_ROOT%"

echo.
echo Build successful.
echo   %SCRIPT_DIR%havok_io.dll
echo   %SCRIPT_DIR%havok_io_cli.exe
echo.
popd
endlocal
exit /b 0

:fail
echo.
echo Build FAILED.
echo.
popd
endlocal
exit /b 1