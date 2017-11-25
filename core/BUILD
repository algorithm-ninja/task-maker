# This folder deals with dependency handling.
package(default_visibility = ["//visibility:public"])

cc_library(
    name = "file_id",
    srcs = ["file_id.cpp"],
    hdrs = ["file_id.hpp"],
    deps = [
        "//util:file",
        "//util:flags",
        "//util:sha256",
    ],
)

cc_library(
    name = "execution",
    srcs = ["execution.cpp"],
    hdrs = ["execution.hpp"],
    deps = [
        ":file_id",
        "//executor:local_executor",
        "//proto:response_cc",
    ],
)

cc_library(
    name = "core",
    srcs = ["core.cpp"],
    hdrs = ["core.hpp"],
    deps = [
        ":execution",
        ":file_id",
    ],
)
