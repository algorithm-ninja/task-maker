# More user-friendly interface on top of sandboxes.
package(default_visibility = ["//visibility:public"])

cc_library(
    name = "executor",
    hdrs = ["executor.hpp"],
    deps = [
        "//proto:request_cc",
        "//proto:response_cc",
        "//proto:sha256_cc",
        "//util:file",
    ],
)

cc_library(
    name = "local_executor",
    srcs = ["local_executor.cpp"],
    hdrs = ["local_executor.hpp"],
    deps = [
        ":executor",
        "//external:gflags",
        "//sandbox",
    ],
)
