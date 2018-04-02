#!/usr/bin/env python

import re

import os.path
from proto.task_pb2 import CPP, C, PYTHON
from proto.task_pb2 import Dependency
from typing import List

from python import language

CXX_INCLUDE = re.compile('#include *["<](.+)[">]')
PY_IMPORT = re.compile('import +(.+)|from +(.+) +import')


def find_python_dependency(content, scope):
    # type: (str, str) -> List[Dependency]
    imports = PY_IMPORT.findall(content)
    dependencies = []  # type: List[Dependency]
    for imp in imports:
        import_files = imp[0] or imp[1]
        for import_file in import_files.split(","):
            file_path = os.path.join(scope, import_file.strip() + ".py")
            basename = os.path.basename(file_path)
            if os.path.exists(file_path):
                dependency = Dependency()
                dependency.name = basename
                dependency.path = file_path
                dependencies += [dependency]
                dependencies += find_dependency(file_path)
    return dependencies


def find_cxx_dependency(content, scope):
    # type: (str, str) -> List[Dependency]
    includes = CXX_INCLUDE.findall(content)
    dependencies = []  # type: List[Dependency]
    for include in includes:
        file_path = os.path.join(scope, include)
        if os.path.islink(file_path):
            file_path = os.path.realpath(file_path)
        # the sandbox does not support file inside subdirs (nor ../something),
        # for convenience skip all the files that includes "/" in the name
        if os.path.exists(file_path) and os.sep not in include:
            dependency = Dependency()
            dependency.name = include
            dependency.path = file_path
            dependencies += [dependency]
            dependencies += find_dependency(file_path)
    return dependencies


def find_dependency(filename):
    # type: (str) -> List[Dependency]
    scope = os.path.dirname(filename)
    try:
        with open(filename) as file:
            lang = language.from_file(filename)
            if lang == PYTHON:
                return make_unique(find_python_dependency(file.read(), scope))
            elif lang in [C, CPP]:
                # TODO add .h and .hpp files
                return make_unique(find_cxx_dependency(file.read(), scope))
            return []
    except IOError:
        return []
    except UnicodeDecodeError:
        return []


def make_unique(deps):
    # type: (List[Dependency]) -> List[Dependency]
    return list(item[1] for item in {dep.name: dep for dep in deps}.items())
