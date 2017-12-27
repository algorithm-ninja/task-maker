package(default_visibility = ["//visibility:public"])

cc_library(
    name = "event_queue",
    srcs = ["event_queue.cpp"],
    hdrs = ["event_queue.hpp"],
    deps = [
        "//proto:event_cc",
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
