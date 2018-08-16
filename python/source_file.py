#!/usr/bin/env python3
import os.path
from typing import Optional, Dict
from distutils.spawn import find_executable

from task_maker.language import Language, from_file as language_from_file, need_compilation
from task_maker.dependency_finder import find_dependency
from task_maker.detect_exe import get_exeflags, EXEFLAG_NONE
from task_maker.formats import SourceFile, Arch, GraderInfo


def is_executable(path: str) -> bool:
    if get_exeflags(path) != EXEFLAG_NONE:
        return True
    with open(path, "rb") as source:
        if source.read(2) == b"#!":
            return True
    return False


def from_file(path: str, write_to: Optional[str] = None,
              target_arch=Arch.DEFAULT, grader_map: Dict[Language, GraderInfo] = dict()) -> SourceFile:
    old_path = path
    if not os.path.exists(path):
        path = find_executable(path)
    if not path:
        raise ValueError("Cannot find %s" % old_path)
    language = language_from_file(path)
    source_file = SourceFile(path, find_dependency(path), language, None, target_arch, grader_map.get(language))
    if write_to:
        if not os.path.isabs(write_to):
            write_to = os.path.join(os.getcwd(), write_to)
        source_file.write_bin_to = write_to
    if not need_compilation(source_file.language):
        if not is_executable(source_file.path):
            raise ValueError("The file %s is not an executable. "
                             "Please check the shebang (#!)" % path)
    return source_file
