#!/usr/bin/env python3

from proto.task_pb2 import SourceFile

import python.language
from python.dependency_finder import find_dependency


def from_file(path: str) -> SourceFile:
    source_file = SourceFile()
    source_file.path = path
    source_file.deps.extend(find_dependency(path))
    source_file.language = python.language.from_file(path)
    return source_file
