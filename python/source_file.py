#!/usr/bin/env python3

from proto.task_pb2 import SourceFile

import python.language
from python.dependency_finder import find_dependency
from python.detect_exe import get_exeflags, EXEFLAG_NONE


def is_executable(path: str) -> bool:
    if get_exeflags(path) != EXEFLAG_NONE:
        return True
    with open(path, "rb") as source:
        if source.read(2) == b"#!":
            return True
    return False


def from_file(path: str) -> SourceFile:
    source_file = SourceFile()
    source_file.path = path
    source_file.deps.extend(find_dependency(path))
    source_file.language = python.language.from_file(path)
    if not python.language.need_compilation(source_file.language):
        if not is_executable(source_file.path):
            raise ValueError("The file %s is not and executable. "
                             "Please check the shebang (#!)" % path)
    return source_file
