find_path(
  GMock_INCLUDE_DIR
  NAMES gmock.h
  PATH_SUFFIXES "gmock"
)
mark_as_advanced(GMock_INCLUDE_DIR)

find_library(
  GMock_LIBRARY
  NAMES gmock
)
mark_as_advanced(GMock_LIBRARY)

add_library(GMock::gmock UNKNOWN IMPORTED)
set_target_properties(GMock::gmock PROPERTIES
  INTERFACE_INCLUDE_DIRECTORIES ${GMock_INCLUDE_DIR}
  IMPORTED_LOCATION ${GMock_LIBRARY})

include(FindPackageHandleStandardArgs)

find_package_handle_standard_args(
  GMock
  REQUIRED_VARS
  GMock_INCLUDE_DIR
  GMock_LIBRARY
)