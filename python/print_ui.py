#!/usr/bin/env python3

from typing import Dict  # pylint: disable=unused-import
from typing import List
from typing import Optional
from python.ui import CompilationStatus
from python.ui import EvaluationResult
from python.ui import EvaluationStatus
from python.ui import GenerationStatus
from python.ui import UI


class PrintUI(UI):
    def __init__(self) -> None:
        super().__init__()
        self._subtasks_scores = dict()  # type: Dict[str, Dict[int, float]]
        self._scores = dict()  # type: Dict[str, float]

    def set_time_limit(self, time_limit: float) -> None:
        print("Time limit is set to %.2f seconds" % time_limit)

    def set_memory_limit(self, memory_limit: int) -> None:
        print("Memory limit is set to %.2f megabytes" % (memory_limit / 1024))

    def set_subtask_info(self, subtask_num: int, max_score: float,
                         testcases: List[int]) -> None:
        print("Subtask %d has max score %.2f and %d testcases" %
              (subtask_num, max_score, len(testcases)))

    def set_compilation_status(self,
                               file_name: str,
                               is_solution: bool,
                               status: CompilationStatus,
                               warnings: Optional[str] = None) -> None:
        print("%sStatus of the compilation of %s is %s" %
              ("[sol] " if is_solution else "", file_name, status))
        if warnings:
            print("Compiler output:", warnings, sep="\n")

    def set_generation_status(self,
                              testcase_num: int,
                              status: GenerationStatus,
                              stderr: Optional[str] = None) -> None:
        print("Status of the generation of testcase %d is %s" % (testcase_num,
                                                                 status))
        if stderr:
            print("Errors:", stderr, sep="\n")

    def set_evaluation_status(self,
                              testcase_num: int,
                              solution_name: str,
                              status: EvaluationStatus,
                              result: Optional[EvaluationResult] = None,
                              error: Optional[str] = None) -> None:
        print("Status of the evaluation of solution %s on testcase %d: %s" %
              (solution_name, testcase_num, status))
        if error:
            print("Errors:", error, sep="\n")
        if result:
            print("Outcome:", result.message)
            print("Score:", result.score)
            print("Resource usage: %.2f cpu, %.2f wall time, %.2f MB memory" %
                  (result.cpu_time, result.wall_time, result.memory / 1024))

    def set_subtask_score(self, subtask_num: int, solution_name: str,
                          score: float) -> None:
        if solution_name not in self._subtasks_scores:
            self._subtasks_scores[solution_name] = dict()
        self._subtasks_scores[solution_name][subtask_num] = score
        print("Solution %s has a score of %.2f on subtask %d" %
              (solution_name, score, subtask_num))

    def set_task_score(self, solution_name: str, score: float) -> None:
        self._scores[solution_name] = score
        print("Solution %s has a score of %.2f" % (solution_name, score))

    def print_final_status(self) -> None:
        max_sol_name = max(map(len, self._scores.keys()))
        for solution_name in self._scores:
            print("Solution %-{0}s has a score of %6.2f".format(max_sol_name) %
                  (solution_name, self._scores[solution_name]))
        for solution_name in self._scores:
            print("Solution %-{0}s has the following scores on subtasks: %s".format(max_sol_name) %
                  (solution_name, " ".join([
                      "%6.2f" % info[1:]
                      for info in sorted(
                          self._subtasks_scores[solution_name].items())
                  ])))

    def fatal_error(self, msg: str) -> None:
        print("FATAL ERROR: %s" % msg)
