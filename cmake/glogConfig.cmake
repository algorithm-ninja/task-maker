find_path(GLOG_INCLUDES "glog/logging.h"
          PATH_SUFFIXES include)
mark_as_advanced(GLOG_INCLUDES)

find_library(GLOG_LIBRARIES "glog")
mark_as_advanced(GLOG_LIBRARIES)

add_library(glog::glog UNKNOWN IMPORTED)
set_target_properties(glog::glog PROPERTIES
  INTERFACE_INCLUDE_DIRECTORIES ${GLOG_INCLUDES}
  IMPORTED_LOCATION ${GLOG_LIBRARIES})

include(FindPackageHandleStandardArgs)

find_package_handle_standard_args(
  GLOG REQUIRED_VARS
  GLOG_INCLUDES GLOG_LIBRARIES)
