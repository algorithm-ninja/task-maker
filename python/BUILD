package(default_visibility = ["//visibility:public"])

py_test(
    name = "test",
    srcs = ["test.py"],
    data = [
        "//bindings:task_maker",
    ],
    default_python_version = "PY3",
    imports = ["bindings"],
    srcs_version = "PY3",
)
