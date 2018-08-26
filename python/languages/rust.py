#!/usr/bin/env python3
from typing import List

from task_maker.args import Arch
from task_maker.languages import CompiledLanguage, CommandType, LanguageManager


class LanguageRust(CompiledLanguage):
    @property
    def name(self):
        return "Rust"

    @property
    def source_extensions(self):
        return [".rs"]

    def get_compilation_command(self, source_filenames: List[str],
                                exe_name: str, for_evaluation: bool,
                                target_arch: Arch) -> (CommandType, List[str]):
        cmd = ["rustc"]
        if for_evaluation:
            cmd += ["--cfg", "EVAL"]
        if target_arch != Arch.DEFAULT:
            raise NotImplementedError(
                "Cannot compile %s: "
                "targetting Rust executables is not supported yet"
                % source_filenames[0])
        cmd += ["-O", "-o", exe_name]
        # with rustc you only need to specify the main file
        cmd += [source_filenames[0]]
        return CommandType.SYSTEM, cmd


def register():
    LanguageManager.register_language(LanguageRust())
