package(default_visibility = ["//visibility:public"])

cc_library(
    name = "pybind11",
    hdrs = glob(
      include=["include/pybind11/**/*.h"],
      exclude=["include/pybind11/eigen.h"],
    ),
    includes = ["include"],
    deps = [
        "@python3//:python",
    ],
)
