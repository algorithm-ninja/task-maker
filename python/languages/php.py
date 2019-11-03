from typing import List

from task_maker.languages import Language, LanguageManager, CommandType


class LanguagePHP(Language):
    @property
    def name(self):
        return "PHP"

    @property
    def source_extensions(self):
        return [".php"]

    def get_execution_command(self, exe_name: str, args: List[str],
                              main=None) -> (CommandType, List[str]):
        """
        Get the command to use to execute a file from this language
        :param exe_name: Name of the (maybe compiled) executable
        :param args: Argument to pass to the executable
        :param main: Name of the main file, useful for Java
        """
        return CommandType.LOCAL_FILE, ["php", exe_name] + args


def register():
    LanguageManager.register_language(LanguagePHP())
