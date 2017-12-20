package(default_visibility = ["//visibility:public"])

load("/tools/python_external", "python_package_lib")

python_package_lib(
    name = "pytest",
    dep = "@pytest//:files",
)

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
    data = glob(["test_task/**"]),
    imports = ["bindings"],
    deps = [
        ":pytest",
        "//python:italian_format",
        "//python:silent_ui",
    ],
)
