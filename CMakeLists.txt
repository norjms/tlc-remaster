# Starflight: The Lost Colony, cross-platform build (Windows, Linux, macOS).
#
# Uses SDL3 through the a4sdl compatibility layer (src/platform/a4sdl) in
# place of Allegro 4, and builds Lua 5.1.5, libnoise, miniaudio and stb from
# the sources vendored in src/thirdparty. SDL3 comes from the system when
# available (find_package), otherwise it is fetched and built statically.
#
#   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
#   cmake --build build --config Release
#
# Run the game from bin/ (it reads data/ relative to the working directory);
# a dev build also finds bin/ on its own when started from the build tree.

cmake_minimum_required(VERSION 3.20)
project(StarflightTLC VERSION 2.1 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 99)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

option(TLC_FETCH_SDL "Fetch and build SDL3 if it is not installed" ON)
set(TLC_SDL_TAG "release-3.4.20" CACHE STRING "SDL3 tag used when fetching")

# ------------------------------------------------------------------ SDL3

find_package(SDL3 CONFIG QUIET)
if(NOT SDL3_FOUND)
  if(NOT TLC_FETCH_SDL)
    message(FATAL_ERROR "SDL3 not found; install it or set TLC_FETCH_SDL=ON")
  endif()
  message(STATUS "SDL3 not found; fetching ${TLC_SDL_TAG}")
  include(FetchContent)
  set(SDL_SHARED OFF CACHE BOOL "" FORCE)
  set(SDL_STATIC ON CACHE BOOL "" FORCE)
  set(SDL_TEST_LIBRARY OFF CACHE BOOL "" FORCE)
  set(SDL_TESTS OFF CACHE BOOL "" FORCE)
  set(SDL_EXAMPLES OFF CACHE BOOL "" FORCE)
  FetchContent_Declare(SDL3
    GIT_REPOSITORY https://github.com/libsdl-org/SDL.git
    GIT_TAG ${TLC_SDL_TAG}
    GIT_SHALLOW TRUE)
  FetchContent_MakeAvailable(SDL3)
endif()

set(TP ${CMAKE_SOURCE_DIR}/src/thirdparty)

# ------------------------------------------------------------- Lua 5.1.5

file(GLOB LUA_SRC ${TP}/lua-5.1.5/*.c)
add_library(lua51 STATIC ${LUA_SRC})
target_include_directories(lua51 PUBLIC ${TP}/lua-5.1.5)
if(UNIX)
  target_compile_definitions(lua51 PRIVATE LUA_USE_POSIX)
endif()
if(MSVC)
  target_compile_definitions(lua51 PRIVATE _CRT_SECURE_NO_WARNINGS)
endif()

# --------------------------------------------------------------- libnoise

file(GLOB_RECURSE NOISE_SRC ${TP}/libnoise/src/*.cpp)
add_library(noise STATIC ${NOISE_SRC})
target_include_directories(noise PUBLIC ${TP}/libnoise/src PRIVATE ${TP}/libnoise/src/noise)
target_compile_definitions(noise PUBLIC NOISE_STATIC=1)

# ----------------------------------------------- a4sdl (Allegro 4 on SDL3)

add_library(a4sdl STATIC
  src/platform/a4sdl/a4_core.cpp
  src/platform/a4sdl/a4_draw.cpp
  src/platform/a4sdl/a4_load.cpp
  src/platform/a4sdl/a4_alfont.cpp)
target_include_directories(a4sdl
  PUBLIC  ${CMAKE_SOURCE_DIR}/src/platform/a4sdl/include
  PRIVATE ${CMAKE_SOURCE_DIR}/src ${CMAKE_SOURCE_DIR}/src/platform/a4sdl)
target_link_libraries(a4sdl PUBLIC SDL3::SDL3)
target_compile_definitions(a4sdl PRIVATE A4_DEV_DATA_DIR="${CMAKE_SOURCE_DIR}/bin")

# ------------------------------------------------------------------ game

set(GAME_SRC
  Archive.cpp AudioSystem.cpp Button.cpp CombatObject.cpp DataMgr.cpp Flux.cpp
  Game.cpp GameState.cpp Label.cpp LogFile.cpp Math.cpp MessageBoxWindow.cpp
  ModeMgr.cpp Module.cpp ModuleAuxiliaryDisplay.cpp ModuleBank.cpp
  ModuleCantina.cpp ModuleCaptainCreation.cpp ModuleCaptainsLounge.cpp
  ModuleCargoWindow.cpp ModuleControlPanel.cpp ModuleCredits.cpp
  ModuleCrewHire.cpp ModuleEncounter.cpp ModuleEngineer.cpp ModuleGameOver.cpp
  ModuleInterstellar.cpp ModuleMedical.cpp ModuleMessageGUI.cpp
  ModulePlanetOrbit.cpp ModulePlanetSurface.cpp ModuleQuestLog.cpp
  ModuleSettings.cpp ModuleShipConfig.cpp ModuleSolarSystem.cpp
  ModuleStarmap.cpp ModuleStarport.cpp ModuleStartup.cpp ModuleTitleScreen.cpp
  ModuleTopGUI.cpp ModuleTradeDepot.cpp PauseMenu.cpp PlanetSurfaceObject.cpp
  PlanetSurfacePlayerVessel.cpp PlanetTileScroller.cpp PlanetaryBody.cpp
  PlayerShipSprite.cpp QuestMgr.cpp Script.cpp ScrollBox.cpp Sprite.cpp
  Stardate.cpp TexturedSphere.cpp TileScroller.cpp Timer.cpp Util.cpp
  Vector3.cpp main.cpp noiseutils.cpp
  tinyxml/tinystr.cpp tinyxml/tinyxml.cpp tinyxml/tinyxmlerror.cpp
  tinyxml/tinyxmlparser.cpp)
list(TRANSFORM GAME_SRC PREPEND ${CMAKE_SOURCE_DIR}/src/)

add_executable(starflighttlc WIN32 MACOSX_BUNDLE
  ${GAME_SRC}
  ${TP}/miniaudio/miniaudio_impl.c)
target_include_directories(starflighttlc PRIVATE ${CMAKE_SOURCE_DIR}/src)
target_compile_definitions(starflighttlc PRIVATE TIXML_USE_STL)
target_link_libraries(starflighttlc PRIVATE a4sdl lua51 noise)
if(UNIX AND NOT APPLE)
  target_link_libraries(starflighttlc PRIVATE ${CMAKE_DL_LIBS} m pthread)
endif()

if(MSVC)
  target_compile_definitions(starflighttlc PRIVATE _CRT_SECURE_NO_WARNINGS _CRT_NONSTDC_NO_WARNINGS)
  target_compile_options(starflighttlc PRIVATE /MP /W3 /wd4996 /wd4244 /wd4267 /wd4305 /wd4018)
  set_property(TARGET starflighttlc PROPERTY VS_DEBUGGER_WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/bin)
else()
  # legacy code: keep the build readable, real problems still error out
  # (0xDEADBEEF-style sentinels in int initializer lists are fine on MSVC)
  target_compile_options(starflighttlc PRIVATE -Wno-write-strings -Wno-deprecated-declarations
    $<$<COMPILE_LANGUAGE:CXX>:-Wno-register -Wno-narrowing>)
  if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    target_compile_options(starflighttlc PRIVATE $<$<COMPILE_LANGUAGE:CXX>:-Wno-c++11-narrowing>)
  endif()
endif()

set_target_properties(starflighttlc PROPERTIES
  MACOSX_BUNDLE_BUNDLE_NAME "Starflight - The Lost Colony"
  MACOSX_BUNDLE_GUI_IDENTIFIER "com.starflight.tlc")

# ---------------------------------------------------------------- install
#
#   cmake --install build --prefix dist/StarflightTLC
#
# Windows/Linux: a portable folder (executable next to data/ and saves/).
# macOS: StarflightTLC.app with data/ and saves/ in Contents/Resources;
# the game finds them there on its own.

set(TLC_DATA_EXCLUDES
  PATTERN "*.exe" EXCLUDE PATTERN "*.dll" EXCLUDE PATTERN "*.bat" EXCLUDE
  PATTERN "*.doc" EXCLUDE PATTERN "assets" EXCLUDE)

if(APPLE)
  set(TLC_RES_DIR "starflighttlc.app/Contents/Resources")
  install(TARGETS starflighttlc BUNDLE DESTINATION .)
else()
  set(TLC_RES_DIR ".")
  install(TARGETS starflighttlc RUNTIME DESTINATION .)
endif()
install(DIRECTORY ${CMAKE_SOURCE_DIR}/bin/data  DESTINATION ${TLC_RES_DIR} ${TLC_DATA_EXCLUDES})
install(DIRECTORY ${CMAKE_SOURCE_DIR}/bin/saves DESTINATION ${TLC_RES_DIR})
install(FILES ${CMAKE_SOURCE_DIR}/LICENSE ${CMAKE_SOURCE_DIR}/README.md DESTINATION ${TLC_RES_DIR})
