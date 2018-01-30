package(default_visibility = ["//visibility:public"])

cc_library(
    name = "sha256",
    srcs = ["sha256.cpp"],
    hdrs = ["sha256.hpp"],
    deps = ["//proto:sha256_cc"],
)

cc_library(
    name = "file",
    srcs = ["file.cpp"],
    hdrs = ["file.hpp"],
    deps = [
        ":sha256",
        "//external:glog",
        "//proto:file_cc",
        "//proto:sha256_cc",
    ],
)

cc_library(
    name = "which",
    srcs = ["which.cpp"],
    hdrs = ["which.hpp"],
    deps = [
        ":file",
        "@com_google_absl//absl/strings",
    ],
)
