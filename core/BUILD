# This folder deals with dependency handling.
package(default_visibility = ["//visibility:public"])

cc_library(
    name = "task_status",
    srcs = [],
    hdrs = ["task_status.hpp"],
)

cc_library(
    name = "waiting_task",
    srcs = [],
    hdrs = ["waiting_task.hpp"],
    deps = [
        ":execution",
        ":file_id",
    ]
)

cc_library(
    name = "file_id",
    srcs = ["file_id.cpp"],
    hdrs = ["file_id.hpp"],
    deps = [
        ":task_status",
        "//external:glog",
        "//util:file",
        "//util:sha256",
        "@com_google_absl//absl/synchronization",
    ],
)

cc_library(
    name = "execution_cacher",
    srcs = ["execution_cacher.cpp"],
    hdrs = ["execution_cacher.hpp"],
    deps = [
        "//external:protobuf",
        "//proto:cache_entry_cc",
        "//proto:request_cc",
        "//proto:response_cc",
        "//util:file",
        "//util:sha256",
    ],
)

cc_library(
    name = "execution",
    srcs = ["execution.cpp"],
    hdrs = ["execution.hpp"],
    deps = [
        ":execution_cacher",
        ":file_id",
        ":task_status",
        "//executor:local_executor",
        "//executor:remote_executor",
        "//proto:response_cc",
    ],
)

cc_library(
    name = "core",
    srcs = ["core.cpp"],
    hdrs = ["core.hpp"],
    deps = [
        ":execution",
        ":execution_cacher",
        ":file_id",
        ":task_status",
        ":waiting_task",
    ],
)
