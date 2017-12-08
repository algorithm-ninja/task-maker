#!/usr/bin/env python3

from enum import Enum
from typing import Dict  # pylint: disable=unused-import
from typing import List
from typing import Optional

from bindings import Execution
from bindings import FileID
from python.source_file import SourceFile  # pylint: disable=unused-import
from python.language import Language
from python.ui import UI


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
        self.subtask = None  # type: Optional[Subtask]
        self.num = -1


class Subtask:
    def __init__(self, max_score: float, score_mode: ScoreMode,
                 testcases: List[Testcase]) -> None:
        self.num = -1
        self.max_score = max_score
        self.score_mode = score_mode
        self.testcases = testcases
        self.task = None  # type: Optional[Task]
        for testcase in testcases:
            testcase.subtask = self


class Task:
    def __init__(self, ui: UI, time_limit: float, memory_limit: int) -> None:
        self.graders = dict()  # type: Dict[Language, List[str]]
        self.solution_src = None  # type: Optional[str]
        self.solution = None  # type: Optional[SourceFile]
        self.checker_src = None  # type: Optional[str]
        self.checker = None  # type: Optional[SourceFile]
        self.testcases = []  # type: List[Testcase]
        self.subtasks = []  # type: List[Subtask]
        self.generated = False
        self.time_limit = time_limit
        self.memory_limit = memory_limit
        self.input_file = None  # type: Optional[str]
        self.output_file = None  # type: Optional[str]
        self._ui = ui
        ui.set_memory_limit(memory_limit)
        ui.set_time_limit(time_limit)

    def add_subtask(self, subtask: Subtask) -> None:
        self.subtasks.append(subtask)
        subtask.num = len(self.subtasks)
        subtask.task = self
        testcase_nums = []  # type: List[int]
        for testcase in subtask.testcases:
            testcase.num = len(self.testcases)
            self.testcases.append(testcase)
            testcase_nums.append(testcase.num)
        self._ui.set_subtask_info(subtask.num, subtask.max_score,
                                  testcase_nums)

    def add_solution(self, solution_src: str) -> None:
        self.solution_src = solution_src

    def add_checker(self, checker_src: str) -> None:
        self.checker_src = checker_src

    def add_grader(self, grader_src: str) -> None:
        lang = Language.from_file(grader_src)
        if lang not in self.graders:
            self.graders[lang] = []
        self.graders[lang].append(grader_src)

    def set_input_file(self, input_file: str) -> None:
        self.input_file = input_file

    def set_output_file(self, output_file: str) -> None:
        self.output_file = output_file

    def setup_io(self, execution: Execution, input_data: FileID) -> FileID:
        if self.input_file is None:
            execution.stdin(input_data)
        else:
            execution.input(self.input_file, input_data)
        if self.output_file is None:
            return execution.stdout()
        return execution.output(self.output_file)
