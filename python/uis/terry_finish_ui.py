#!/usr/bin/env python3
from task_maker.config import Config
from task_maker.uis import FinishUI, get_max_sol_len
from task_maker.uis.terry import TerryUIInterface, SolutionInfo
from task_maker.uis.terry_curses_ui import print_terry_solution_info


class TerryFinishUI(FinishUI):
    """
    FinishUI for Terry-like tasks
    """

    def __init__(self, config: Config, interface: TerryUIInterface):
        super().__init__(config, interface)
        self.task = interface.task

    def print(self):
        self.printer.bold("Task: ")
        self.printer.text(self.task.name + "\n")
        self.printer.text("\n")

        self.printer.blue("Compilations:\n", bold=True)
        self.printer.blue("Non solution files\n", bold=False)
        max_sol_len = get_max_sol_len(self.interface)
        for non_solution, result in self.interface.non_solutions.items():
            self._print_compilation(non_solution, result, max_sol_len)
        self.printer.blue("Solutions\n", bold=False)
        for solution, result in self.interface.solutions.items():
            self._print_compilation(solution, result, max_sol_len)
        self.printer.text("\n")

        self.printer.blue("Evaluations\n", bold=True)
        for solution in self.interface.solutions_info:
            self._print_solution(solution)
            self.printer.text("\n")

        self.printer.blue("Summary\n", bold=True)
        self.print_summary()

        self.print_final_messages()

    def print_summary(self):
        max_sol_len = get_max_sol_len(self.interface)
        for solution in self.interface.solutions_info:
            self._print_summary_row(solution, max_sol_len)

    def _print_solution(self, solution: str):
        info = self.interface.solutions_info[solution]  # type: SolutionInfo
        score = self.task.max_score * info.score

        self.printer.bold(solution)
        self.printer.text(" ")
        self._print_score(score, self.task.max_score, [score])
        self.printer.text("\n")

        self.printer.text("{:>10}: {}\n".format("Seed", info.seed))
        self.printer.text("{:>10}:".format("Generation"))
        if info.generation.result:
            self._print_resources(info.generation.result.resources)
        self.printer.text("\n")
        if info.generation.stderr_content:
            self.printer.text(info.generation.stderr_content)

        if self.task.validator and info.validation.result:
            self.printer.text("{:>10}:".format("Validation"))
            self._print_resources(info.validation.result.resources)
            self.printer.text("\n")
            if info.validation.stderr_content:
                self.printer.text(info.validation.stderr_content)

        if info.solution.result:
            self.printer.text("{:>10}:".format("Evaluation"))
            self._print_resources(info.solution.result.resources)
            self.printer.text("\n")
            if info.solution.stderr_content:
                self.printer.text(info.solution.stderr_content)

        if info.checking.result:
            self.printer.text("{:>10}:".format("Checker"))
            self._print_resources(info.checking.result.resources)
            self.printer.text("\n")
        if info.message:
            self.printer.text("{:>10}: ".format("Message"))
            self.printer.red(info.message, bold=False)
            self.printer.text("\n")
        if info.checking.stderr_content:
            self.printer.text(info.checking.stderr_content)

    def _print_summary_row(self, solution: str, max_sol_len: int):
        info = self.interface.solutions_info[solution]  # type: SolutionInfo
        print_terry_solution_info(self.printer, solution, info, max_sol_len,
                                  "?", self.task.max_score)
