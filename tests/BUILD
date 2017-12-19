package(default_visibility = ["//visibility:public"])

py_test(
    name = "simple_bindings",
    size = "small",
    srcs = ["simple_bindings.py"],
    imports = ["bindings"],
    deps = [
        "//bindings:task_maker",
    ],
)

py_test(
    name = "task",
    size = "small",
    srcs = ["task.py"],
    imports = ["bindings"],
    deps = [
        "//bindings:task_maker",
        "//python:task_maker",
        "//python:silent_ui",
        "//python:ui",
    ],
    data = glob(["test_task/**"])
)
