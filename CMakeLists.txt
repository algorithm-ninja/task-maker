cmake_minimum_required(VERSION 3.5)


list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
list(APPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")

ENABLE_LANGUAGE(CXX)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include(HunterGate)
include(AddressSanitizer)
include(ThreadSanitizer)
include(UndefinedSanitizer)

HunterGate(
    URL "https://github.com/ruslo/hunter/archive/v0.23.16.tar.gz"
    SHA1 "dbe5b1c966414c4a055983c11d5251a2d8f2f16d"
    FILEPATH "${CMAKE_CURRENT_LIST_DIR}/cmake/config.cmake"
)

set(CMAKE_POSITION_INDEPENDENT_CODE TRUE)

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

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/tools/DEBIAN/control.in
               ${CMAKE_CURRENT_BINARY_DIR}/DEBIAN/control)

# Enable colors in ninja
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fdiagnostics-color=always") 
# Other flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wno-unused-parameter -g")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-delete-non-virtual-dtor")
set(CMAKE_CXX_FLAGS_RELEASE "-O3")

# if hunter is disabled all these lines are noop
hunter_add_package(GTest)
hunter_add_package(CapnProto)
hunter_add_package(pybind11)

# these finders are bundled with cmake
find_package(GTest REQUIRED)

# these finders are provided by hunter, when hunter is disabled the ones in cmake are used
find_package(CapnProto CONFIG REQUIRED)
find_package(GMock CONFIG REQUIRED)
find_package(pybind11 CONFIG REQUIRED)
find_package(dw CONFIG)

add_subdirectory(capnp)
add_subdirectory(third_party)
add_subdirectory(cpp)
add_subdirectory(python)
