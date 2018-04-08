#!/usr/bin/env python3
from typing import Dict, Set, Tuple
from typing import List, Optional

import os.path
from proto.event_pb2 import EvaluationResult, TerryEvaluationResult, \
    EventStatus, RunningTaskInfo

from python.ui import UI


class SolutionStatus:
    def __init__(self) -> None:
        self.testcase_errors = dict()  # type: Dict[int, str]
        self.testcase_result = dict()  # type: Dict[int, EvaluationResult]
        self.testcase_status = dict()  # type: Dict[int, EventStatus]
        self.subtask_scores = dict()  # type: Dict[int, float]
        self.score = None  # type: Optional[float]
        self.compiled = False


class TerryStatus:
    def __init__(self) -> None:
        self.status = None  # type: EventStatus
        self.errors = None  # type: Optional[str]
        self.result = None  # type: Optional[TerryEvaluationResult]


class SilentUI(UI):
    def __init__(self, solutions: List[str], format: str) -> None:
        super().__init__(solutions, format)
        self._num_testcases = 0
        self._subtask_max_scores = dict()  # type: Dict[int, float]
        self._subtask_testcases = dict()  # type: Dict[int, List[int]]
        self._other_compilations = []  # type: List[str]
        self._compilation_status = dict()  # type: Dict[str, EventStatus]
        self._compilation_errors = dict()  # type: Dict[str, str]
        self._generation_status = dict()  # type: Dict[int, EventStatus]
        self._generation_errors = dict()  # type: Dict[int, str]
        self._terry_test_status = dict()  # type: Dict[str, TerryStatus]
        self._compilation_cache = set()  # type: Set[str]
        self._generation_cache = set()  # type: Set[int]
        self._evaluation_cache = set()  # type: Set[Tuple[str, int]]
        self._terry_generation_cache = set()  # type: Set[str]
        self._terry_evaluation_cache = set()  # type: Set[str]
        self._terry_check_cache = set()  # type: Set[str]
        self._time_limit = 0.0
        self._memory_limit = 0.0
        self._solution_status = dict()  # type: Dict[str, SolutionStatus]
        self._running_tasks = list()  # type: List[RunningTaskInfo]

    def set_time_limit(self, time_limit: float) -> None:
        self._time_limit = time_limit

    def set_memory_limit(self, memory_limit: int) -> None:
        self._memory_limit = memory_limit

    def set_subtask_info(self, subtask_num: int, max_score: float,
                         testcases: List[int]) -> None:
        self._subtask_testcases[subtask_num] = testcases
        self._subtask_max_scores[subtask_num] = max_score
        self._num_testcases = max(self._num_testcases, max(testcases) + 1)

    def set_compilation_status(self, file_name: str, status: EventStatus,
                               warnings: Optional[str] = None,
                               from_cache: bool = False):
        is_solution = file_name in self.solutions
        if is_solution:
            if file_name not in self._solution_status:
                self._solution_status[file_name] = SolutionStatus()
        else:
            if file_name not in self._other_compilations:
                self._other_compilations.append(file_name)
        self._compilation_status[file_name] = status
        if warnings:
            self._compilation_errors[file_name] = warnings
        if from_cache:
            self._compilation_cache.add(file_name)

    def set_generation_status(self, testcase_num: int, status: EventStatus,
                              stderr: Optional[str] = None,
                              from_cache: bool = False):
        self._generation_status[testcase_num] = status
        if stderr:
            self._generation_errors[testcase_num] = stderr
        if from_cache:
            self._generation_cache.add(testcase_num)

    def set_terry_generation_status(self, solution: str, status: EventStatus,
                                    stderr: Optional[str] = None,
                                    from_cache: bool = False):
        if solution not in self._terry_test_status:
            self._terry_test_status[solution] = TerryStatus()
        self._terry_test_status[solution].status = status
        self._terry_test_status[solution].errors = stderr
        if from_cache:
            self._terry_generation_cache.add(solution)

    def set_evaluation_status(self,
                              testcase_num: int,
                              solution_name: str,
                              status: EventStatus,
                              result: Optional[EvaluationResult] = None,
                              error: Optional[str] = None,
                              from_cache: bool = False
                              ):
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            self._solution_status[solution_name] = SolutionStatus()
        sol_status = self._solution_status[solution_name]
        sol_status.testcase_status[testcase_num] = status
        if error:
            sol_status.testcase_errors[testcase_num] = error
        if result:
            sol_status.testcase_result[testcase_num] = result
        if from_cache:
            self._evaluation_cache.add((solution_name, testcase_num))

    def set_terry_evaluation_status(self, solution: str, status: EventStatus,
                                    error: Optional[str] = None,
                                    from_cache: bool = False):
        if solution not in self._terry_test_status:
            self._terry_test_status[solution] = TerryStatus()
        self._terry_test_status[solution].status = status
        self._terry_test_status[solution].errors = error
        if from_cache:
            self._terry_evaluation_cache.add(solution)

    def set_terry_check_status(self,
                               solution: str,
                               status: EventStatus,
                               error: Optional[str] = None,
                               result: Optional[TerryEvaluationResult] = None,
                               from_cache: bool = False
                               ):
        if solution not in self._terry_test_status:
            self._terry_test_status[solution] = TerryStatus()
        self._terry_test_status[solution].status = status
        self._terry_test_status[solution].errors = error
        self._terry_test_status[solution].result = result
        if from_cache:
            self._terry_check_cache.add(solution)

    def set_subtask_score(self, subtask_num: int, solution_name: str,
                          score: float) -> None:
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            raise RuntimeError("Something weird happened")
        self._solution_status[solution_name].subtask_scores[
            subtask_num] = score

    def set_task_score(self, solution_name: str, score: float) -> None:
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            raise RuntimeError("Something weird happened")
        self._solution_status[solution_name].score = score

    def set_running_tasks(self, tasks: List[RunningTaskInfo]):
        self._running_tasks = tasks

    def print_final_status(self) -> None:
        pass

    def fatal_error(self, msg: str) -> None:
        print("FATAL ERROR: %s" % msg)

    def stop(self, msg: str) -> None:
        print(msg)
