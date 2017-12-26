# Protobufs for communication
package(default_visibility = ["//visibility:public"])

load("@org_pubref_rules_protobuf//cpp:rules.bzl", "cc_proto_library")
load("@org_pubref_rules_protobuf//python:rules.bzl", "py_proto_library")

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

cc_proto_library(
    name = "cache_entry_cc",
    proto_deps = [
        ":request_cc",
        ":response_cc",
    ],
    protos = ["cache_entry.proto"],
)

cc_proto_library(
    name = "task_cc",
    protos = ["task.proto"],
)

py_proto_library(
    name = "task_py",
    protos = ["task.proto"],
)

cc_proto_library(
    name = "event_cc",
    protos = ["event.proto"],
)

py_proto_library(
    name = "event_py",
    protos = ["event.proto"],
)

cc_proto_library(
    name = "manager_cc",
    proto_deps = [
        ":event_cc",
        ":task_cc",
    ],
    protos = ["manager.proto"],
)

py_proto_library(
    name = "manager_py",
    proto_deps = [
        ":event_py",
        ":task_py",
    ],
    protos = ["manager.proto"],
)

cc_proto_library(
    name = "server_cc",
    proto_deps = [
        ":file_cc",
        ":request_cc",
        ":response_cc",
        ":sha256_cc",
    ],
    protos = ["server.proto"],
    with_grpc = True,
)
