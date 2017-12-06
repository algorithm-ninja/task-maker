package(default_visibility = ["//visibility:public"])

py_test(
    name = "test",
    size = "small",
    srcs = ["test.py"],
    imports = ["bindings"],
    deps = [
        "//bindings:task_maker",
    ],
)

py_library(
    name = "language",
    srcs = ["language.py"],
)

py_library(
    name = "source_file",
    srcs = ["source_file.py"],
    deps = [":language"],
)

py_library(
    name = "task",
    srcs = ["task.py"],
    deps = [
        ":language",
        ":source_file",
    ],
)

py_library(
    name = "dispatcher",
    srcs = ["dispatcher.py"],
    imports = ["bindings"],
    deps = [
        "//bindings:task_maker",
    ],
)
