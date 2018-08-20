#!/usr/bin/env python3
from enum import Enum
from task_maker.formats import Task
from typing import List, Dict

from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import Execution, Result, ResultStatus


class TestcaseGenerationStatus(Enum):
    WAITING = 0
    GENERATING = 1
    GENERATED = 2
    VALIDATING = 3
    VALIDATED = 4
    SOLVING = 5
    DONE = 6
    FAILURE = 7


class SourceFileCompilationStatus(Enum):
    WAITING = 0
    COMPILING = 1
    DONE = 2
    FAILURE = 3


class TestcaseSolutionStatus(Enum):
    WAITING = 0
    SOLVING = 1
    SOLVED = 2
    CHECKING = 3
    DONE = 4
    FAILURE = 5


class TestcaseSolutionResult(Enum):
    WAITING = 0
    SUCCESS = 1
    SIGNAL = 2
    RETURN_CODE = 3
    TIME_LIMIT = 4
    WALL_LIMIT = 5
    MEMORY_LIMIT = 6
    MISSING_FILES = 7
    INTERNAL_ERROR = 8


class SubtaskSolutionResult(Enum):
    WAITING = 0
    ACCEPTED = 1
    PARTIAL = 2
    REJECTED = 3


class SolutionStatus:
    def __init__(self, subtasks: Dict[int, List[int]]):
        self.testcase_status = dict(
        )  # type: Dict[int, Dict[int, TestcaseSolutionStatus]]
        self.score = None
        self.subtask_scores = [0.0] * len(subtasks)
        self.subtask_results = [SubtaskSolutionResult.WAITING] * len(subtasks)
        self.testcase_results = dict((st_num,
                                      dict((tc_num,
                                            TestcaseSolutionResult.WAITING)
                                           for tc_num in subtask))
                                     for st_num, subtask in subtasks.items())
        for st_num, subtask in subtasks.items():
            self.testcase_status[st_num] = dict()
            for tc_num in subtask:
                self.testcase_status[st_num][
                    tc_num] = TestcaseSolutionStatus.WAITING

    def update_eval_result(self, subtask: int, testcase: int, result: Result):
        # TODO implement this
        pass

    def update_check_result(self, subtask: int, testcase: int, result: Result):
        # TODO implement this
        pass


class IOILikeUIInterface:
    def __init__(self, task: Task, testcases: Dict[int, List[int]]):
        self.task = task
        self.subtasks = dict(
        )  # type: Dict[int, Dict[int, TestcaseGenerationStatus]]
        self.testcases = testcases
        self.non_solutions = dict(
        )  # type: Dict[str, SourceFileCompilationStatus]
        self.solutions = dict()  # type: Dict[str, SourceFileCompilationStatus]
        self.testing = dict()  # type: Dict[str, SolutionStatus]

        for st_num, subtask in testcases.items():
            self.subtasks[st_num] = dict()
            for tc_num in subtask:
                self.subtasks[st_num][
                    tc_num] = TestcaseGenerationStatus.WAITING

    def add_non_solution(self, source_file: SourceFile):
        name = source_file.name
        self.non_solutions[name] = SourceFileCompilationStatus.WAITING
        if source_file.need_compilation:
            def notifyStartCompiltion():
                self.non_solutions[
                    name] = SourceFileCompilationStatus.COMPILING

            def getResultCompilation(result: Result):
                if result.status == ResultStatus.SUCCESS:
                    self.non_solutions[name] = SourceFileCompilationStatus.DONE
                else:
                    # TODO: write somewhere why
                    self.non_solutions[
                        name] = SourceFileCompilationStatus.FAILURE

            source_file.compilation.notifyStart(notifyStartCompiltion)
            source_file.compilation.getResult(getResultCompilation)
        else:
            self.non_solutions[name] = SourceFileCompilationStatus.DONE

    def add_solution(self, source_file: SourceFile):
        name = source_file.name
        self.solutions[name] = SourceFileCompilationStatus.WAITING
        self.testing[name] = SolutionStatus(self.testcases)

        if source_file.need_compilation:
            def notifyStartCompiltion():
                self.solutions[name] = SourceFileCompilationStatus.COMPILING

            def getResultCompilation(result: Result):
                if result.status == ResultStatus.SUCCESS:
                    self.solutions[name] = SourceFileCompilationStatus.DONE
                else:
                    # TODO: write somewhere why
                    self.solutions[name] = SourceFileCompilationStatus.FAILURE

            source_file.compilation.notifyStart(notifyStartCompiltion)
            source_file.compilation.getResult(getResultCompilation)
        else:
            self.solutions[name] = SourceFileCompilationStatus.DONE

    def add_generation(self, subtask: int, testcase: int,
                       generation: Execution):
        def notifyStartGeneration():
            self.subtasks[subtask][
                testcase] = TestcaseGenerationStatus.GENERATING

        def getResultGeneration(result: Result):
            if result.status == ResultStatus.SUCCESS:
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.GENERATED
            else:
                # TODO: write somewhere why
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.FAILURE

        generation.notifyStart(notifyStartGeneration)
        generation.getResult(getResultGeneration)

    def add_validation(self, subtask: int, testcase: int,
                       validation: Execution):
        def notifyStartValidation():
            self.subtasks[subtask][
                testcase] = TestcaseGenerationStatus.VALIDATING

        def getResultValidation(result: Result):
            if result.status == ResultStatus.SUCCESS:
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.VALIDATED
            else:
                # TODO: write somewhere why
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.FAILURE

        validation.notifyStart(notifyStartValidation)
        validation.getResult(getResultValidation)

    def add_solving(self, subtask: int, testcase: int, solving: Execution):
        def notifyStartSolving():
            self.subtasks[subtask][testcase] = TestcaseGenerationStatus.SOLVING

        def getResultSolving(result: Result):
            if result.status == ResultStatus.SUCCESS:
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.DONE
            else:
                # TODO: write somewhere why
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.FAILURE

        solving.notifyStart(notifyStartSolving)
        solving.getResult(getResultSolving)

    def add_evaluate_solution(self, subtask: int, testcase: int, solution: str,
                              evaluation: Execution):
        def notifyStartEvaluation():
            self.testing[solution].testcase_status[subtask][
                testcase] = TestcaseSolutionStatus.SOLVING

        def getResultEvaluation(result: Result):
            self.testing[solution].update_eval_result(subtask, testcase,
                                                      result)

        evaluation.notifyStart(notifyStartEvaluation)
        evaluation.getResult(getResultEvaluation)

    def add_evaluate_checking(self, subtask: int, testcase: int, solution: str,
                              checking: Execution):
        def notifyStartChecking():
            self.testing[solution].testcase_status[subtask][
                testcase] = TestcaseSolutionStatus.CHECKING

        def getResultChecking(result: Result):
            self.testing[solution].update_check_result(subtask, testcase,
                                                       result)

        checking.notifyStart(notifyStartChecking)
        checking.getResult(getResultChecking)
