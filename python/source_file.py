#!/usr/bin/env python3
import os.path
from distutils.spawn import find_executable
from task_maker.args import CacheMode, Arch
from task_maker.config import Config
from typing import Optional, Dict, List

from task_maker.detect_exe import get_exeflags, EXEFLAG_NONE
from task_maker.languages import LanguageManager, Language, CommandType, \
    GraderInfo, Dependency


class SourceFile:
    @staticmethod
    def from_file(
            path: str,
            unit_name: str,
            write_to: Optional[str] = None,
            target_arch=Arch.DEFAULT,
            grader_map: Dict[Language, GraderInfo] = dict()) -> "SourceFile":
        old_path = path
        if not os.path.exists(path):
            path = find_executable(path)
        if not path:
            raise ValueError("Cannot find %s" % old_path)
        language = LanguageManager.from_file(path)
        source_file = SourceFile(path, unit_name,
                                 language.get_dependencies(path), language,
                                 None, target_arch, grader_map.get(language))
        if write_to:
            if not os.path.isabs(write_to):
                write_to = os.path.join(os.getcwd(), write_to)
            source_file.write_bin_to = write_to
        if not language.need_compilation:
            if not is_executable(source_file.path):
                raise ValueError("The file %s is not an executable. "
                                 "Please check the shebang (#!)" % path)
        return source_file

    def __init__(self, path: str, unit_name: str,
                 dependencies: List[Dependency], language: Language,
                 write_bin_to: Optional[str], target_arch: Arch,
                 grader: Optional["GraderInfo"]):
        self.path = path
        self.unit_name = unit_name
        self.dependencies = dependencies
        self.language = language
        self.write_bin_to = write_bin_to
        self.target_arch = target_arch
        self.grader = grader
        self.name = os.path.basename(path)
        self.exe_name = os.path.splitext(
            os.path.basename(write_bin_to or path))[0]
        self.prepared = False

    # prepare the source file for execution, compile the source if needed
    def prepare(self, frontend, config: Config):
        if self.prepared:
            return
        if self.language.need_compilation:
            self._compile(frontend, config)
        else:
            self._not_compile(frontend, config)
        self.prepared = True

    def _compile(self, frontend, config: Config):
        source = frontend.provideFile(self.path,
                                      "Source file for " + self.name, False)
        compilation_files = [self.name]
        if self.grader:
            compilation_files += [d.name for d in self.grader.files]
        cmd_type, cmd = self.language.get_compilation_command(
            compilation_files, self.exe_name, self.unit_name, True,
            self.target_arch)

        if cmd_type != CommandType.SYSTEM:
            raise ValueError("Local file compilers are not supported yet")
        if not cmd:
            raise ValueError("Unexpected empty compiler command")

        self.compilation = frontend.addExecution(
            "Compilation of %s" % self.name)
        if config.cache == CacheMode.NOTHING:
            self.compilation.disableCache()
        self.compilation.setExecutablePath(cmd[0])
        self.compilation.setArgs(cmd[1:])
        if self.language.need_unit_name:
            self.compilation.addInput(
                self.unit_name + self.language.source_extensions[0], source)
        else:
            self.compilation.addInput(self.name, source)
        for dep in self.dependencies:
            self.compilation.addInput(
                dep.name, frontend.provideFile(dep.path, dep.path, False))
        if self.grader:
            for dep in self.grader.files:
                self.compilation.addInput(
                    dep.name, frontend.provideFile(dep.path, dep.path, False))
        self.compilation_stderr = self.compilation.stderr(False)
        self.executable = self.compilation.output(self.exe_name, True)
        if self.write_bin_to and not config.dry_run:
            self.executable.getContentsToFile(self.write_bin_to, True, True)

    def _not_compile(self, frontend, config: Config):
        self.executable = frontend.provideFile(
            self.path, "Source file for " + self.name, True)
        if self.write_bin_to and not config.dry_run:
            self.executable.getContentsToFile(self.write_bin_to, True, True)

    def execute(self, frontend, description: str, args: List[str], group=None):
        if group:
            execution = group.addExecution(description)
        else:
            execution = frontend.addExecution(description)
        cmd_type, cmd = self.language.get_execution_command(
            self.exe_name, args, self.name)
        execution.setArgs(cmd[1:])
        # if the command type is local_file then the executable compiled/copied
        # otherwise an external command is used to run the program, so it needs
        # to be copied in the sandbox
        if cmd_type == CommandType.LOCAL_FILE:
            execution.setExecutable(cmd[0], self.executable)
        else:
            execution.setExecutablePath(cmd[0])
            execution.addInput(self.exe_name, self.executable)
        if not self.language.need_compilation:
            for dep in self.dependencies:
                execution.addInput(
                    dep.name, frontend.provideFile(dep.path, dep.path, False))
        return execution

    def __repr__(self):
        return "<SourceFile path=%s language=%s>" % (self.path, self.language)


def is_executable(path: str) -> bool:
    if get_exeflags(path) != EXEFLAG_NONE:
        return True
    with open(path, "rb") as source:
        if source.read(2) == b"#!":
            return True
    return False
