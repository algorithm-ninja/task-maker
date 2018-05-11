cmake_minimum_required(VERSION 3.2)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")

ENABLE_LANGUAGE(CXX)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 14)

include(HunterGate)
include(ThreadSanitizer)
include(Protobuf)
include(GRPC)

HunterGate(
    URL "https://github.com/ruslo/hunter/archive/v0.20.69.tar.gz"
    SHA1 "e02d106c762c81efb215587c5516c11416c00b52"
    # Needed to compile gRPC because it needs -fPIC
    FILEPATH ${CMAKE_CURRENT_LIST_DIR}/cmake/config.cmake
)

project(task-maker VERSION 1.0.2)

find_package(PythonInterp 3.5 REQUIRED)

# Enable colors in ninja
set(CMAKE_CXX_FLAGS "-fdiagnostics-color=always -Wall -Wextra -Wno-unused-parameter")
set(CMAKE_CXX_FLAGS_RELEASE "-O3")

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


add_subdirectory(proto)
add_subdirectory(cpp)
add_subdirectory(python)
