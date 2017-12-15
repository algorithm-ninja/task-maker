#!/usr/bin/env python3
import glob
import operator
import os.path
from enum import Enum
from functools import reduce
from typing import Dict  # pylint: disable=unused-import
from typing import List
from typing import Optional

from bindings import Execution
from bindings import FileID
from python.language import Language
from python.source_file import SourceFile  # pylint: disable=unused-import
from python.ui import UI


class ScoreMode(Enum):
    SUM = 0
    MIN = 1
    MUL = 2


class Input:
    def __init__(self,
                 generator: Optional[str] = None,
                 generator_deps: Optional[List[str]] = None,
                 args: Optional[List[str]] = None,
                 path: Optional[str] = None,
                 validator: Optional[str] = None,
                 validator_deps: Optional[List[str]] = None) -> None:
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
        if generator_deps is not None:
            self.generator_deps = generator_deps
        else:
            self.generator_deps = []
        if validator_deps is not None:
            self.validator_deps = validator_deps
        else:
            self.validator_deps = []


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
        if not testcases:
            raise ValueError("You need to specify at least one testcase")
        self.num = -1
        self.max_score = max_score
        self.score_mode = score_mode
        self.testcases = testcases
        self.task = None  # type: Optional[Task]
        for testcase in testcases:
            testcase.subtask = self

    def compute_score(self, testcase_scores: List[float]) -> float:
        if self.score_mode == ScoreMode.SUM:
            best_score = len(testcase_scores)
        else:
            best_score = 1
        if self.score_mode == ScoreMode.SUM:
            score = sum(testcase_scores)
        elif self.score_mode == ScoreMode.MIN:
            score = min(testcase_scores)
        elif self.score_mode == ScoreMode.MUL:
            score = reduce(operator.mul, testcase_scores, 1)
        return score / best_score * self.max_score


class Task:
    def __init__(self, ui: UI, time_limit: float, memory_limit: int) -> None:
        self._graders = dict()  # type: Dict[Language, List[str]]
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
        subtask.num = len(self.subtasks)
        self.subtasks.append(subtask)
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
        if lang not in self._graders:
            self._graders[lang] = []
        self._graders[lang].append(grader_src)

    def graders(self, language: Language) -> List[str]:
        if language not in self._graders:
            return []
        return self._graders[language]

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

    def store_results(self, task_dir: str) -> None:
        input_dir = os.path.join(task_dir, "input")
        output_dir = os.path.join(task_dir, "output")
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        for file in glob.glob(os.path.join(input_dir, "input*.txt")):
            os.remove(file)
        for file in glob.glob(os.path.join(output_dir, "output*.txt")):
            os.remove(file)
        for testcase in self.testcases:
            if testcase.input_id:
                testcase.input_id.write_to(
                    os.path.join(input_dir, "input%d.txt" % testcase.num),
                    False, False)
            if testcase.output_id:
                testcase.output_id.write_to(
                    os.path.join(output_dir, "output%d.txt" % testcase.num),
                    False, False)
        if self.checker_src:
            checker_dir = os.path.dirname(os.path.join(task_dir,
                                                       self.checker_src))
            checker_name = os.path.splitext(
                os.path.basename(self.checker_src))[0]
            checker_path = os.path.join(checker_dir, checker_name)
            if self.checker and self.checker.compilation_output:
                self.checker.compilation_output.write_to(checker_path,
                                                         True, True)
