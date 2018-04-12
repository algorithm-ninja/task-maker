package(default_visibility = ["//visibility:public"])

cc_library(
    name = "ioi_generation",
    srcs = ["ioi_generation.cpp"],
    hdrs = ["ioi_generation.hpp"],
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
    name = "ioi_evaluation",
    srcs = ["ioi_evaluation.cpp"],
    hdrs = ["ioi_evaluation.hpp"],
    deps = [
        ":ioi_generation",
        "//core",
        "//core:execution",
        "//core:file_id",
        "//external:glog",
        "//manager:evaluation",
        "//manager:event_queue",
        "//manager:source_file",
        "//proto:manager_cc",
        "//proto:task_cc",
        "//util:which",
    ],
)

cc_library(
    name = "ioi_format",
    srcs = ["ioi_format.cpp"],
    hdrs = ["ioi_format.hpp"],
    deps = [
        ":ioi_evaluation",
        ":ioi_generation",
        "//manager:evaluation_info",
        "//proto:manager_cc",
    ],
)
