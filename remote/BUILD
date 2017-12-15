# Server and worker for remote execution
package(default_visibility = ["//visibility:public"])

load("@org_pubref_rules_protobuf//cpp:rules.bzl", "GRPC_COMPILE_DEPS")

cc_binary(
    name = "server",
    srcs = ["server.cpp"],
    deps = [
        "//proto:server_cc",
        "//util:flags",
        "//util:file",
    ] + GRPC_COMPILE_DEPS,
)
