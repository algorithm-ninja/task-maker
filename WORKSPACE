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

new_git_repository(
    name = "pybind11",
    build_file = "tools/pybind11.BUILD",
    remote = "https://github.com/pybind/pybind11",
    tag = "v2.2.1",
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

# Rules for internal python
new_http_archive(
    name = "python_repo",
    build_file = "tools/python.BUILD",
    sha256 = "cda7d967c9a4bfa52337cdf551bcc5cff026b6ac50a8834e568ce4a794ca81da",
    url = "https://www.python.org/ftp/python/3.6.3/Python-3.6.3.tar.xz",
)

bind(
    name = "python_3_6_hdr",
    actual = "@python_repo//:python_3_6_hdr",
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
