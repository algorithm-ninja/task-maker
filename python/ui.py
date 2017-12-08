#!/usr/bin/env python3

from enum import Enum
from typing import Optional

from python.task import Subtask


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
    SUCCESS = 4
    FAILURE = 5


class EvaluationStatus(Enum):
    WAITING = 0
    RUNNING = 1
    CHECKING = 2
    SUCCESS = 3
    FAILURE = 4


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

    def set_subtask_info(self, subtask: Subtask) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_task_score(self, score: float) -> None:
        raise NotImplementedError("Please subclass this class")

    def final_status(self) -> None:
        raise NotImplementedError("Please subclass this class")
