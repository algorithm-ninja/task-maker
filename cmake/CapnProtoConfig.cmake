#
# Finds the Cap'n Proto libraries, and compiles schema files.
#
# Configuration variables (optional):
#   CAPNPC_OUTPUT_DIR
#       Directory to place compiled schema sources (default: the same directory as the schema file).
#   CAPNPC_IMPORT_DIRS
#       List of additional include directories for the schema compiler.
#       (CMAKE_CURRENT_SOURCE_DIR and CAPNP_INCLUDE_DIRECTORY are always included.)
#   CAPNPC_SRC_PREFIX
#       Schema file source prefix (default: CMAKE_CURRENT_SOURCE_DIR).
#   CAPNPC_FLAGS
#       Additional flags to pass to the schema compiler.
#
# Variables that are discovered:
#   CAPNP_EXECUTABLE
#       Path to the `capnp` tool (can be set to override).
#   CAPNPC_CXX_EXECUTABLE
#       Path to the `capnpc-c++` tool (can be set to override).
#   CAPNP_INCLUDE_DIRECTORY
#       Include directories for the library's headers (can be set to override).
#   CANP_LIBRARIES
#       The Cap'n Proto library paths.
#   CAPNP_LIBRARIES_LITE
#       Paths to only the 'lite' libraries.
#   CAPNP_DEFINITIONS
#       Compiler definitions required for building with the library.
#   CAPNP_FOUND
#       Set if the libraries have been located.
#
# Example usage:
#
#   find_package(CapnProto REQUIRED)
#   include_directories(${CAPNP_INCLUDE_DIRECTORY})
#   add_definitions(${CAPNP_DEFINITIONS})
#
#   capnp_generate_cpp(CAPNP_SRCS CAPNP_HDRS schema.capnp)
#   add_executable(a a.cc ${CAPNP_SRCS} ${CAPNP_HDRS})
#   target_link_library(a ${CAPNP_LIBRARIES})
#
# For out-of-source builds:
#
#   set(CAPNPC_OUTPUT_DIR ${CMAKE_CURRENT_BINARY_DIR})
#   include_directories(${CAPNPC_OUTPUT_DIR})
#   capnp_generate_cpp(...)
#

# CAPNP_GENERATE_CPP ===========================================================

function(CAPNP_GENERATE_CPP SOURCES HEADERS)
  if(NOT ARGN)
    message(SEND_ERROR "CAPNP_GENERATE_CPP() called without any source files.")
  endif()
  set(tool_depends ${EMPTY_STRING})
  #Use cmake targets available
  if(TARGET capnp_tool)
    set(CAPNP_EXECUTABLE capnp_tool)
    GET_TARGET_PROPERTY(CAPNPC_CXX_EXECUTABLE capnpc_cpp CAPNPC_CXX_EXECUTABLE)
    GET_TARGET_PROPERTY(CAPNP_INCLUDE_DIRECTORY capnp_tool CAPNP_INCLUDE_DIRECTORY)
    list(APPEND tool_depends capnp_tool capnpc_cpp)
  endif()
  if(NOT CAPNP_EXECUTABLE)
    message(SEND_ERROR "Could not locate capnp executable (CAPNP_EXECUTABLE).")
  endif()
  if(NOT CAPNPC_CXX_EXECUTABLE)
    message(SEND_ERROR "Could not locate capnpc-c++ executable (CAPNPC_CXX_EXECUTABLE).")
  endif()
  if(NOT CAPNP_INCLUDE_DIRECTORY)
    message(SEND_ERROR "Could not locate capnp header files (CAPNP_INCLUDE_DIRECTORY).")
  endif()

  if(DEFINED CAPNPC_OUTPUT_DIR)
    # Prepend a ':' to get the format for the '-o' flag right
    set(output_dir ":${CAPNPC_OUTPUT_DIR}")
  else()
    set(output_dir ":.")
  endif()

  if(NOT DEFINED CAPNPC_SRC_PREFIX)
    set(CAPNPC_SRC_PREFIX "${CMAKE_CURRENT_SOURCE_DIR}")
  endif()
  get_filename_component(CAPNPC_SRC_PREFIX "${CAPNPC_SRC_PREFIX}" ABSOLUTE)

  # Default compiler includes. Note that in capnp's own test usage of capnp_generate_cpp(), these
  # two variables will end up evaluating to the same directory. However, it's difficult to
  # deduplicate them because if CAPNP_INCLUDE_DIRECTORY came from the capnp_tool target property,
  # then it must be a generator expression in order to handle usages in both the build tree and the
  # install tree. This vastly overcomplicates duplication detection, so the duplication doesn't seem
  # worth fixing.
  set(include_path -I "${CAPNPC_SRC_PREFIX}" -I "${CAPNP_INCLUDE_DIRECTORY}")

  if(DEFINED CAPNPC_IMPORT_DIRS)
    # Append each directory as a series of '-I' flags in ${include_path}
    foreach(directory ${CAPNPC_IMPORT_DIRS})
      get_filename_component(absolute_path "${directory}" ABSOLUTE)
      list(APPEND include_path -I "${absolute_path}")
    endforeach()
  endif()

  set(${SOURCES})
  set(${HEADERS})
  foreach(schema_file ${ARGN})
    get_filename_component(file_path "${schema_file}" ABSOLUTE)
    get_filename_component(file_dir "${file_path}" PATH)
    if(NOT EXISTS "${file_path}")
      message(FATAL_ERROR "Cap'n Proto schema file '${file_path}' does not exist!")
    endif()

    # Figure out where the output files will go
    if (NOT DEFINED CAPNPC_OUTPUT_DIR)
      set(CAPNPC_OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/")
    endif()
    # Output files are placed in CAPNPC_OUTPUT_DIR, at a location as if they were
    # relative to CAPNPC_SRC_PREFIX.
    string(LENGTH "${CAPNPC_SRC_PREFIX}" prefix_len)
    string(SUBSTRING "${file_path}" 0 ${prefix_len} output_prefix)
    if(NOT "${CAPNPC_SRC_PREFIX}" STREQUAL "${output_prefix}")
      message(SEND_ERROR "Could not determine output path for '${schema_file}' ('${file_path}') with source prefix '${CAPNPC_SRC_PREFIX}' into '${CAPNPC_OUTPUT_DIR}'.")
    endif()

    string(SUBSTRING "${file_path}" ${prefix_len} -1 output_path)
    set(output_base "${CAPNPC_OUTPUT_DIR}${output_path}")

    add_custom_command(
        OUTPUT "${output_base}.c++" "${output_base}.h"
        COMMAND "${CAPNP_EXECUTABLE}"
        ARGS compile
        -o ${CAPNPC_CXX_EXECUTABLE}${output_dir}
        --src-prefix ${CAPNPC_SRC_PREFIX}
        ${include_path}
        ${CAPNPC_FLAGS}
        ${file_path}
        DEPENDS "${schema_file}" ${tool_depends}
        COMMENT "Compiling Cap'n Proto schema ${schema_file}"
        VERBATIM
    )

    list(APPEND ${SOURCES} "${output_base}.c++")
    list(APPEND ${HEADERS} "${output_base}.h")
  endforeach()

  set_source_files_properties(${${SOURCES}} ${${HEADERS}} PROPERTIES GENERATED TRUE)
  set(${SOURCES} ${${SOURCES}} PARENT_SCOPE)
  set(${HEADERS} ${${HEADERS}} PARENT_SCOPE)
endfunction()

# Find Libraries/Paths =========================================================

# Use pkg-config to get path hints and definitions
find_package(PkgConfig QUIET)
pkg_check_modules(PKGCONFIG_CAPNP capnp)
pkg_check_modules(PKGCONFIG_CAPNP_RPC capnp-rpc QUIET)

find_library(CAPNP_LIB_KJ kj
    HINTS "${PKGCONFIG_CAPNP_LIBDIR}" ${PKGCONFIG_CAPNP_LIBRARY_DIRS}
    )
find_library(CAPNP_LIB_KJ-ASYNC kj-async
    HINTS "${PKGCONFIG_CAPNP_RPC_LIBDIR}" ${PKGCONFIG_CAPNP_RPC_LIBRARY_DIRS}
    )
find_library(CAPNP_LIB_CAPNP capnp
    HINTS "${PKGCONFIG_CAPNP_LIBDIR}" ${PKGCONFIG_CAPNP_LIBRARY_DIRS}
    )
find_library(CAPNP_LIB_CAPNP-RPC capnp-rpc
    HINTS "${PKGCONFIG_CAPNP_RPC_LIBDIR}" ${PKGCONFIG_CAPNP_RPC_LIBRARY_DIRS}
    )
mark_as_advanced(CAPNP_LIB_KJ CAPNP_LIB_KJ-ASYNC CAPNP_LIB_CAPNP CAPNP_LIB_CAPNP-RPC)
set(CAPNP_LIBRARIES_LITE
    ${CAPNP_LIB_KJ}
    ${CAPNP_LIB_CAPNP}
    )
set(CAPNP_LIBRARIES
    ${CAPNP_LIBRARIES_LITE}
    ${CAPNP_LIB_KJ-ASYNC}
    ${CAPNP_LIB_CAPNP-RPC}
    )

# Was only the 'lite' library found?
if(CAPNP_LIB_CAPNP AND NOT CAPNP_LIB_CAPNP-RPC)
  set(CAPNP_DEFINITIONS -DCAPNP_LITE)
else()
  set(CAPNP_DEFINITIONS)
endif()

find_path(CAPNP_INCLUDE_DIRECTORY capnp/generated-header-support.h
    HINTS "${PKGCONFIG_CAPNP_INCLUDEDIR}" ${PKGCONFIG_CAPNP_INCLUDE_DIRECTORY}
    )

find_program(CAPNP_EXECUTABLE
    NAMES capnp
    DOC "Cap'n Proto Command-line Tool"
    HINTS "${PKGCONFIG_CAPNP_PREFIX}/bin"
    )

find_program(CAPNPC_CXX_EXECUTABLE
    NAMES capnpc-c++
    DOC "Capn'n Proto C++ Compiler"
    HINTS "${PKGCONFIG_CAPNP_PREFIX}/bin"
    )

# Only *require* the include directory, libkj, and libcapnp. If compiling with
# CAPNP_LITE, nothing else will be found.
include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(CAPNP DEFAULT_MSG
    CAPNP_INCLUDE_DIRECTORY
    CAPNP_LIB_KJ
    CAPNP_LIB_CAPNP
    )

add_library(CapnProto::kj UNKNOWN IMPORTED)
set_target_properties(CapnProto::kj PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES ${CAPNP_INCLUDE_DIRECTORY}
    IMPORTED_LOCATION ${CAPNP_LIB_KJ})

add_library(CapnProto::kj-async UNKNOWN IMPORTED)
set_target_properties(CapnProto::kj-async PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES ${CAPNP_INCLUDE_DIRECTORY}
    IMPORTED_LOCATION ${CAPNP_LIB_KJ-ASYNC})

add_library(CapnProto::capnp UNKNOWN IMPORTED)
set_target_properties(CapnProto::capnp PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES ${CAPNP_INCLUDE_DIRECTORY}
    IMPORTED_LOCATION ${CAPNP_LIB_CAPNP})

add_library(CapnProto::capnp-rpc UNKNOWN IMPORTED)
set_target_properties(CapnProto::capnp-rpc PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES ${CAPNP_INCLUDE_DIRECTORY}
    IMPORTED_LOCATION ${CAPNP_LIB_CAPNP-RPC})
