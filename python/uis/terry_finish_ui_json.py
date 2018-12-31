#!/usr/bin/env python3
import json
from task_maker.config import Config
from task_maker.uis import FinishUI, result_to_str
from task_maker.uis.ioi_finish_ui_json import get_compilations, enum_to_str
from task_maker.uis.terry import TerryUIInterface, SolutionInfo


def get_solution(solution: SolutionInfo):
    return {
        "name": solution.source_file.name,
        "path": solution.source_file.path,
        "language": solution.source_file.language.name,
        "status": enum_to_str(solution.status),
        "seed": solution.seed,
        "score": solution.score,
        "message": solution.message,
        "generation_result": result_to_str(solution.gen_result),
        "generation_stderr": solution.gen_stderr,
        "validation_result": result_to_str(solution.val_result),
        "validation_stderr": solution.val_stderr,
        "solution_result": result_to_str(solution.sol_result),
        "solution_stderr": solution.sol_stderr,
        "checker_result": result_to_str(solution.check_result),
        "checker_stderr": solution.check_stderr,
        "testcases_status":
            [enum_to_str(s) for s in solution.testcases_status]
    }


class TerryFinishUIJSON(FinishUI):
    """
    FinishUI in JSON for Terry-like tasks
    """

    def __init__(self, config: Config, interface: TerryUIInterface):
        super().__init__(config, interface)
        self.task = interface.task

    def print(self):
        res = {
            "action": "terry-result",
            "task": self.task.to_dict(),
            "solutions": get_compilations(self.interface.solutions),
            "non_solutions": get_compilations(self.interface.non_solutions),
            "testing": self._get_testing()
        }
        print(json.dumps(res))

    def print_summary(self):
        pass

    def _get_testing(self):
        return {
            name: get_solution(solution)
            for name, solution in self.interface.solutions_info.items()
        }
