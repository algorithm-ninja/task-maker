#!/usr/bin/env python3
from typing import List

from task_maker.args import Arch
from task_maker.languages import CompiledLanguage, CommandType, \
    LanguageManager, make_unique
from task_maker.languages.c import find_c_dependency


class LanguageCPP(CompiledLanguage):
    @property
    def name(self):
        return "C++"

    @property
    def source_extensions(self):
        return [".cpp", ".cc", ".cxx", ".c++", ".C"]

    @property
    def header_extensions(self):
        return [".hpp"]

    def get_compilation_command(self, source_filenames: List[str],
                                exe_name: str, for_evaluation: bool,
                                target_arch: Arch) -> (CommandType, List[str]):
        cmd = ["c++"]
        if for_evaluation:
            cmd += ["-DEVAL"]
        if target_arch == Arch.I686:
            cmd += ["-m32"]
        cmd += ["-O2", "-std=c++14", "-Wall", "-o", exe_name]
        cmd += source_filenames
        return CommandType.SYSTEM, cmd

    def get_dependencies(self, filename: str):
        return make_unique(find_c_dependency(filename))


def register():
    LanguageManager.register_language(LanguageCPP())
