# Sandboxes. Other code should only depend on sandbox.{hpp,cpp} and link
# all the available sandboxes for that system.
package(default_visibility = ["//visibility:public"])

cc_library(
    name = "sandbox",
    srcs = ["sandbox.cpp"],
    hdrs = ["sandbox.hpp"],
)

cc_library(
    name = "unix",
    srcs = ["unix.cpp"],
    hdrs = ["unix.hpp"],
    deps = [":sandbox"],
    alwayslink = 1,
)

cc_test(
    name = "unix_test",
    size = "small",
    srcs = ["unix_test.cpp"],
    data = [
        "//sandbox/test:busywait_arg1",
        "//sandbox/test:copy_int",
        "//sandbox/test:malloc_arg1",
        "//sandbox/test:return_arg1",
        "//sandbox/test:signal_arg1",
        "//sandbox/test:wait_arg1",
    ],
    deps = [
        ":sandbox",
        ":unix",
        "@googletest//:gtest_main",
    ],
)

cc_library(
    name = "echo",
    srcs = ["echo.cpp"],
    hdrs = ["echo.hpp"],
    deps = [":sandbox"],
)
