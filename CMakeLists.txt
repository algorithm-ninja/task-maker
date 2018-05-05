cmake_minimum_required(VERSION 3.2)

cmake_policy(SET CMP0048 NEW)

project(task-maker VERSION 1.0.2)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# Disable testing as it is currently broken with absl
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)

# Enable colors in ninja
set(CMAKE_CXX_FLAGS "-fdiagnostics-color=always -std=c++11")
set(CMAKE_CXX_FLAGS_RELEASE "-O3")

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")

# Add gtest and gmock with a different name because the usual one collides with
# a dependency of grpc
add_library(googletest ${CMAKE_CURRENT_SOURCE_DIR}/googletest/googletest/src/gtest-all.cc)
target_include_directories(googletest
  PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/googletest/googletest/include
  ${CMAKE_CURRENT_SOURCE_DIR}/googletest/googletest)
add_library(googlemock ${CMAKE_CURRENT_SOURCE_DIR}/googletest/googlemock/src/gmock-all.cc)
target_include_directories(googlemock
  PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/googletest/googlemock/include
  ${CMAKE_CURRENT_SOURCE_DIR}/googletest/googlemock)
target_link_libraries(googlemock googletest)

add_subdirectory(glog EXCLUDE_FROM_ALL)
add_subdirectory(grpc EXCLUDE_FROM_ALL)
add_subdirectory(nlohmann_json EXCLUDE_FROM_ALL)
add_subdirectory(absl EXCLUDE_FROM_ALL)

find_package(Protobuf REQUIRED)
find_package(GRPC REQUIRED)

add_subdirectory(proto)
add_subdirectory(cpp)
add_subdirectory(python)