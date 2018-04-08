#!/usr/bin/env python3

import curses
import signal
import threading
from typing import List
from typing import Optional

from proto.event_pb2 import EventStatus, EvaluationResult, WAITING, RUNNING, \
    FAILURE, GENERATING, GENERATED, VALIDATING, VALIDATED, EXECUTING, \
    EXECUTED, CHECKING, SOLVING, DONE, MISSING, CORRECT, WRONG

from python.printer import Printer, CursesPrinter, StdoutPrinter
from python.uis.silent_ui import SilentUI, SolutionStatus


class CursesUI(SilentUI):
    def __init__(self, solutions: List[str], format: str) -> None:
        super().__init__(solutions, format)
        self._max_sol_len = max(map(len, solutions))
        self._done = False
        self._stopped = False
        self._failure = None  # type: Optional[str]
        self._ui_thread = threading.Thread(target=curses.wrapper,
                                           args=(self._ui,))
        self._ui_thread.start()

    def set_compilation_status(self, file_name: str, status: EventStatus,
                               warnings: Optional[str] = None,
                               from_cache: bool = False):
        super().set_compilation_status(file_name, status, warnings,
                                       from_cache)
        self._max_sol_len = max(self._max_sol_len, len(file_name))

    # pylint: disable=no-self-use
    def _print_compilation_status(self, name: str, status: EventStatus,
                                  loading: str, printer: Printer):
        if status == WAITING:
            printer.text("...")
        elif status == RUNNING:
            printer.bold(loading)
        elif status == DONE:
            printer.green("OK")
        elif status == FAILURE:
            printer.red("FAILURE")
        else:
            printer.red(EventStatus.Name(status))
        if name in self._compilation_cache:
            printer.text("  [cached]")
        printer.text("\n")

    # pylint: enable=no-self-use

    def _print_compilation(self, sources: List[str], loading: str,
                           printer: Printer) -> None:
        for comp in sorted(sources):
            printer.text("%{}s: ".format(self._max_sol_len) % comp)
            self._print_compilation_status(comp, self._compilation_status[comp],
                                           loading, printer)

    def _print_generation_status(self, printer: Printer) -> None:
        for subtask in sorted(self._subtask_testcases):
            if subtask > 0:
                printer.text("|")
            for testcase in sorted(self._subtask_testcases[subtask]):
                status = self._generation_status.get(testcase, -1)
                if status == WAITING:
                    printer.text(".")
                elif status == GENERATING:
                    printer.blue("g")
                elif status == GENERATED:
                    printer.text("G")
                elif status == VALIDATING:
                    printer.blue("v")
                elif status == VALIDATED:
                    printer.text("V")
                elif status == SOLVING:
                    printer.blue("s")
                elif status == DONE:
                    printer.green("S")
                elif status == FAILURE:
                    printer.red("F")
                else:
                    printer.text(".")

    def _print_subtasks_scores(self, status: SolutionStatus, loading: str,
                               printer: Printer) -> None:
        if not status.subtask_scores:
            printer.text("% 4s" % "...")
        elif status.score is not None:
            if status.score == self.max_score:
                printer.bold("% 4.f" % status.score)
            else:
                printer.text("% 4.f" % status.score)
        else:
            printer.bold("% 4s" % loading)

        for subtask in sorted(self._subtask_max_scores):
            testcases = self._subtask_testcases[subtask]
            if all(tc not in status.testcase_status
                   or status.testcase_status[tc] == WAITING
                   for tc in testcases):
                printer.text(" % 4s" % "...")
            elif subtask in status.subtask_scores:
                if self._subtask_max_scores[subtask] == \
                        status.subtask_scores[subtask]:
                    printer.bold(" % 4.f" % status.subtask_scores[subtask])
                else:
                    printer.text(" % 4.f" % status.subtask_scores[subtask])
            else:
                printer.bold(" % 4s" % loading)

    def _print_terry_solution_row(self, solution, status, printer,
                                  loading_char):
        printer.text("%{}s: ".format(self._max_sol_len) % solution)
        if status.status != DONE and status.status != FAILURE:
            printer.text("  %s   " % loading_char)

        if status.status == WAITING:
            printer.text("...")
        elif status.status == GENERATING:
            printer.blue("generating")
        elif status.status == GENERATED:
            printer.text("generated")
        elif status.status == VALIDATING:
            printer.blue("validating")
        elif status.status == VALIDATED:
            printer.text("validated")
        elif status.status == EXECUTING:
            printer.blue("executing")
        elif status.status == EXECUTED:
            printer.text("executed")
        elif status.status == CHECKING:
            printer.blue("checking")
        elif status.status == DONE:
            printer.text("%2d/%2d " % (status.result.score * self.max_score,
                                       self.max_score))
            for testcase in status.result.testcases:
                if testcase == MISSING:
                    printer.text("m ")
                elif testcase == CORRECT:
                    printer.green("c ")
                elif testcase == WRONG:
                    printer.red("w ")
        elif status.status == FAILURE:
            printer.red("      FAIL")
        else:
            raise ValueError("Invalid status: ", status.status)
        printer.text("\n")

    def _ioi_ui(self, pad, printer, stdscr) -> None:
        loading_chars = "-\\|/"
        cur_loading_char = 0
        pos_x, pos_y = 0, 0
        while not self._done and not self._stopped and self._failure is None:
            max_y, max_x = stdscr.getmaxyx()
            cur_loading_char = (cur_loading_char + 1) % len(loading_chars)
            loading = loading_chars[cur_loading_char]
            pad.clear()

            printer.bold("Running... %s\n" % self.task_name)

            printer.text("Time limit: %.2f\n" % self._time_limit)
            printer.text("Memory limit: %.2f\n" % (self._memory_limit / 1024))

            self._print_compilation(self._other_compilations, loading, printer)
            printer.text("\n")

            printer.blue("Generation status: ")
            self._print_generation_status(printer)
            printer.text("\n")
            printer.text("\n")

            printer.blue("Evaluation")
            printer.bold("%s total" % (" " * (self._max_sol_len + 4)))
            for max_score in self._subtask_max_scores.values():
                printer.bold("% 4.f " % max_score)
            printer.text("\n")

            for sol in sorted(self.solutions):
                printer.text("%{}s: ".format(self._max_sol_len) % sol)
                if sol not in self._compilation_status or \
                        self._compilation_status[sol] == WAITING:
                    printer.text("....")
                elif self._compilation_status[sol] == RUNNING:
                    printer.bold("  " + loading + " ")
                elif self._compilation_status[sol] == DONE:
                    printer.green(" OK ")
                    printer.text(
                        " % 3d/%d  " %
                        (len(self._solution_status[sol].testcase_result),
                         self._num_testcases))
                    self._print_subtasks_scores(self._solution_status[sol],
                                                loading, printer)
                else:
                    printer.red("FAIL")
                printer.text("\n")
            printer.text("\n")
            printer.blue("Running tasks:\n")
            for task in self._running_tasks:
                printer.text(
                    "  %s -- %ds\n" % (task.description, task.duration))
            try:
                pressed_key = stdscr.getkey()
                if pressed_key == "KEY_UP":
                    pos_y -= 1
                elif pressed_key == "KEY_DOWN":
                    pos_y += 1
                elif pressed_key == "KEY_LEFT":
                    pos_x -= 1
                elif pressed_key == "KEY_RIGHT":
                    pos_x += 1
                pos_x = max(pos_x, 0)
                pos_y = max(pos_y, 0)
            except curses.error:
                pass

            pad.refresh(pos_y, pos_x, 0, 0, max_y - 1, max_x - 1)

    def _terry_ui(self, pad, printer, stdscr):
        loading_chars = "-\\|/"
        cur_loading_char = 0
        pos_x, pos_y = 0, 0
        while not self._done and not self._stopped and self._failure is None:
            max_y, max_x = stdscr.getmaxyx()
            cur_loading_char = (cur_loading_char + 1) % len(loading_chars)
            loading = loading_chars[cur_loading_char]
            pad.clear()

            printer.bold("Running... %s\n" % self.task_name)

            self._print_compilation(self._other_compilations, loading, printer)
            printer.text("\n")

            printer.blue("Testing\n")
            for solution, status in sorted(self._terry_test_status.items()):
                self._print_terry_solution_row(solution, status, printer,
                                               loading)

            printer.text("\n")
            printer.blue("Running tasks:\n")
            for task in self._running_tasks:
                printer.text(
                    "  %s -- %ds\n" % (task.description, task.duration))
            try:
                pressed_key = stdscr.getkey()
                if pressed_key == "KEY_UP":
                    pos_y -= 1
                elif pressed_key == "KEY_DOWN":
                    pos_y += 1
                elif pressed_key == "KEY_LEFT":
                    pos_x -= 1
                elif pressed_key == "KEY_RIGHT":
                    pos_x += 1
                pos_x = max(pos_x, 0)
                pos_y = max(pos_y, 0)
            except curses.error:
                pass

            pad.refresh(pos_y, pos_x, 0, 0, max_y - 1, max_x - 1)

    def _ui(self, stdscr: 'curses._CursesWindow') -> None:
        if hasattr(signal, 'pthread_sigmask'):
            signal.pthread_sigmask(signal.SIG_BLOCK, [signal.SIGINT])
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, curses.COLORS):
            curses.init_pair(i, i, -1)
        curses.halfdelay(1)

        pad = curses.newpad(1000, 1000)
        printer = CursesPrinter(pad)

        if self.format == "ioi":
            self._ioi_ui(pad, printer, stdscr)
        elif self.format == "terry":
            self._terry_ui(pad, printer, stdscr)
        else:
            raise NotImplementedError()

        curses.endwin()
        if self._stopped:
            print(self._stopped)

    def _ioi_final_status(self, printer: StdoutPrinter):
        printer.blue("Solutions\n")

        def print_testcase(sol: str, testcase: int,
                           tc_status: EvaluationResult, max_time: float,
                           max_mem: float) -> None:
            printer.text("%3d) " % testcase)
            if tc_status.score == 1.0:
                printer.green("[%.2f] " % tc_status.score, bold=False)
            else:
                printer.red("[%.2f] " % tc_status.score, bold=False)
            printer.text("[")
            if tc_status.cpu_time_used >= max_time * 0.9:
                printer.bold("%5.3fs" % tc_status.cpu_time_used)
            else:
                printer.text("%5.3fs" % tc_status.cpu_time_used)
            printer.text(" |")
            if tc_status.memory_used_kb >= max_mem * 0.9:
                printer.bold("%5.1fMiB" % (tc_status.memory_used_kb / 1024))
            else:
                printer.text("%5.1fMiB" % (tc_status.memory_used_kb / 1024))
            printer.text("] %s" % tc_status.message)
            if (sol, testcase) in self._evaluation_cache:
                printer.text(" [cached]")
            printer.right("[%s]" % sol)

        if self._generation_cache:
            printer.text("%d/%d inputs and outputs come from the cache\n\n" % (
                len(self._generation_cache), self._num_testcases))

        for sol in sorted(self._solution_status):
            status = self._solution_status[sol]
            printer.bold("%s: " % sol)
            if status.score is None:
                printer.red("not available\n")
            elif status.score == self.max_score:
                printer.green("%.2f / %.2f\n" % (status.score, self.max_score),
                              bold=False)
            else:
                printer.text("%.2f / %.2f\n" % (status.score, self.max_score))

            if sol in self._compilation_errors:
                printer.red("Compilation errors\n")
                printer.text(self._compilation_errors[sol])
                printer.text("\n")

            if status.score is None:
                continue

            for num, subtask in sorted(self._subtask_testcases.items()):
                if num not in status.subtask_scores:
                    printer.text("Subtask #%d: " % (num + 1))
                    printer.red("skipped\n")
                    continue
                if status.subtask_scores[num] == self._subtask_max_scores[num]:
                    printer.bold("Subtask #%d: %.2f/%.2f\n" %
                                 (num + 1, status.subtask_scores[num],
                                  self._subtask_max_scores[num]))
                else:
                    printer.text("Subtask #%d: %.2f/%.2f\n" %
                                 (num + 1, status.subtask_scores[num],
                                  self._subtask_max_scores[num]))

                max_time = max(status.testcase_result[testcase].cpu_time_used
                               for testcase in subtask)
                max_mem = max(status.testcase_result[testcase].memory_used_kb
                              for testcase in subtask)
                for testcase in sorted(subtask):
                    if testcase not in status.testcase_result:
                        printer.text("%3d) " % testcase)
                        printer.red("skipped\n")
                        continue
                    tc_status = status.testcase_result[testcase]
                    print_testcase(sol, testcase, tc_status, max_time, max_mem)

            printer.text("\n")

        printer.blue("Scores")
        printer.bold("%s total" % (" " * (self._max_sol_len - 4)))
        for num, max_score in sorted(self._subtask_max_scores.items()):
            printer.bold("% 4.f " % max_score)
        printer.text("\n")

        for sol in sorted(self.solutions):
            printer.text("%{}s:  ".format(self._max_sol_len) % sol)
            self._print_subtasks_scores(self._solution_status[sol], "?",
                                        printer)
            printer.text("\n")

    def _terry_final_status(self, printer):
        printer.blue("Solutions\n")

        def print_phase_stats(phase, cpu_time, wall_time, memory_kb, cached):
            # type: (str, float, float, float, bool) -> None
            printer.text("%10s: %.3fs | %.3fs | %.1fMiB%s\n"
                         % (phase, cpu_time, wall_time, memory_kb / 1024,
                            " [cached]" if cached else ""))

        for solution, status in sorted(self._terry_test_status.items()):
            result = status.result
            printer.bold(solution + "\n")
            if status.status == DONE:
                print_phase_stats("Generation", result.gen_cpu_time,
                                  result.gen_wall_time, result.gen_memory_kb,
                                  solution in self._terry_generation_cache)
                print_phase_stats("Evaluation", result.eval_cpu_time,
                                  result.eval_wall_time, result.eval_memory_kb,
                                  solution in self._terry_evaluation_cache)
                print_phase_stats("Check", result.check_cpu_time,
                                  result.check_wall_time,
                                  result.check_memory_kb,
                                  solution in self._terry_check_cache)
                printer.text("%10s: %s\n" % ("Seed", result.seed))
            if solution in self._compilation_errors:
                printer.red("Compilation errors\n")
                printer.text(self._compilation_errors[solution])
            if status.errors and status.errors.strip():
                printer.red("Errors\n")
                printer.text(status.errors.strip())
            printer.text("\n")

        printer.blue("Summary\n")
        for solution, status in sorted(self._terry_test_status.items()):
            self._print_terry_solution_row(solution, status, printer, "?")

    def print_final_status(self) -> None:
        self._done = True
        self._ui_thread.join()

        printer = StdoutPrinter()

        printer.blue("Compilation\n")
        self._print_compilation(self._other_compilations, "?", printer)
        printer.text("\n")
        self._print_compilation(self.solutions, "?", printer)
        printer.text("\n")

        if self.format == "ioi":
            self._ioi_final_status(printer)
        elif self.format == "terry":
            self._terry_final_status(printer)
        else:
            raise NotImplementedError()

        if self._generation_errors:
            printer.red("\nGeneration errors\n")
            printer.blue("Generation summary: ")
            self._print_generation_status(printer)
            printer.text("\n")
            for testcase, error in self._generation_errors.items():
                printer.bold("Testcase %d\n" % testcase)
                printer.text(error)
                printer.text("\n")

        if self._failure:
            printer.red("Fatal error\n")
            printer.red(self._failure)
            printer.text("\n")
            return

    def fatal_error(self, msg: str) -> None:
        if not self._failure:
            self._failure = msg
        else:
            self._failure += "\n" + msg

    def stop(self, msg: str) -> None:
        self._stopped = msg
