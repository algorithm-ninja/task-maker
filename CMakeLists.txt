cmake_minimum_required(VERSION 3.2)

cmake_policy(SET CMP0048 NEW)

project(task-maker VERSION 1.0.2)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

set(CMAKE_CXX_FLAGS "-Wall -g")
set(CMAKE_CXX_FLAGS_RELEASE "-O3")

add_compile_options(-std=c++11)

list(APPEND CMAKE_PREFIX_PATH "/opt/grpc" "/opt/protobuf")

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")

find_package(Protobuf REQUIRED)
find_package(GRPC REQUIRED)

add_subdirectory(nlohmann_json)
add_subdirectory(googletest)
add_subdirectory(absl)
add_subdirectory(glog)
add_subdirectory(proto)
add_subdirectory(cpp)

# TODO: python
