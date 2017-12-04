package(default_visibility = ["//visibility:public"])

py_test(
    name = "test",
    size = "small",
    srcs = ["test.py"],
    data = [
        "//bindings:task_maker",
    ],
    imports = ["bindings"],
)
