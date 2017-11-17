workspace(name = "oii_task_maker")

git_repository(
    name = "org_pubref_rules_protobuf",
    remote = "https://github.com/pubref/rules_protobuf.git",
    tag = "v0.8.0",
)

new_git_repository(
    name = "googletest",
    remote = "https://github.com/google/googletest",
    tag = "release-1.8.0",
    build_file = "BUILD.googletest",
)

load("@org_pubref_rules_protobuf//cpp:rules.bzl", "cpp_proto_repositories")
cpp_proto_repositories()


