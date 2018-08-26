#!/usr/bin/env python3
from typing import List

from task_maker.args import Arch
from task_maker.languages import CompiledLanguage, CommandType, LanguageManager


class LanguagePascal(CompiledLanguage):
    @property
    def name(self):
        return "Pascal"

    @property
    def source_extensions(self):
        return [".pas"]

    def get_compilation_command(self, source_filenames: List[str],
                                exe_name: str, for_evaluation: bool,
                                target_arch: Arch) -> (CommandType, List[str]):
        cmd = ["fpc"]
        if for_evaluation:
            cmd += ["-dEVAL"]
        if target_arch != Arch.DEFAULT:
            raise NotImplementedError(
                "Cannot compile %s: "
                "targetting Pascal executables is not supported yet"
                % source_filenames[0])
        cmd += ["-O2", "-XS", "-o", exe_name]
        cmd += source_filenames
        return CommandType.SYSTEM, cmd

def register():
    LanguageManager.register_language(LanguagePascal())
