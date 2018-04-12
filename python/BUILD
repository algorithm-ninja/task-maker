package(default_visibility = ["//visibility:public"])

load("@python_deps//:requirements.bzl", "pypi_requirements")

py_library(
    name = "language",
    srcs = ["language.py"],
    deps = [
        "//proto:task_py",
        pypi_requirements(),
    ],
)

py_library(
    name = "detect_exe",
    srcs = ["detect_exe.py"],
)

py_library(
    name = "detect_format",
    srcs = ["detect_format.py"],
    deps = [
        pypi_requirements(),
    ],
)

py_library(
    name = "source_file",
    srcs = ["source_file.py"],
    deps = [
        ":dependency_finder",
        ":detect_exe",
        ":language",
        "//proto:task_py",
        pypi_requirements(),
    ],
)

py_library(
    name = "ui",
    srcs = ["ui.py"],
    deps = [
        "//proto:event_py",
        pypi_requirements(),
    ],
)

py_library(
    name = "silent_ui",
    srcs = ["uis/silent_ui.py"],
    deps = [
        ":ui",
        "//proto:event_py",
        pypi_requirements(),
    ],
)

py_library(
    name = "curses_ui",
    srcs = ["uis/curses_ui.py"],
    deps = [
        ":printer",
        ":silent_ui",
        ":ui",
        "//proto:event_py",
        pypi_requirements(),
    ],
)

py_library(
    name = "print_ui",
    srcs = ["uis/print_ui.py"],
    deps = [
        ":ui",
        "//proto:event_py",
        pypi_requirements(),
    ],
)

py_library(
    name = "dependency_finder",
    srcs = ["dependency_finder.py"],
    deps = [
        ":language",
        "//proto:task_py",
        pypi_requirements(),
    ],
)

py_library(
    name = "sanitize",
    srcs = ["sanitize.py"],
    deps = [
        ":dependency_finder",
        pypi_requirements(),
    ],
)

py_library(
    name = "ioi_format",
    srcs = ["ioi_format.py"],
    deps = [
        ":absolutize",
        ":dependency_finder",
        ":language",
        ":sanitize",
        ":source_file",
        "//proto:manager_py",
        "//proto:task_py",
        pypi_requirements(),
    ],
)

py_library(
    name = "terry_format",
    srcs = ["terry_format.py"],
    deps = [
        ":dependency_finder",
        ":language",
        ":sanitize",
        ":source_file",
        "//proto:manager_py",
        "//proto:task_py",
        pypi_requirements(),
    ],
)

py_library(
    name = "args",
    srcs = ["args.py"],
    deps = [
        ":curses_ui",
        ":print_ui",
        ":silent_ui",
        "//proto:manager_py",
        "//proto:task_py",
    ],
)

py_library(
    name = "absolutize",
    srcs = ["absolutize.py"],
    deps = [
        "//proto:manager_py",
        "//proto:task_py",
    ],
)

py_library(
    name = "printer",
    srcs = ["printer.py"],
    deps = [
    ],
)

py_library(
    name = "manager",
    srcs = ["manager.py"],
    deps = [
        "//proto:manager_py",
    ],
)

py_binary(
    name = "task_maker",
    srcs = ["task_maker.py"],
    data = [
        "//manager",
        "//remote:server",
        "//remote:worker",
    ],
    deps = [
        ":args",
        ":detect_format",
        ":ioi_format",
        ":manager",
        ":terry_format",
        pypi_requirements(),
    ],
)
