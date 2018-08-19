#!/usr/bin/env python3
from typing import Optional, List, Tuple

from event_pb2 import DONE, FAILURE

from task_maker.tests.test import TestingUI


class TestSolution:
    def check_solution(self, ui: TestingUI):
        raise NotImplementedError("Subclass this class!")


class TestSolutionCompile(TestSolution):
    def __init__(self, task: "TestInterface", name: str, score: float,
                 st_score: Optional[List],
                 tc_outcome: Optional[List[Tuple[float, str]]]):
        self.task = task
        self.name = name
        self.score = score
        self.st_score = st_score
        self.tc_outcome = tc_outcome

    def check_solution(self, ui: TestingUI):
        assert self.name in ui.solutions
        assert ui._compilation_status[self.name] == DONE
        solution = ui._solution_status[self.name]
        assert solution.score == self.score
        if self.st_score:
            for num, score in enumerate(self.st_score):
                assert solution.subtask_scores[num] == score
        if self.tc_outcome:
            for num, outcome in enumerate(self.tc_outcome):
                score, message = outcome
                testcase = solution.testcase_result[num]
                assert testcase.score == score
                assert message in testcase.message.strip()
                if message == "CPU limit exeeded":
                    assert testcase.cpu_time_used > self.task.timelimit
                    assert testcase.wall_time_used > self.task.timelimit

    def __repr__(self):
        return "<TestSolutionCompile name=%s score=%f>" \
               % (self.name, self.score)


class TestSolutionNotCompile(TestSolution):
    def __init__(self, task: "TestInterface", name: str,
                 message: Optional[str]):
        self.task = task
        self.name = name
        self.message = message

    def check_solution(self, ui: TestingUI):
        assert self.name in ui._compilation_errors
        assert self.name in ui._compilation_status
        assert ui._compilation_status[self.name] == FAILURE
        if self.message:
            assert self.message in ui._compilation_errors[self.name]

    def __repr__(self):
        return "<TestSolutionNotCompile name=%s>" % self.name


class TerryTestSolution:
    def __init__(self, task: "TerryTestInterface", name: str, score: float,
                 tc_score: Optional[List]):
        self.task = task
        self.name = name
        self.score = score
        self.tc_score = tc_score

    def check_solution(self, ui: TestingUI):
        assert self.name in ui.solutions
        assert ui._compilation_status[self.name] == DONE
        solution = ui._terry_test_status[self.name]
        assert abs(solution.result.score * self.task.max_score -
                   self.score) < 0.0001
        if self.tc_score:
            for status, expected in zip(solution.result.testcases,
                                        self.tc_score):
                assert status == expected


class TestInterface:
    def __init__(self, name, desc, timelimit, memlimit):
        self.solutions = []  # type: List[TestSolution]
        self.generator_name = None  # type: Optional[str]
        self.validator_name = None  # type: Optional[str]
        self.generation_errors = None  # type: Optional[str]
        self.fatal_error = False  # type: bool
        self.name = name
        self.desc = desc
        self.timelimit = timelimit
        self.memlimit = memlimit

    def add_solution(self,
                     name: str,
                     score: float,
                     st_score=None,
                     tc_outcome=None):
        self.solutions.append(
            TestSolutionCompile(self, name, score, st_score, tc_outcome))

    def add_not_compile(self, name: str, message=None):
        self.solutions.append(TestSolutionNotCompile(self, name, message))

    def set_generator(self, name: str):
        self.generator_name = name

    def set_validator(self, name: str):
        self.validator_name = name

    def set_generation_errors(self, errors: str):
        self.generation_errors = errors

    def set_fatal_error(self):
        self.fatal_error = True

    def run_checks(self, ui: TestingUI):
        assert ui.task_name == "%s (%s)" % (self.desc, self.name)
        assert ui._time_limit == self.timelimit
        assert ui._memory_limit == self.memlimit

        if self.generator_name:
            assert self.generator_name in ui._other_compilations
        if self.validator_name:
            assert self.validator_name in ui._other_compilations

        if not self.generation_errors:
            assert not ui._generation_errors
        else:
            assert ui._generation_errors
            for errors in ui._generation_errors.values():
                assert self.generation_errors in errors

        for sol in self.solutions:
            sol.check_solution(ui)

        if self.fatal_error:
            assert ui.fatal_errors
        else:
            assert not ui.fatal_errors


class TerryTestInterface:
    def __init__(self, name: str, desc: str, max_score: float):
        self.solutions = []  # type: List[TerryTestSolution]
        self.generator_name = None  # type: Optional[str]
        self.validator_name = None  # type: Optional[str]
        self.checker_name = None  # type: Optional[str]
        self.max_score = max_score
        self.name = name
        self.desc = desc
        self.fatal_error = False

    def set_generator(self, name: str):
        self.generator_name = name

    def set_validator(self, name: str):
        self.validator_name = name

    def set_checker(self, name: str):
        self.checker_name = name

    def set_fatal_error(self):
        self.fatal_error = True

    def add_solution(self, name: str, score: float, tc_score: Optional[List]):
        self.solutions.append(TerryTestSolution(self, name, score, tc_score))

    def run_checks(self, ui: TestingUI):
        assert ui.task_name == "%s (%s)" % (self.desc, self.name)
        if self.fatal_error:
            assert ui.fatal_errors
        else:
            assert not ui.fatal_errors

        for sol in self.solutions:
            sol.check_solution(ui)

        if self.generator_name:
            assert self.generator_name in ui._other_compilations
        if self.validator_name:
            assert self.validator_name in ui._other_compilations
        if self.checker_name:
            assert self.checker_name in ui._other_compilations
