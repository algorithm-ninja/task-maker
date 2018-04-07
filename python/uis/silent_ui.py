#!/usr/bin/env python

from __future__ import print_function

from typing import Dict, Set, Tuple  # pylint: disable=unused-import
from typing import List, Optional

import os.path
from proto.event_pb2 import EvaluationResult, TerryEvaluationResult, \
    EventStatus, RunningTaskInfo

from python.ui import UI


class SolutionStatus:
    def __init__(self):
        self.testcase_errors = dict()  # type: Dict[int, str]
        self.testcase_result = dict()  # type: Dict[int, EvaluationResult]
        self.testcase_status = dict()  # type: Dict[int, EventStatus]
        self.subtask_scores = dict()  # type: Dict[int, float]
        self.score = None  # type: Optional[float]
        self.compiled = False


class TerryStatus:
    def __init__(self):
        self.status = None  # type: EventStatus
        self.errors = None  # type: Optional[str]
        self.result = None  # type: Optional[TerryEvaluationResult]


class SilentUI(UI):
    def __init__(self, solutions, format):
        # type: (List[str], str) -> None
        UI.__init__(self, solutions, format)
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

    def set_time_limit(self, time_limit):
        # type: (float) -> None
        self._time_limit = time_limit

    def set_memory_limit(self, memory_limit):
        # type: (int) -> None
        self._memory_limit = memory_limit

    def set_subtask_info(self, subtask_num, max_score, testcases):
        # type: (int, float, List[int]) -> None
        self._subtask_testcases[subtask_num] = testcases
        self._subtask_max_scores[subtask_num] = max_score
        self._num_testcases = max(self._num_testcases, max(testcases) + 1)

    def set_compilation_status(self, file_name, status, warnings=None,
                               from_cache=False):
        # type: (str, EventStatus, Optional[str], bool) -> None
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

    def set_generation_status(self, testcase_num, status, stderr=None,
                              from_cache=False):
        # type: (int, EventStatus, Optional[str], bool) -> None
        self._generation_status[testcase_num] = status
        if stderr:
            self._generation_errors[testcase_num] = stderr
        if from_cache:
            self._generation_cache.add(testcase_num)

    def set_terry_generation_status(self, solution, status, stderr=None,
                                    from_cache=False):
        # type: (str, EventStatus, Optional[str], bool) -> None
        if solution not in self._terry_test_status:
            self._terry_test_status[solution] = TerryStatus()
        self._terry_test_status[solution].status = status
        self._terry_test_status[solution].errors = stderr
        if from_cache:
            self._terry_generation_cache.add(solution)

    def set_evaluation_status(self,
                              testcase_num,  # type: int
                              solution_name,  # type: str
                              status,  # type: EventStatus
                              result=None,  # type: Optional[EvaluationResult]
                              error=None,  # type: Optional[str]
                              from_cache=False  # type: bool
                              ):
        # type: (...) -> None
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

    def set_terry_evaluation_status(self, solution, status, error=None,
                                    from_cache=False):
        # type: (str, EventStatus, Optional[str], bool) -> None
        if solution not in self._terry_test_status:
            self._terry_test_status[solution] = TerryStatus()
        self._terry_test_status[solution].status = status
        self._terry_test_status[solution].errors = error
        if from_cache:
            self._terry_evaluation_cache.add(solution)

    def set_terry_check_status(self,
                               solution,  # type: str
                               status,  # type: EventStatus
                               error=None,  # type: Optional[str]
                               result=None,
                               # type: Optional[TerryEvaluationResult]
                               from_cache=False  # type: bool
                               ):
        # type: (...) -> None
        if solution not in self._terry_test_status:
            self._terry_test_status[solution] = TerryStatus()
        self._terry_test_status[solution].status = status
        self._terry_test_status[solution].errors = error
        self._terry_test_status[solution].result = result
        if from_cache:
            self._terry_check_cache.add(solution)

    def set_subtask_score(self, subtask_num, solution_name, score):
        # type: (int, str, float) -> None
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            raise RuntimeError("Something weird happened")
        self._solution_status[solution_name].subtask_scores[
            subtask_num] = score

    def set_task_score(self, solution_name, score):
        # type: (str, float) -> None
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            raise RuntimeError("Something weird happened")
        self._solution_status[solution_name].score = score

    def set_running_tasks(self, tasks):
        # type: (List[RunningTaskInfo]) -> None
        self._running_tasks = tasks

    def print_final_status(self):
        pass

    def fatal_error(self, msg):
        # type: (str) -> None
        print("FATAL ERROR: %s" % msg)

    def stop(self, msg):
        # type: (str) -> None
        print(msg)
