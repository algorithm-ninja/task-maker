#!/usr/bin/env python3
from task_maker.config import Config
from task_maker.printer import CursesPrinter
from task_maker.uis import CursesUI, get_max_sol_len
from task_maker.uis.ioi_curses_ui import print_compilation_status
from task_maker.uis.terry import TerryUIInterface, SolutionInfo, \
    SolutionStatus, TestcaseStatus


def print_terry_solution_info(printer: CursesPrinter, solution: str,
                              info: SolutionInfo, max_sol_len: int,
                              loading: str, max_score: float):
    """
    Print the status of a solution, including the name and what it's doing.
    This can be called also if the evaluation has ended.
    """
    printer.text("{:>{len}} ".format(solution, len=max_sol_len))
    if info.status == SolutionStatus.WAITING:
        printer.text(" ... ")
    elif info.status == SolutionStatus.FAILED:
        printer.red(" FAIL", bold=True)
        printer.text(" {}".format(info.message))
    elif info.status == SolutionStatus.DONE:
        score = info.score * max_score
        if score == 0.0:
            printer.red("{:^5.0f}".format(score), bold=True)
        elif score == max_score:
            printer.green("{:^5.0f}".format(score), bold=True)
        else:
            printer.yellow("{:^5.0f}".format(score), bold=True)
    else:
        printer.text("  {}   ".format(loading))
        if info.status == SolutionStatus.GENERATING:
            printer.text("Generating")
        elif info.status == SolutionStatus.GENERATED:
            printer.text("Generated")
        elif info.status == SolutionStatus.VALIDATING:
            printer.text("Validating")
        elif info.status == SolutionStatus.VALIDATED:
            printer.text("Validated")
        elif info.status == SolutionStatus.SOLVING:
            printer.text("Solving")
        elif info.status == SolutionStatus.SOLVED:
            printer.text("Solved")
        elif info.status == SolutionStatus.CHECKING:
            printer.text("Checking")

    if info.status == SolutionStatus.DONE:
        for status in info.testcases_status:
            if status == TestcaseStatus.MISSING:
                printer.bold(" m")
            elif status == TestcaseStatus.CORRECT:
                printer.green(" c")
            else:
                printer.red(" w")
    printer.text("\n")


class TerryCursesUI(CursesUI):
    """
    UIInterface for Terry-like tasks
    """
    def __init__(self, config: Config, interface: TerryUIInterface):
        super().__init__(config, interface)

    def _loop(self, printer: CursesPrinter, loading: str):
        task_name = self.interface.task.name
        if self.config.bulk_number is not None:
            task_name += " [%d / %d]" % (self.config.bulk_number + 1,
                                         self.config.bulk_total)

        printer.bold("Running... %s\n" % task_name)
        printer.text("\n")

        max_sol_len = get_max_sol_len(self.interface)

        printer.blue("Compilation:\n", bold=True)
        for name, result in self.interface.non_solutions.items():
            print_compilation_status(printer, name, max_sol_len, loading,
                                     result.status)
        printer.text("\n")
        for name, result in self.interface.solutions.items():
            print_compilation_status(printer, name, max_sol_len, loading,
                                     result.status)
        printer.text("\n")

        for solution, info in self.interface.solutions_info.items():
            print_terry_solution_info(printer, solution, info, max_sol_len,
                                      loading, self.interface.task.max_score)

        printer.text("\n")

        self._print_running_tasks(printer)
