#!/usr/bin/env python3

import os.path
import re
from collections import namedtuple
from typing import List

from python.language import Language

CXX_INCLUDE = re.compile('#include *["<](.+)[">]')
PY_IMPORT = re.compile('import +(.+)|from +(.+) +import')

Dependency = namedtuple("Dependency", ["name", "path"])


def find_python_dependency(content: str, scope: str) -> List[Dependency]:
    imports = PY_IMPORT.findall(content)
    dependencies = []  # type: List[Dependency]
    for imp in imports:
        import_files = imp[0] or imp[1]
        for import_file in import_files.split(","):
            file_path = os.path.join(scope, import_file.strip() + ".py")
            basename = os.path.basename(file_path)
            if os.path.exists(file_path):
                dependencies += [Dependency(name=basename, path=file_path)]
                dependencies += find_dependency(file_path)
    return dependencies


def find_cxx_dependency(content: str, scope: str) -> List[Dependency]:
    includes = CXX_INCLUDE.findall(content)
    dependencies = []  # type: List[Dependency]
    for include in includes:
        file_path = os.path.join(scope, include)
        # the sandbox does not support file inside subdirs (nor ../something),
        # for convenience skip all the files that includes "/" in the name
        if os.path.exists(file_path) and os.sep not in include:
            dependencies += [Dependency(name=include, path=file_path)]
            dependencies += find_dependency(file_path)
    return dependencies


def find_dependency(filename: str) -> List[Dependency]:
    scope = os.path.dirname(filename)
    try:
        with open(filename) as file:
            lang = Language.from_file(filename)
            if lang == Language.PY:
                return list(set(find_python_dependency(file.read(), scope)))
            elif lang in [Language.C, Language.CPP,
                          Language.C_HEADER, Language.CPP_HEADER]:
                return list(set(find_cxx_dependency(file.read(), scope)))
            return []
    except FileNotFoundError:
        return []
    except UnicodeDecodeError:
        return []
