#!/usr/bin/env python3
import os.path
import shutil
from distutils.spawn import find_executable
from task_maker.args import CacheMode
from task_maker.config import Config
from typing import Optional, Dict, List

from task_maker.dependency_finder import find_dependency
from task_maker.detect_exe import get_exeflags, EXEFLAG_NONE
from task_maker.formats import Arch, GraderInfo, Dependency
from task_maker.language import Language, from_file as language_from_file, need_compilation


class SourceFile:
    @staticmethod
    def from_file(
            path: str,
            write_to: Optional[str] = None,
            target_arch=Arch.DEFAULT,
            grader_map: Dict[Language, GraderInfo] = dict()) -> "SourceFile":
        old_path = path
        if not os.path.exists(path):
            path = find_executable(path)
        if not path:
            raise ValueError("Cannot find %s" % old_path)
        language = language_from_file(path)
        source_file = SourceFile(path, find_dependency(path), language, None,
                                 target_arch, grader_map.get(language))
        if write_to:
            if not os.path.isabs(write_to):
                write_to = os.path.join(os.getcwd(), write_to)
            source_file.write_bin_to = write_to
        if not need_compilation(source_file.language):
            if not is_executable(source_file.path):
                raise ValueError("The file %s is not an executable. "
                                 "Please check the shebang (#!)" % path)
        return source_file

    def __init__(self, path: str, dependencies: List[Dependency],
                 language: Language, write_bin_to: Optional[str],
                 target_arch: Arch, grader: Optional["GraderInfo"]):
        self.path = path
        self.dependencies = dependencies
        self.language = language
        self.write_bin_to = write_bin_to
        self.target_arch = target_arch
        self.grader = grader
        self.name = os.path.basename(path)
        self.exe_name = os.path.splitext(
            os.path.basename(write_bin_to or path))[0]
        self.need_compilation = need_compilation(self.language)
        self.prepared = False

    # prepare the source file for execution, compile the source if needed
    def prepare(self, frontend, config: Config):
        if self.prepared:
            return
        if self.need_compilation:
            self._compile(frontend, config)
        else:
            self._not_compile(frontend)
        self.prepared = True

    def _compile(self, frontend, config: Config):
        source = frontend.provideFile(self.path,
                                      "Source file for " + self.name, False)
        if self.language == Language.CPP:
            compiler = "c++"
            args = [
                "-O2", "-std=c++14", "-DEVAL", "-Wall", "-o", self.exe_name,
                self.name
            ]
            if self.grader:
                args += [f.name for f in self.grader.files]
            if self.target_arch == Arch.I686:
                args.append("-m32")
        elif self.language == Language.C:
            compiler = "cc"
            args = [
                "-O2", "-std=c11", "-DEVAL", "-Wall", "-o", self.exe_name,
                self.name
            ]
            if self.grader:
                args += [f.name for f in self.grader.files]
            if self.target_arch == Arch.I686:
                args.append("-m32")
        elif self.language == Language.PASCAL:
            compiler = "fpc"
            args = ["-O2", "-XS", "-dEVAL", "-o", self.exe_name, self.name]
            if self.grader:
                args += [f.name for f in self.grader.files]
            if self.target_arch != Arch.DEFAULT:
                raise NotImplementedError(
                    "Cannot compile %s: targetting Pascal executables is not supported yet"
                    % self.path)
        elif self.language == Language.RUST:
            compiler = "rustc"
            args = ["-O", "--cfg", "EVAL", "-o", self.exe_name, self.name]
            if self.target_arch != Arch.DEFAULT:
                raise NotImplementedError(
                    "Cannot compile %s: targetting Rust executables is not supported yet"
                    % self.path)
        # TODO add language plugin system
        else:
            raise NotImplementedError(
                "Cannot compile %s: unknown language" % self.path)

        self.compilation = frontend.addExecution(
            "Compilation of %s" % self.name)
        if config.cache == CacheMode.NOTHING:
            self.compilation.disableCache()
        self.compilation.setExecutablePath(compiler)
        self.compilation.setArgs(args)
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
        if self.write_bin_to:
            self.executable.getContentsToFile(self.write_bin_to, True, True)

    def _not_compile(self, frontend):
        self.executable = frontend.provideFile(
            self.path, "Source file for " + self.name, True)
        if self.write_bin_to:
            self.executable.getContentsToFile(self.write_bin_to, True, True)

    def execute(self, frontend, description: str, args: List[str]):
        execution = frontend.addExecution(description)
        execution.setExecutable(self.exe_name, self.executable)
        execution.setArgs(args)
        if not self.need_compilation:
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
