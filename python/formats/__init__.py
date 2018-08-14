#!/usr/bin/env python3
from enum import Enum
from typing import List, Dict, Optional


class Language(Enum):
    INVALID_LANGUAGE = 0
    CPP = 1
    C = 2
    PASCAL = 3
    PYTHON = 4
    BASH = 5
    RUBY = 6
    ERLANG = 7
    RUST = 8


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
    def __init__(self, path: str, dependencies: List[Dependency], language: Language, write_bin_to: Optional[str],
                 target_arch: Arch):
        self.path = path
        self.dependencies = dependencies
        self.language = language
        self.write_bin_to = write_bin_to
        self.target_arch = target_arch

    def __repr__(self):
        return "<SourceFile path=%s language=%s>" % (self.path, self.language)


class TestCase:
    def __init__(self, generator: Optional[SourceFile], generator_args: List[str], extra_deps: List[Dependency],
                 validator: Optional[SourceFile], validator_args: List[str], input_file: Optional[str],
                 output_file: Optional[str], write_input_to: Optional[str], write_output_to: Optional[str]):
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
        return "<TestCase generator=%s args=%s>" % (self.generator, str(self.generator_args))


class Subtask:
    def __init__(self, score_mode: ScoreMode, max_score: float, testcases: Dict[int, TestCase]):
        self.score_mode = score_mode
        self.max_score = max_score
        self.testcases = testcases

    def __repr__(self):
        return "<Subtask score_mode=%s max_score=%f>" % (self.score_mode.name, self.max_score)


class GraderInfo:
    def __init__(self, for_language: Language, files: List[Dependency]):
        self.for_language = for_language
        self.files = files

    def __repr__(self):
        return "<GraderInfo language=%s>" % self.for_language.name


class Task:
    def __init__(self, name: str, title: str, subtasks: Dict[int, Subtask], official_solution: Optional[SourceFile],
                 grader_info: List[GraderInfo], checker: Optional[SourceFile], time_limit: float, memory_limit_kb: int,
                 input_file: str, output_file: str):
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
    def __init__(self, name: str, title: str, max_score: float, generator: SourceFile, validator: SourceFile,
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
