find_path(CLI11_INCLUDES "CLI11.hpp"
  PATH_SUFFIXES include)

add_library(CLI11::CLI11 INTERFACE IMPORTED)
target_include_directories(CLI11::CLI11 INTERFACE ${CLI11_INCLUDES})

include(FindPackageHandleStandardArgs)

find_package_handle_standard_args(CLI11 REQUIRED_VARS
  CLI11_INCLUDES)