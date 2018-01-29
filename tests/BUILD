package(default_visibility = ["//visibility:public"])

load("@python_deps//:requirements.bzl", "requirement")

py_library(
    name = "test",
    srcs = ["test.py"],
    deps = [
        requirement("pytest"),
        "//proto:event_py",
        "//python:args",
        "//python:silent_ui",
        "//python:task_maker",
    ],
)

py_test(
    name = "with_st",
    size = "medium",
    timeout = "short",
    srcs = ["with_st.py"],
    data = glob(["task_with_st/**"]),
    flaky = True,
    deps = [
        ":test"
    ],
)

py_test(
    name = "without_st",
    size = "medium",
    timeout = "short",
    srcs = ["without_st.py"],
    data = glob(["task_without_st/**"]),
    flaky = True,
    deps = [
        ":test"
    ],
)
