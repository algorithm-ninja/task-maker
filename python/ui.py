#!/usr/bin/env python3

from typing import List
from typing import Optional

from proto.event_pb2 import Event, EventStatus, EvaluationResult


class UI:
    def __init__(self, solutions: List[str]) -> None:
        self.task_name = ""
        self.solutions = solutions

    def from_event(self, event: Event) -> None:
        event_type = event.WhichOneof("event_oneof")
        if event_type == "fatal_error":
            self.fatal_error(event.fatal_error.msg)
        elif event_type == "task_score":
            self.set_task_score(event.task_score.solution,
                                event.task_score.score)
        elif event_type == "subtask_score":
            self.set_subtask_score(event.subtask_score.subtask_id,
                                   event.subtask_score.solution,
                                   event.subtask_score.score)
        elif event_type == "compilation":
            compilation = event.compilation
            self.set_compilation_status(compilation.filename,
                                        compilation.status, compilation.stderr)
        elif event_type == "generation":
            generation = event.generation
            self.set_generation_status(generation.testcase, generation.status,
                                       generation.error)
        elif event_type == "evaluation":
            evaluation = event.evaluation
            res = evaluation.result if evaluation.HasField("result") else None
            self.set_evaluation_status(evaluation.testcase, evaluation.solution,
                                       evaluation.status, res)

        elif event_type == "running_tasks":
            self.set_running_tasks(event.running_tasks.task)

    def set_task_name(self, task_name: str) -> None:
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
                               status: EventStatus,
                               warnings: Optional[str] = None) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_generation_status(self,
                              testcase_num: int,
                              status: EventStatus,
                              stderr: Optional[str] = None) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_evaluation_status(self,
                              testcase_num: int,
                              solution_name: str,
                              status: EventStatus,
                              result: Optional[EvaluationResult] = None,
                              error: Optional[str] = None) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_subtask_score(self, subtask_num: int, solution_name: str,
                          score: float) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_task_score(self, solution_name: str, score: float) -> None:
        raise NotImplementedError("Please subclass this class")

    def set_running_tasks(self, tasks):
        raise NotImplementedError("Please subclass this class")

    def print_final_status(self) -> None:
        raise NotImplementedError("Please subclass this class")

    def fatal_error(self, msg: str) -> None:
        raise NotImplementedError("Please subclass this class")

    def stop(self, msg: str) -> None:
        raise NotImplementedError("Please subclass this class")