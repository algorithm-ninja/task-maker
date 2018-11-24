#!/usr/bin/env python3
import os.path
import re
import subprocess
from typing import List
from distutils.spawn import find_executable

from task_maker.args import Arch
from task_maker.languages import CompiledLanguage, CommandType, \
    LanguageManager, Dependency, make_unique

CXX_INCLUDE = re.compile('#include *["<](.+)[">]')


def old_find_c_dependency(filename: str, strip=None) -> List[Dependency]:
    """
    Legacy method to find all the non-system dependencies of a C/C++ source
    file. Will be used if no compiler (cc command) is found on this system.
    Will return the list of all the headers required for the compilation.
    """
    scope = os.path.dirname(filename)
    if strip is None:
        strip = scope + "/"
    with open(filename) as file:
        content = file.read()
    includes = CXX_INCLUDE.findall(content)
    dependencies = []  # type: List[Dependency]
    for include in includes:
        file_path = os.path.join(scope, include)
        if file_path.startswith(strip):
            include = file_path[len(strip):]
        if os.path.islink(file_path):
            file_path = os.path.realpath(file_path)
        if os.path.exists(file_path):
            dependency = Dependency(include, file_path)
            dependencies += [dependency]
            dependencies += old_find_c_dependency(file_path, strip)
    return dependencies


def new_find_c_dependency(filename: str) -> List[Dependency]:
    """
    New method for finding the headers required for the compilation. It uses the
    cc command (default C compiler) for fetching the list of dependencies (it
    uses the -MM flag).
    """
    proc = subprocess.run(["cc", "-MM", filename], stdout=subprocess.PIPE)
    if proc.returncode != 0:
        return []
    # the output of this command is something like:
    #
    #   filename.o: \
    #    /abs/path/to/file1.h \
    #    /abs/path/to/file2.h \
    #
    strip = os.path.dirname(filename) + "/"
    data = proc.stdout.decode().split()
    if len(data) < 2:
        return []
    # skip the output object and the current source
    data = data[2:]
    result = []  # type: List[Dependency]
    for dep in data:
        # skip the "new lines"
        if dep == "\\":
            continue
        name = dep
        if name.startswith(strip):
            name = name[len(strip):]
        result.append(Dependency(name, dep))
    return result


def find_c_dependency(filename: str) -> List[Dependency]:
    """
    Chooses which method to use for getting the list of all the compile time
    dependencies.
    """
    if find_executable("cc") is not None:
        return new_find_c_dependency(filename)
    else:
        return old_find_c_dependency(filename)


class LanguageC(CompiledLanguage):
    @property
    def name(self):
        return "C"

    @property
    def source_extensions(self):
        return [".c"]

    @property
    def header_extensions(self):
        return [".h"]

    def get_compilation_command(self, source_filenames: List[str],
                                exe_name: str, unit_name: str,
                                for_evaluation: bool,
                                target_arch: Arch) -> (CommandType, List[str]):
        cmd = ["cc"]
        if for_evaluation:
            cmd += ["-DEVAL"]
        if target_arch == Arch.I686:
            cmd += ["-m32"]
        cmd += ["-O2", "-std=c11", "-Wall", "-o", exe_name]
        cmd += source_filenames
        return CommandType.SYSTEM, cmd

    def get_dependencies(self, filename: str):
        return make_unique(find_c_dependency(filename))


def register():
    LanguageManager.register_language(LanguageC())
