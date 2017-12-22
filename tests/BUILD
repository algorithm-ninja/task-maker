package(default_visibility = ["//visibility:public"])

load("//tools:smart_py_binary.bzl", "smart_py_test")

smart_py_test(
    name = "simple_bindings",
    size = "medium",
    timeout = "short",
    srcs = ["simple_bindings.py"],
    deps = [
        "//bindings:task_maker",
    ],
)

smart_py_test(
    name = "task",
    size = "medium",
    timeout = "short",
    srcs = ["task.py"],
    data = glob(["test_task/**"]),
    flaky = True,
    deps = [
        "//python:italian_format",
        "//python:silent_ui",
    ],
)
