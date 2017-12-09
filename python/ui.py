#!/usr/bin/env python3

from enum import Enum
from typing import List
from typing import Optional


class CompilationStatus(Enum):
    WAITING = 0
    RUNNING = 1
    SUCCESS = 2
    FAILURE = 3


class GenerationStatus(Enum):
    WAITING = 0
    GENERATING = 1
    GENERATED = 2
    VALIDATING = 3
    VALIDATED = 4
    SOLVING = 5
    SUCCESS = 6
    FAILURE = 7


class EvaluationStatus(Enum):
    WAITING = 0
    EXECUTING = 1
    EXECUTED = 2
    CHECKING = 3
    SUCCESS = 4
    FAILURE = 5


class EvaluationResult:
    def __init__(self, score: float, message: str, cpu_time: float,
                 wall_time: float, memory: int) -> None:
        self.score = score
        self.message = message
        self.cpu_time = cpu_time
        self.wall_time = wall_time
        self.memory = memory


class UI:
    def __init__(self, task_name: str) -> None:
        self.task_name = task_name

    def set_time_limit(self, time_limit: float) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_memory_limit(self, memory_limit: int) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_subtask_info(self, subtask_num: int, max_score: float,
                         testcases: List[int]) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_compilation_status(self,
                               file_name: str,
                               is_solution: bool,
                               status: CompilationStatus,
                               warnings: Optional[str] = None) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_generation_status(self,
                              testcase_num: int,
                              status: GenerationStatus,
                              stderr: Optional[str] = None) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_evaluation_status(self,
                              testcase_num: int,
                              solution_name: str,
                              status: EvaluationStatus,
                              result: Optional[EvaluationResult] = None,
                              error: Optional[str] = None) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_subtask_score(self, subtask_num: int, solution_name: str,
                          score: float) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_task_score(self, solution_name: str, score: float) -> None:
        raise NotImplementedError("Please subclass this class")

    def print_final_status(self) -> None:
        raise NotImplementedError("Please subclass this class")
