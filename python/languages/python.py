#!/usr/bin/env python3
import os.path
import re
from typing import List

from task_maker.languages import Language, LanguageManager, Dependency, \
    make_unique

PY_IMPORT = re.compile('import +(.+)|from +(.+) +import')


def find_python_dependency(filename: str) -> List[Dependency]:
    scope = os.path.dirname(filename)
    with open(filename) as file:
        content = file.read()
    imports = PY_IMPORT.findall(content)
    dependencies = []  # type: List[Dependency]
    for imp in imports:
        import_files = imp[0] or imp[1]
        for import_file in import_files.split(","):
            file_path = os.path.join(scope, import_file.strip() + ".py")
            basename = os.path.basename(file_path)
            if os.path.exists(file_path):
                dependency = Dependency(basename, file_path)
                dependencies += [dependency]
                dependencies += find_python_dependency(file_path)
    print("DEPS", dependencies)
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
