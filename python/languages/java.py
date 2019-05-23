from typing import List

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

        main_class = "grader" if "grader.java" in source_filenames else unit_name
        commands = [
            f"javac {' '.join(source_filenames)}",
            f"echo Main-Class: {main_class} > MANIFEST.MF",
            f"jar cvmf MANIFEST.MF {exe_name} *.class",
        ]
        return CommandType.SYSTEM, ["sh", "-c", "&&".join(commands)]

    def get_execution_command(self, exe_name: str, args: List[str], main=None) -> (CommandType, List[str]):
        return CommandType.SYSTEM, ["java", "-jar", exe_name, *args]


def register():
    LanguageManager.register_language(LanguageJava())
