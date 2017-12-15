#!/usr/bin/env python3

import os.path
import re
from typing import List
from collections import namedtuple

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
        # the sandbox does not support file inside subdirs (nor ../something), for convenience skip
        # all the files that includes "/" in the name
        if os.path.exists(file_path) and os.sep not in include:
            dependencies += [Dependency(name=include, path=file_path)]
            dependencies += find_dependency(file_path)
    return dependencies


def find_dependency(filename: str) -> List[Dependency]:
    scope = os.path.dirname(filename)
    ext = os.path.splitext(filename)[1]
    try:
        with open(filename) as file:
            if ext == ".py":
                return list(set(find_python_dependency(file.read(), scope)))
            elif ext in [".cpp", ".hpp", ".c", ".h"]:
                return list(set(find_cxx_dependency(file.read(), scope)))
            return []
    except FileNotFoundError:
        return []


def sanitize_command(args: List[str]) -> List[Dependency]:
    dependencies = []  # type: List[Dependency]
    for i, arg in enumerate(args):
        if os.path.exists(arg):
            name = _sanitize_filename(arg)
            args[i] = name
            dependencies += [Dependency(name=name, path=arg)]
    return dependencies


def _sanitize_filename(filename: str) -> str:
    return "".join(c if c != os.sep else "__" for c in filename)
