#!/usr/bin/env python

from __future__ import print_function

from typing import Dict  # pylint: disable=unused-import
from typing import List
from typing import Optional

from proto.event_pb2 import EvaluationResult, TerryEvaluationResult, \
    RunningTaskInfo, EventStatus, DONE

from python.ui import UI


class PrintUI(UI):
    def __init__(self, solutions, format):
        # type: (List[str], str) -> None
        UI.__init__(self, solutions, format)
        self._subtasks_scores = dict()  # type: Dict[str, Dict[int, float]]
        self._running_tasks = list()  # type: List[RunningTaskInfo]
        self._scores = dict()  # type: Dict[str, float]

    def set_time_limit(self, time_limit):
        # type: (float) -> None
        print("Time limit is set to %.2f seconds" % time_limit)

    def set_memory_limit(self, memory_limit):
        # type: (int) -> None
        print("Memory limit is set to %.2f megabytes" % (memory_limit / 1024))

    def set_subtask_info(self, subtask_num, max_score, testcases):
        # type: (int, float, List[int]) -> None
        print("Subtask %d has max score %.2f and %d testcases" %
              (subtask_num, max_score, len(testcases)))

    def set_compilation_status(self, file_name, status, warnings=None,
                               from_cache=False):
        # type: (str, EventStatus, Optional[str], bool) -> None
        is_solution = file_name in self.solutions
        print("%sStatus of the compilation of %s is %s%s" %
              ("[sol] " if is_solution else "",
               file_name,
               EventStatus.Name(status),
               " [cached]" if from_cache else ""))
        if warnings:
            print("Compiler output:", warnings, sep="\n")

    def set_generation_status(self, testcase_num, status, stderr=None,
                              from_cache=False):
        # type: (int, EventStatus, Optional[str], bool) -> None
        print("Status of the generation of testcase %d is %s%s"
              % (testcase_num, EventStatus.Name(status),
                 " [cached]" if from_cache else ""))
        if stderr:
            print("Errors:", stderr, sep="\n")

    def set_terry_generation_status(self, solution, status, stderr=None,
                                    from_cache=False):
        # type: (str, EventStatus, Optional[str], bool) -> None
        print("Status of the generation of input for %s is %s%s"
              % (solution, EventStatus.Name(status),
                 " [cached]" if from_cache else ""))
        if stderr:
            print("Errors:", stderr, sep="\n")

    def set_evaluation_status(self,
                              testcase_num,  # type: int
                              solution_name,  # type: str
                              status,  # type: EventStatus
                              result=None,  # type: Optional[EvaluationResult]
                              error=None,  # type: Optional[str]
                              from_cache=False  # type: bool
                              ):
        # type: (...) -> None
        print("Status of the evaluation of solution %s on testcase %d: %s%s" %
              (solution_name, testcase_num, EventStatus.Name(status),
               " [cached]" if from_cache else ""))
        if error:
            print("Errors:", error, sep="\n")
        if status == DONE:
            print("Outcome:", result.message)
            print("Score:", result.score)
            print("Resource usage: %.2f cpu, %.2f wall time, %.2f MB memory" %
                  (result.cpu_time_used, result.wall_time_used,
                   result.memory_used_kb / 1024))

    def set_terry_evaluation_status(self, solution, status, error=None,
                                    from_cache=False):
        # type: (str, EventStatus, Optional[str], bool) -> None
        print("Status of the evaluation of solution %s is %s%s"
              % (solution, EventStatus.Name(status),
                 " [cached]" if from_cache else ""))
        if error:
            print("Errors:", error, sep="\n")

    def set_terry_check_status(self,
                               solution,  # type: str
                               status,  # type: EventStatus
                               error=None,  # type: Optional[str]
                               result=None,
                               # type: Optional[TerryEvaluationResult]
                               from_cache=False  # type: bool
                               ):
        # type: (...) -> None
        print("Status of the checking of solution %s is %s%s"
              % (solution, EventStatus.Name(status),
                 " [cached]" if from_cache else ""))
        if error:
            print("Errors:", error, sep="\n")
        if result is not None:
            print("Result:", result)

    def set_subtask_score(self, subtask_num, solution_name, score):
        # type: (int, str, float) -> None
        if solution_name not in self._subtasks_scores:
            self._subtasks_scores[solution_name] = dict()
        self._subtasks_scores[solution_name][subtask_num] = score
        print("Solution %s has a score of %.2f on subtask %d" %
              (solution_name, score, subtask_num))

    def set_task_score(self, solution_name, score):
        # type: (str, float) -> None
        self._scores[solution_name] = score
        print("Solution %s has a score of %.2f" % (solution_name, score))

    def set_running_tasks(self, tasks):
        # type: (List[RunningTaskInfo]) -> None
        self._running_tasks = tasks
        print("Running tasks:\n  %s" % "\n  ".join(
            "%s -- %ds" % (task.description, task.duration) for task in tasks))

    def print_final_status(self):
        max_sol_name = max(map(len, self.solutions))
        for solution_name in self._scores:
            print("Solution %-{0}s has a score of %6.2f".format(max_sol_name) %
                  (solution_name, self._scores[solution_name]))
        for solution_name in self._scores:
            print("Solution %-{0}s has the following scores on subtasks: %s"
                  .format(max_sol_name) %
                  (solution_name, " ".join([
                      "%6.2f" % info[1:]
                      for info in sorted(
                          self._subtasks_scores[solution_name].items())
                  ])))

    def fatal_error(self, msg):
        # type: (str) -> None
        print("FATAL ERROR: %s" % msg)

    def stop(self, msg):
        # type: (str) -> None
        print(msg)
