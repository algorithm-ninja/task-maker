#!/usr/bin/env python3
from enum import Enum
from typing import List, Dict

from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import Execution


class TestcaseGenerationStatus(Enum):
    WAITING = 0
    GENERATING = 1
    GENERATED = 2
    VALIDATING = 3
    VALIDATED = 4
    SOLVING = 5
    SOLVED = 6
    CHECKING = 7
    DONE = 8
    FAILURE = 9


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


class IOILikeUIInterface:
    def __init__(self, testcases: Dict[int, List[int]]):
        self.subtasks = dict(
        )  # type: Dict[int, Dict[int, TestcaseGenerationStatus]]
        self.non_solutions = dict(
        )  # type: Dict[str, SourceFileCompilationStatus]
        self.solutions = dict()  # type: Dict[str, SourceFileCompilationStatus]
        self.testing = dict(
        )  # type: Dict[str, Dict[int, Dict[int, TestcaseSolutionStatus]]]

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

            def getResultCompilation(result):
                pass  # TODO implement this

            source_file.compilation.notifyStart(notifyStartCompiltion)
            source_file.compilation.getResult(getResultCompilation)
        else:
            self.non_solutions[name] = SourceFileCompilationStatus.DONE

    def add_solution(self, source_file: SourceFile):
        name = source_file.name
        self.solutions[name] = SourceFileCompilationStatus.WAITING
        self.testing[name] = dict()
        for st_num, subtask in self.subtasks.items():
            self.testing[name][st_num] = dict()
            for tc_num in subtask.keys():
                self.testing[name][st_num][
                    tc_num] = TestcaseSolutionStatus.WAITING
        if source_file.need_compilation:

            def notifyStartCompiltion():
                self.solutions[name] = SourceFileCompilationStatus.COMPILING

            def getResultCompilation(result):
                pass  # TODO implement this

            source_file.compilation.notifyStart(notifyStartCompiltion)
            source_file.compilation.getResult(getResultCompilation)
        else:
            self.solutions[name] = SourceFileCompilationStatus.DONE

    def add_generation(self, subtask: int, testcase: int,
                       generation: Execution):
        def notifyStartGeneration():
            self.subtasks[subtask][
                testcase] = TestcaseGenerationStatus.GENERATING

        def getResultGeneration():
            # TODO implement this really
            self.subtasks[subtask][
                testcase] = TestcaseGenerationStatus.GENERATED

        generation.notifyStart(notifyStartGeneration)
        generation.getResult(getResultGeneration)

    def add_validation(self, subtask: int, testcase: int,
                       validation: Execution):
        def notifyStartValidation():
            self.subtasks[subtask][
                testcase] = TestcaseGenerationStatus.VALIDATING

        def getResultValidation():
            # TODO implement this really
            self.subtasks[subtask][
                testcase] = TestcaseGenerationStatus.VALIDATED

        validation.notifyStart(notifyStartValidation)
        validation.getResult(getResultValidation)

    def add_solving(self, subtask: int, testcase: int, solving: Execution):
        def notifyStartSolving():
            self.subtasks[subtask][testcase] = TestcaseGenerationStatus.SOLVING

        def getResultSolving():
            # TODO implement this really
            self.subtasks[subtask][testcase] = TestcaseGenerationStatus.SOLVED

        solving.notifyStart(notifyStartSolving)
        solving.getResult(getResultSolving)

    def add_evaluate_solution(self, subtask: int, testcase: int, solution: str,
                              evaluation: Execution):
        def notifyStartEvaluation():
            self.testing[solution][subtask][
                testcase] = TestcaseSolutionStatus.SOLVING

        def getResultEvaluation():
            # TODO implement this really
            self.testing[solution][subtask][
                testcase] = TestcaseSolutionStatus.SOLVED

        evaluation.notifyStart(notifyStartEvaluation)
        evaluation.getResult(getResultEvaluation)

    def add_evaluate_checking(self, subtask: int, testcase: int, solution: str,
                              checking: Execution):
        def notifyStartChecking():
            self.testing[solution][subtask][
                testcase] = TestcaseSolutionStatus.CHECKING

        def getResultChecking():
            # TODO implement this really
            self.testing[solution][subtask][
                testcase] = TestcaseSolutionStatus.DONE

        checking.notifyStart(notifyStartChecking)
        checking.getResult(getResultChecking)
        # TODO calculate the status of the solution on this testcase and update the score
