# Protobufs for communication
package(default_visibility = ["//visibility:public"])

load("@org_pubref_rules_protobuf//cpp:rules.bzl", "cc_proto_library")

cc_proto_library(
    name = "sha256_cc",
    protos = ["sha256.proto"],
)

cc_proto_library(
    name = "resources_cc",
    protos = ["resources.proto"],
)

cc_proto_library(
    name = "file_cc",
    proto_deps = ["sha256_cc"],
    protos = ["file.proto"],
)

cc_proto_library(
    name = "request_cc",
    proto_deps = [
        ":file_cc",
        ":resources_cc",
    ],
    protos = ["request.proto"],
)

cc_proto_library(
    name = "response_cc",
    proto_deps = [
        ":file_cc",
        ":resources_cc",
    ],
    protos = ["response.proto"],
)
