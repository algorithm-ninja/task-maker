#!/usr/bin/env python3
import os.path
from distutils.spawn import find_executable
from typing import Optional, Dict, List

from task_maker.args import CacheMode, Arch
from task_maker.config import Config
from task_maker.detect_exe import get_exeflags, EXEFLAG_NONE
from task_maker.languages import LanguageManager, Language, CommandType, \
    GraderInfo, Dependency
from task_maker.task_maker_frontend import Frontend, File, ExecutionGroup, \
    Execution


def is_executable(path: str) -> bool:
    if get_exeflags(path) != EXEFLAG_NONE:
        return True
    with open(path, "rb") as source:
        if source.read(2) == b"#!":
            return True
    return False


class SourceFile:
    @staticmethod
    def from_file(path: str, unit_name: str, copy_executable: bool,
                  write_to: Optional[str], target_arch: Arch,
                  grader_map: Dict[Language, GraderInfo]) -> "SourceFile":
        """
        Handy constructor to build a SourceFile
        :param path: path to the source file
        :param unit_name: name of the unit of this source file. Usually the name
            of the task
        :param copy_executable: Whether to copy the executable into write_to
        :param write_to: Where to copy the executable, if copy_executable
        :param target_arch: Architecture to target the build
        :param grader_map: Map with the graders for all the languages
        """
        if copy_executable and not write_to:
            raise ValueError(
                "Asked to copy the executable but not specified where")
        old_path = path
        if not os.path.exists(path):
            path = find_executable(path)
        if not path:
            raise ValueError("Cannot find %s" % old_path)

        language = LanguageManager.from_file(path)
        dependencies = language.get_dependencies(path)
        grader = grader_map.get(language)
        if write_to:
            exe_name = os.path.basename(write_to)
        else:
            exe_name = os.path.splitext(os.path.basename(path))[0]
        source_file = SourceFile(path, unit_name, exe_name, dependencies,
                                 language, copy_executable and write_to,
                                 target_arch, grader)
        if not language.need_compilation:
            if not is_executable(source_file.path):
                raise ValueError("The file %s is not an executable. "
                                 "Please check the shebang (#!)" % path)
        return source_file

    def __init__(self, path: str, unit_name: str, exe_name: str,
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
        self.exe_name = exe_name
        self.prepared = False
        # set only after `prepare`
        self.executable = None  # type: Optional[File]
        self.compilation_stderr = None  # type: Optional[File]
        self.compilation_stdout = None  # type: Optional[File]

    def prepare(self, frontend: Frontend, config: Config):
        """
        Prepare the source file for execution, compile the source if needed.
        After this call self.executable will be available. If the source file
        is to compile then compilation_stderr and compilation_stdout will be
        available too
        """
        if self.prepared:
            return
        if self.language.need_compilation:
            self._compile(frontend, config)
        else:
            self._not_compile(frontend, config)
        if self.write_bin_to and not config.dry_run:
            self.executable.getContentsToFile(self.write_bin_to, True, True)
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
            source_name = self.unit_name + self.language.source_extensions[0]
        else:
            source_name = self.name
        self.compilation.addInput(source_name, source)

        for dep in self.dependencies:
            self.compilation.addInput(
                dep.name, frontend.provideFile(dep.path, dep.path, False))
        if self.grader:
            for dep in self.grader.files:
                self.compilation.addInput(
                    dep.name, frontend.provideFile(dep.path, dep.path, False))
        self.executable = self.compilation.output(self.exe_name, True)
        self.compilation_stderr = self.compilation.stderr(False)
        self.compilation_stdout = self.compilation.stdout(False)

    def _not_compile(self, frontend, config: Config):
        self.executable = frontend.provideFile(
            self.path, "Source file for " + self.name, True)

    def execute(self,
                frontend,
                description: str,
                args: List[str],
                group: ExecutionGroup = None) -> Execution:
        """
        Prepare an execution for this source file. The .prepare() method must be
        called first. This method returns an Execution with the group, the
            executable, the args and the dependencies already set.
        :param frontend: The frontend
        :param description: The description for the execution
        :param args: The command line arguments to pass to the executable
        :param group: An optional execution group
        """
        if not self.prepared:
            raise ValueError("The source file needs to be prepared first")
        if group:
            execution = group.addExecution(description)
        else:
            execution = frontend.addExecution(description)
        cmd_type, cmd = self.language.get_execution_command(
            self.exe_name, args, self.unit_name)
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
