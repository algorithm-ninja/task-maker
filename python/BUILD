package(default_visibility = ["//visibility:public"])

py_test(
    name = "test",
    srcs = ["test.py"],
    data = [
        "//bindings:core.so",
        "//bindings:execution.so",
        "//bindings:file_id.so",
    ],
    imports = ["bindings"],
)
