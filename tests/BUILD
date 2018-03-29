package(default_visibility = ["//visibility:public"])

load("@python_deps//:requirements.bzl", "requirement")

py_library(
    name = "test",
    srcs = [
        "test.py",
        "utils.py",
    ],
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
    deps = [
        ":test",
    ],
)

py_test(
    name = "without_st",
    size = "medium",
    timeout = "short",
    srcs = ["without_st.py"],
    data = glob(["task_without_st/**"]),
    deps = [
        ":test",
    ],
)

py_test(
    name = "with_bugged_gen",
    size = "medium",
    timeout = "short",
    srcs = ["with_bugged_gen.py"],
    data = glob(["task_with_bugged_gen/**"]),
    deps = [
        ":test",
    ],
)

py_test(
    name = "with_bugged_sol",
    size = "medium",
    timeout = "short",
    srcs = ["with_bugged_sol.py"],
    data = glob(["task_with_bugged_sol/**"]),
    deps = [
        ":test",
    ],
)

py_test(
    name = "with_stdin",
    size = "medium",
    timeout = "short",
    srcs = ["with_stdin.py"],
    data = glob(["task_with_stdin/**"]),
    deps = [
        ":test",
    ],
)

py_test(
    name = "with_checker",
    size = "medium",
    timeout = "short",
    srcs = ["with_checker.py"],
    data = glob(["task_with_checker/**"]),
    deps = [
        ":test",
    ],
)

py_test(
    name = "with_bugged_checker",
    size = "medium",
    timeout = "short",
    srcs = ["with_bugged_checker.py"],
    data = glob(["task_with_bugged_checker/**"]),
    deps = [
        ":test",
    ],
)

py_test(
    name = "without_gen",
    size = "medium",
    timeout = "short",
    srcs = ["without_gen.py"],
    data = glob(["task_without_gen/**"]),
    deps = [
        ":test",
    ],
)

py_test(
    name = "terry_with_validator",
    size = "medium",
    timeout = "short",
    srcs = ["terry_with_validator.py"],
    data = glob(["task_terry_with_validator/**"]),
    deps = [
        ":test",
        "//proto:event_py",
    ],
)

py_test(
    name = "terry_without_validator",
    size = "medium",
    timeout = "short",
    srcs = ["terry_without_validator.py"],
    data = glob(["task_terry_without_validator/**"]),
    deps = [
        ":test",
        "//proto:event_py",
    ],
)

py_test(
    name = "terry_with_bugged_gen",
    size = "medium",
    timeout = "short",
    srcs = ["terry_with_bugged_gen.py"],
    data = glob(["task_terry_with_bugged_gen/**"]),
    deps = [
        ":test",
        "//proto:event_py",
    ],
)
