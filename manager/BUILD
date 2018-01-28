package(default_visibility = ["//visibility:public"])

load("@org_pubref_rules_protobuf//cpp:rules.bzl", "GRPC_COMPILE_DEPS")

cc_library(
    name = "event_queue",
    srcs = ["event_queue.cpp"],
    hdrs = ["event_queue.hpp"],
    deps = [
        "//proto:event_cc",
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
        "//proto:task_cc",
        "@com_google_absl//absl/types:optional",
    ],
)

cc_library(
    name = "generation",
    srcs = ["generation.cpp"],
    hdrs = ["generation.hpp"],
    deps = [
        ":event_queue",
        ":source_file",
        "//core",
        "//core:file_id",
        "//proto:manager_cc",
        "//proto:task_cc",
    ],
)

cc_library(
    name = "evaluation",
    srcs = ["evaluation.cpp"],
    hdrs = ["evaluation.hpp"],
    deps = [
        ":event_queue",
        ":generation",
        ":source_file",
        "//core",
        "//core:execution",
        "//core:file_id",
        "//proto:manager_cc",
        "//proto:task_cc",
    ],
)

cc_binary(
    name = "manager",
    srcs = ["manager.cpp"],
    deps = [
        "//core:core",
        "//sandbox:unix",
        ":evaluation",
        ":event_queue",
        "//util:file",
        "//proto:manager_cc",
        "//external:gflags",
        "//external:glog",
        "@com_google_absl//absl/types:optional",
        "@com_google_absl//absl/memory",
    ] + GRPC_COMPILE_DEPS,
)
