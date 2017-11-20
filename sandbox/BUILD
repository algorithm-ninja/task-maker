# Sandboxes. Other code should only depend on sandbox.{hpp,cpp} and link
# all the available sandboxes for that system.

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
)

cc_library(
    name = "echo",
    srcs = ["echo.cpp"],
    hdrs = ["echo.hpp"],
    deps = [":sandbox"],
)
