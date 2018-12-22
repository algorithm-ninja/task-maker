#!/usr/bin/env python3
import time

from enum import Enum
from task_maker.formats import IOITask, ScoreMode
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import Execution, Result, ResultStatus
from task_maker.uis import result_to_str, UIInterface
from typing import List, Dict, Optional, Callable


class TestcaseGenerationStatus(Enum):
    """
    Status of the generation of a testcase
    """
    WAITING = 0  # waiting to start
    GENERATING = 1  # started generation of the testcase
    GENERATED = 2  # the testcase has been generated
    VALIDATING = 3  # started validation of the testcase
    VALIDATED = 4  # the testcase has been validated
    SOLVING = 5  # started the solution
    DONE = 6  # the solution ended correctly
    FAILURE = 7  # the process of generation failed


class TestcaseSolutionStatus(Enum):
    """
    Status of a solution in a testcase
    """
    WAITING = 0  # waiting to start
    SOLVING = 1  # started the evaluation
    SOLVED = 2  # evaluation ended but the checker didn't start nor finished
    CHECKING = 3  # the checker started
    ACCEPTED = 4  # the solution scored 100%
    WRONG_ANSWER = 5  # the solution scored 0%
    PARTIAL = 6  # the solution scored some points
    FAILED = 7  # the solution or the checker failed
    SKIPPED = 8  # the execution was skipped


class SubtaskSolutionResult(Enum):
    """
    Status of the evaluation of a subtask
    """
    WAITING = 0  # the subtask evaluation has not yet started
    RUNNING = 1  # the subtask evaluation has started
    ACCEPTED = 2  # all the testcases have been solved
    PARTIAL = 3  # some testcases have been solved and the score is positive
    REJECTED = 4  # the score of the subtask is zero


class TestcaseSolutionInfo:
    """
    Information about a solution of a testcase
    """

    def __init__(self):
        # to be considered definitive only if checked == True
        self.status = TestcaseSolutionStatus.WAITING
        self.result = []  # type: List[Result]
        self.score = 0.0
        self.message = "Waiting..."
        self.checker_outcome = "Waiting..."
        self.checked = False
        self.checker_result = None  # type: Result


class TestcaseGenerationResult:
    """
    Information about the generation of a testcase
    """

    def __init__(self):
        self.status = TestcaseGenerationStatus.WAITING
        self.generation_result = None  # type: Result
        self.generation_stderr = ""
        self.validation_result = None  # type: Result
        self.validation_stderr = ""
        self.solution_result = None  # type: Result
        self.solution_stderr = ""


class CustomCheckerState:
    """
    State of a custom checker in a testcase
    """

    def __init__(self, solution: str):
        self.solution = solution
        self.result = None  # type: Result
        self.stdout = None  # type: str
        self.stderr = None  # type: str
        self.callback = None  # type: Optional[Callable[[], None]]

    def set_result(self, result: Result):
        self.result = result
        self._check()

    def set_stdout(self, stdout: str):
        self.stdout = stdout
        self._check()

    def set_stderr(self, stderr: str):
        self.stderr = stderr
        self._check()

    def set_callback(self, callback: Callable[[], None]):
        """
        The callback will be called when the checker has done and all the
        information are ready
        """
        self.callback = callback
        self._check()

    def _check(self):
        if self.result is not None and self.stdout is not None and \
                self.stderr is not None and self.callback is not None:
            self.callback()


class SolutionStatus:
    """
    Task status of a solution, this is the source of truth for the evaluation of
    a solution
    """

    def __init__(self, source_file: SourceFile, task: IOITask,
                 interface: "IOIUIInterface", subtasks: Dict[int, List[int]]):
        self.interface = interface
        self.source_file = source_file
        self.task = task
        self.score = 0.0
        self.subtask_scores = dict((st_num, 0.0) for st_num in subtasks)
        self.subtask_results = [SubtaskSolutionResult.WAITING] * len(subtasks)
        self.testcase_results = dict(
        )  # type: Dict[int, Dict[int, TestcaseSolutionInfo]]

        for st_num, subtask in subtasks.items():
            self.testcase_results[st_num] = dict()
            for tc_num in subtask:
                self.testcase_results[st_num][tc_num] = TestcaseSolutionInfo()

    def update_eval_result(self, subtask: int, testcase: int, result: Result,
                           num: int):
        """
        Set the result of the evaluation of a testcase. In case of communication
        task num is the process number of the evaluator.
        """
        self.subtask_results[subtask] = SubtaskSolutionResult.RUNNING
        testcase_status = self.testcase_results[subtask][testcase]
        testcase_status.result[num] = result
        self._update_eval_result_internal(subtask, testcase)

    def _update_eval_result_internal(self, subtask: int, testcase: int):
        testcase_status = self.testcase_results[subtask][testcase]
        # do anything only when all the executions end
        if not all(res for res in testcase_status.result):
            return
        if all(res.status == ResultStatus.SUCCESS
               for res in testcase_status.result):
            # if the checker came first do not overwrite
            if testcase_status.status not in [
                    TestcaseSolutionStatus.ACCEPTED,
                    TestcaseSolutionStatus.PARTIAL,
                    TestcaseSolutionStatus.WRONG_ANSWER,
                    TestcaseSolutionStatus.FAILED
            ]:
                testcase_status.status = TestcaseSolutionStatus.SOLVED
        else:
            # if one execution fails overwrite the checker response, if any
            testcase_status.status = TestcaseSolutionStatus.FAILED
            testcase_status.checked = True
            self._compute_st_score(subtask)
        testcase_status.message = self._get_solution_message(testcase_status)

    def update_default_check_result(self, subtask: int, testcase: int,
                                    result: Result):
        """
        Set the result of the default checker (diff) of a testcase
        """
        # the default checker is used only in batch type tasks, no need for
        # communication's out-of-order callbacks
        testcase_status = self.testcase_results[subtask][testcase]
        testcase_status.checker_result = result
        testcase_status.checked = True
        if result.status == ResultStatus.SUCCESS:
            testcase_status.status = TestcaseSolutionStatus.ACCEPTED
            testcase_status.checker_outcome = "Output is correct"
            self.testcase_results[subtask][testcase].score = 1.0
        elif result.status == ResultStatus.RETURN_CODE:
            testcase_status.status = TestcaseSolutionStatus.WRONG_ANSWER
            testcase_status.checker_outcome = "Output is not correct"
            self.testcase_results[subtask][testcase].score = 0.0
        else:
            testcase_status.status = TestcaseSolutionStatus.FAILED
            testcase_status.checker_outcome = "Internal error: " + result.error

        testcase_status.message = self._get_solution_message(testcase_status)
        self._compute_st_score(subtask)

    def update_custom_check_result(self, subtask: int, testcase: int,
                                   state: CustomCheckerState):
        """
        Set the result of the custom checker of a testcase
        """
        # premise: this can be called before update_eval_result on
        # communication or even between difference calls of it.
        # assumption: this method may safely assume that all the next executions
        # will end successfully. If else update_eval_result will overwrite the
        # result later
        testcase_status = self.testcase_results[subtask][testcase]
        testcase_status.checker_result = state.result
        # if the solution failed there is no need for the checker
        if testcase_status.checked:
            return
        if state.result.status != ResultStatus.SUCCESS:
            testcase_status.status = TestcaseSolutionStatus.FAILED
            testcase_status.checker_outcome = "Failed to check: " + \
                                              result_to_str(state.result)
            testcase_status.message = self._get_solution_message(
                testcase_status)
            testcase_status.checked = True
            return
        stdout = state.stdout.strip()
        try:
            score = float(stdout)
        except ValueError:
            testcase_status.status = TestcaseSolutionStatus.FAILED
            testcase_status.checker_outcome = \
                "Failed to check: invalid score: {}".format(stdout)
            testcase_status.message = self._get_solution_message(
                testcase_status)
            testcase_status.checked = True
            self.interface.add_error("Invalid output '{}' for checker "
                                     "at testcase #{} for solution {}".format(
                                         stdout, testcase,
                                         self.source_file.name))
            return
        if not 0.0 <= score <= 1.0:
            testcase_status.status = TestcaseSolutionStatus.FAILED
            testcase_status.checker_outcome = \
                "Failed to check: invalid score: {}".format(stdout)
            testcase_status.message = self._get_solution_message(
                testcase_status)
            testcase_status.checked = True
            self.interface.add_error("Invalid score '{}' from checker "
                                     "at testcase #{} for solution {}".format(
                                         stdout, testcase,
                                         self.source_file.name))
            return
        self.testcase_results[subtask][testcase].score = score
        if score == 1.0:
            testcase_status.status = TestcaseSolutionStatus.ACCEPTED
            testcase_status.checker_outcome = "Output is correct"
        elif score == 0.0:
            testcase_status.status = TestcaseSolutionStatus.WRONG_ANSWER
            testcase_status.checker_outcome = "Output is not correct"
        else:
            testcase_status.status = TestcaseSolutionStatus.PARTIAL
            testcase_status.checker_outcome = "Output is partially correct"
        if stdout:
            testcase_status.checker_outcome = state.stderr.strip()
        testcase_status.message = self._get_solution_message(testcase_status)
        testcase_status.checked = all(res for res in testcase_status.result)
        self._compute_st_score(subtask)

    def _compute_st_score(self, subtask: int):
        # skip if not all the testcases have been computed
        if not all(t.checked for t in self.testcase_results[subtask].values()):
            return
        scores = [t.score for t in self.testcase_results[subtask].values()]
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

    def _get_solution_message(self,
                              testcase_status: TestcaseSolutionInfo) -> str:
        if all(res.status == ResultStatus.SUCCESS
               for res in testcase_status.result):
            return testcase_status.checker_outcome

        return " | ".join(map(result_to_str, testcase_status.result))


class IOIUIInterface(UIInterface):
    """
    IOI-like task variant of the UI interface
    """

    def __init__(self, task: IOITask, testcases: Dict[int, List[int]],
                 do_print: bool, json: bool):
        super().__init__(task, do_print, json)

        self.task = task
        self.subtasks = dict(
        )  # type: Dict[int, Dict[int, TestcaseGenerationResult]]
        self.testcases = testcases
        self.testing = dict()  # type: Dict[str, SolutionStatus]

        for st_num, subtask in testcases.items():
            self.subtasks[st_num] = dict()
            for tc_num in subtask:
                self.subtasks[st_num][tc_num] = TestcaseGenerationResult()

    def add_solution(self, source_file: SourceFile):
        super().add_solution(source_file)
        self.testing[source_file.name] = SolutionStatus(
            source_file, self.task, self, self.testcases)

    def add_generation(self, subtask: int, testcase: int,
                       generation: Execution):
        """
        Start tacking the generation of a testcase
        """
        log_prefix = "Generation of input {} of subtask {} ".format(
            testcase, subtask).ljust(50)
        testcase_status = self.subtasks[subtask][testcase]
        self.ui_printer.generation(testcase, subtask, "WAITING")

        def notifyStartGeneration():
            self.ui_printer.generation(testcase, subtask, "START")
            testcase_status.status = TestcaseGenerationStatus.GENERATING
            self.running[log_prefix] = time.monotonic()

        def getResultGeneration(result: Result):
            del self.running[log_prefix]
            testcase_status.generation_result = result
            if result.status == ResultStatus.SUCCESS:
                self.ui_printer.generation(
                    testcase, subtask, "SUCCESS", cached=result.was_cached)
                testcase_status.status = TestcaseGenerationStatus.GENERATED
            else:
                self.add_error("Failed to generate testcase #%d" % testcase)
                self.ui_printer.generation(
                    testcase,
                    subtask,
                    "FAIL",
                    data=result.status,
                    cached=result.was_cached)
                testcase_status.status = TestcaseGenerationStatus.FAILURE

        def skippedGeneration():
            self.ui_printer.generation(testcase, subtask, "SKIPPED")

        def getStderr(stderr):
            self.ui_printer.generation(testcase, subtask, "STDERR", stderr)
            testcase_status.generation_stderr = stderr

        generation.stderr(False).getContentsAsString(getStderr)
        generation.notifyStart(notifyStartGeneration)
        generation.getResult(getResultGeneration, skippedGeneration)

    def add_validation(self, subtask: int, testcase: int,
                       validation: Execution):
        """
        Start tracking the validation of a testcase
        """
        log_prefix = "Validation of input {} of subtask {} ".format(
            testcase, subtask).ljust(50)
        testcase_status = self.subtasks[subtask][testcase]
        self.ui_printer.validation(testcase, subtask, "WAITING")

        def notifyStartValidation():
            self.ui_printer.validation(testcase, subtask, "START")
            testcase_status.status = TestcaseGenerationStatus.VALIDATING
            self.running[log_prefix] = time.monotonic()

        def getResultValidation(result: Result):
            del self.running[log_prefix]
            testcase_status.validation_result = result
            if result.status == ResultStatus.SUCCESS:
                self.ui_printer.validation(
                    testcase, subtask, "SUCCESS", cached=result.was_cached)
                testcase_status.status = TestcaseGenerationStatus.VALIDATED
            else:
                self.add_error("Failed to validate testcase #%d" % testcase)
                self.ui_printer.validation(
                    testcase,
                    subtask,
                    "FAIL",
                    data=result.status,
                    cached=result.was_cached)
                testcase_status.status = TestcaseGenerationStatus.FAILURE

        def skippedValidation():
            self.ui_printer.validation(testcase, subtask, "SKIPPED")

        def getStderr(stderr):
            self.ui_printer.validation(
                testcase, subtask, "STDERR", data=stderr)
            testcase_status.validation_stderr = stderr

        validation.stderr(False).getContentsAsString(getStderr)
        validation.notifyStart(notifyStartValidation)
        validation.getResult(getResultValidation, skippedValidation)

    def add_solving(self, subtask: int, testcase: int, solving: Execution):
        """
        Start tracking the execution of the official solution on a testcase
        """
        log_prefix = "Generation of output {} of subtask {} ".format(
            testcase, subtask).ljust(50)
        testcase_status = self.subtasks[subtask][testcase]
        self.ui_printer.solving(testcase, subtask, "WAITING")

        def notifyStartSolving():
            self.ui_printer.solving(testcase, subtask, "START")
            testcase_status.status = TestcaseGenerationStatus.SOLVING
            self.running[log_prefix] = time.monotonic()

        def getResultSolving(result: Result):
            del self.running[log_prefix]
            testcase_status.solution_result = result
            if result.status == ResultStatus.SUCCESS:
                self.ui_printer.solving(
                    testcase, subtask, "SUCCESS", cached=result.was_cached)
                testcase_status.status = TestcaseGenerationStatus.DONE
            else:
                self.add_error(
                    "Failed to generate output of testcase #%d" % testcase)
                self.ui_printer.solving(
                    testcase,
                    subtask,
                    "FAIL",
                    data=result.status,
                    cached=result.was_cached)
                testcase_status.status = TestcaseGenerationStatus.FAILURE

        def skippedSolving():
            self.ui_printer.solving(testcase, subtask, "SKIPPED")

        def getStderr(stderr):
            self.ui_printer.solving(testcase, subtask, "STDERR", data=stderr)
            testcase_status.solution_stderr = stderr

        solving.stderr(False).getContentsAsString(getStderr)
        solving.notifyStart(notifyStartSolving)
        solving.getResult(getResultSolving, skippedSolving)

    def add_evaluate_solution(self, subtask: int, testcase: int, solution: str,
                              evaluations: List[Execution]):
        """
        Start tracking the evaluation of a solution on a testcase
        """
        self.testing[solution].testcase_results[subtask][testcase].result = [
                                                                                None
                                                                            ] * len(
            evaluations)
        started = False
        skipped = False
        num_processes = len(evaluations)
        for num, evaluation in enumerate(evaluations):
            if len(evaluations) == 1:
                log_prefix = "Evaluate {} on case {} ".format(
                    solution, testcase).ljust(50)
            else:
                log_prefix = "Evaluate {}/{} on case {} ".format(
                    solution, num, testcase).ljust(50)
            self.ui_printer.evaluate(solution, num, num_processes, testcase,
                                     subtask, "WAITING")

            def notifyStartEvaluation():
                nonlocal started
                self.ui_printer.evaluate(solution, num, num_processes,
                                         testcase, subtask, "START")
                if not started and not skipped:
                    self.testing[solution].testcase_results[subtask][
                        testcase].status = TestcaseSolutionStatus.SOLVING
                    started = True
                self.running[log_prefix] = time.monotonic()

            def getResultEvaluation(result: Result):
                del self.running[log_prefix]
                if result.status == ResultStatus.SUCCESS:
                    self.ui_printer.evaluate(
                        solution,
                        num,
                        num_processes,
                        testcase,
                        subtask,
                        "SUCCESS",
                        cached=result.was_cached)
                else:
                    self.ui_printer.evaluate(
                        solution,
                        num,
                        num_processes,
                        testcase,
                        subtask,
                        "FAIL",
                        data=result.status,
                        cached=result.was_cached)

                self.testing[solution].update_eval_result(
                    subtask, testcase, result, num)

            def skippedEvaluation():
                nonlocal skipped
                skipped = True
                self.testing[solution].testcase_results[subtask][
                    testcase].status = TestcaseSolutionStatus.SKIPPED
                self.ui_printer.evaluate(solution, num, num_processes,
                                         testcase, subtask, "SKIPPED")

            evaluation.notifyStart(notifyStartEvaluation)
            evaluation.getResult(getResultEvaluation, skippedEvaluation)

    def add_evaluate_checking(self, subtask: int, testcase: int, solution: str,
                              checking: Execution):
        """
        Start tracking the checking of a solution in a testcase
        """
        log_prefix = "Checking {} on case {} ".format(solution,
                                                      testcase).ljust(50)
        has_custom_checker = self.task.checker
        custom_checker_state = CustomCheckerState(solution)
        self.ui_printer.checking(solution, testcase, subtask, "WAITING")

        def notifyStartChecking():
            self.ui_printer.checking(solution, testcase, subtask, "START")
            self.testing[solution].testcase_results[subtask][
                testcase].status = TestcaseSolutionStatus.CHECKING
            self.running[log_prefix] = time.monotonic()

        def getResultChecking(result: Result):
            del self.running[log_prefix]
            if has_custom_checker:
                custom_checker_state.set_result(result)
                if result.status == ResultStatus.SUCCESS:
                    self.ui_printer.checking(
                        solution,
                        testcase,
                        subtask,
                        "SUCCESS",
                        cached=result.was_cached)
                else:
                    self.add_error(
                        "Checker failed for testcase #%d for solution %s" %
                        (testcase, solution))
                    self.ui_printer.checking(
                        solution,
                        testcase,
                        subtask,
                        "FAIL",
                        data=result.status,
                        cached=result.was_cached)
            else:
                self.ui_printer.checking(
                    solution,
                    testcase,
                    subtask,
                    "SUCCESS",
                    cached=result.was_cached)
                self.testing[solution].update_default_check_result(
                    subtask, testcase, result)
                self.ui_printer.testcase_outcome(
                    solution, testcase, subtask,
                    self.testing[solution].testcase_results[subtask][testcase])

        def skippedChecking():
            self.ui_printer.checking(solution, testcase, subtask, "SKIPPED")

        def getStdout(stdout):
            custom_checker_state.set_stdout(stdout)

        def getStderr(stderr):
            custom_checker_state.set_stderr(stderr)

        def customCheckerResult():
            self.testing[solution].update_custom_check_result(
                subtask, testcase, custom_checker_state)
            self.ui_printer.testcase_outcome(
                solution, testcase, subtask,
                self.testing[solution].testcase_results[subtask][testcase])

        if has_custom_checker:
            custom_checker_state.set_callback(customCheckerResult)
            checking.stdout(False).getContentsAsString(getStdout)
            checking.stderr(False).getContentsAsString(getStderr)
        checking.notifyStart(notifyStartChecking)
        checking.getResult(getResultChecking, skippedChecking)
