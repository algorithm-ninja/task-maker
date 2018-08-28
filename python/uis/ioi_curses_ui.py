#!/usr/bin/env python3
import time
import curses
import threading
from task_maker.formats import Task

from task_maker.printer import CursesPrinter, Printer
from task_maker.task_maker_frontend import ResultStatus
from task_maker.uis.ioi import IOIUIInterface, SourceFileCompilationStatus, \
    TestcaseGenerationStatus, SubtaskSolutionResult, TestcaseSolutionStatus, \
    SolutionStatus, TestcaseSolutionInfo

# frames per second of the UI
from typing import Dict

FPS = 30


def print_solution_column(printer: Printer, solution: str, max_sol_len: int):
    printer.text("%{}s ".format(max_sol_len) % solution)


def print_compilation_status(printer: Printer, solution: str, max_sol_len: int,
                             loading_char: str,
                             status: SourceFileCompilationStatus):
    print_solution_column(printer, solution, max_sol_len)
    if status == SourceFileCompilationStatus.WAITING:
        printer.text("...")
    elif status == SourceFileCompilationStatus.COMPILING:
        printer.text(loading_char)
    elif status == SourceFileCompilationStatus.DONE:
        printer.green("OK", bold=True)
    else:
        printer.red("FAIL", bold=True)
    printer.text("\n")


def print_testcase_generation_status(printer: Printer,
                                     status: TestcaseGenerationStatus):
    if status == TestcaseGenerationStatus.WAITING:
        printer.text(".")
    elif status == TestcaseGenerationStatus.GENERATING:
        printer.blue("g", bold=True)
    elif status == TestcaseGenerationStatus.GENERATED:
        printer.text("G")
    elif status == TestcaseGenerationStatus.VALIDATING:
        printer.blue("v", bold=True)
    elif status == TestcaseGenerationStatus.VALIDATED:
        printer.text("V")
    elif status == TestcaseGenerationStatus.SOLVING:
        printer.blue("s", bold=True)
    elif status == TestcaseGenerationStatus.DONE:
        printer.green("S", bold=True)
    else:
        printer.red("F", bold=True)


def print_subtask_result(printer: Printer, text: str,
                         result: SubtaskSolutionResult):
    if result == SubtaskSolutionResult.WAITING:
        printer.text(text)
    elif result == SubtaskSolutionResult.RUNNING:
        printer.text(text)
    elif result == SubtaskSolutionResult.ACCEPTED:
        printer.green(text)
    elif result == SubtaskSolutionResult.PARTIAL:
        printer.yellow(text)
    elif result == SubtaskSolutionResult.REJECTED:
        printer.red(text)
    else:
        raise ValueError(result)


def print_testcase_solution_result(printer: Printer, loading: str,
                                   info: TestcaseSolutionInfo):
    if info.status == TestcaseSolutionStatus.WAITING:
        printer.text(".")
    elif info.status == TestcaseSolutionStatus.SOLVING:
        printer.blue(loading)
    elif info.status == TestcaseSolutionStatus.SOLVED:
        printer.text("s")
    elif info.status == TestcaseSolutionStatus.CHECKING:
        printer.text(loading)
    elif info.status == TestcaseSolutionStatus.SKIPPED:
        printer.text("X")
    elif info.checked and info.status == TestcaseSolutionStatus.ACCEPTED:
        printer.green("A", bold=True)
    elif info.checked and info.status == TestcaseSolutionStatus.WRONG_ANSWER:
        printer.red("W", bold=True)
    elif info.checked and info.status == TestcaseSolutionStatus.PARTIAL:
        printer.yellow("P", bold=True)
    elif info.checked and info.status == TestcaseSolutionStatus.FAILED:
        for res in info.result:
            if res.status != ResultStatus.SUCCESS:
                result = res
                break
        else:
            result = None
        # marked as failed even if no solution failed --> the checker
        if result is None:
            printer.bold("I", bold=True)
        elif result.status == ResultStatus.SIGNAL:
            printer.red("R", bold=True)
        elif result.status == ResultStatus.RETURN_CODE:
            printer.red("R", bold=True)
        elif result.status == ResultStatus.TIME_LIMIT:
            printer.red("T", bold=True)
        elif result.status == ResultStatus.WALL_LIMIT:
            printer.red("T", bold=True)
        elif result.status == ResultStatus.MEMORY_LIMIT:
            printer.red("M", bold=True)
        elif result.status == ResultStatus.MISSING_FILES:
            printer.red("F", bold=True)
        elif result.status == ResultStatus.INTERNAL_ERROR:
            printer.bold("I", bold=True)
        else:
            raise ValueError(result)
    elif not info.checked:
        printer.blue(loading)
    else:
        raise ValueError("{} {}".format(info.checked, info.status))


def print_solutions_result(printer: Printer, task: Task,
                           solutions: Dict[str, SolutionStatus],
                           max_sol_len: int, loading: str):
    printer.text(" " * max_sol_len + " ")
    max_score = sum(st.max_score for st in task.subtasks.values())
    printer.bold("{:^5.0f}|".format(max_score))
    for subtask in task.subtasks.values():
        printer.bold("{:^5.0f}".format(subtask.max_score))
    printer.text("\n")

    for solution, status in solutions.items():
        print_solution_column(printer, solution, max_sol_len)
        if all([
            s == SubtaskSolutionResult.WAITING
            for s in status.subtask_results
        ]):
            printer.text(" ... ")
        elif any([
            s == SubtaskSolutionResult.RUNNING
            for s in status.subtask_results
        ]):
            printer.text("  {}  ".format(loading))
        else:
            printer.text(" {:^3.0f} ".format(status.score))
        printer.text("|")

        for score, result in zip(status.subtask_scores.values(),
                                 status.subtask_results):
            if result == SubtaskSolutionResult.WAITING:
                printer.text(" ... ")
            elif result == SubtaskSolutionResult.RUNNING:
                printer.text("  {}  ".format(loading))
            else:
                print_subtask_result(printer, " {:^3.0f} ".format(score),
                                     result)

        printer.text("  ")
        for (st_num, testcases), st_result in zip(
                status.testcase_results.items(), status.subtask_results):
            print_subtask_result(printer, "[", st_result)
            for tc_num, testcase in testcases.items():
                print_testcase_solution_result(printer, loading,
                                               testcase)
            print_subtask_result(printer, "]", st_result)

        printer.text("\n")


class IOICursesUI:
    def __init__(self, interface: IOIUIInterface):
        self.interface = interface
        self.thread = threading.Thread(
            target=curses.wrapper, args=(self._wrapper,))
        self.stopped = False

    def start(self):
        self.stopped = False
        self.thread.start()

    def stop(self):
        self.stopped = True
        self.thread.join()

    def _wrapper(self, stdscr):
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, curses.COLORS):
            curses.init_pair(i, i, -1)
        curses.halfdelay(1)
        pad = curses.newpad(10000, 1000)
        printer = CursesPrinter(pad)
        loading_chars = "-\\|/"
        cur_loading_char = 0
        pos_x, pos_y = 0, 0
        while not self.stopped:
            last_draw = time.monotonic()
            cur_loading_char = (cur_loading_char + 1) % len(loading_chars)
            loading = loading_chars[cur_loading_char]
            pad.clear()
            self._loop(printer, loading)

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

            max_y, max_x = stdscr.getmaxyx()
            pad.refresh(pos_y, pos_x, 0, 0, max_y - 1, max_x - 1)

            if time.monotonic() - last_draw < 1 / FPS:
                time.sleep(1 / FPS - (time.monotonic() - last_draw))

        curses.endwin()

    def _loop(self, printer: CursesPrinter, loading: str):
        max_sol_len = 1 + max([len(s) for s in self.interface.non_solutions] +
                              [len(s) for s in self.interface.solutions] + [0])

        printer.bold("Running... %s\n" % self.interface.task.name)
        printer.text("Time limit: %.2fs\n" % self.interface.task.time_limit)
        printer.text("Memory limit: %.2fMiB\n" %
                     (self.interface.task.memory_limit_kb / 1024))
        printer.text("\n")

        printer.blue("Compilation:\n", bold=True)
        for name, result in self.interface.non_solutions.items():
            print_compilation_status(printer, name, max_sol_len, loading,
                                     result.status)
        printer.text("\n")
        for name, result in self.interface.solutions.items():
            print_compilation_status(printer, name, max_sol_len, loading,
                                     result.status)
        printer.text("\n")

        printer.blue("Generation: ", bold=True)
        for st_num, subtask in self.interface.subtasks.items():
            printer.text("[")
            for tc_num, testcase in subtask.items():
                print_testcase_generation_status(printer, testcase.status)
            printer.text("]")
        printer.text("\n\n")

        printer.blue("Evaluation:\n", bold=True)

        print_solutions_result(printer, self.interface.task,
                               self.interface.testing, max_sol_len, loading)

        printer.text("\n")

        printer.blue("Running tasks:\n", bold=True)
        running = sorted(
            (t, n) for n, t in self.interface.running.copy().items())
        now = time.monotonic()
        for start, task in running:
            duration = now - start
            printer.text(" - {0: <50} {1: .1f}s\n".format(
                task.strip(), duration))
