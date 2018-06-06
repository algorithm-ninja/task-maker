find_path(nlohmann_json_INCLUDES "nlohmann/json.hpp"
          PATH_SUFFIXES include)

add_library(nlohmann_json INTERFACE)
target_include_directories(nlohmann_json INTERFACE ${nlohmann_json_INCLUDES})

include(FindPackageHandleStandardArgs)

find_package_handle_standard_args(nlohmann_json REQUIRED_VARS
  nlohmann_json_INCLUDES)