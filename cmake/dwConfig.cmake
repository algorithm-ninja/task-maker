find_library(
  dw_LIBRARY
  NAMES dw
)
mark_as_advanced(dw_LIBRARY)

if (NOT dw_LIBRARY)
  message(STATUS "libdw not found")
  set(dw_FOUND FALSE)
else()
  message(STATUS "Found dw: ${dw_LIBRARY}")
  add_library(dw UNKNOWN IMPORTED)
  set_target_properties(dw PROPERTIES
      IMPORTED_LOCATION ${dw_LIBRARY})
  set(dw_FOUND TRUE)
endif ()
