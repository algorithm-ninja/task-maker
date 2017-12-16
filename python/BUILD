package(default_visibility = ["//visibility:public"])

py_test(
    name = "test",
    size = "small",
    srcs = ["test.py"],
    imports = ["bindings"],
    deps = [
        "//bindings:task_maker",
    ],
)

py_library(
    name = "language",
    srcs = ["language.py"],
)

py_library(
    name = "source_file",
    srcs = ["source_file.py"],
    deps = [
        ":dependency_finder",
        ":language",
        ":ui",
        "//bindings:task_maker",
    ],
)

py_library(
    name = "task",
    srcs = ["task.py"],
    deps = [
        ":language",
        ":source_file",
        ":ui",
        "//bindings:task_maker",
    ],
)

py_library(
    name = "dispatcher",
    srcs = ["dispatcher.py"],
    imports = ["bindings"],
    deps = [
        ":ui",
        "//bindings:task_maker",
    ],
)

py_library(
    name = "ui",
    srcs = ["ui.py"],
)

py_library(
    name = "curses_ui",
    srcs = ["curses_ui.py"],
    deps = [":ui"],
)

py_library(
    name = "print_ui",
    srcs = ["print_ui.py"],
    deps = [":ui"],
)

py_library(
    name = "generation",
    srcs = ["generation.py"],
    deps = [
        ":dependency_finder",
        ":dispatcher",
        ":language",
        ":sanitize",
        ":source_file",
        ":task",
        ":ui",
        "//bindings:task_maker",
    ],
)

py_library(
    name = "evaluation",
    srcs = ["evaluation.py"],
    deps = [
        ":dispatcher",
        ":language",
        ":source_file",
        ":task",
        ":ui",
        "//bindings:task_maker",
    ],
)

py_library(
    name = "dependency_finder",
    srcs = ["dependency_finder.py"],
    deps = [
        ":language"
    ]
)

py_library(
    name = "sanitize",
    srcs = ["sanitize.py"],
    deps = [
        ":dependency_finder"
    ]
)

py_binary(
    name = "task_maker",
    srcs = ["task_maker.py"],
    deps = [
        ":curses_ui",
        ":dispatcher",
        ":evaluation",
        ":generation",
        ":print_ui",
        ":task",
        "@pyyaml//:pyyaml",
    ],
)
