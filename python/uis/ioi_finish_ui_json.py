#!/usr/bin/env python3
import json
from task_maker.config import Config
from task_maker.task_maker_frontend import ResultStatus, Result, Resources
from task_maker.uis import FinishUI, SourceFileCompilationResult
from task_maker.uis.ioi import IOIUIInterface, TestcaseGenerationResult, \
    SolutionStatus
from typing import Any, Optional, Dict


def _enum_to_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    return str(val).split(".")[-1]


def _resources_to_dict(res: Optional[Resources]) -> Optional[dict]:
    if res is None:
        return None
    return {
        "cpu_time": res.cpu_time,
        "sys_time": res.sys_time,
        "wall_time": res.wall_time,
        "memory": res.memory
    }


def _result_to_dict(res: Optional[Result]) -> Optional[dict]:
    if res is None:
        return None
    return {
        "status":
            _enum_to_str(res.status),
        "signal":
            res.signal if res.status == ResultStatus.SIGNAL else None,
        "return_code":
            res.return_code if res.status == ResultStatus.RETURN_CODE else None,
        "error":
            res.error if res.status == ResultStatus.INTERNAL_ERROR else None,
        "resources":
            _resources_to_dict(res.resources),
        "was_cached":
            res.was_cached,
        "was_killed":
            res.was_killed
    }


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
            "task": {
                "name": self.task.name,
                "title": self.task.title
            },
            "subtasks": self._get_subtasks(),
            "solutions": self._get_compilations(self.interface.solutions),
            "non_solutions":
                self._get_compilations(self.interface.non_solutions),
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
            "status": _enum_to_str(testcase.status),
            "generation_result": _result_to_dict(testcase.generation_result),
            "generation_stderr": testcase.generation_stderr,
            "validation_result": _result_to_dict(testcase.validation_result),
            "validation_stderr": testcase.validation_stderr,
            "solution_result": _result_to_dict(testcase.solution_result),
            "solution_stderr": testcase.solution_stderr
        }

    def _get_compilations(self, files: Dict[str, SourceFileCompilationResult]):
        return {
            name: {
                "status": _enum_to_str(compilation.status),
                "stderr": compilation.stderr,
                "result": _result_to_dict(compilation.result)
            }
            for name, compilation in files.items()
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
                [_enum_to_str(res) for res in solution.subtask_results],
            "testcase_results": {
                st_num: {
                    tc_num: {
                        "status":
                            _enum_to_str(testcase.status),
                        "result":
                            [_result_to_dict(res) for res in testcase.result],
                        "score":
                            testcase.score,
                        "message":
                            testcase.message,
                        "checker_outcome":
                            testcase.checker_outcome,
                        "checker_result":
                            _result_to_dict(testcase.checker_result)
                    }
                    for tc_num, testcase in subtask.items()
                }
                for st_num, subtask in solution.testcase_results.items()
            }
        }
