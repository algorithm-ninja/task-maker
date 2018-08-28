#!/usr/bin/env python3
from functools import reduce
from task_maker.task_maker_frontend import ResultStatus

from task_maker.uis.ioi import SourceFileCompilationStatus, \
    TestcaseSolutionStatus
from typing import Optional, List, Tuple

from task_maker.tests.test import interface


class TestSolution:
    def check_solution(self):
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

    def check_solution(self):
        assert self.name in interface.solutions.keys()
        assert self.name in interface.testing.keys()
        solution = interface.solutions[self.name]
        testing = interface.testing[self.name]

        assert solution.status == SourceFileCompilationStatus.DONE
        assert testing.score == self.score
        if self.st_score:
            for num, score in enumerate(self.st_score):
                assert testing.subtask_scores[num] == score
        # flatten the testcases
        testcases = reduce(lambda d1, d2: {**d1, **d2},
                           testing.testcase_results.values(), {})
        if self.tc_outcome:
            for num, (score, message) in enumerate(self.tc_outcome):
                testcase = testcases[num]
                assert testcase.checked
                assert testcase.score == score
                assert message in testcase.message

    def __repr__(self):
        return "<TestSolutionCompile name=%s score=%f>" \
               % (self.name, self.score)


class TestSolutionNotCompile(TestSolution):
    def __init__(self, task: "TestInterface", name: str,
                 message: Optional[str]):
        self.task = task
        self.name = name
        self.message = message

    def check_solution(self):
        assert self.name in interface.solutions.keys()
        assert self.name in interface.testing.keys()
        solution = interface.solutions[self.name]
        assert solution.status == SourceFileCompilationStatus.FAILURE
        if self.message:
            assert self.message in solution.stderr

    def __repr__(self):
        return "<TestSolutionNotCompile name=%s>" % self.name


# class TerryTestSolution:
#     def __init__(self, task: "TerryTestInterface", name: str, score: float,
#                  tc_score: Optional[List]):
#         self.task = task
#         self.name = name
#         self.score = score
#         self.tc_score = tc_score
#
#     def check_solution(self):
#         assert self.name in ui.solutions
#         assert ui._compilation_status[self.name] == DONE
#         solution = ui._terry_test_status[self.name]
#         assert abs(solution.result.score * self.task.max_score -
#                    self.score) < 0.0001
#         if self.tc_score:
#             for status, expected in zip(solution.result.testcases,
#                                         self.tc_score):
#                 assert status == expected


class TestInterface:
    def __init__(self, name: str, desc: str, timelimit: float, memlimit: int):
        self.solutions = []  # type: List[TestSolution]
        self.generator_name = None  # type: Optional[str]
        self.validator_name = None  # type: Optional[str]
        self.generation_errors = None  # type: Optional[str]
        self.validation_errors = None  # type: Optional[str]
        self.solution_errors = None  # type: Optional[str]
        self.checker_errors = None  # type: Optional[str]
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

    def set_validation_errors(self, errors: str):
        self.validation_errors = errors

    def set_solution_errors(self, errors: str):
        self.solution_errors = errors

    def set_checker_errors(self, errors: str):
        self.checker_errors = errors

    def run_checks(self):
        task = interface.task
        assert task.name == self.name
        assert task.title == self.desc
        assert task.time_limit == self.timelimit
        assert task.memory_limit_kb == self.memlimit

        if self.generator_name:
            assert self.generator_name in interface.non_solutions.keys()
        if self.validator_name:
            assert self.validator_name in interface.non_solutions.keys()

        testcases = [
            testcase for subtask in interface.subtasks.values()
            for testcase in subtask.values()
        ]
        if not self.generation_errors:
            for testcase in testcases:
                if testcase.generation_result:
                    assert testcase.generation_result.status == \
                           ResultStatus.SUCCESS
        else:
            assert any(self.generation_errors in testcase.generation_stderr
                       for testcase in testcases)
        if not self.validation_errors:
            for testcase in testcases:
                if testcase.validation_result:
                    assert testcase.validation_result.status == \
                           ResultStatus.SUCCESS
        else:
            assert any(self.validation_errors in testcase.validation_stderr
                       for testcase in testcases)
        if not self.solution_errors:
            for testcase in testcases:
                if testcase.solution_result:
                    assert testcase.solution_result.status == \
                           ResultStatus.SUCCESS
        else:
            assert any(self.solution_errors in testcase.solution_stderr
                       for testcase in testcases)
        if self.checker_errors:
            for status in interface.testing.values():
                for subtask in status.testcase_results.values():
                    for testcase in subtask.values():
                        assert testcase.checked
                        assert testcase.status == TestcaseSolutionStatus.FAILED
                        assert self.checker_errors in testcase.message
                        assert self.checker_errors in testcase.checker_outcome

        for sol in self.solutions:
            sol.check_solution()


# class TerryTestInterface:
#     def __init__(self, name: str, desc: str, max_score: float):
#         self.solutions = []  # type: List[TerryTestSolution]
#         self.generator_name = None  # type: Optional[str]
#         self.validator_name = None  # type: Optional[str]
#         self.checker_name = None  # type: Optional[str]
#         self.max_score = max_score
#         self.name = name
#         self.desc = desc
#         self.fatal_error = False
#
#     def set_generator(self, name: str):
#         self.generator_name = name
#
#     def set_validator(self, name: str):
#         self.validator_name = name
#
#     def set_checker(self, name: str):
#         self.checker_name = name
#
#     def set_fatal_error(self):
#         self.fatal_error = True
#
#     def add_solution(self, name: str, score: float, tc_score: Optional[List]):
#         self.solutions.append(TerryTestSolution(self, name, score, tc_score))
#
#     def run_checks(self, ui: TestingUI):
#         assert ui.task_name == "%s (%s)" % (self.desc, self.name)
#         if self.fatal_error:
#             assert ui.fatal_errors
#         else:
#             assert not ui.fatal_errors
#
#         for sol in self.solutions:
#             sol.check_solution(ui)
#
#         if self.generator_name:
#             assert self.generator_name in ui._other_compilations
#         if self.validator_name:
#             assert self.validator_name in ui._other_compilations
#         if self.checker_name:
#             assert self.checker_name in ui._other_compilations
