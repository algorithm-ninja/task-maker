#!/usr/bin/env python3

import os
from enum import Enum


class Language(Enum):
    # pylint: disable=invalid-name
    C = 0
    CPP = 1
    PY = 2
    SH = 3
    C_HEADER = 4
    CPP_HEADER = 5


    @classmethod
    def from_file(cls, path: str) -> 'Language':
        ext = os.path.splitext(path)[1]
        if ext in ['.cpp', '.cc', '.C']:
            return cls.CPP
        elif ext in ['.c']:
            return cls.C
        elif ext in ['.py']:
            return cls.PY
        elif ext in ['.sh']:
            return cls.SH
        elif ext in ['.h']:
            return cls.C_HEADER
        elif ext in ['.hpp']:
            return cls.CPP_HEADER
        else:
            raise RuntimeError("Unknown source file language")

    def needs_compilation(self) -> bool:
        return self not in [Language.SH, Language.PY]
