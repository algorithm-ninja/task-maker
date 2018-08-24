#!/usr/bin/env python3
from typing import List

from task_maker.formats import Task
from task_maker.printer import StdoutPrinter
from task_maker.task_maker_frontend import ResultStatus
from task_maker.uis import result_to_str
from task_maker.uis.ioi import IOIUIInterface, SourceFileCompilationResult, \
    SourceFileCompilationStatus
from task_maker.uis.ioi_curses_ui import print_solutions_result

LIMITS_MARGIN = 0.8


class IOIFinishUI:
    def __init__(self, task: Task, interface: IOIUIInterface):
        self.task = task
        self.interface = interface
        self.printer = StdoutPrinter()

    def print(self):
        self.printer.bold("Task: ")
        self.printer.text(self.task.name + "\n")
        self.printer.text("\n")

        self.printer.blue("Compilations:\n", bold=True)
        self.printer.blue("Non solution files\n", bold=False)
        max_sol_len = max(
            map(
                len,
                list(self.interface.non_solutions.keys()) + list(
                    self.interface.solutions.keys())))
        for non_solution, result in self.interface.non_solutions.items():
            self._print_compilation(non_solution, result, max_sol_len)
        self.printer.blue("Solutions\n", bold=False)
        for solution, result in self.interface.solutions.items():
            self._print_compilation(solution, result, max_sol_len)
        self.printer.text("\n")

        self.printer.blue("Generation:\n", bold=True)
        generated = self._print_generation()
        self.printer.text("\n")

        if generated:
            self.printer.blue("Evaluation:\n", bold=True)
            for solution in self.interface.testing:
                self._print_solution(solution)
                self.printer.text("\n")
            self.printer.text("\n")

        self.printer.blue("Summary:\n", bold=True)
        print_solutions_result(self.printer, self.task, self.interface.testing,
                               max_sol_len, "?")

        if sorted(self.interface.warnings):
            self.printer.text("\n")
            self.printer.yellow("Warnings:\n", bold=True)
            for warning in self.interface.warnings:
                self.printer.text("- " + warning + "\n")

        if sorted(self.interface.errors):
            self.printer.text("\n")
            self.printer.red("Errors:\n", bold=True)
            for error in self.interface.errors:
                self.printer.text("- " + error + "\n")

    def _print_compilation(self, solution: str,
                           result: SourceFileCompilationResult,
                           max_sol_len: int):
        if result.status == SourceFileCompilationStatus.DONE:
            self.printer.green(
                "{:<{len}}    OK  ".format(solution, len=max_sol_len),
                bold=True)
        else:
            self.printer.red(
                "{:<{len}}   FAIL ".format(solution, len=max_sol_len),
                bold=True)
        if result.need_compilation:
            if not result.result:
                self.printer.text("  UNKNOWN")
            else:
                if result.result.status != ResultStatus.INTERNAL_ERROR and \
                        result.result.status != ResultStatus.MISSING_FILES and \
                        result.result.status != ResultStatus.MISSING_EXECUTABLE:
                    self.printer.text(" {:>6.3f}s | {:>5.1f}MiB".format(
                        result.result.resources.cpu_time +
                        result.result.resources.sys_time,
                        result.result.resources.memory / 1024))
                if result.result.status == ResultStatus.RETURN_CODE:
                    self.printer.text(
                        " | Exited with %d" % result.result.return_code)
                elif result.result.status == ResultStatus.SIGNAL:
                    self.printer.text(
                        " | Killed with signal %d" % result.result.signal)
                elif result.result.status == ResultStatus.INTERNAL_ERROR:
                    self.printer.text(
                        "  Internal error %s" % result.result.error)
                elif result.result.status == ResultStatus.MISSING_FILES:
                    self.printer.text("  Missing files")
                elif result.result.status == ResultStatus.MISSING_EXECUTABLE:
                    self.printer.text("  " + result.result.error)
                elif result.result.status == ResultStatus.SUCCESS:
                    pass
                else:
                    self.printer.text("  " + result.result.status)
        self.printer.text("\n")
        if result.stderr:
            self.printer.text(result.stderr)

    def _print_generation(self):
        success = True
        for st_num, subtask in self.interface.subtasks.items():
            self.printer.bold("Subtask {}: ".format(st_num))
            self.printer.text("{} points\n".format(
                int(self.task.subtasks[st_num].max_score)))

            for tc_num, result in subtask.items():
                self.printer.text("#{:<2}  ".format(tc_num))
                if result.generation_result:
                    if result.generation_result.status == ResultStatus.SUCCESS:
                        self.printer.green("Generated")
                        self.printer.text(" | ")
                    else:
                        self.printer.red("Generation failed ")
                        self.printer.red(
                            result_to_str(result.generation_result),
                            bold=False)
                        success = False
                else:
                    self.printer.green("Copied")
                    self.printer.text(" | ")

                if result.validation_result:
                    if result.validation_result.status == ResultStatus.SUCCESS:
                        self.printer.green("Validated")
                        self.printer.text(" | ")
                    else:
                        self.printer.red("Validation failed ")
                        self.printer.red(
                            result_to_str(result.validation_result),
                            bold=False)
                        success = False

                if result.solution_result:
                    if result.solution_result.status == ResultStatus.SUCCESS:
                        self.printer.green("Solved")
                    else:
                        self.printer.red("Solution failed ")
                        self.printer.red(
                            result_to_str(result.solution_result), bold=False)
                        success = False

                self.printer.text("\n")
        return success

    def _print_solution(self, solution: str):
        self.printer.bold(solution)
        self.printer.text(": ")
        status = self.interface.testing[solution]
        max_score = sum(st.max_score for st in self.task.subtasks.values())
        self._print_score(status.score, max_score,
                          status.subtask_scores.values())
        self.printer.text("\n")
        if self.interface.solutions[
                solution].status == SourceFileCompilationStatus.FAILURE:
            self.printer.red("Skipped due to compilation failure", bold=False)
            self.printer.right("[{}]".format(solution))
            return

        for (st_num, subtask), st_score, subtask_info in zip(
                status.testcase_results.items(),
                status.subtask_scores.values(), self.task.subtasks.values()):
            self.printer.bold("Subtask #{}: ".format(st_num))
            self._print_score(st_score, subtask_info.max_score,
                              [tc.score for tc in subtask.values()])
            self.printer.text("\n")
            for tc_num, testcase in subtask.items():
                self.printer.text("{:>3}) ".format(tc_num))
                if testcase.score == 0.0:
                    self.printer.red(
                        "[{:.2}]".format(testcase.score), bold=False)
                elif testcase.score == 1.0:
                    self.printer.green(
                        "[{:.2}]".format(testcase.score), bold=False)
                else:
                    self.printer.yellow(
                        "[{:.2}]".format(testcase.score), bold=False)

                if testcase.result:
                    used_time = testcase.result.resources.cpu_time + \
                                testcase.result.resources.sys_time
                    memory = testcase.result.resources.memory / 1024
                else:
                    used_time = 0
                    memory = 0
                self.printer.text(" [")
                if used_time >= LIMITS_MARGIN * self.task.time_limit:
                    self.printer.yellow(
                        "{:.3f}s".format(used_time), bold=False)
                else:
                    self.printer.text("{:.3f}s".format(used_time))
                self.printer.text(" |")
                if memory >= LIMITS_MARGIN * self.task.memory_limit_kb / 1024:
                    self.printer.yellow(
                        "{:5.1f}MiB".format(memory), bold=False)
                else:
                    self.printer.text("{:5.1f}MiB".format(memory))
                self.printer.text("] ")

                self.printer.text(testcase.message)
                self.printer.right("[{}]".format(solution))

    def _print_score(self, score: float, max_score: float,
                     individual: List[float]):
        if score == 0.0 and not all(individual):
            self.printer.red("{:.2f} / {:.2f}".format(score, max_score))
        elif score == max_score and all(individual):
            self.printer.green("{:.2f} / {:.2f}".format(score, max_score))
        else:
            self.printer.yellow("{:.2f} / {:.2f}".format(score, max_score))
