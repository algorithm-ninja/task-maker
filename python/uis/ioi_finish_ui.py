#!/usr/bin/env python3

from task_maker.config import Config
from task_maker.task_maker_frontend import ResultStatus
from task_maker.uis import result_to_str, FinishUI, get_max_sol_len, \
    SourceFileCompilationStatus
from task_maker.uis.ioi import IOIUIInterface, TestcaseGenerationStatus
from task_maker.uis.ioi_curses_ui import print_solutions_result


class IOIFinishUI(FinishUI):
    """
    FinishUI for IOI-like tasks
    """

    def __init__(self, config: Config, interface: IOIUIInterface):
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
        if self.interface.statements:
            self.printer.blue("Statements\n", bold=False)
            for name, statement in self.interface.statements.items():
                self._print_statement(name, statement, max_sol_len)
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
        self.print_summary()

        self.print_final_messages()

    def print_summary(self):
        max_sol_len = get_max_sol_len(self.interface)
        print_solutions_result(self.printer, self.task, self.interface.testing,
                               max_sol_len, "?")

    def _print_generation(self):
        success = True
        for st_num, subtask in self.interface.subtasks.items():
            self.printer.bold("Subtask {}: ".format(st_num))
            self.printer.text("{} points".format(
                int(self.task.subtasks[st_num].max_score)))
            subtask_info = self.task.subtasks[st_num]
            if subtask_info.name:
                self.printer.text(" [{}]".format(subtask_info.name))
            self.printer.text("\n")
            if subtask_info.description:
                self.printer.text(subtask_info.description + "\n")
            for constraint in subtask_info.constraints:
                self.printer.text("- {}\n".format(str(constraint)))

            for tc_num, result in subtask.items():
                self.printer.text("#{:<2}  ".format(tc_num))
                if result.generation and result.generation.result:
                    if result.generation.result.status == ResultStatus.SUCCESS:
                        self.printer.green("Generated")
                    else:
                        self.printer.red("Generation failed ")
                        self.printer.red(
                            result_to_str(result.generation.result),
                            bold=False)
                        self.printer.text("\n" +
                                          result.generation.stderr_content)
                        success = False
                else:
                    if result.status == TestcaseGenerationStatus.FAILURE:
                        self.printer.red("Failed")
                    else:
                        self.printer.green("Copied")

                if result.validation and result.validation.result:
                    self.printer.text(" | ")
                    if result.validation.result.status == ResultStatus.SUCCESS:
                        self.printer.green("Validated")
                    else:
                        self.printer.red("Validation failed ")
                        self.printer.red(
                            result_to_str(result.validation.result),
                            bold=False)
                        self.printer.text("\n" +
                                          result.validation.stderr_content)
                        success = False

                if result.solution and result.solution.result:
                    self.printer.text(" | ")
                    if result.solution.result.status == ResultStatus.SUCCESS:
                        self.printer.green("Solved")
                    else:
                        self.printer.red("Solution failed ")
                        self.printer.red(
                            result_to_str(result.solution.result), bold=False)
                        self.printer.text("\n" +
                                          result.solution.stderr_content)
                        success = False

                self.printer.text("\n")
        return success

    def _print_solution(self, solution: str):
        self.printer.bold(solution)
        self.printer.text(": ")
        status = self.interface.testing[solution]
        max_score = sum(st.max_score for st in self.task.subtasks.values())
        self._print_score(status.score, max_score, [
            tc.score for st in status.testcase_results.values()
            for tc in st.values()
        ])
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
            if subtask_info.name:
                self.printer.text(" [{}]".format(subtask_info.name))
            self.printer.text("\n")
            for tc_num, testcase in subtask.items():
                self.printer.text("{:>3}) ".format(tc_num))
                if testcase.score == 0.0:
                    self.printer.red(
                        "[{:.2f}]".format(testcase.score), bold=False)
                elif testcase.score == 1.0:
                    self.printer.green(
                        "[{:.2f}]".format(testcase.score), bold=False)
                else:
                    self.printer.yellow(
                        "[{:.2f}]".format(testcase.score), bold=False)

                if all(res for res in testcase.result):
                    used_time = sum(r.resources.cpu_time + r.resources.sys_time
                                    for r in testcase.result)
                    memory = sum(r.resources.memory
                                 for r in testcase.result) / 1024
                else:
                    used_time = 0
                    memory = 0
                self._print_exec_stat(used_time, memory, self.task.time_limit,
                                      self.task.memory_limit_kb, "")
                if self.config.detailed_checker and testcase.checker_result:
                    self._print_resources(testcase.checker_result.resources,
                                          self.task.time_limit * 2,
                                          self.task.memory_limit_kb * 2,
                                          "checker")

                self.printer.text(" ")
                self.printer.text(testcase.message)
                self.printer.right("[{}]".format(solution))
