package(default_visibility = ["//visibility:public"])

cc_library(
    name = "sha256",
    srcs = ["sha256.cpp"],
    hdrs = ["sha256.hpp"],
    deps = ["//proto:sha256_cc"],
)

cc_library(
    name = "flags",
    srcs = ["flags.cpp"],
    hdrs = ["flags.hpp"],
    deps = [
        "//external:gflags",
    ],
)

cc_library(
    name = "file",
    srcs = ["file.cpp"],
    hdrs = ["file.hpp"],
    deps = [
        ":flags",
        ":sha256",
        "//proto:file_cc",
        "//proto:sha256_cc",
    ],
)
