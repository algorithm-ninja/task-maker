#!/usr/bin/env python3

import json
from enum import Enum
from task_maker.formats import TerryTask
from task_maker.remote import Execution
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import Result, ResultStatus
from task_maker.uis import UIInterface, result_to_str
from typing import Optional, Dict, List


class SolutionStatus(Enum):
    """
    Status of the evaluation of a solution
    """
    WAITING = 0  # the evaluation is pending
    GENERATING = 1  # the input file is generating
    GENERATED = 2  # the input file has been generated
    VALIDATING = 3  # the input file is validating
    VALIDATED = 4  # the input file has been validated
    SOLVING = 5  # the solution has started
    SOLVED = 6  # the solution ended well
    CHECKING = 7  # the checker is running
    DONE = 8  # the checker has done
    FAILED = 9  # the evaluation failed


class TestcaseStatus(Enum):
    """
    Outcome of a testcase from a solution
    """
    MISSING = 0  # the solution didn't answered the testcase
    CORRECT = 1  # the solution answered well
    WRONG = 2  # the solution didn't answered well


class SolutionInfo:
    """
    Information about a solution and it's evaluation
    """

    def __init__(self, source_file: SourceFile):
        self.status = SolutionStatus.WAITING
        # each solution can be evaluated with different seeds
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
        self.source_file = source_file
        self.testcases_status = []  # type: List[TestcaseStatus]


class TerryUIInterface(UIInterface):
    """
    Terry-like task variant of the UI interface
    """

    def __init__(self, task: TerryTask, do_print: bool, json: bool):
        super().__init__(task, do_print, json)
        self.task = task
        self.solutions_info = dict()  # type: Dict[str, SolutionInfo]

    def add_solution(self, source_file: SourceFile):
        super().add_solution(source_file)
        self.solutions_info[source_file.name] = SolutionInfo(source_file)

    def add_generation(self, solution: str, seed: int, generation: Execution):
        """
        Start tracking the generation of a testcase
        """
        info = self.solutions_info[solution]
        info.seed = seed

        def on_start():
            info.status = SolutionStatus.GENERATING

        def on_done(result: Result):
            info.gen_result = result
            info.gen_stderr = generation.stderr_content
            if result.status == ResultStatus.SUCCESS:
                info.status = SolutionStatus.GENERATED
            else:
                self.add_error(
                    "Failed to generate input for {} with seed {}".format(
                        solution, seed))
                info.status = SolutionStatus.FAILED
                info.message = "Generator failed: " + result_to_str(result)

        generation.bind(on_done, on_start)

    def add_validation(self, solution: str, validation: Execution):
        """
        Start tracking the validation of a testcase
        """
        info = self.solutions_info[solution]

        def on_start():
            info.status = SolutionStatus.VALIDATING

        def on_done(result: Result):
            info.val_result = result
            info.val_stderr = validation.stderr_content
            if result.status == ResultStatus.SUCCESS:
                info.status = SolutionStatus.VALIDATED
            else:
                self.add_error(
                    "Failed to validate input for {}".format(solution))
                info.status = SolutionStatus.FAILED
                info.message = "Validator failed: " + result_to_str(result)

        validation.bind(on_done, on_start)

    def add_solving(self, solution: str, solving: Execution):
        """
        Start tracking the evaluation of a solution
        """
        info = self.solutions_info[solution]

        def on_start():
            info.status = SolutionStatus.SOLVING

        def on_done(result: Result):
            info.sol_result = result
            info.sol_stderr = solving.stderr_content
            if result.status == ResultStatus.SUCCESS:
                info.status = SolutionStatus.SOLVED
            else:
                self.add_error("Solution {} failed".format(solution))
                info.status = SolutionStatus.FAILED
                info.message = "Solution failed: " + result_to_str(result)

        solving.bind(on_done, on_start)

    def add_checking(self, solution: str, checking: Execution):
        """
        Start the tracking of a checker
        """
        info = self.solutions_info[solution]

        def on_start():
            info.status = SolutionStatus.CHECKING

        def on_done(result: Result):
            info.check_result = result
            info.check_stderr = checking.stderr_content
            self._compute_score(solution, checking.stdout_content)
            self.ui_printer.terry_solution_outcome(solution, info)
            if result.status == ResultStatus.SUCCESS:
                info.status = SolutionStatus.DONE
            else:
                self.add_error(
                    "Checker failed on output of solution {}".format(solution))
                info.status = SolutionStatus.FAILED
                info.message = "Checker failed: " + result_to_str(result)

        checking.bind(on_done, on_start)

    def _compute_score(self, solution: str, check_outcome: str):
        """
        Process the checker's outcome and compute the score of a solution
        """
        info = self.solutions_info[solution]
        try:
            outcome = json.loads(check_outcome)
        except json.JSONDecodeError as ex:
            info.message = "Checker's output is not valid json: {}".format(ex)
            return

        score = outcome.get("score")
        if score is None or not 0.0 <= score <= 1.0:
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
