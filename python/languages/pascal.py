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

    @property
    def need_unit_name(self):
        return True

    def get_compilation_command(self, source_filenames: List[str],
                                exe_name: str, unit_name: str,
                                for_evaluation: bool,
                                target_arch: Arch) -> (CommandType, List[str]):
        cmd = ["fpc"]
        if for_evaluation:
            cmd += ["-dEVAL"]
        if target_arch != Arch.DEFAULT:
            raise NotImplementedError(
                "Cannot compile %s: "
                "targetting Pascal executables is not supported yet" %
                source_filenames[0])
        cmd += ["-Fe/dev/stderr"]  # fpc emits errors on stdout by default
        cmd += ["-O2", "-XS", "-o" + exe_name]
        cmd += [unit_name + ".pas"] + source_filenames[1:]
        return CommandType.SYSTEM, cmd


def register():
    LanguageManager.register_language(LanguagePascal())
