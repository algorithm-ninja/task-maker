#!/usr/bin/env python3
import time

from enum import Enum
from task_maker.formats import Task, ScoreMode
from task_maker.printer import StdoutPrinter, Printer
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


class TestcaseSolutionResult(Enum):
    WAITING = 0
    SOLVING = 1
    SOLVED = 2
    CHECKING = 3
    ACCEPTED = 4
    WRONG_ANSWER = 5
    PARTIAL = 6
    SIGNAL = 7
    RETURN_CODE = 8
    TIME_LIMIT = 9
    WALL_LIMIT = 10
    MEMORY_LIMIT = 11
    MISSING_FILES = 12
    INTERNAL_ERROR = 13
    SKIPPED = 14


class SubtaskSolutionResult(Enum):
    WAITING = 0
    RUNNING = 1
    ACCEPTED = 2
    PARTIAL = 3
    REJECTED = 4


class CustomCheckerState:
    def __init__(self, solution: str):
        self.solution = solution
        self.result = None  # type: Result
        self.stdout = None  # type: str
        self.stderr = None  # type: str
        self.callback = None

    def set_result(self, result: Result):
        self.result = result
        self._check()

    def set_stdout(self, stdout: str):
        self.stdout = stdout
        self._check()

    def set_stderr(self, stderr: str):
        self.stderr = stderr
        self._check()

    def set_callback(self, callback):
        self.callback = callback
        self._check()

    def _check(self):
        if self.result is not None and self.stdout is not None and \
                self.stderr is not None and self.callback is not None:
            self.callback()


class SolutionStatus:
    def __init__(self, source_file: SourceFile, task: Task,
                 subtasks: Dict[int, List[int]]):
        self.source_file = source_file
        self.task = task
        self.score = 0.0
        self.subtask_scores = dict((st_num, 0.0) for st_num in subtasks)
        self.subtask_results = [SubtaskSolutionResult.WAITING] * len(subtasks)
        self.testcase_results = dict(
        )  # type: Dict[int, Dict[int, TestcaseSolutionResult]]
        self.testcase_scores = dict()
        self.st_remaining_cases = [
            len(subtask) for subtask in subtasks.values()
        ]

        for st_num, subtask in subtasks.items():
            self.testcase_results[st_num] = dict()
            self.testcase_scores[st_num] = dict()
            for tc_num in subtask:
                self.testcase_results[st_num][
                    tc_num] = TestcaseSolutionResult.WAITING
                self.testcase_scores[st_num][tc_num] = 0.0

    def update_eval_result(self, subtask: int, testcase: int, result: Result):
        self.subtask_results[subtask] = SubtaskSolutionResult.RUNNING
        # TODO generate and store somewhere the message
        if result.status == ResultStatus.SIGNAL:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.SIGNAL
        elif result.status == ResultStatus.RETURN_CODE:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.RETURN_CODE
        elif result.status == ResultStatus.TIME_LIMIT:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.TIME_LIMIT
        elif result.status == ResultStatus.WALL_LIMIT:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.WALL_LIMIT
        elif result.status == ResultStatus.MEMORY_LIMIT:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.MEMORY_LIMIT
        elif result.status == ResultStatus.MISSING_FILES:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.MISSING_FILES
        elif result.status == ResultStatus.INTERNAL_ERROR:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.INTERNAL_ERROR
        else:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.SOLVED
        if result.status != ResultStatus.SUCCESS:
            self.st_remaining_cases[subtask] -= 1
            if self.st_remaining_cases[subtask] == 0:
                self._compute_st_score(subtask)
        # TODO store used resources

    def update_default_check_result(self, subtask: int, testcase: int,
                                    result: Result):
        if result.status == ResultStatus.SUCCESS:
            self.testcase_scores[subtask][testcase] = 1.0
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.ACCEPTED
        elif result.status == ResultStatus.RETURN_CODE:
            self.testcase_scores[subtask][testcase] = 0.0
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.WRONG_ANSWER
        else:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.INTERNAL_ERROR

        self.st_remaining_cases[subtask] -= 1
        if self.st_remaining_cases[subtask] == 0:
            self._compute_st_score(subtask)

    def update_custom_check_result(self, subtask: int, testcase: int,
                                   state: CustomCheckerState):
        if state.result.status != ResultStatus.SUCCESS:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.INTERNAL_ERROR
            return
        try:
            score = float(state.stdout)
        except ValueError:
            if state.result.status != ResultStatus.SUCCESS:
                self.testcase_results[subtask][
                    testcase] = TestcaseSolutionResult.INTERNAL_ERROR
            return
        if not 0.0 <= score <= 1.0:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.INTERNAL_ERROR
            return
        self.testcase_scores[subtask][testcase] = score
        if score == 1.0:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.ACCEPTED
            message = "Accepted"
        elif score == 0.0:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.WRONG_ANSWER
            message = "Wrong answer"
        else:
            self.testcase_results[subtask][
                testcase] = TestcaseSolutionResult.PARTIAL
            message = "Parial score"
        if state.stdout:
            message = state.stdout

        self.st_remaining_cases[subtask] -= 1
        if self.st_remaining_cases[subtask] == 0:
            self._compute_st_score(subtask)

    def _compute_st_score(self, subtask: int):
        scores = self.testcase_scores[subtask].values()
        score_mode = self.task.subtasks[subtask].score_mode
        if score_mode == ScoreMode.MIN:
            score = min(scores)
        elif score_mode == ScoreMode.MAX:
            score = max(scores)
        elif score_mode == ScoreMode.SUM:
            score = sum(scores) / len(scores)
        else:
            raise ValueError("Invalid score mode", score_mode)
        score *= self.task.subtasks[subtask].max_score
        self.subtask_scores[subtask] = score
        self.score = sum(self.subtask_scores.values())
        if min(scores) == 1.0:
            self.subtask_results[subtask] = SubtaskSolutionResult.ACCEPTED
        elif score == 0.0:
            self.subtask_results[subtask] = SubtaskSolutionResult.REJECTED
        else:
            self.subtask_results[subtask] = SubtaskSolutionResult.PARTIAL


class IOIUIInterface:
    def __init__(self, task: Task, testcases: Dict[int, List[int]],
                 do_print: bool):
        self.task = task
        self.subtasks = dict(
        )  # type: Dict[int, Dict[int, TestcaseGenerationStatus]]
        self.testcases = testcases
        self.non_solutions = dict(
        )  # type: Dict[str, SourceFileCompilationStatus]
        self.non_solutions_stderr = dict()  # type: Dict[str, str]
        self.solutions = dict()  # type: Dict[str, SourceFileCompilationStatus]
        self.solutions_stderr = dict()  # type: Dict[str, str]
        self.testing = dict()  # type: Dict[str, SolutionStatus]
        self.running = dict()  # type: Dict[str, float]

        if do_print:
            self.printer = StdoutPrinter()
        else:
            self.printer = Printer()

        for st_num, subtask in testcases.items():
            self.subtasks[st_num] = dict()
            for tc_num in subtask:
                self.subtasks[st_num][
                    tc_num] = TestcaseGenerationStatus.WAITING

    def add_non_solution(self, source_file: SourceFile):
        name = source_file.name
        log_prefix = "Compilation of non-solution {} ".format(name).ljust(50)
        self.non_solutions[name] = SourceFileCompilationStatus.WAITING
        self.printer.text(log_prefix + "WAITING\n")
        if source_file.need_compilation:

            def notifyStartCompiltion():
                self.printer.text(log_prefix + "START\n")
                self.non_solutions[
                    name] = SourceFileCompilationStatus.COMPILING
                self.running[log_prefix] = time.monotonic()

            def getResultCompilation(result: Result):
                del self.running[log_prefix]
                if result.status == ResultStatus.SUCCESS:
                    self.printer.green(log_prefix + "SUCCESS\n")
                    self.non_solutions[name] = SourceFileCompilationStatus.DONE
                else:
                    self.printer.red(log_prefix +
                                     "FAIL: {}\n".format(result.status))
                    self.non_solutions[
                        name] = SourceFileCompilationStatus.FAILURE

            def getStderr(stderr):
                if stderr:
                    self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")
                self.non_solutions_stderr[name] = stderr

            source_file.compilation_stderr.getContentsAsString(getStderr)
            source_file.compilation.notifyStart(notifyStartCompiltion)
            source_file.compilation.getResult(getResultCompilation)
        else:
            self.printer.green(log_prefix + "SUCCESS\n")
            self.non_solutions[name] = SourceFileCompilationStatus.DONE

    def add_solution(self, source_file: SourceFile):
        name = source_file.name
        log_prefix = "Compilation of solution {} ".format(name).ljust(50)
        self.solutions[name] = SourceFileCompilationStatus.WAITING
        self.testing[name] = SolutionStatus(source_file, self.task,
                                            self.testcases)
        self.printer.text(log_prefix + "WAITING\n")

        if source_file.need_compilation:

            def notifyStartCompiltion():
                self.printer.text(log_prefix + "START\n")
                self.solutions[name] = SourceFileCompilationStatus.COMPILING
                self.running[log_prefix] = time.monotonic()

            def getResultCompilation(result: Result):
                del self.running[log_prefix]
                if result.status == ResultStatus.SUCCESS:
                    self.printer.green(log_prefix + "SUCCESS\n")
                    self.solutions[name] = SourceFileCompilationStatus.DONE
                else:
                    self.printer.red(log_prefix +
                                     "FAIL: {}\n".format(result.status))
                    self.solutions[name] = SourceFileCompilationStatus.FAILURE

            def getStderr(stderr):
                if stderr:
                    self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")
                self.solutions_stderr[name] = stderr

            source_file.compilation_stderr.getContentsAsString(getStderr)
            source_file.compilation.notifyStart(notifyStartCompiltion)
            source_file.compilation.getResult(getResultCompilation)
        else:
            self.printer.green(log_prefix + "SUCCESS\n")
            self.solutions[name] = SourceFileCompilationStatus.DONE

    def add_generation(self, subtask: int, testcase: int,
                       generation: Execution):
        log_prefix = "Generation of input {} of subtask {} ".format(
            testcase, subtask).ljust(50)
        self.printer.text(log_prefix + "WAITING\n")

        def notifyStartGeneration():
            self.printer.text(log_prefix + "START\n")
            self.subtasks[subtask][
                testcase] = TestcaseGenerationStatus.GENERATING
            self.running[log_prefix] = time.monotonic()

        def getResultGeneration(result: Result):
            del self.running[log_prefix]
            if result.status == ResultStatus.SUCCESS:
                self.printer.green(log_prefix + "SUCCESS\n")
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.GENERATED
            else:
                self.printer.red(log_prefix +
                                 "FAIL: {}\n".format(result.status))
                # TODO: write somewhere why
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.FAILURE

        def skippedGeneration():
            self.printer.red(log_prefix + "SKIPPED\n")

        def getStderr(stderr):
            if stderr:
                self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")

        generation.stderr(False).getContentsAsString(getStderr)
        generation.notifyStart(notifyStartGeneration)
        generation.getResult(getResultGeneration, skippedGeneration)

    def add_validation(self, subtask: int, testcase: int,
                       validation: Execution):
        log_prefix = "Validation of input {} of subtask {} ".format(
            testcase, subtask).ljust(50)
        self.printer.text(log_prefix + "WAITING\n")

        def notifyStartValidation():
            self.printer.text(log_prefix + "START\n")
            self.subtasks[subtask][
                testcase] = TestcaseGenerationStatus.VALIDATING
            self.running[log_prefix] = time.monotonic()

        def getResultValidation(result: Result):
            del self.running[log_prefix]
            if result.status == ResultStatus.SUCCESS:
                self.printer.green(log_prefix + "SUCCESS\n")
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.VALIDATED
            else:
                self.printer.red(log_prefix +
                                 "FAIL: {}\n".format(result.status))
                # TODO: write somewhere why
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.FAILURE

        def skippedValidation():
            self.printer.red(log_prefix + "SKIPPED\n")

        def getStderr(stderr):
            if stderr:
                self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")

        validation.stderr(False).getContentsAsString(getStderr)
        validation.notifyStart(notifyStartValidation)
        validation.getResult(getResultValidation, skippedValidation)

    def add_solving(self, subtask: int, testcase: int, solving: Execution):
        log_prefix = "Generation of output {} of subtask {} ".format(
            testcase, subtask).ljust(50)
        self.printer.text(log_prefix + "WAITING\n")

        def notifyStartSolving():
            self.printer.text(log_prefix + "START\n")
            self.subtasks[subtask][testcase] = TestcaseGenerationStatus.SOLVING
            self.running[log_prefix] = time.monotonic()

        def getResultSolving(result: Result):
            del self.running[log_prefix]
            if result.status == ResultStatus.SUCCESS:
                self.printer.green(log_prefix + "SUCCESS\n")
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.DONE
            else:
                self.printer.red(log_prefix +
                                 "FAIL: {}\n".format(result.status))
                # TODO: write somewhere why
                self.subtasks[subtask][
                    testcase] = TestcaseGenerationStatus.FAILURE

        def skippedSolving():
            self.printer.red(log_prefix + "SKIPPED\n")

        def getStderr(stderr):
            if stderr:
                self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")

        solving.stderr(False).getContentsAsString(getStderr)
        solving.notifyStart(notifyStartSolving)
        solving.getResult(getResultSolving, skippedSolving)

    def add_evaluate_solution(self, subtask: int, testcase: int, solution: str,
                              evaluation: Execution):
        log_prefix = "Evaluate {} on case {} ".format(solution,
                                                      testcase).ljust(50)
        self.printer.text(log_prefix + "WAITING\n")

        def notifyStartEvaluation():
            self.printer.text(log_prefix + "START\n")
            self.testing[solution].testcase_results[subtask][
                testcase] = TestcaseSolutionResult.SOLVING
            self.running[log_prefix] = time.monotonic()

        def getResultEvaluation(result: Result):
            del self.running[log_prefix]
            if result.status == ResultStatus.SUCCESS:
                self.printer.green(log_prefix + "SUCCESS\n")
            else:
                self.printer.red(log_prefix +
                                 "FAIL: {}\n".format(result.status))

            self.testing[solution].update_eval_result(subtask, testcase,
                                                      result)

        def skippedEvaluation():
            self.testing[solution].testcase_results[subtask][
                testcase] = TestcaseSolutionResult.SKIPPED
            self.printer.yellow(log_prefix + "SKIPPED\n")

        evaluation.notifyStart(notifyStartEvaluation)
        evaluation.getResult(getResultEvaluation, skippedEvaluation)

    def add_evaluate_checking(self, subtask: int, testcase: int, solution: str,
                              checking: Execution):
        log_prefix = "Checking {} on case {} ".format(solution,
                                                      testcase).ljust(50)
        has_custom_checker = self.task.checker
        custom_checker_state = CustomCheckerState(solution)
        self.printer.text(log_prefix + "WAITING\n")

        def notifyStartChecking():
            self.printer.text(log_prefix + "START\n")
            self.testing[solution].testcase_results[subtask][
                testcase] = TestcaseSolutionResult.CHECKING
            self.running[log_prefix] = time.monotonic()

        def getResultChecking(result: Result):
            del self.running[log_prefix]
            if has_custom_checker:
                if result.status == ResultStatus.SUCCESS:
                    self.printer.green(log_prefix + "SUCCESS\n")
                    custom_checker_state.set_result(result)
                else:
                    self.printer.red(log_prefix +
                                     "FAIL: {}\n".format(result.status))
            else:
                self.printer.green(log_prefix + "SUCCESS\n")
                self.testing[solution].update_default_check_result(
                    subtask, testcase, result)

        def skippedChecking():
            self.printer.yellow(log_prefix + "SKIPPED\n")

        def getStdout(stdout):
            custom_checker_state.set_stdout(stdout)

        def getStderr(stderr):
            custom_checker_state.set_stderr(stderr)

        def customCheckerResult():
            self.testing[solution].update_custom_check_result(
                subtask, testcase, custom_checker_state)

        if has_custom_checker:
            custom_checker_state.set_callback(customCheckerResult)
            checking.stdout(False).getContentsAsString(getStdout)
            checking.stderr(False).getContentsAsString(getStderr)
        checking.notifyStart(notifyStartChecking)
        checking.getResult(getResultChecking, skippedChecking)