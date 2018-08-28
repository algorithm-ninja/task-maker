#!/usr/bin/env python3
import os.path
import re
from typing import List

from task_maker.args import Arch
from task_maker.languages import CompiledLanguage, CommandType, \
    LanguageManager, Dependency, make_unique

CXX_INCLUDE = re.compile('#include *["<](.+)[">]')


def find_c_dependency(filename: str) -> List[Dependency]:
    scope = os.path.dirname(filename)
    with open(filename) as file:
        content = file.read()
    includes = CXX_INCLUDE.findall(content)
    dependencies = []  # type: List[Dependency]
    for include in includes:
        file_path = os.path.join(scope, include)
        if os.path.islink(file_path):
            file_path = os.path.realpath(file_path)
        # the sandbox does not support file inside subdirs (nor ../something),
        # for convenience skip all the files that includes "/" in the name
        if os.path.exists(file_path) and os.sep not in include:
            dependency = Dependency(include, file_path)
            dependencies += [dependency]
            dependencies += find_c_dependency(file_path)
    return dependencies


class LanguageC(CompiledLanguage):
    @property
    def name(self):
        return "C"

    @property
    def source_extensions(self):
        return [".c"]

    @property
    def header_extensions(self):
        return [".h"]

    def get_compilation_command(self, source_filenames: List[str],
                                exe_name: str, unit_name: str,
                                for_evaluation: bool,
                                target_arch: Arch) -> (CommandType, List[str]):
        cmd = ["cc"]
        if for_evaluation:
            cmd += ["-DEVAL"]
        if target_arch == Arch.I686:
            cmd += ["-m32"]
        cmd += ["-O2", "-std=c11", "-Wall", "-o", exe_name]
        cmd += source_filenames
        return CommandType.SYSTEM, cmd

    def get_dependencies(self, filename: str):
        return make_unique(find_c_dependency(filename))


def register():
    LanguageManager.register_language(LanguageC())
