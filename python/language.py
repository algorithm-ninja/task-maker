#!/usr/bin/env python3

from itertools import chain
import os
from enum import Enum
from typing import List


class Language(Enum):
    INVALID_LANGUAGE = 0
    CPP = 1
    C = 2
    PASCAL = 3
    PYTHON = 4
    BASH = 5
    RUBY = 6
    ERLANG = 7
    RUST = 8


EXTENSIONS = {
    Language.CPP: [".cpp", ".C", ".cc"],
    Language.C: [".c"],
    Language.PASCAL: [".pas"],
    Language.PYTHON: [".py"],
    Language.BASH: [".sh", ""],  # TODO(edomora97) add executable format
    Language.RUBY: [".rb"],
    Language.ERLANG: [".erl"],
    Language.RUST: [".rs"],
}


def valid_extensions() -> List[str]:
    return list(chain(*EXTENSIONS.values()))


def from_file(path: str) -> Language:
    ext = os.path.splitext(path)[1]
    for lang, exts in EXTENSIONS.items():
        if ext in exts:
            return lang
    return Language.INVALID_LANGUAGE


def grader_from_file(path: str) -> Language:
    return from_file(path)


def need_compilation(language: Language) -> bool:
    return language in [Language.CPP, Language.C, Language.PASCAL, Language.RUST]
