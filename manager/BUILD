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
