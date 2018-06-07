find_path(plog_INCLUDES "plog/Log.h"
  PATH_SUFFIXES include)

add_library(plog::plog INTERFACE IMPORTED)
set_property(TARGET plog::plog APPEND PROPERTY
  INTERFACE_INCLUDE_DIRECTORIES ${plog_INCLUDES})


include(FindPackageHandleStandardArgs)

find_package_handle_standard_args(plog REQUIRED_VARS
  plog_INCLUDES)