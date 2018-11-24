#!/usr/bin/env python3

import glob
import importlib.util
import os.path
from abc import ABC, abstractmethod
from enum import Enum
from task_maker.args import Arch
from typing import List, Dict


class Dependency:
    """
    Describes a dependency of an executable. The `name` is the name to use
    inside the sandbox, the `path` is outside the sandbox.
    """
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path

    def __repr__(self):
        return "<Dependency name=%s path=%s>" % (self.name, self.path)


class GraderInfo:
    """
    Contains the information about a grader, the language it's for and a list
    of files required during the compilation/execution.
    """
    def __init__(self, for_language: "Language", files: List[Dependency]):
        self.for_language = for_language
        self.files = files

    def __repr__(self):
        return "<GraderInfo language=%s>" % self.for_language.name


class CommandType(Enum):
    """
    Type of command to execute in the sandbox for the specified language:
    * LOCAL_FILE: a file inside the sandbox (like a solution)
    * SYSTEM: a file present outside the sandbox (like a compiler)
    """
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
    def source_extension(self) -> str:
        """
        The main extension for this language (with the dot).
        """
        return self.source_extensions[0]

    @property
    def header_extensions(self) -> List[str]:
        """
        List of the extensions (with the dot) of the header files for this
        language.
        """
        return []

    @property
    def need_unit_name(self) -> bool:
        """
        Whether this language needs the source file to be called in a proper
        way. The basename without extension is passed to get_compilation_command
        """
        return False

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
                                exe_name: str, unit_name: str,
                                for_evaluation: bool,
                                target_arch: Arch) -> (CommandType, List[str]):
        """
        Get the command to use to compile some files from this language
        :param source_filenames: List of files to compile
        :param exe_name: Name of the executable to produce
        :param unit_name: Name of the source file that may be used to compile.
            It is used only the languages that requires a specific name of the
            source file. It's without the extension.
        :param for_evaluation: Whether to set the EVAL variable
        :param target_arch: Architecture to target the executable on
        """
        pass

    def get_dependencies(self, filename: str) -> List[Dependency]:
        """
        Read the file and recursively search for dependencies. If the language
        is compiled those files will be copied at the compilation phase, if the
        language is not compiled they will be copied at the execution phase.
        :param filename: Root file from which search the dependencies
        """
        return []

    def __repr__(self):
        return "<Language {}>".format(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


class CompiledLanguage(Language, ABC):
    """
    A language that needs an extra phase: compilation.
    """
    @property
    def need_compilation(self):
        return True


class LanguageManager:
    """
    Manage all the supported languages. LanguageManager.load_languages() should
    be called in order to support the languages.
    """
    # List of the known languages.
    LANGUAGES = []  # type: List[Language]
    # (extension with dot -> Language) association.
    EXT_CACHE = {}  # type: Dict[str, Language]

    @staticmethod
    def load_languages():
        """
        Iterates through the files in this package, load them and register the
        languages.
        """
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
        """
        Given a loaded language put it in the cache of known languages, building
        the cache of the known extensions.
        """
        LanguageManager.LANGUAGES.append(language)
        for ext in language.source_extensions:
            if ext in LanguageManager.EXT_CACHE:
                raise ValueError(
                    "Extension {} already registered for language {}".format(
                        ext, LanguageManager.EXT_CACHE[ext].name))
            LanguageManager.EXT_CACHE[ext] = language

    @staticmethod
    def from_file(path: str) -> Language:
        """
        Given the path to a file, returns the associated language. Raises an
        excepetion if the language is unknown.
        """
        name, ext = os.path.splitext(path)
        if ext not in LanguageManager.EXT_CACHE:
            raise ValueError("Unknown language for file {}".format(path))
        return LanguageManager.EXT_CACHE[ext]

    @staticmethod
    def valid_extensions() -> List[str]:
        """
        Returns a list of all the known extensions (with the dots).
        """
        return list(LanguageManager.EXT_CACHE.keys())


def make_unique(deps: List[Dependency]) -> List[Dependency]:
    """
    Remove all the duplicates from a list of dependencies.
    """
    return list(item[1] for item in {dep.name: dep for dep in deps}.items())
