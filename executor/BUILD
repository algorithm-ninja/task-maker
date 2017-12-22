# More user-friendly interface on top of sandboxes.
package(default_visibility = ["//visibility:public"])

load("@org_pubref_rules_protobuf//cpp:rules.bzl", "GRPC_COMPILE_DEPS")

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
        "//sandbox",
    ],
)

cc_library(
    name = "remote_executor",
    srcs = ["remote_executor.cpp"],
    hdrs = ["remote_executor.hpp"],
    deps = [
        ":executor",
        "//remote:common",
    ] + GRPC_COMPILE_DEPS,
)
