#!/usr/bin/env python3
import curses
import threading
from task_maker.printer import CursesPrinter
from task_maker.ui import IOILikeUIInterface, SourceFileCompilationStatus, \
    TestcaseGenerationStatus


def print_solution_column(printer: CursesPrinter, solution: str,
                          max_sol_len: int):
    printer.text("%{}s ".format(max_sol_len) % solution)


def print_compilation_status(printer: CursesPrinter, solution: str,
                             max_sol_len: int, loading_char: str,
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


def print_testcase_generation_status(printer: CursesPrinter,
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


class IOILikeCursesUI:
    def __init__(self, interface: IOILikeUIInterface):
        self.interface = interface
        self.thread = threading.Thread(
            target=curses.wrapper, args=(self._wrapper, ))
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
        pad = curses.newpad(1000, 1000)
        printer = CursesPrinter(pad)
        loading_chars = "-\\|/"
        cur_loading_char = 0
        pos_x, pos_y = 0, 0
        while not self.stopped:
            max_y, max_x = stdscr.getmaxyx()
            cur_loading_char = (cur_loading_char + 1) % len(loading_chars)
            loading = loading_chars[cur_loading_char]

            pad.clear()
            self._loop(printer, loading)
            pad.refresh(pos_y, pos_x, 0, 0, max_y - 1, max_x - 1)

        curses.endwin()

    def _loop(self, printer: CursesPrinter, loading: str):
        max_sol_len = 4 + max([len(s) for s in self.interface.non_solutions] +
                              [len(s) for s in self.interface.solutions] + [0])

        printer.bold("Running... %s\n" % self.interface.task.name)
        printer.text("Time limit: %.2fs\n" % self.interface.task.time_limit)
        printer.text("Memory limit: %.2fMiB\n" %
                     (self.interface.task.memory_limit_kb / 1024))
        printer.text("\n")

        printer.blue("Compilation:\n", bold=True)
        for name, status in self.interface.non_solutions.items():
            print_compilation_status(printer, name, max_sol_len, loading,
                                     status)
        printer.text("\n")
        for name, status in self.interface.solutions.items():
            print_compilation_status(printer, name, max_sol_len, loading,
                                     status)
        printer.text("\n")

        printer.blue("Generation: ", bold=True)
        for st_num, subtask in self.interface.subtasks.items():
            printer.text("[")
            for tc_num, testcase in subtask.items():
                print_testcase_generation_status(printer, testcase)
            printer.text("]")
        printer.text("\n\n")

        printer.blue("Evaluation:\n", bold=True)
        for solution, status in self.interface.testing.items():
            print_solution_column(printer, solution, max_sol_len)
            printer.text(str(status.score))

            printer.text("\n")