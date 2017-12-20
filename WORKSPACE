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

load("//tools:python.bzl", "python_repository")

python_repository(
    name = "python3",
    version = "3",
)

new_git_repository(
    name = "pyyaml",
    build_file = "tools/pyyaml.BUILD",
    remote = "https://github.com/yaml/pyyaml.git",
    tag = "3.12",
)

new_http_archive(
    name = "pytest",
    url = "https://pypi.python.org/packages/53/d0/208853c09be8377e6d4de7c0df875ef7ef37189373d76a74b65b44e50528/pytest-3.2.3.tar.gz",
    sha256 = "27fa6617efc2869d3e969a3e75ec060375bfb28831ade8b5cdd68da3a741dc3c",
    build_file = "tools/pytest.BUILD",
    strip_prefix = "pytest-3.2.3",
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
