package(default_visibility = ["//visibility:public"])

load('/tools/python_external', 'python_package_lib')

python_package_lib(
    name = 'pytest',
    dep = '@pytest//:files',
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
    imports = ["bindings"],
    deps = [
        "//bindings:task_maker",
        "//python:task_maker",
        "//python:silent_ui",
        "//python:ui",
        ":pytest",
    ],
    data = glob(["test_task/**"])
)
