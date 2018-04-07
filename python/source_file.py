#!/usr/bin/env python
import os.path
from typing import Optional

from proto.task_pb2 import SourceFile, DEFAULT

import python.language
from python.dependency_finder import find_dependency
from python.detect_exe import get_exeflags, EXEFLAG_NONE


def is_executable(path):
    # type: (str) -> bool
    if get_exeflags(path) != EXEFLAG_NONE:
        return True
    with open(path, "rb") as source:
        if source.read(2) == b"#!":
            return True
    return False


def from_file(path, write_to=None, target_arch=DEFAULT):
    # type: (str, Optional[str], int) -> SourceFile
    source_file = SourceFile()
    source_file.path = path
    source_file.deps.extend(find_dependency(path))
    source_file.language = python.language.from_file(path)
    if write_to:
        if not os.path.isabs(write_to):
            write_to = os.path.join(os.getcwd(), write_to)
        source_file.write_bin_to = write_to
    if target_arch != DEFAULT:
        source_file.target_arch = target_arch
    if not python.language.need_compilation(source_file.language):
        if not is_executable(source_file.path):
            raise ValueError("The file %s is not an executable. "
                             "Please check the shebang (#!)" % path)
    return source_file
