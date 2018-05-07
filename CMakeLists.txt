cmake_minimum_required(VERSION 3.2)

include("cmake/HunterGate.cmake")

HunterGate(
    URL "https://github.com/ruslo/hunter/archive/v0.20.69.tar.gz"
    SHA1 "e02d106c762c81efb215587c5516c11416c00b52"
    # Needed to compile gRPC because it needs -fPIC
    FILEPATH ${CMAKE_CURRENT_LIST_DIR}/cmake/config.cmake
)

project(task-maker VERSION 1.0.2)

# Enable colors in ninja
set(CMAKE_CXX_FLAGS "-fdiagnostics-color=always -Wall -Wextra")
set(CMAKE_CXX_FLAGS_RELEASE "-O3")

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")

set(CMAKE_CXX_STANDARD_REQUIRED true)
set(CMAKE_CXX_STANDARD 11)

hunter_add_package(gRPC)
find_package(gRPC CONFIG REQUIRED)

hunter_add_package(GTest)
find_package(GTest CONFIG REQUIRED)
find_package(GMock CONFIG REQUIRED)

hunter_add_package(gflags)
find_package(gflags CONFIG REQUIRED)

hunter_add_package(glog)
find_package(glog CONFIG REQUIRED)

hunter_add_package(gRPC)
find_package(gRPC CONFIG REQUIRED)

hunter_add_package(nlohmann_json)
find_package(nlohmann_json CONFIG REQUIRED)

hunter_add_package(Protobuf)
find_package(Protobuf CONFIG REQUIRED)

# TODO(edomora97) mode abseil to hunter
# Disable testing as it is currently broken with absl
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
add_subdirectory(third_party/abseil-cpp)

include(cmake/Protobuf.cmake)
include(cmake/GRPC.cmake)

add_subdirectory(proto)
add_subdirectory(cpp)
add_subdirectory(python)