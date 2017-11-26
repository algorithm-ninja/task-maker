# Python bindings
package(default_visibility = ["//visibility:public"])

cc_binary(
    name = "sum.so",
    srcs = ["sum.cpp"],
    linkshared = 1,
    linkstatic = 1,
    deps = [
        "@pybind11//:pybind11",
    ],
)
