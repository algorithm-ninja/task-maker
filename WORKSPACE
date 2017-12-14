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

new_http_archive(
    name = "ruamel_yaml",
    build_file = "tools/ruamel_yaml.BUILD",
    strip_prefix = "ruamel-yaml-ea4d54f8e034",
    url = "https://bitbucket.org/ruamel/yaml/get/0.15.34.tar.bz2",
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
