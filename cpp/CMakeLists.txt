project(task-maker-cpp)

add_library(cpp_util
  util/file.cpp
  util/sha256.cpp
  util/which.cpp
)
target_include_directories(cpp_util PUBLIC .)
target_link_libraries(cpp_util
  proto_cpp
  absl_bad_optional_access
  absl::strings
  absl::synchronization
  glog
)

add_library(cpp_core
  core/core.cpp
  core/execution_cacher.cpp
  core/execution.cpp
  core/file_id.cpp
)
target_link_libraries(cpp_core
  cpp_util
)


# TODO: compile sandboxes individually, disable them on unsupported OSes
add_library(cpp_sandbox
  sandbox/echo.cpp
  sandbox/sandbox.cpp
  sandbox/unix.cpp
)
target_link_libraries(cpp_sandbox
  cpp_util
)
IF (APPLE)
  set(CPP_SANDBOX -Wl,-force_load cpp_sandbox)
else()
  set(CPP_SANDBOX
      -Wl,--whole-archive cpp_sandbox -Wl,--no-whole-archive)
endif()

# TODO: compile sandbox tests

add_library(cpp_remote
  remote/common.cpp
)
target_link_libraries(cpp_remote
  cpp_util
)

add_library(cpp_executor
  executor/local_executor.cpp
  executor/remote_executor.cpp
)
target_link_libraries(cpp_executor
  cpp_sandbox
  cpp_util
  cpp_remote
)

add_library(cpp_manager_lib
  manager/event_queue.cpp
  manager/source_file.cpp
  manager/ioi_format/ioi_format.cpp
  manager/ioi_format/ioi_evaluation.cpp
  manager/ioi_format/ioi_generation.cpp
  manager/terry_format/terry_format.cpp
  manager/terry_format/terry_evaluation.cpp
  manager/terry_format/terry_generation.cpp
)
target_link_libraries(cpp_manager_lib
  cpp_core
  cpp_remote
  cpp_executor
  nlohmann_json
)

add_executable(manager
  manager/manager.cpp
)
target_link_libraries(manager
  ${CPP_SANDBOX}
  cpp_manager_lib
)

add_executable(server
  remote/server.cpp
)
target_link_libraries(server
  cpp_remote
)

add_executable(worker
  remote/worker.cpp
)
target_link_libraries(worker
  ${CPP_SANDBOX}
  cpp_executor
)
