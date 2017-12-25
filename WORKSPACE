workspace(name = "oii_task_maker")

git_repository(
    name = "org_pubref_rules_protobuf",
    remote = "https://github.com/pubref/rules_protobuf.git",
    tag = "v0.8.1",
)

new_git_repository(
    name = "googletest",
    build_file = "tools/googletest.BUILD",
    remote = "https://github.com/google/googletest",
    tag = "release-1.8.0",
)

git_repository(
    name = "com_github_gflags_gflags",
    remote = "https://github.com/gflags/gflags.git",
    tag = "v2.2.1",
)

# Rules for glog.
git_repository(
    name = "bazel_rules",
    commit = "36c56e5b96731d01693500f86dcb23ff9b405e34",
    remote = "https://github.com/antonovvk/bazel_rules",
)

new_git_repository(
    name = "glog_repo",
    build_file = "tools/glog.BUILD",
    remote = "https://github.com/google/glog.git",
    tag = "v0.3.5",
)

# Rules for Python
git_repository(
    name = "io_bazel_rules_python",
    commit = "63cdc8f29b6e6ff517744756cc67cf05577ae724",
    remote = "https://github.com/bazelbuild/rules_python",
)

load("@io_bazel_rules_python//python:pip.bzl", "pip_repositories", "pip_import")

pip_repositories()

pip_import(
    name = "python_deps",
    requirements = "//tools:requirements.txt",
)

load(
    "@python_deps//:requirements.bzl",
    pip_grpcio_install = "pip_install",
)

pip_grpcio_install()

# Rules for absl
git_repository(
    name = "com_google_absl",
    commit = "dedb4eec6cf0addc26cc27b67c270aa5a478fcc5",
    remote = "https://github.com/abseil/abseil-cpp.git",
)

# CCTZ (Time-zone framework).
http_archive(
    name = "com_googlesource_code_cctz",
    strip_prefix = "cctz-master",
    urls = ["https://github.com/google/cctz/archive/master.zip"],
)

# RE2 regular-expression framework. Used by some unit-tests.
http_archive(
    name = "com_googlesource_code_re2",
    strip_prefix = "re2-master",
    urls = ["https://github.com/google/re2/archive/master.zip"],
)

bind(
    name = "glog",
    actual = "@glog_repo//:glog",
)

bind(
    name = "gflags",
    actual = "@com_github_gflags_gflags//:gflags",
)

bind(
    name = "gflags_nothreads",
    actual = "@com_github_gflags_gflags//:gflags_nothreads",
)

load("@org_pubref_rules_protobuf//cpp:rules.bzl", "cpp_proto_repositories")

cpp_proto_repositories()
