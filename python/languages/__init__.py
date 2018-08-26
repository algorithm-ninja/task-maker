#!/usr/bin/env python3

import glob
import importlib.util
import os.path
from abc import ABC, abstractmethod
from enum import Enum
from task_maker.args import Arch
from typing import List, Dict


class Dependency:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path

    def __repr__(self):
        return "<Dependency name=%s path=%s>" % (self.name, self.path)


class GraderInfo:
    def __init__(self, for_language: "Language", files: List[Dependency]):
        self.for_language = for_language
        self.files = files

    def __repr__(self):
        return "<GraderInfo language=%s>" % self.for_language.name


class CommandType(Enum):
    LOCAL_FILE = 0
    SYSTEM = 1


class Language(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique name of this language
        """
        pass

    @property
    def need_compilation(self) -> bool:
        """
        Whether this language needs to be compiled. If set to False
        get_compilation_command will never be executed
        :return:
        """
        return False

    @property
    @abstractmethod
    def source_extensions(self) -> List[str]:
        """
        List of extensions (with the dot) of the source files for this language.
        The first one is to be considered the principal. The set of extension
        of this language must not intersect the one from any other language.
        """
        pass

    @property
    def header_extensions(self) -> List[str]:
        """
        List of the extensions (with the dot) of the header files for this
        language.
        """
        return []

    def get_execution_command(self, exe_name: str, args: List[str],
                              main=None) -> (CommandType, List[str]):
        """
        Get the command to use to execute a file from this language
        :param exe_name: Name of the (maybe compiled) executable
        :param args: Argument to pass to the executable
        :param main: Name of the main file, useful for Java
        """
        return CommandType.LOCAL_FILE, [exe_name] + args

    def get_compilation_command(self, source_filenames: List[str],
                                exe_name: str, for_evaluation: bool,
                                target_arch: Arch) -> (CommandType, List[str]):
        """
        Get the command to use to compile some files from this language
        :param source_filenames: List of files to compile
        :param exe_name: Name of the executable to produce
        :param for_evaluation: Whether to set the EVAL variable
        :param target_arch: Architecture to target the executable on
        """
        pass

    def get_dependencies(self, filename: str) -> List[Dependency]:
        """
        Read the file and recursively search for dependencies
        :param filename: Root file from which search the dependencies
        """
        return []

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


class CompiledLanguage(Language, ABC):
    @property
    def need_compilation(self):
        return True


class LanguageManager:
    LANGUAGES = []  # type: List[Language]
    EXT_CACHE = {}  # type: Dict[str, Language]

    @staticmethod
    def load_languages():
        languages = glob.glob(os.path.dirname(__file__) + "/*.py")
        for language in languages:
            if language.endswith("__init__.py"):
                continue
            lang_name = language.split("/")[-1][:-3]
            spec = importlib.util.spec_from_file_location(
                "task_maker.languages." + lang_name, language)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not hasattr(module, "register"):
                raise ValueError(
                    "Plugin for language {} does not have register hook".
                    format(lang_name))
            module.register()

    @staticmethod
    def register_language(language: Language):
        LanguageManager.LANGUAGES.append(language)
        for ext in language.source_extensions:
            if ext in LanguageManager.EXT_CACHE:
                raise ValueError(
                    "Extension {} already registered for language {}".format(
                        ext, LanguageManager.EXT_CACHE[ext].name))
            LanguageManager.EXT_CACHE[ext] = language

    @staticmethod
    def from_file(path: str) -> Language:
        name, ext = os.path.splitext(path)
        if ext not in LanguageManager.EXT_CACHE:
            raise ValueError("Unknown language for file {}".format(path))
        return LanguageManager.EXT_CACHE[ext]

    @staticmethod
    def valid_extensions() -> List[str]:
        return list(LanguageManager.EXT_CACHE.keys())


def make_unique(deps: List[Dependency]) -> List[Dependency]:
    return list(item[1] for item in {dep.name: dep for dep in deps}.items())
