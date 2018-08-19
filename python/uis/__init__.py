#!/usr/bin/env python3
from enum import Enum
from typing import Dict, Optional


class EvaluationResult:
    def __init__(self, score: float, message: str, cpu_time_used: float,
                 wall_time_used: float, memory_used_kb: float):
        self.score = score
        self.message = message
        self.cpu_time_used = cpu_time_used
        self.wall_time_used = wall_time_used
        self.memory_used_kb = memory_used_kb


class EventStatus(Enum):
    WAITING = 0
    RUNNING = 1
    GENERATING = 2
    GENERATED = 3
    VALIDATING = 4
    VALIDATED = 5
    SOLVING = 6
    EXECUTING = 7
    EXECUTED = 8
    CHECKING = 9
    DONE = 10
    FAILURE = 11


class SolutionStatus:
    def __init__(self):
        self.testcase_errors = dict()  # type: Dict[int, str]
        self.testcase_result = dict()  # type: Dict[int, EvaluationResult]
        self.testcase_status = dict()  # type: Dict[int, EventStatus]
        self.subtask_scores = dict()  # type: Dict[int, float]
        self.score = None  # type: Optional[float]
        self.compiled = False

    def __repr__(self):
        return "<SolutionStatus [%s]>" % (", ".join(
            "%d: %.1f" % (i, tc.score)
            for i, tc in self.testcase_result.items()))


class TerryStatus:
    def __init__(self):
        self.status = EventStatus.WAITING  # type: EventStatus
        self.errors = None  # type: Optional[str]
        # self.result = None  # type: Optional[TerryEvaluationResult]
