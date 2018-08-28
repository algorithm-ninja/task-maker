#!/usr/bin/env python3

from task_maker.languages import Language, LanguageManager


class LanguageShell(Language):
    @property
    def name(self):
        return "Shell"

    @property
    def source_extensions(self):
        return [".sh"]


def register():
    LanguageManager.register_language(LanguageShell())
