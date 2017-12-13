#!/usr/bin/env python3

import os
import curses
import threading

from typing import Dict  # pylint: disable=unused-import
from typing import List
from typing import Optional
from python.ui import CompilationStatus
from python.ui import EvaluationResult
from python.ui import EvaluationStatus
from python.ui import GenerationStatus
from python.ui import UI


class SolutionStatus:
    def __init__(self) -> None:
        self.testcase_errors = dict()  # type: Dict[int, str]
        self.testcase_result = dict()  # type: Dict[int, EvaluationResult]
        self.testcase_status = dict()  # type: Dict[int, EvaluationStatus]
        self.subtask_scores = dict()  # type: Dict[int, float]
        self.score = None  # type: Optional[float]
        self.compiled = False


class Printer:
    def text(self, what: str) -> None:
        pass

    def red(self, what: str) -> None:
        pass

    def green(self, what: str) -> None:
        pass

    def blue(self, what: str) -> None:
        pass

    def bold(self, what: str) -> None:
        pass


class StdoutPrinter(Printer):
    def __init__(self) -> None:
        def _get_color(color: int) -> str:
            return curses.tparm(curses.tigetstr("setaf"), color).decode("utf8")

        self.bold_fmt = curses.tparm(curses.tigetstr("bold")).decode()
        if curses.COLORS >= 256:
            self.green_fmt = _get_color(82) + self.bold_fmt
        else:
            self.green_fmt = _get_color(curses.COLOR_GREEN) + self.bold_fmt
        self.red_fmt = _get_color(curses.COLOR_RED) + self.bold_fmt
        self.blue_fmt = _get_color(curses.COLOR_BLUE) + self.bold_fmt
        self.reset_fmt = curses.tparm(curses.tigetstr("sgr0")).decode()

    def text(self, what: str) -> None:
        print(what, end="")

    def red(self, what: str) -> None:
        print(self.red_fmt + what + self.reset_fmt, end="")

    def green(self, what: str) -> None:
        print(self.green_fmt + what + self.reset_fmt, end="")

    def blue(self, what: str) -> None:
        print(self.blue_fmt + what + self.reset_fmt, end="")

    def bold(self, what: str) -> None:
        print(self.bold_fmt + what + self.reset_fmt, end="")


class CursesPrinter(Printer):
    def __init__(self, stdscr: 'curses._CursesWindow') -> None:
        self.stdscr = stdscr
        self.bold_fmt = curses.A_BOLD
        if curses.COLORS >= 256:
            self.green_fmt = curses.A_BOLD | curses.color_pair(82)
        else:
            self.green_fmt = curses.color_pair(curses.COLOR_GREEN)
        self.red_fmt = curses.A_BOLD | curses.color_pair(curses.COLOR_RED)
        self.blue_fmt = curses.A_BOLD | curses.color_pair(curses.COLOR_BLUE)

    def text(self, what: str) -> None:
        self.stdscr.addstr(what)

    def red(self, what: str) -> None:
        self.stdscr.addstr(what, self.red_fmt)

    def green(self, what: str) -> None:
        self.stdscr.addstr(what, self.green_fmt)

    def blue(self, what: str) -> None:
        self.stdscr.addstr(what, self.blue_fmt)

    def bold(self, what: str) -> None:
        self.stdscr.addstr(what, self.bold_fmt)


class CursesUI(UI):

    def __init__(self, task_name: str) -> None:
        super().__init__(task_name)
        self._num_testcases = 0
        self._subtask_max_scores = dict()  # type: Dict[int, float]
        self._subtask_testcases = dict()  # type: Dict[int, List[int]]
        self._solutions = []  # type: List[str]
        self._other_compilations = []  # type: List[str]
        self._compilation_status = dict()  # type: Dict[str, CompilationStatus]
        self._compilation_errors = dict()  # type: Dict[str, str]
        self._generation_status = dict()  # type: Dict[int, GenerationStatus]
        self._generation_errors = dict()  # type: Dict[int, str]
        self._time_limit = 0.0
        self._memory_limit = 0.0
        self._solution_status = dict()  # type: Dict[str, SolutionStatus]
        self._done = False
        self._failure = None  # type: Optional[str]
        self._max_sol_len = 13
        self._ui_thread = threading.Thread(
            target=curses.wrapper, args=(self._ui, ))
        self._ui_thread.start()

    # pylint: disable=no-self-use
    def _print_compilation_status(self, status: CompilationStatus,
                                  loading: str, printer: Printer) -> None:
        if status == CompilationStatus.WAITING:
            printer.text("...")
        elif status == CompilationStatus.RUNNING:
            printer.bold(loading)
        elif status == CompilationStatus.SUCCESS:
            printer.green("OK")
        elif status == CompilationStatus.FAILURE:
            printer.red("FAILURE")
        printer.text("\n")
    # pylint: enable=no-self-use

    def _print_compilation(self, sources: List[str], loading: str, printer: Printer) -> None:
        for comp in sources:
            printer.text("%{}s: ".format(self._max_sol_len) % comp)
            self._print_compilation_status(self._compilation_status[comp], loading, printer)

    def _print_generation_status(self, printer: Printer) -> None:
        for subtask in self._subtask_testcases:
            if subtask > 0:
                printer.text("|")
            for testcase in self._subtask_testcases[subtask]:
                status = self._generation_status[testcase]
                if status == GenerationStatus.WAITING:
                    printer.text(".")
                elif status == GenerationStatus.GENERATING:
                    printer.text("g")
                elif status == GenerationStatus.GENERATED:
                    printer.text("G")
                elif status == GenerationStatus.VALIDATING:
                    printer.text("v")
                elif status == GenerationStatus.VALIDATED:
                    printer.text("V")
                elif status == GenerationStatus.SOLVING:
                    printer.text("s")
                elif status == GenerationStatus.SUCCESS:
                    printer.green("S")
                elif status == GenerationStatus.FAILURE:
                    printer.red("F")
                else:
                    printer.red("?")

    def _print_subtasks_scores(self, status: SolutionStatus,
                               loading: str, printer: Printer) -> None:
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
            if all(tc not in status.testcase_status or
                   status.testcase_status[tc] == EvaluationStatus.WAITING
                   for tc in testcases):
                printer.text(" % 4s" % "...")
            elif subtask in status.subtask_scores:
                if self._subtask_max_scores[subtask] == status.subtask_scores[subtask]:
                    printer.bold(" % 4.f" % status.subtask_scores[subtask])
                else:
                    printer.text(" % 4.f" % status.subtask_scores[subtask])
            else:
                printer.bold(" % 4s" % loading)

    def _ui(self, stdscr: 'curses._CursesWindow') -> None:
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
        will_exit = False
        max_y, max_x = stdscr.getmaxyx()

        while (not will_exit or not self._done) and self._failure is None:
            cur_loading_char = (cur_loading_char + 1) % len(loading_chars)
            loading = loading_chars[cur_loading_char]
            pad.clear()

            if self._done:
                printer.green("Done\n")
            elif self._failure:
                printer.red("Failure\n")
            else:
                printer.bold("Running...\n")

            printer.text("Time limit: %.2f\n" % self._time_limit)
            printer.text("Memory limit: %.2f\n" % (self._memory_limit / 1024))

            self._print_compilation(self._other_compilations, loading, printer)
            printer.text("\n")
            self._print_compilation(self._solutions, loading, printer)
            printer.text("\n")

            printer.blue("Generation status: ")
            self._print_generation_status(printer)
            printer.text("\n")
            printer.text("\n")

            printer.blue("Evaluation")
            printer.bold("%s total" % (" " * (self._max_sol_len - 1)))
            for max_score in self._subtask_max_scores.values():
                printer.bold("% 4.f " % max_score)
            printer.text("\n")

            for sol in sorted(self._solutions):
                printer.text("%{}s: % 3d/%d  ".format(self._max_sol_len) %
                             (sol,
                              len(self._solution_status[sol].testcase_result),
                              self._num_testcases))
                self._print_subtasks_scores(self._solution_status[sol], loading, printer)
                printer.text("\n")

            try:
                pressed_key = stdscr.getkey()
                if pressed_key == "q":
                    will_exit = not will_exit
                elif pressed_key == "KEY_UP":
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

            if will_exit:
                printer.text("\n(will exit automatically)")
            elif self._done:
                printer.bold("\nPress q to exit...")
            pad.refresh(pos_y, pos_x, 0, 0, max_y-1, max_x-1)
        curses.endwin()

    def set_time_limit(self, time_limit: float) -> None:
        self._time_limit = time_limit

    def set_memory_limit(self, memory_limit: int) -> None:
        self._memory_limit = memory_limit

    def set_subtask_info(self, subtask_num: int, max_score: float,
                         testcases: List[int]) -> None:
        self._subtask_testcases[subtask_num] = testcases
        self._subtask_max_scores[subtask_num] = max_score
        self._num_testcases = max(self._num_testcases, max(testcases) + 1)

    def set_compilation_status(self,
                               file_name: str,
                               is_solution: bool,
                               status: CompilationStatus,
                               warnings: Optional[str] = None) -> None:
        if is_solution:
            if file_name not in self._solutions:
                self._solutions.append(file_name)
                self._max_sol_len = max(self._max_sol_len, len(file_name))
            if file_name not in self._solution_status:
                self._solution_status[file_name] = SolutionStatus()
        else:
            if file_name not in self._other_compilations:
                self._other_compilations.append(file_name)
                self._max_sol_len = max(self._max_sol_len, len(file_name))
        self._compilation_status[file_name] = status
        if warnings:
            self._compilation_errors[file_name] = warnings

    def set_generation_status(self,
                              testcase_num: int,
                              status: GenerationStatus,
                              stderr: Optional[str] = None) -> None:
        self._generation_status[testcase_num] = status
        if stderr:
            self._generation_errors[testcase_num] = stderr

    def set_evaluation_status(self,
                              testcase_num: int,
                              solution_name: str,
                              status: EvaluationStatus,
                              result: Optional[EvaluationResult] = None,
                              error: Optional[str] = None) -> None:
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            self._solution_status[solution_name] = SolutionStatus()
        sol_status = self._solution_status[solution_name]
        sol_status.testcase_status[testcase_num] = status
        if error:
            sol_status.testcase_errors[testcase_num] = error
        if result:
            sol_status.testcase_result[testcase_num] = result

    def set_subtask_score(self, subtask_num: int, solution_name: str,
                          score: float) -> None:
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            raise RuntimeError("Something weird happened")
        self._solution_status[solution_name].subtask_scores[
            subtask_num] = score

    def set_task_score(self, solution_name: str, score: float) -> None:
        solution_name = os.path.basename(solution_name)
        if solution_name not in self._solution_status:
            raise RuntimeError("Something weird happened")
        self._solution_status[solution_name].score = score

    def print_final_status(self) -> None:
        self._done = True
        self._ui_thread.join()

        printer = StdoutPrinter()

        if any(len(errors) for sol, errors in self._compilation_errors.items()):
            printer.red("Compilation errors\n")
            for sol, errors in sorted(self._compilation_errors.items()):
                if errors:
                    printer.text("Solution ")
                    printer.bold(sol)
                    printer.text("\n")
                    print(errors)

        printer.blue("Compilation\n")
        self._print_compilation(self._other_compilations, "?", printer)
        printer.text("\n")
        self._print_compilation(self._solutions, "?", printer)
        printer.text("\n")

        printer.blue("Generation status: ")
        self._print_generation_status(printer)
        printer.text("\n")
        printer.text("\n")

        # TODO print the summary for each solution with the time/memory for easy testcase

        printer.blue("Scores")
        printer.bold("%s total" % (" " * (self._max_sol_len-4)))
        for max_score in self._subtask_max_scores.values():
            printer.bold("% 4.f " % max_score)
        printer.text("\n")

        for sol in sorted(self._solutions):
            printer.text("%{}s:  ".format(self._max_sol_len) % sol)
            self._print_subtasks_scores(self._solution_status[sol], "?", printer)
            printer.text("\n")

        if self._failure:
            printer.red("Fatal error\n")
            printer.red(self._failure)

    def fatal_error(self, msg: str) -> None:
        self._failure = msg
