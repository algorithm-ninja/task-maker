package(default_visibility = ["//visibility:public"])

py_binary(
    name = "test",
    srcs = ["test.py"],
    data = ["//bindings:sum.so"],
    imports = ["bindings"],
)
