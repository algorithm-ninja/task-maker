# Python bindings

cc_binary(
    name = "file_id.so",
    srcs = ["file_id.cpp"],
    linkshared = 1,
    linkstatic = 1,
    deps = [
        "//core:file_id",
        "@pybind11//:pybind11",
    ],
)

cc_binary(
    name = "execution.so",
    srcs = ["execution.cpp"],
    linkshared = 1,
    linkstatic = 1,
    deps = [
        "//core:execution",
        "@pybind11//:pybind11",
    ],
)

cc_binary(
    name = "core.so",
    srcs = ["core.cpp"],
    linkshared = 1,
    linkstatic = 1,
    deps = [
        "//core",
        "//sandbox:unix",
        "@pybind11//:pybind11",
    ],
)

py_library(
    name = "task_maker",
    srcs = ["__init__.py"],
    data = [
        ":core.so",
        ":execution.so",
        ":file_id.so",
    ],
    visibility = ["//visibility:public"],
)
