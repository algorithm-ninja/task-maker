#!/usr/bin/env python3
import os.path
import re
from task_maker.args import Arch
from task_maker.languages import CompiledLanguage, CommandType, \
    LanguageManager, Dependency, make_unique
from typing import List

ASY_INCLUDE = re.compile('(?:include|import) *(.+);')
ASY_GRAPHIC = re.compile(r"""graphic\(['"](.+)['"]\)""")


def find_asy_dependency(filename: str, strip=None) -> List[Dependency]:
    """
    Find all the dependencies of a asy source file. Will return the list of all
    the other asy files required for the compilation.
    """
    scope = os.path.dirname(filename)
    if strip is None:
        strip = scope + "/"
    with open(filename) as file:
        content = file.read()
    includes = ASY_INCLUDE.findall(content)
    graphics = ASY_GRAPHIC.findall(content)
    dependencies = []  # type: List[Dependency]
    for include in includes:
        file_path = os.path.join(scope, include) + ".asy"
        if file_path.startswith(strip):
            include = file_path[len(strip):]
        if os.path.islink(file_path):
            file_path = os.path.realpath(file_path)
        if os.path.exists(file_path):
            dependency = Dependency(include, file_path)
            dependencies += [dependency]
            dependencies += find_asy_dependency(file_path, strip)
    for graphic in graphics:
        file_path = os.path.join(scope, graphic)
        name = file_path[len(scope) + 1:]
        dependencies += [Dependency(name, file_path)]
    return dependencies


class LanguageAsy(CompiledLanguage):
    @property
    def name(self):
        return "Asy"

    @property
    def source_extensions(self):
        return [".asy"]

    @property
    def header_extensions(self):
        return []

    def exe_name(self, path: str, write_to: str):
        return os.path.basename(path).replace(".asy", ".pdf")

    def get_compilation_command(self, source_filenames: List[str],
                                exe_name: str, unit_name: str,
                                for_evaluation: bool,
                                target_arch: Arch) -> (CommandType, List[str]):
        cmd = ["asy"]
        cmd += ["-f", "pdf", "-o", exe_name]
        cmd += source_filenames
        return CommandType.SYSTEM, cmd

    def get_dependencies(self, filename: str):
        return make_unique(find_asy_dependency(filename))


def register():
    LanguageManager.register_language(LanguageAsy())
