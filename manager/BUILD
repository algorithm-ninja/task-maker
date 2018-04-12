package(default_visibility = ["//visibility:public"])

load("@org_pubref_rules_protobuf//cpp:rules.bzl", "GRPC_COMPILE_DEPS")

cc_library(
    name = "event_queue",
    srcs = ["event_queue.cpp"],
    hdrs = ["event_queue.hpp"],
    deps = [
        "//proto:event_cc",
        "//proto:manager_cc",
        "@com_google_absl//absl/base:core_headers",
        "@com_google_absl//absl/synchronization",
        "@com_google_absl//absl/types:optional",
    ],
)

cc_library(
    name = "source_file",
    srcs = ["source_file.cpp"],
    hdrs = ["source_file.hpp"],
    deps = [
        ":event_queue",
        "//core",
        "//core:execution",
        "//external:glog",
        "//proto:manager_cc",
        "//proto:task_cc",
        "//util:which",
        "@com_google_absl//absl/types:optional",
    ],
)

cc_library(
    name = "generation",
    hdrs = ["generation.hpp"],
    deps = [
    ],
)

cc_library(
    name = "evaluation",
    hdrs = ["evaluation.hpp"],
    deps = [
        ":source_file",
    ],
)

cc_library(
    name = "evaluation_info",
    hdrs = ["evaluation_info.hpp"],
    deps = [
        ":evaluation",
        ":event_queue",
        ":generation",
        ":source_file",
        "//core",
    ],
)

cc_binary(
    name = "manager",
    srcs = ["manager.cpp"],
    deps = [
        "//core:core",
        "//sandbox:unix",
        ":event_queue",
        ":evaluation_info",
        "//util:file",
        "//proto:manager_cc",
        "//external:gflags",
        "//external:glog",
        "//manager/ioi_format:ioi_format",
        "//manager/terry_format:terry_format",
        "@com_google_absl//absl/types:optional",
        "@com_google_absl//absl/memory",
    ] + GRPC_COMPILE_DEPS,
)
