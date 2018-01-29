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

py_test(
    name = "with_bugged_gen",
    size = "medium",
    timeout = "short",
    srcs = ["with_bugged_gen.py"],
    data = glob(["task_with_bugged_gen/**"]),
    flaky = True,
    deps = [
        ":test"
    ],
)

py_test(
    name = "with_bugged_sol",
    size = "medium",
    timeout = "short",
    srcs = ["with_bugged_sol.py"],
    data = glob(["task_with_bugged_sol/**"]),
    flaky = True,
    deps = [
        ":test"
    ],
)

py_test(
    name = "with_stdin",
    size = "medium",
    timeout = "short",
    srcs = ["with_stdin.py"],
    data = glob(["task_with_stdin/**"]),
    flaky = True,
    deps = [
        ":test"
    ],
)
