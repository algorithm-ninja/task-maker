package(default_visibility = ["//visibility:public"])

load("//tools:pkg.bzl", "pkg_tar", "pkg_deb", "strip_tar")

genrule(
    name = "task-maker-runner",
    srcs = [],
    outs = ["task-maker"],
    cmd = """
cat > $@ <<EOF
#!/usr/bin/env sh
/opt/task-maker/task-maker "\$$@"
EOF
    """,
    executable = True,
    output_to_bindir = True,
)

pkg_tar(
    name = "release-unstripped",
    extension = "tar.xz",
    files = [
        ":task-maker-runner",
        "//python:task_maker",
    ],
    mode = "0755",
    package_dir = "/opt/task-maker/task-maker.runfiles/oii_task_maker/",
    strip_prefix = ".",
    symlinks = {
        "opt/task-maker/task-maker": "task-maker.runfiles/oii_task_maker/python/task_maker",
        "usr/bin/task-maker": "/opt/task-maker/task-maker.runfiles/oii_task_maker/task-maker",
    },
)

strip_tar(
    name = "release-tar",
    out = "release.tar.xz",
    data = ":release-unstripped",
)

pkg_deb(
    name = "release-deb",
    architecture = "amd64",
    data = "release-tar",
    depends = [
        "python3",
        "python",
    ],
    description = "The new cmsMake",
    maintainer = "Edoardo Morassutto <edoardo.morassutto@gmail.com>",
    package = "task-maker",
    version = "1.0.1",
)
