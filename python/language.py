#!/usr/bin/env python3

import os
from itertools import chain
from typing import List

from task_maker.formats import Language

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
