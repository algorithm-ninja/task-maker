#!/usr/bin/env python3

from enum import Enum
from typing import Dict  # pylint: disable=unused-import
from typing import List
from typing import Optional

from bindings import FileID  # pylint: disable=unused-import
from python.source_file import SourceFile  # pylint: disable=unused-import
from python.language import Language


class ScoreMode(Enum):
    SUM = 0
    MIN = 1
    MUL = 2


class Input:
    def __init__(self,
                 generator: Optional[str] = None,
                 args: Optional[List[str]] = None,
                 path: Optional[str] = None,
                 validator: Optional[str] = None) -> None:
        if (generator is None) == (path is None):
            raise ValueError(
                "You need to specify exactly a generator or a path")
        if (generator is None) != (args is None):
            raise ValueError(
                "Args should be specified together with a generator")
        if (path is None) and (validator is None):
            raise ValueError("You should validate generated inputs")
        self.should_generate = generator is not None
        self.generator = generator
        self.args = args
        self.path = path
        self.validator = validator


class Testcase:
    def __init__(self, input_file: Input,
                 output: Optional[str] = None) -> None:
        # If the output is None, it will be generated with the official
        # solution. Otherwise it must be the path to the correct output
        # file.
        if not isinstance(input_file, Input):
            raise ValueError("The input file should be an instance of Input")
        if output is not None and not isinstance(output, str):
            raise ValueError(
                "The output should be either none or a path to a file")
        if input_file.path is None and output is not None:
            raise ValueError(
                "You should not provide an output for generated inputs")
        self.input = input_file
        self.output = output
        self.input_id = None  # type: Optional[FileID]
        self.output_id = None  # type: Optional[FileID]


class Subtask:
    def __init__(self, num: int, score: int, score_mode: ScoreMode,
                 tc_begin: int, tc_end: int) -> None:
        self.num = num
        self.score = score
        self.score_mode = score_mode
        if tc_begin >= tc_end or tc_begin < 0:
            raise ValueError("Invalid testcase range given")
        self.tc_range = (tc_begin, tc_end)


class Task:
    def __init__(self) -> None:
        self.graders = dict()  # type: Dict[Language, List[str]]
        self.solution_src = None  # type: Optional[str]
        self.checker_src = None  # type: Optional[str]
        self.checker = None  # type: Optional[SourceFile]
        self.compiled_checker = None  # type: Optional[FileID]
        self.testcases = []  # type: List[Testcase]
        self.subtasks = []  # type: List[Subtask]
        self.generated = False

    def add_testcase(self, testcase: Testcase) -> None:
        self.testcases.append(testcase)

    def add_subtask(self, subtask: Subtask) -> None:
        if subtask.tc_range[1] >= len(self.testcases):
            raise ValueError("Subtask with unknown testcase given")
        self.subtasks.append(subtask)

    def add_solution(self, solution_src: str) -> None:
        self.solution_src = solution_src

    def add_checker(self, checker_src: str) -> None:
        self.checker_src = checker_src

    def add_grader(self, grader_src: str) -> None:
        lang = Language.from_file(grader_src)
        if lang not in self.graders:
            self.graders[lang] = []
        self.graders[lang].append(grader_src)

    def was_generated(self) -> bool:
        return self.generated
