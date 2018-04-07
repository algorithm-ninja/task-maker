#!/usr/bin/env python

from typing import List
from typing import Optional

from proto.event_pb2 import Event, EventStatus, EvaluationResult, \
    RunningTaskInfo


class UI:
    def __init__(self, solutions, format):
        # type: (List[str], str) -> None
        self.task_name = ""
        self.solutions = solutions
        self.format = format

    def from_event(self, event):
        # type: (Event) -> None
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
                                        compilation.status,
                                        compilation.stderr,
                                        compilation.from_cache)
        elif event_type == "generation":
            generation = event.generation
            self.set_generation_status(generation.testcase, generation.status,
                                       generation.error, generation.from_cache)
        elif event_type == "terry_generation":
            generation = event.terry_generation
            self.set_terry_generation_status(generation.solution,
                                             generation.status,
                                             generation.error,
                                             generation.from_cache)
        elif event_type == "evaluation":
            evaluation = event.evaluation
            res = evaluation.result if evaluation.HasField("result") else None
            self.set_evaluation_status(evaluation.testcase, evaluation.solution,
                                       evaluation.status, res, None,
                                       evaluation.from_cache)
        elif event_type == "terry_evaluation":
            evaluation = event.terry_evaluation
            self.set_terry_evaluation_status(evaluation.solution,
                                             evaluation.status,
                                             evaluation.errors,
                                             evaluation.from_cache)
        elif event_type == "terry_check":
            check = event.terry_check
            res = check.result if check.HasField("result") else None
            self.set_terry_check_status(check.solution, check.status,
                                        check.errors, res, check.from_cache)
        elif event_type == "running_tasks":
            self.set_running_tasks(event.running_tasks.task)

    def set_task_name(self, task_name):
        # type: (str) -> None
        self.task_name = task_name

    def set_max_score(self, max_score):
        # type: (float) -> None
        self.max_score = max_score

    def set_time_limit(self, time_limit):
        # type: (float) -> None
        raise NotImplementedError("Please subclass this class")

    def set_memory_limit(self, memory_limit):
        # type: (int) -> None
        raise NotImplementedError("Please subclass this class")

    def set_subtask_info(self, subtask_num, max_score, testcases):
        # type: (int, float, List[int]) -> None
        raise NotImplementedError("Please subclass this class")

    def set_compilation_status(self, file_name, status, warnings=None,
                               from_cache=False):
        # type: (str, EventStatus, Optional[str], bool) -> None
        raise NotImplementedError("Please subclass this class")

    def set_generation_status(self, testcase_num, status, stderr=None,
                              from_cache=False):
        # type: (int, EventStatus, Optional[str], bool) -> None
        raise NotImplementedError("Please subclass this class")

    def set_terry_generation_status(self, solution, status, stderr=None,
                                    from_cache=False):
        # type: (str, EventStatus, Optional[str], bool) -> None
        raise NotImplementedError("Please subclass this class")

    def set_evaluation_status(self,
                              testcase_num,  # type: int
                              solution_name,  # type: str
                              status,  # type: EventStatus
                              result=None,  # type: Optional[EvaluationResult]
                              error=None,  # type: Optional[str],
                              from_cache=False  # type: bool
                              ):
        # type: (...) -> None
        raise NotImplementedError("Please subclass this class")

    def set_terry_evaluation_status(self, solution, status, error=None,
                                    from_cache=False):
        # type: (str, EventStatus, Optional[str], bool) -> None
        raise NotImplementedError("Please subclass this class")

    def set_terry_check_status(self, solution, status, error=None,
                               score=None, from_cache=False):
        # type: (str, EventStatus, Optional[str], Optional[float], bool) -> None
        raise NotImplementedError("Please subclass this class")

    def set_subtask_score(self, subtask_num, solution_name, score):
        # type: (int, str, float) -> None
        raise NotImplementedError("Please subclass this class")

    def set_task_score(self, solution_name, score):
        # type: (str, float) -> None
        raise NotImplementedError("Please subclass this class")

    def set_running_tasks(self, tasks):
        # type: (List[RunningTaskInfo]) -> None
        raise NotImplementedError("Please subclass this class")

    def print_final_status(self):
        raise NotImplementedError("Please subclass this class")

    def fatal_error(self, msg):
        # type: (str) -> None
        raise NotImplementedError("Please subclass this class")

    def stop(self, msg):
        # type: (str) -> None
        raise NotImplementedError("Please subclass this class")
