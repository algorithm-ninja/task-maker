#!/usr/bin/env python3
import hashlib
import os.path
import shutil

from enum import Enum
from task_maker.language import Language, need_compilation
from typing import List, Dict, Optional


class ScoreMode(Enum):
    INVALID_SCORE_MODE = 0
    MIN = 1
    MAX = 2
    SUM = 3


class Arch(Enum):
    DEFAULT = 0
    X86_64 = 1
    I686 = 2


class Dependency:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path

    def __repr__(self):
        return "<Dependency name=%s path=%s>" % (self.name, self.path)


class SourceFile:
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
    def prepare(self, frontend):
        if self.prepared:
            return
        if self.need_compilation:
            self._compile(frontend)
        else:
            self._not_compile(frontend)
        self.prepared = True

    def _compile(self, frontend):
        source = frontend.provideFile(self.path, "Source file for " + self.name, False)
        if self.language == Language.CPP:
            compiler = "c++"
            args = [
                "-O2", "-std=c++14", "-DEVAL", "-Wall", "-o", self.exe_name,
                self.name
            ]
            if self.target_arch == Arch.I686:
                args.append("-m32")
        elif self.language == Language.C:
            compiler = "cc"
            args = [
                "-O2", "-std=c11", "-DEVAL", "-Wall", "-o", self.exe_name,
                self.name
            ]
            if self.target_arch == Arch.I686:
                args.append("-m32")
        elif self.language == Language.PASCAL:
            compiler = "fpc"
            args = ["-O2", "-XS", "-dEVAL", "-o", self.exe_name, self.name]
            if self.target_arch == Arch.DEFAULT:
                raise NotImplementedError(
                    "Cannot compile %s: targetting Pascal executables is not supported yet"
                    % self.path)
        elif self.language == Language.RUST:
            compiler = "rustc"
            args = ["-O", "--cfg", "EVAL", "-o", self.exe_name, self.name]
            if self.target_arch == Arch.DEFAULT:
                raise NotImplementedError(
                    "Cannot compile %s: targetting Rust executables is not supported yet"
                    % self.path)
        # TODO add language plugin system
        else:
            raise NotImplementedError(
                "Cannot compile %s: unknown language" % self.path)

        # TODO this should be done by the worker
        compiler = shutil.which(compiler)
        if not compiler:
            raise FileNotFoundError(
                "Cannot compile %s: missing compiler" % self.path)

        self.compilation = frontend.addExecution("Compilation of %s" % self.name)
        self.compilation.setExecutablePath(compiler)
        self.compilation.setArgs(args)
        self.compilation.addInput(self.name, source)
        for dep in self.dependencies:
            self.compilation.addInput(
                dep.name,
                frontend.provideFile(dep.path, dep.path, False))
        if self.grader:
            for dep in self.grader.files:
                self.compilation.addInput(
                    dep.name,
                    frontend.provideFile(dep.path, dep.path, False))
        self.compilation_stderr = self.compilation.stderr(False)
        self.executable = self.compilation.output(self.exe_name, True)
        # TODO set cache
        # TODO set time/memory limits?
        self.compilation.notifyStart(lambda: print("Compilation of %s" % self.name, "started"))
        self.compilation.getResult(lambda res: print(res))

    def _not_compile(self, frontend):
        self.executable = frontend.provideFile(self.path, "Source file for " + self.name, True)

    def execute(self, frontend, description: str,
                args: List[str]):
        execution = frontend.addExecution(description)
        execution.notifyStart(lambda: print(description, "started"))
        execution.setExecutable(self.exe_name, self.executable)
        execution.setArgs(args)
        if not self.need_compilation:
            for dep in self.dependencies:
                execution.addInput(
                    dep.name,
                    frontend.provideFile(dep.path, dep.path, False))
        return execution

    def __repr__(self):
        return "<SourceFile path=%s language=%s>" % (self.path, self.language)


class TestCase:
    def __init__(self, generator: Optional[SourceFile],
                 generator_args: List[str], extra_deps: List[Dependency],
                 validator: Optional[SourceFile], validator_args: List[str],
                 input_file: Optional[str], output_file: Optional[str],
                 write_input_to: Optional[str],
                 write_output_to: Optional[str]):
        self.generator = generator
        self.generator_args = generator_args
        self.extra_deps = extra_deps
        self.validator = validator
        self.validator_args = validator_args
        self.input_file = input_file
        self.output_file = output_file
        self.write_input_to = write_input_to
        self.write_output_to = write_output_to

    def __repr__(self):
        return "<TestCase generator=%s args=%s>" % (self.generator,
                                                    str(self.generator_args))


class Subtask:
    def __init__(self, score_mode: ScoreMode, max_score: float,
                 testcases: Dict[int, TestCase]):
        self.score_mode = score_mode
        self.max_score = max_score
        self.testcases = testcases

    def __repr__(self):
        return "<Subtask score_mode=%s max_score=%f>" % (self.score_mode.name,
                                                         self.max_score)


class GraderInfo:
    def __init__(self, for_language: Language, files: List[Dependency]):
        self.for_language = for_language
        self.files = files

    def __repr__(self):
        return "<GraderInfo language=%s>" % self.for_language.name


class Task:
    def __init__(self, name: str, title: str, subtasks: Dict[int, Subtask],
                 official_solution: Optional[SourceFile],
                 grader_info: List[GraderInfo], checker: Optional[SourceFile],
                 time_limit: float, memory_limit_kb: int, input_file: str,
                 output_file: str):
        self.name = name
        self.title = title
        self.subtasks = subtasks
        self.official_solution = official_solution
        self.grader_info = grader_info
        self.checker = checker
        self.time_limit = time_limit
        self.memory_limit_kb = memory_limit_kb
        self.input_file = input_file
        self.output_file = output_file

    def __repr__(self):
        return "<Task name=%s title=%s>" % (self.name, self.title)


class TerryTask:
    def __init__(self, name: str, title: str, max_score: float,
                 generator: SourceFile, validator: SourceFile,
                 checker: SourceFile, solution: SourceFile):
        self.name = name
        self.title = title
        self.max_score = max_score
        self.generator = generator
        self.validator = validator
        self.checker = checker
        self.solution = solution

    def __repr__(self):
        return "<TerryTask name=%s title=%s>" % (self.name, self.title)
