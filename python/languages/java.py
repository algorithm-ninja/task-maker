from typing import List
import os

from task_maker.args import Arch
from task_maker.languages import CompiledLanguage, CommandType, LanguageManager


class LanguageJava(CompiledLanguage):
    @property
    def name(self):
        return "Java"

    @property
    def source_extensions(self):
        return [".java"]

    def get_compilation_command(self, source_filenames: List[str],
                                exe_name: str, unit_name: str,
                                for_evaluation: bool,
                                target_arch: Arch) -> (CommandType, List[str]):
        GRAAL_PATH = os.getenv("TM_GRAAL_PATH") or "/usr/lib/jvm/java-8-graal/bin/"
        main_class = "grader" if "grader.java" in source_filenames else unit_name
        commands = [
            f"{GRAAL_PATH}javac {' '.join(source_filenames)}",
            f"{GRAAL_PATH}native-image {main_class} {exe_name}",
        ]
        return CommandType.SYSTEM, ["sh", "-c", "&&".join(commands)]


def register():
    LanguageManager.register_language(LanguageJava())
