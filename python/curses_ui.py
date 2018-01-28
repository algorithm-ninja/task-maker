#!/usr/bin/env python3

import curses
import signal
import threading
from typing import List
from typing import Optional

from proto.event_pb2 import EventStatus, EvaluationResult, WAITING, RUNNING, \
    FAILURE, GENERATING, GENERATED, VALIDATING, VALIDATED, SOLVING, DONE

from python.silent_ui import SilentUI, SolutionStatus


class Printer:
    def text(self, what: str) -> None:
        pass

    def red(self, what: str, bold: bool = True) -> None:
        pass

    def green(self, what: str, bold: bool = True) -> None:
        pass

    def blue(self, what: str, bold: bool = True) -> None:
        pass

    def bold(self, what: str, bold: bool = True) -> None:
        pass


class StdoutPrinter(Printer):
    def __init__(self) -> None:
        def _get_color(color: int) -> str:
            return curses.tparm(curses.tigetstr("setaf"), color).decode("utf8")

        self.bold_fmt = curses.tparm(curses.tigetstr("bold")).decode()
        if curses.COLORS >= 256:
            self.green_fmt = _get_color(82)
        else:
            self.green_fmt = _get_color(curses.COLOR_GREEN)
        self.red_fmt = _get_color(curses.COLOR_RED)
        self.blue_fmt = _get_color(curses.COLOR_BLUE)
        self.reset_fmt = curses.tparm(curses.tigetstr("sgr0")).decode()
        self.right_fmt = curses.tparm(curses.tigetstr("cuf"), 1000).decode()

    # pylint: disable=no-self-use
    def left_fmt(self, amount: int) -> str:
        return curses.tparm(curses.tigetstr("cub"), amount).decode()

    # pylint: enable=no-self-use

    def text(self, what: str) -> None:
        print(what, end="")

    def red(self, what: str, bold: bool = True) -> None:
        print(
            self.red_fmt + (self.bold_fmt
                            if bold else "") + what + self.reset_fmt,
            end="")

    def green(self, what: str, bold: bool = True) -> None:
        print(
            self.green_fmt + (self.bold_fmt
                              if bold else "") + what + self.reset_fmt,
            end="")

    def blue(self, what: str, bold: bool = True) -> None:
        print(
            self.blue_fmt + (self.bold_fmt
                             if bold else "") + what + self.reset_fmt,
            end="")

    def bold(self, what: str, bold: bool = True) -> None:
        print(self.bold_fmt + what + self.reset_fmt, end="")

    def right(self, what: str) -> None:
        print(self.right_fmt + self.left_fmt(len(what) - 1) + what)


class CursesPrinter(Printer):
    def __init__(self, stdscr: 'curses._CursesWindow') -> None:
        self.stdscr = stdscr
        self.bold_fmt = curses.A_BOLD
        if curses.COLORS >= 256:
            self.green_fmt = curses.color_pair(82)
        else:
            self.green_fmt = curses.color_pair(curses.COLOR_GREEN)
        self.red_fmt = curses.color_pair(curses.COLOR_RED)
        self.blue_fmt = curses.color_pair(curses.COLOR_BLUE)

    def text(self, what: str) -> None:
        self.stdscr.addstr(what)

    def red(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what, self.red_fmt | (self.bold_fmt if bold else 0))

    def green(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what, self.green_fmt | (self.bold_fmt
                                                   if bold else 0))

    def blue(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what, self.blue_fmt | (self.bold_fmt
                                                  if bold else 0))

    def bold(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what, self.bold_fmt)


class CursesUI(SilentUI):
    def __init__(self, solutions: List[str]) -> None:
        super().__init__(solutions)
        self._max_sol_len = max(map(len, solutions))
        self._done = False
        self._failure = None  # type: Optional[str]
        self._ui_thread = threading.Thread(target=curses.wrapper,
                                           args=(self._ui,))
        self._ui_thread.start()

    def set_compilation_status(self,
                               file_name: str,
                               status: EventStatus,
                               warnings: Optional[str] = None) -> None:
        super().set_compilation_status(file_name, status, warnings)
        self._max_sol_len = max(self._max_sol_len, len(file_name))

    # pylint: disable=no-self-use
    def _print_compilation_status(self, status: EventStatus,
                                  loading: str, printer: Printer) -> None:
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
        printer.text("\n")

    # pylint: enable=no-self-use

    def _print_compilation(self, sources: List[str], loading: str,
                           printer: Printer) -> None:
        for comp in sources:
            printer.text("%{}s: ".format(self._max_sol_len) % comp)
            self._print_compilation_status(self._compilation_status[comp],
                                           loading, printer)

    def _print_generation_status(self, printer: Printer) -> None:
        for subtask in self._subtask_testcases:
            if subtask > 0:
                printer.text("|")
            for testcase in self._subtask_testcases[subtask]:
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
        max_score = sum(self._subtask_max_scores.values())
        if not status.subtask_scores:
            printer.text("% 4s" % "...")
        elif status.score is not None:
            if status.score == max_score:
                printer.bold("% 4.f" % status.score)
            else:
                printer.text("% 4.f" % status.score)
        else:
            printer.bold("% 4s" % loading)

        for subtask in self._subtask_max_scores:
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

    def _ui(self, stdscr: 'curses._CursesWindow') -> None:
        if hasattr(signal, 'pthread_sigmask'):
            signal.pthread_sigmask(signal.SIG_BLOCK, [signal.SIGINT])
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, curses.COLORS):
            curses.init_pair(i, i, -1)
        curses.halfdelay(1)

        loading_chars = "-\\|/"
        cur_loading_char = 0
        pad = curses.newpad(1000, 1000)
        printer = CursesPrinter(pad)
        pos_x, pos_y = 0, 0
        max_y, max_x = stdscr.getmaxyx()

        while not self._done and self._failure is None:
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
        curses.endwin()

    def print_final_status(self) -> None:
        self._done = True
        self._ui_thread.join()

        printer = StdoutPrinter()

        printer.blue("Compilation\n")
        self._print_compilation(self._other_compilations, "?", printer)
        printer.text("\n")
        self._print_compilation(self.solutions, "?", printer)
        printer.text("\n")

        printer.blue("Solutions\n")
        max_score = sum(self._subtask_max_scores.values())

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
            printer.right("[%s]" % sol)

        for sol in sorted(self._solution_status):
            status = self._solution_status[sol]
            printer.bold("%s: " % sol)
            if status.score is None:
                printer.red("not available\n")
            elif status.score == max_score:
                printer.green(
                    "%.2f / %.2f\n" % (status.score, max_score), bold=False)
            else:
                printer.text("%.2f / %.2f\n" % (status.score, max_score))

            if sol in self._compilation_errors:
                printer.red("Compilation errors\n")
                printer.text(self._compilation_errors[sol])
                printer.text("\n")

            if status.score is None:
                continue

            for num, subtask in sorted(self._subtask_testcases.items()):
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
                    tc_status = status.testcase_result[testcase]
                    print_testcase(sol, testcase, tc_status, max_time, max_mem)

            printer.text("\n")

        printer.blue("Scores")
        printer.bold("%s total" % (" " * (self._max_sol_len - 4)))
        for max_score in self._subtask_max_scores.values():
            printer.bold("% 4.f " % max_score)
        printer.text("\n")

        for sol in sorted(self.solutions):
            printer.text("%{}s:  ".format(self._max_sol_len) % sol)
            self._print_subtasks_scores(self._solution_status[sol], "?",
                                        printer)
            printer.text("\n")

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

    def fatal_error(self, msg: str) -> None:
        if not self._failure:
            self._failure = msg
        else:
            self._failure += "\n" + msg
        self.print_final_status()
