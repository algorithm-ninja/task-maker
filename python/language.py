#!/usr/bin/env python

import os
from itertools import chain
from typing import List

from proto.task_pb2 import CPP, C, PASCAL, PYTHON, BASH, RUBY, INVALID_LANGUAGE

EXTENSIONS = {
    CPP: [".cpp", ".C", ".cc"],
    C: [".c"],
    PASCAL: [".pas"],
    PYTHON: [".py"],
    BASH: [".sh"],
    RUBY: [".rb"],
}


def valid_extensions():
    # type: () -> List[str]
    return list(chain(*EXTENSIONS.values()))


def from_file(path):
    # type: (str) -> int
    ext = os.path.splitext(path)[1]
    for lang, exts in EXTENSIONS.items():
        if ext in exts:
            return lang
    return INVALID_LANGUAGE


def grader_from_file(path):
    # type: (str) -> int
    return from_file(path)


def need_compilation(language):
    # type: (int) -> bool
    return language in [CPP, C, PASCAL]
