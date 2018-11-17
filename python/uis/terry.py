#!/usr/bin/env python3
from enum import Enum
import json
import time
from typing import Optional, Dict, List

from task_maker.formats import TerryTask
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import Execution, Result, ResultStatus
from task_maker.uis import UIInterface, result_to_str


class SolutionStatus(Enum):
    WAITING = 0
    GENERATING = 1
    GENERATED = 2
    VALIDATING = 3
    VALIDATED = 4
    SOLVING = 5
    SOLVED = 6
    CHECKING = 7
    DONE = 8
    FAILED = 9


class TestcaseStatus(Enum):
    MISSING = 0
    CORRECT = 1
    WRONG = 2


class SolutionInfo:
    def __init__(self):
        self.status = SolutionStatus.WAITING
        self.seed = None
        self.gen_result = None  # type: Optional[Result]
        self.val_result = None  # type: Optional[Result]
        self.sol_result = None  # type: Optional[Result]
        self.check_result = None  # type: Optional[Result]
        self.gen_stderr = ""
        self.val_stderr = ""
        self.sol_stderr = ""
        self.check_stderr = ""
        self.score = 0.0
        self.message = ""
        self.testcases_status = []  # type: List[TestcaseStatus]


class TerryUIInterface(UIInterface):
    def __init__(self, task: TerryTask, do_print: bool):
        super().__init__(task, do_print)
        self.task = task
        self.solutions_info = dict()  # type: Dict[str, SolutionInfo]

    def add_solution(self, source_file: SourceFile):
        super().add_solution(source_file)
        self.solutions_info[source_file.name] = SolutionInfo()

    def add_generation(self, solution: str, seed: int, generation: Execution):
        log_prefix = "Generation of input for {} with seed {} ".format(
            solution, seed).ljust(50)
        info = self.solutions_info[solution]
        info.seed = seed
        self.printer.text(log_prefix + "WAITING\n")

        def notify_start():
            self.printer.text(log_prefix + "START\n")
            info.status = SolutionStatus.GENERATING
            self.running[log_prefix] = time.monotonic()

        def get_result(result: Result):
            del self.running[log_prefix]
            info.gen_result = result
            cached = " [cached]" if result.was_cached else ""
            if result.status == ResultStatus.SUCCESS:
                self.printer.green(log_prefix + "SUCCESS" + cached + "\n")
                info.status = SolutionStatus.GENERATED
            else:
                self.add_error(
                    "Failed to generate input for {} with seed {}".format(
                        solution, seed))
                self.printer.red(log_prefix +
                                 "FAIL: {} {}\n".format(result.status, cached))
                info.status = SolutionStatus.FAILED
                info.message = "Generator failed: " + result_to_str(result)

        def skipped():
            self.printer.red(log_prefix + "SKIPPED\n")

        def get_stderr(stderr: str):
            if stderr:
                self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")
            info.gen_stderr = stderr

        generation.stderr(False).getContentsAsString(get_stderr)
        generation.notifyStart(notify_start)
        generation.getResult(get_result, skipped)

    def add_validation(self, solution: str, validation: Execution):
        log_prefix = "Validation of input for {} ".format(solution).ljust(50)
        info = self.solutions_info[solution]
        self.printer.text(log_prefix + "WAITING\n")

        def notify_start():
            self.printer.text(log_prefix + "START\n")
            info.status = SolutionStatus.VALIDATING
            self.running[log_prefix] = time.monotonic()

        def get_result(result: Result):
            del self.running[log_prefix]
            info.val_result = result
            cached = " [cached]" if result.was_cached else ""
            if result.status == ResultStatus.SUCCESS:
                self.printer.green(log_prefix + "SUCCESS" + cached + "\n")
                info.status = SolutionStatus.VALIDATED
            else:
                self.add_error(
                    "Failed to validate input for {}".format(solution))
                self.printer.red(log_prefix +
                                 "FAIL: {} {}\n".format(result.status, cached))
                info.status = SolutionStatus.FAILED
                info.message = "Validator failed: " + result_to_str(result)

        def skipped():
            self.printer.red(log_prefix + "SKIPPED\n")

        def get_stderr(stderr: str):
            if stderr:
                self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")
            info.val_stderr = stderr

        validation.stderr(False).getContentsAsString(get_stderr)
        validation.notifyStart(notify_start)
        validation.getResult(get_result, skipped)

    def add_solving(self, solution: str, solving: Execution):
        log_prefix = "Running solution {} ".format(solution).ljust(50)
        info = self.solutions_info[solution]
        self.printer.text(log_prefix + "WAITING\n")

        def notify_start():
            self.printer.text(log_prefix + "START\n")
            info.status = SolutionStatus.SOLVING
            self.running[log_prefix] = time.monotonic()

        def get_result(result: Result):
            del self.running[log_prefix]
            info.sol_result = result
            cached = " [cached]" if result.was_cached else ""
            if result.status == ResultStatus.SUCCESS:
                self.printer.green(log_prefix + "SUCCESS" + cached + "\n")
                info.status = SolutionStatus.SOLVED
            else:
                self.add_error("Solution {} failed".format(solution))
                self.printer.red(log_prefix +
                                 "FAIL: {} {}\n".format(result.status, cached))
                info.status = SolutionStatus.FAILED
                info.message = "Solution failed: " + result_to_str(result)

        def skipped():
            self.printer.red(log_prefix + "SKIPPED\n")

        def get_stderr(stderr: str):
            if stderr:
                self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")
            info.sol_stderr = stderr

        solving.stderr(False).getContentsAsString(get_stderr)
        solving.notifyStart(notify_start)
        solving.getResult(get_result, skipped)

    def add_checking(self, solution: str, checking: Execution):
        log_prefix = "Checking output of solution {} ".format(solution).ljust(
            50)
        info = self.solutions_info[solution]
        self.printer.text(log_prefix + "WAITING\n")

        def notify_start():
            self.printer.text(log_prefix + "START\n")
            info.status = SolutionStatus.CHECKING
            self.running[log_prefix] = time.monotonic()

        def get_result(result: Result):
            del self.running[log_prefix]
            info.check_result = result
            cached = " [cached]" if result.was_cached else ""
            if result.status == ResultStatus.SUCCESS:
                self.printer.green(log_prefix + "SUCCESS" + cached + "\n")
                info.status = SolutionStatus.DONE
            else:
                self.add_error(
                    "Checker failed on output of solution {}".format(solution))
                self.printer.red(log_prefix +
                                 "FAIL: {} {}\n".format(result.status, cached))
                info.status = SolutionStatus.FAILED
                info.message = "Checker failed: " + result_to_str(result)

        def skipped():
            self.printer.red(log_prefix + "SKIPPED\n")

        def get_stderr(stderr: str):
            if stderr:
                self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")
            info.check_stderr = stderr

        def get_stdout(stdout: str):
            self._compute_score(solution, stdout)

        checking.stderr(False).getContentsAsString(get_stderr)
        checking.stdout(False).getContentsAsString(get_stdout)
        checking.notifyStart(notify_start)
        checking.getResult(get_result, skipped)

    def _compute_score(self, solution: str, check_outcome: str):
        info = self.solutions_info[solution]
        try:
            outcome = json.loads(check_outcome)
        except json.JSONDecodeError as ex:
            info.message = "Checker's output is not valid json: {}".format(ex)
            return

        score = outcome.get("score")
        if not 0.0 <= score <= 1.0:
            info.message = "Score is not in [0.0, 1.0]: {}".format(score)
            return
        info.score = score
        for val, feedback in zip(outcome["validation"]["cases"],
                                 outcome["feedback"]["cases"]):
            # TODO store the checker messages somewhere
            # (val["message"], feedback["message"])
            if val["status"] == "missing":
                info.testcases_status.append(TestcaseStatus.MISSING)
            elif feedback["correct"]:
                info.testcases_status.append(TestcaseStatus.CORRECT)
            else:
                info.testcases_status.append(TestcaseStatus.WRONG)
