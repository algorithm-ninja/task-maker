#!/usr/bin/env python3

import datetime
import os
#import curses

from typing import cast
from typing import Dict  # pylint: disable=unused-import
from typing import List
from typing import Optional
from python.ui import CompilationStatus
from python.ui import EvaluationResult
from python.ui import EvaluationStatus
from python.ui import GenerationStatus
from python.ui import UI


class SolutionStatus:
    def __init__(self) -> None:
        self.testcase_errors = dict()  # type: Dict[int, str]
        self.testcase_result = dict()  # type: Dict[int, EvaluationResult]
        self.testcase_status = dict()  # type: Dict[int, EvaluationStatus]
        self.subtask_scores = dict()  # type: Dict[int, float]
        self.score = None  # type: Optional[float]
        self.compiled = False


class CursesUI(UI):
    def __init__(self, task_name: str) -> None:
        super().__init__(task_name)
        self._num_testcases = 0
        self._subtask_max_scores = dict()  # type: Dict[int, float]
        self._subtask_testcases = dict()  # type: Dict[int, List[int]]
        self._solutions = []  # type: List[str]
        self._other_compilations = []  # type: List[str]
        self._compilation_status = dict()  # type: Dict[str, CompilationStatus]
        self._compilation_errors = dict()  # type: Dict[str, str]
        self._generation_status = dict()  # type: Dict[int, GenerationStatus]
        self._generation_errors = dict()  # type: Dict[int, str]
        self._time_limit = 0.0
        self._memory_limit = 0.0
        self._solution_status = dict()  # type: Dict[str, SolutionStatus]
        self._last_refresh = datetime.datetime.now()

    def _refresh(self, force: bool = False) -> None:
        if not force and self._last_refresh + datetime.timedelta(
                0, 0, 0, 50) > datetime.datetime.now():
            return
        os.system("clear")
        self._last_refresh = datetime.datetime.now()
        print("Time limit:", self._time_limit)
        print("Memory limit:", self._memory_limit / 1024)
        for comp in self._other_compilations:
            print("%30s: %s" % (comp, self._compilation_status[comp]))

        print()
        for comp in self._solutions:
            print("%30s: %s" % (comp, self._compilation_status[comp]))
        print()

        print("Generation status: % 2d/%d" % (len(
            list(
                filter(lambda x: x == GenerationStatus.SUCCESS,
                       self._generation_status.values()))),
                                              self._num_testcases))
        print()

        for sol in self._solutions:
            print("%30s: % 3d/%d  %s" % (
                sol, len(self._solution_status[sol].testcase_result),
                self._num_testcases,
                "score: % 4.f " % cast(float, self._solution_status[sol].score)
                if self._solution_status[sol].score is not None else ""))

    def set_time_limit(self, time_limit: float) -> None:
        self._time_limit = time_limit
        self._refresh()

    def set_memory_limit(self, memory_limit: int) -> None:
        self._memory_limit = memory_limit
        self._refresh()

    def set_subtask_info(self, subtask_num: int, max_score: float,
                         testcases: List[int]) -> None:
        self._subtask_testcases[subtask_num] = testcases
        self._subtask_max_scores[subtask_num] = max_score
        self._num_testcases = max(self._num_testcases, max(testcases) + 1)
        self._refresh()

    def set_compilation_status(self,
                               file_name: str,
                               is_solution: bool,
                               status: CompilationStatus,
                               warnings: Optional[str] = None) -> None:
        if is_solution:
            if file_name not in self._solutions:
                self._solutions.append(file_name)
            if file_name not in self._solution_status:
                self._solution_status[file_name] = SolutionStatus()
        else:
            if file_name not in self._other_compilations:
                self._other_compilations.append(file_name)
        self._compilation_status[file_name] = status
        if warnings:
            self._compilation_errors[file_name] = warnings
        self._refresh()

    def set_generation_status(self,
                              testcase_num: int,
                              status: GenerationStatus,
                              stderr: Optional[str] = None) -> None:
        self._generation_status[testcase_num] = status
        if stderr:
            self._generation_errors[testcase_num] = stderr
        self._refresh()

    def set_evaluation_status(self,
                              testcase_num: int,
                              solution_name: str,
                              status: EvaluationStatus,
                              result: Optional[EvaluationResult] = None,
                              error: Optional[str] = None) -> None:
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            self._solution_status[solution_name] = SolutionStatus()
        sol_status = self._solution_status[solution_name]
        sol_status.testcase_status[testcase_num] = status
        if error:
            sol_status.testcase_errors[testcase_num] = error
        if result:
            sol_status.testcase_result[testcase_num] = result
        self._refresh()

    def set_subtask_score(self, subtask_num: int, solution_name: str,
                          score: float) -> None:
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            raise RuntimeError("Something weird happened")
        self._solution_status[solution_name].subtask_scores[
            subtask_num] = score
        self._refresh()

    def set_task_score(self, solution_name: str, score: float) -> None:
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            raise RuntimeError("Something weird happened")
        self._solution_status[solution_name].score = score
        self._refresh()

    def print_final_status(self) -> None:
        self._refresh(force=True)

    def fatal_error(self, msg: str) -> None:
        pass
