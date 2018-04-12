package(default_visibility = ["//visibility:public"])

load("@org_pubref_rules_protobuf//cpp:rules.bzl", "GRPC_COMPILE_DEPS")

cc_library(
    name = "terry_generation",
    srcs = ["terry_generation.cpp"],
    hdrs = ["terry_generation.hpp"],
    deps = [
        "//core",
        "//core:file_id",
        "//manager:event_queue",
        "//manager:generation",
        "//manager:source_file",
        "//proto:manager_cc",
        "//proto:task_cc",
    ],
)

cc_library(
    name = "terry_evaluation",
    srcs = ["terry_evaluation.cpp"],
    hdrs = ["terry_evaluation.hpp"],
    deps = [
        ":terry_generation",
        "//core",
        "//core:execution",
        "//core:file_id",
        "//external:glog",
        "//external:json",
        "//manager:evaluation",
        "//manager:event_queue",
        "//manager:source_file",
        "//proto:manager_cc",
        "//proto:task_cc",
    ],
)

cc_library(
    name = "terry_format",
    srcs = ["terry_format.cpp"],
    hdrs = ["terry_format.hpp"],
    deps = [
        ":terry_evaluation",
        ":terry_generation",
        "//manager:evaluation_info",
        "//proto:manager_cc",
    ],
)
