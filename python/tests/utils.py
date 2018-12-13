#!/usr/bin/env python3
from abc import ABC, abstractmethod
from functools import reduce
from task_maker.task_maker_frontend import ResultStatus
from task_maker.tests.test import interface
from task_maker.uis import SourceFileCompilationStatus
from task_maker.uis.ioi import TestcaseSolutionStatus, IOIUIInterface
from task_maker.uis.terry import SolutionInfo
from typing import Optional, List, Tuple, Callable


class TestSolution(ABC):
    """
    Base class for a testing solution info.
    """

    @abstractmethod
    def check_solution(self):
        """
        Run the checks of this solution.
        """
        raise NotImplementedError("Subclass this class!")


class TestSolutionCompile(TestSolution):
    """
    Test a solution that expects to be compiled/executed.
    """

    def __init__(self, task: "TestInterface", name: str, score: float,
                 st_score: Optional[List[float]],
                 tc_outcome: Optional[List[Tuple[float, str]]]):
        """
        :param task: The interface of the task.
        :param name: The name of the solution to test.
        :param score: The expected score of the solution.
        :param st_score: An optional list of floats, the score for each subtask.
        :param tc_outcome: An optional list of (score, message) for each
        testcase.
        """
        self.task = task
        self.name = name
        self.score = score
        self.st_score = st_score
        self.tc_outcome = tc_outcome

    def check_solution(self):
        """
        Check that the solution is known to the interface, it has been
        compiled/executed the score is correct for both the solution and all the
        subtasks and test cases.
        """
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
    """
    Test a solution that must not compile.
    """

    def __init__(self, task: "TestInterface", name: str,
                 message: Optional[str]):
        self.task = task
        self.name = name
        self.message = message

    def check_solution(self):
        """
        Check that the solution is known to the interface and it gets the
        expected error message.
        """
        assert self.name in interface.solutions.keys()
        assert self.name in interface.testing.keys()
        solution = interface.solutions[self.name]
        assert solution.status == SourceFileCompilationStatus.FAILURE
        if self.message:
            assert self.message in solution.stderr

    def __repr__(self):
        return "<TestSolutionNotCompile name=%s>" % self.name


class TerryTestSolution:
    """
    Test a terry solution.
    """

    def __init__(self, task: "TerryTestInterface", name: str, score: float,
                 tc_score: Optional[List[float]]):
        """
        :param task: The task interface.
        :param name: The name of the solution.
        :param score: The score the solution should get.
        :param tc_score: A list of scores the solution should get for each test
        case.
        """
        self.task = task
        self.name = name
        self.score = score
        self.tc_score = tc_score

    def check_solution(self):
        """
        Check the solution is known to the interface and it gets the correct
        score and the correct score for all the test cases.
        """
        assert self.name in interface.solutions
        assert self.name in interface.solutions_info
        assert interface.solutions[
                   self.name].status == SourceFileCompilationStatus.DONE
        info = interface.solutions_info[self.name]  # type: SolutionInfo
        assert abs(info.score * self.task.max_score - self.score) < 0.0001
        if self.tc_score:
            for status, expected in zip(info.testcases_status, self.tc_score):
                assert status == expected


class TestInterface:
    """
    Interface with all the test information, including the solutions, and the
    task metadata.
    """

    def __init__(self, name: str, desc: str, timelimit: float, memlimit: int):
        self.solutions = []  # type: List[TestSolution]
        self.generator_name = None  # type: Optional[str]
        self.validator_name = None  # type: Optional[str]
        self.generation_errors = None  # type: Optional[str]
        self.validation_errors = None  # type: Optional[str]
        self.solution_errors = None  # type: Optional[str]
        self.checker_errors = None  # type: Optional[str]
        self.errors = None  # type: Optional[str]
        self.name = name
        self.desc = desc
        self.timelimit = timelimit
        self.memlimit = memlimit
        self.callback = None  # type: Optional[Callable[[IOIUIInterface], None]]

    def add_solution(self, name: str, score: float,
                     st_score: Optional[List[float]] = None,
                     tc_outcome: Optional[List[Tuple[float, str]]] = None):
        """
        Add a solution that should compile/execute.
        """
        self.solutions.append(
            TestSolutionCompile(self, name, score, st_score, tc_outcome))

    def add_not_compile(self, name: str, message=None):
        """
        Add a solution that should not compile whit the optional error message.
        """
        self.solutions.append(TestSolutionNotCompile(self, name, message))

    def set_generator(self, name: str):
        """
        Set the name of the generator.
        """
        self.generator_name = name

    def set_validator(self, name: str):
        """
        Set the name of the validator.
        """
        self.validator_name = name

    def set_generation_errors(self, errors: str):
        """
        Set a generation error that should be present in at least one test case.
        """
        self.generation_errors = errors

    def set_validation_errors(self, errors: str):
        """
        Set a validation error that should be present in at least one test case.
        """
        self.validation_errors = errors

    def set_solution_errors(self, errors: str):
        """
        Set a solution stderr that should be present in at least one test case.
        """
        self.solution_errors = errors

    def set_checker_errors(self, errors: str):
        """
        Set a checker error that should be present in at least one test case.
        """
        self.checker_errors = errors

    def set_errors(self, errors: str):
        """
        Set an error that should be present in the interface.
        """
        self.errors = errors

    def set_callback(self, callback: Callable[[IOIUIInterface], None]):
        """
        Set a callback to be run after all the other tests are done, it's a
        function that takes a IOIUIInterface
        """
        self.callback = callback

    def run_checks(self):
        """
        Run all the specified tests.
        """
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
        if self.errors:
            assert self.errors in interface.errors
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

        if self.callback is not None:
            self.callback(self)


class TerryTestInterface:
    """
    Interface to test a terry task, it contains all the testing information
    about the task.
    """
    def __init__(self, name: str, desc: str, max_score: float):
        self.solutions = []  # type: List[TerryTestSolution]
        self.generator_name = None  # type: Optional[str]
        self.validator_name = None  # type: Optional[str]
        self.checker_name = None  # type: Optional[str]
        self.max_score = max_score
        self.name = name
        self.desc = desc
        self.error = ""

    def set_generator(self, name: str):
        """
        Set the name of the generator.
        """
        self.generator_name = name

    def set_validator(self, name: str):
        """
        Set the name of the validator.
        """
        self.validator_name = name

    def set_checker(self, name: str):
        """
        Set the name of the checker.
        """
        self.checker_name = name

    def expect_error(self, error: str):
        """
        Expect the interface to have this error.
        """
        self.error = error

    def add_solution(self, name: str, score: float,
                     tc_score: Optional[List[float]] = None):
        """
        Add a solution.
        """
        self.solutions.append(TerryTestSolution(self, name, score, tc_score))

    def run_checks(self):
        """
        Run all the specified tests.
        """
        assert interface.task.name == self.name
        assert interface.task.title == self.desc
        if self.generator_name:
            assert self.generator_name in interface.non_solutions
        if self.validator_name:
            assert self.validator_name in interface.non_solutions
        if self.checker_name:
            assert self.checker_name in interface.non_solutions
        if self.error:
            assert any(self.error in error for error in interface.errors)
        for sol in self.solutions:
            sol.check_solution()
