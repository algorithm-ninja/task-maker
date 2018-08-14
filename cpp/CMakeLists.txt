add_subdirectory(sandbox/test)

add_library(cpp_util
  util/file.cpp
  util/sha256.cpp
  util/which.cpp
  util/flags.cpp
)
target_include_directories(cpp_util PUBLIC .)
target_link_libraries(cpp_util
  capnp_cpp
  CapnProto::kj
)
# this flag is needed on travis
if (TRAVIS)
  target_compile_definitions(cpp_util PRIVATE REMOVE_ALSO_MOUNT_POINTS=1)
endif()



add_library(cpp_sandbox
  sandbox/sandbox.cpp
)

target_link_libraries(cpp_sandbox
  cpp_util
)

add_library(cpp_sandbox_echo
  sandbox/echo.cpp
)
target_link_libraries(cpp_sandbox_echo
  cpp_sandbox
)

if (APPLE)
  set(CPP_SANDBOXES -Wl,-force_load cpp_sandbox_echo ${CPP_SANDBOXES})
else()
  set(CPP_SANDBOXES
    -Wl,--whole-archive cpp_sandbox_echo -Wl,--no-whole-archive ${CPP_SANDBOXES})
endif()

if (UNIX)
  add_library(cpp_sandbox_unix
    sandbox/unix.cpp
  )
  target_link_libraries(cpp_sandbox_unix
    cpp_sandbox
  )

  add_executable(sandbox_unix_test
    sandbox/unix_test.cpp
    sandbox/unix.cpp
  )
  target_link_libraries(sandbox_unix_test
    cpp_sandbox
    GTest::Main
    GMock::gmock
  )


  if (APPLE)
    set(CPP_SANDBOXES -Wl,-force_load cpp_sandbox_unix ${CPP_SANDBOXES})
  else()
    set(CPP_SANDBOXES
      -Wl,--whole-archive cpp_sandbox_unix -Wl,--no-whole-archive ${CPP_SANDBOXES})
  endif()
endif()



#add_library(cpp_core
#  core/core.cpp
#  core/execution_cacher.cpp
#  core/execution.cpp
#  core/file_id.cpp
#)
#target_link_libraries(cpp_core
#  cpp_util
#  cpp_remote
#)

add_library(cpp_worker
  worker/executor.cpp
  worker/manager.cpp
  worker/main.cpp
)

target_link_libraries(cpp_worker
  cpp_sandbox
  cpp_util
)

add_library(cpp_server
  server/dispatcher.cpp
  server/server.cpp
  server/main.cpp
)
target_link_libraries(cpp_server
  cpp_util
)


#add_library(cpp_manager_lib
#  manager/event_queue.cpp
  #manager/source_file.cpp
  #manager/ioi_format/ioi_format.cpp
  #manager/ioi_format/ioi_evaluation.cpp
  #manager/ioi_format/ioi_generation.cpp
  #manager/terry_format/terry_format.cpp
  #manager/terry_format/terry_evaluation.cpp
  #manager/terry_format/terry_generation.cpp
#)
#target_link_libraries(cpp_manager_lib
  #cpp_core
  #cpp_remote
  #cpp_executor
  #nlohmann_json
#)

add_executable(task-maker
  #manager/manager.cpp
  #remote/server.cpp
  #remote/worker.cpp
  main.cpp
)
target_link_libraries(task-maker
  ${CPP_SANDBOXES}
  cpp_worker
  cpp_server
)
target_compile_definitions(task-maker PRIVATE TASK_MAKER_VERSION="${GIT_FULL_VERSION}")

gtest_discover_tests(sandbox_unix_test)
