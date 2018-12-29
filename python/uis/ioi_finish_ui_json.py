#!/usr/bin/env python3
import json
from task_maker.config import Config
from task_maker.uis import FinishUI
from task_maker.uis.ioi import IOIUIInterface, TestcaseGenerationResult, \
    SolutionStatus
from task_maker.utils import get_compilations, enum_to_str, result_to_dict, \
    get_execution


class IOIFinishUIJSON(FinishUI):
    """
    FinishUI in JSON for IOI-like tasks
    """

    def __init__(self, config: Config, interface: IOIUIInterface):
        super().__init__(config, interface)
        self.task = interface.task

    def print(self):
        res = {
            "action": "result",
            "task": self.task.to_dict(),
            "subtasks": self._get_subtasks(),
            "solutions": get_compilations(self.interface.solutions),
            "non_solutions": get_compilations(self.interface.non_solutions),
            "testing": self._get_testing(),
            "warnings": self.interface.warnings,
            "errors": self.interface.errors
        }
        print(json.dumps(res))

    def print_summary(self):
        pass

    def _get_subtasks(self):
        return {
            st_num: {
                tc_num: self._get_testcase(testcase)
                for tc_num, testcase in subtask.items()
            }
            for st_num, subtask in self.interface.subtasks.items()
        }

    def _get_testcase(self, testcase: TestcaseGenerationResult):
        return {
            "status": enum_to_str(testcase.status),
            "generation": get_execution(testcase.generation),
            "validation": get_execution(testcase.validation),
            "solution": get_execution(testcase.solution)
        }

    def _get_testing(self):
        return {
            name: self._get_solution(solution)
            for name, solution in self.interface.testing.items()
        }

    def _get_solution(self, solution: SolutionStatus):
        return {
            "name":
                solution.source_file.name,
            "path":
                solution.source_file.path,
            "language":
                solution.source_file.language.name,
            "score":
                solution.score,
            "subtask_scores":
                solution.subtask_scores,
            "subtask_results":
                [enum_to_str(res) for res in solution.subtask_results],
            "testcase_results": {
                st_num: {
                    tc_num: {
                        "status":
                            enum_to_str(testcase.status),
                        "result":
                            [result_to_dict(res) for res in testcase.result],
                        "score":
                            testcase.score,
                        "message":
                            testcase.message,
                        "checker_outcome":
                            testcase.checker_outcome,
                        "checker_result":
                            result_to_dict(testcase.checker_result)
                    }
                    for tc_num, testcase in subtask.items()
                }
                for st_num, subtask in solution.testcase_results.items()
            }
        }
