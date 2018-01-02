package(default_visibility = ["//visibility:public"])

load("@python_deps//:requirements.bzl", "requirement")

py_library(
    name = "language",
    srcs = ["language.py"],
    deps = [
        "//proto:task_py",
    ],
)

py_library(
    name = "detect_exe",
    srcs = ["detect_exe.py"],
)

py_library(
    name = "source_file",
    srcs = ["source_file.py"],
    deps = [
        ":dependency_finder",
        ":detect_exe",
        ":language",
        "//proto:task_py",
    ],
)

py_library(
    name = "ui",
    srcs = ["ui.py"],
)

py_library(
    name = "silent_ui",
    srcs = ["silent_ui.py"],
    deps = [":ui"],
)

py_library(
    name = "curses_ui",
    srcs = ["curses_ui.py"],
    deps = [
        ":silent_ui",
        ":ui",
    ],
)

py_library(
    name = "print_ui",
    srcs = ["print_ui.py"],
    deps = [":ui"],
)

py_library(
    name = "dependency_finder",
    srcs = ["dependency_finder.py"],
    deps = [
        ":language",
        "//proto:task_py",
    ],
)

py_library(
    name = "sanitize",
    srcs = ["sanitize.py"],
    deps = [
        ":dependency_finder",
    ],
)

py_library(
    name = "italian_format",
    srcs = ["italian_format.py"],
    deps = [
        ":dependency_finder",
        ":language",
        ":sanitize",
        ":source_file",
        "//proto:manager_py",
        "//proto:task_py",
        requirement("PyYAML"),
    ],
)

py_library(
    name = "args",
    srcs = ["args.py"],
    deps = [
        "//proto:manager_py",
        ":curses_ui",
        ":print_ui",
        ":silent_ui",
    ]
)

py_library(
    name = "absolutize",
    srcs = ["absolutize.py"],
    deps = [
        "//proto:manager_py",
        "//proto:task_py",
    ]
)

py_binary(
    name = "task_maker",
    srcs = ["task_maker.py"],
    deps = [
        ":absolutize",
        ":args",
        ":italian_format",
        requirement("grpcio"),
    ],
)
