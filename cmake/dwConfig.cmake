find_library(
  dw_LIBRARY
  NAMES dw
)
mark_as_advanced(dw_LIBRARY)

add_library(dw UNKNOWN IMPORTED)
set_target_properties(dw PROPERTIES
    IMPORTED_LOCATION ${dw_LIBRARY})

include(FindPackageHandleStandardArgs)

find_package_handle_standard_args(
  dw
  REQUIRED_VARS
  dw_LIBRARY
)
