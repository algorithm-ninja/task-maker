cmake_minimum_required(VERSION 3.10)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
list(APPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")

ENABLE_LANGUAGE(CXX)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 14)

include(HunterGate)
include(ThreadSanitizer)

HunterGate(
    URL "https://github.com/ruslo/hunter/archive/v0.23.14.tar.gz"
    SHA1 "f58bcf274f29097ac380bfe4955d2a66f077e741"
)

# extract project version from git tag
execute_process(
  COMMAND git describe --tags
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
  OUTPUT_VARIABLE GIT_FULL_VERSION
  OUTPUT_STRIP_TRAILING_WHITESPACE
)
# cmake project version must be major.minor.patch with all
# integers. GIT_FULL_VERSION is accurate even for branch not tagged
# the format of GIT_FULL_VERSION is v1.2.3-gsha1 or v1.2.3
execute_process(
  COMMAND echo ${GIT_FULL_VERSION}
  COMMAND cut -d- -f1
  COMMAND cut -dv -f2
  OUTPUT_VARIABLE GIT_LAST_VERSION
  OUTPUT_STRIP_TRAILING_WHITESPACE
)

project(task-maker VERSION ${GIT_LAST_VERSION})

include(CTest)
enable_testing()
include(GoogleTest)

find_package(PythonInterp 3.5 REQUIRED)

# Enable colors in ninja
set(CMAKE_CXX_FLAGS "-fdiagnostics-color=always -Wall -Wextra -Wno-unused-parameter")
set(CMAKE_CXX_FLAGS_RELEASE "-O3")

# if hunter is disabled all these lines are noop
hunter_add_package(GTest)
hunter_add_package(CapnProto)

# these finders are bundled with cmake
find_package(GTest REQUIRED)

# these finders are provided by hunter, when hunter is disabled the ones in cmake are used
# TODO: add the one for CapnProto
find_package(CapnProto CONFIG REQUIRED)
find_package(GMock CONFIG REQUIRED)

add_subdirectory(capnp)
add_subdirectory(cpp)
add_subdirectory(python)
