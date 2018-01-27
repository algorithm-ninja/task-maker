package(default_visibility = ["//visibility:public"])

load("@python_deps//:requirements.bzl", "requirement")

py_test(
    name = "task",
    size = "medium",
    timeout = "short",
    srcs = ["task.py"],
    data = glob(["test_task/**"]),
    flaky = True,
    deps = [
        requirement("pytest"),
        "//proto:event_py",
        "//python:args",
        "//python:silent_ui",
        "//python:task_maker",
    ],
)
