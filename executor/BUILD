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
    name = "executor_builder",
    srcs = ["executor_builder.cpp"],
    hdrs = ["executor_builder.hpp"],
    deps = [
        ":executor",
    ],
)
