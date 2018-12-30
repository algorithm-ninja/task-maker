#!/usr/bin/env python3
import os.path
from distutils.spawn import find_executable
from task_maker.args import Arch
from task_maker.detect_exe import get_exeflags, EXEFLAG_NONE
from task_maker.languages import LanguageManager, Language, CommandType, \
    GraderInfo, Dependency
from task_maker.remote import ExecutionPool, Execution
from task_maker.task_maker_frontend import File
from typing import Optional, Dict, List


def is_executable(path: str) -> bool:
    """
    Check if the file is an executable or a script with a shebang.
    """
    if get_exeflags(path) != EXEFLAG_NONE:
        return True
    with open(path, "rb") as source:
        if source.read(2) == b"#!":
            return True
    return False


class SourceFile:
    """
    A SourceFile contains a ref to a source file, this class will manage it's
    compilation and execution.
    """

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
        exe_name = language.exe_name(path, write_to)
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
        self.pool = None  # type: ExecutionPool
        # set only after `prepare`
        self.executable = None  # type: Optional[File]
        self.compilation = None  # type: Optional[Execution]
        self.compilation_stderr = None  # type: Optional[File]
        self.compilation_stdout = None  # type: Optional[File]

    @property
    def prepared(self) -> bool:
        return self.pool is not None

    def prepare(self, pool: ExecutionPool):
        """
        Prepare the source file for execution, compile the source if needed.
        After this call self.executable will be available. If the source file
        is to compile then compilation_stderr and compilation_stdout will be
        available too
        """
        if self.prepared:
            return
        self.pool = pool
        if self.language.need_compilation:
            self._compile()
        else:
            self._not_compile()
        if self.write_bin_to and not self.pool.config.dry_run:
            self.executable.getContentsToFile(self.write_bin_to, True, True)

    def _compile(self):
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

        if self.language.need_unit_name:
            source_name = self.unit_name + self.language.source_extensions[0]
        else:
            source_name = self.name
        inputs = {
            source_name:
                self.pool.frontend.provideFile(
                    self.path, "Source file for " + self.name, False)
        }
        for dep in self.dependencies:
            inputs[dep.name] = self.pool.frontend.provideFile(
                dep.path, dep.path, False)
        if self.grader:
            for dep in self.grader.files:
                inputs[dep.name] = self.pool.frontend.provideFile(
                    dep.path, dep.path, False)
        self.compilation = Execution(
            "Compilation of %s" % self.name,
            self.pool,
            cmd[0],
            cmd[1:],
            "compilation", {
                "file": self.name,
                "path": self.path
            },
            inputs=inputs,
            outputs=[(self.exe_name, True)],
            store_stderr=True,
            store_stdout=True)
        self.executable = self.compilation.output(self.exe_name)

    def _not_compile(self):
        self.executable = self.pool.frontend.provideFile(
            self.path, "Source file for " + self.name, True)

    def __repr__(self):
        return "<SourceFile path=%s language=%s>" % (self.path, self.language)
