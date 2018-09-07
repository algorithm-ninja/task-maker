#!/usr/bin/env python3
import os.path
import re
from typing import List, Set

from task_maker.languages import Language, LanguageManager, Dependency, \
    make_unique

PY_IMPORT = re.compile('import +(.+)|from +(.+) +import')


def _extract_imports(filename: str) -> List[str]:
    with open(filename) as file:
        content = file.read()
    imports = PY_IMPORT.findall(content)
    return [imp for imps in imports for imp in (imps[0] or imps[1]).split(",")]


def find_python_dependency(filename: str) -> List[Dependency]:
    scope = os.path.dirname(filename)
    dependencies = []  # type: List[Dependency]
    pending = {filename}  # type: Set[str]
    done = {}  # type: Set[str]
    while pending:
        path = pending.pop()
        imports = _extract_imports(path)
        done.add(path)
        for imp in imports:
            imp_path = os.path.join(scope, imp + ".py")
            if os.path.exists(imp_path) and imp_path not in done:
                basename = os.path.basename(imp_path)
                dependencies.append(Dependency(basename, imp_path))
                pending.add(imp_path)

    return dependencies


class LanguagePython(Language):
    @property
    def name(self):
        return "Python"

    @property
    def source_extensions(self):
        return [".py"]

    def get_dependencies(self, filename: str):
        return make_unique(find_python_dependency(filename))


def register():
    LanguageManager.register_language(LanguagePython())
