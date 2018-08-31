add_subdirectory(sandbox/test)

add_subdirectory(frontend)

add_library(cpp_util
  util/file.cpp
  util/sha256.cpp
  util/which.cpp
  util/flags.cpp
  util/union_promise.cpp
  util/misc.cpp
  util/log_manager.cpp
)
target_include_directories(cpp_util PUBLIC .)
target_link_libraries(cpp_util
  backward
  capnp_cpp
  CapnProto::kj
  CapnProto::kj-async
  CapnProto::capnp
  CapnProto::capnp-rpc
)
# this flag is needed on travis
if (TRAVIS)
  target_compile_definitions(cpp_util PRIVATE REMOVE_ALSO_MOUNT_POINTS=1)
endif()

add_library(cpp_sandbox
  sandbox/sandbox.cpp
  sandbox/main.cpp
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

add_library(cpp_worker
  worker/cache.cpp
  worker/executor.cpp
  worker/manager.cpp
  worker/main.cpp
)

target_link_libraries(cpp_worker
  cpp_sandbox
  cpp_util
  whereami
)

add_library(cpp_server
  server/dispatcher.cpp
  server/server.cpp
  server/main.cpp
  server/cache.cpp
)
target_link_libraries(cpp_server
  cpp_util
)

add_executable(task-maker
  main.cpp
)
target_link_libraries(task-maker
  ${CPP_SANDBOXES}
  cpp_worker
  cpp_server
)
target_compile_definitions(task-maker PRIVATE TASK_MAKER_VERSION="${GIT_FULL_VERSION}")

gtest_discover_tests(sandbox_unix_test)
