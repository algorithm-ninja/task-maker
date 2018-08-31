#!/usr/bin/env python3
import curses
from abc import ABC, abstractmethod
from enum import Enum
import signal
import threading
import time
from typing import Dict, List

from task_maker.config import Config
from task_maker.printer import StdoutPrinter, Printer, CursesPrinter
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import Result, ResultStatus, Resources


class SourceFileCompilationStatus(Enum):
    WAITING = 0
    COMPILING = 1
    DONE = 2
    FAILURE = 3


class SourceFileCompilationResult:
    def __init__(self, need_compilation):
        self.need_compilation = need_compilation
        self.status = SourceFileCompilationStatus.WAITING
        self.stderr = ""
        self.result = None  # type: Result


class UIInterface:
    def __init__(self, do_print: bool):
        self.non_solutions = dict(
        )  # type: Dict[str, SourceFileCompilationResult]
        self.solutions = dict()  # type: Dict[str, SourceFileCompilationResult]
        self.running = dict()  # type: Dict[str, float]
        self.warnings = list()  # type: List[str]
        self.errors = list()  # type: List[str]

        if do_print:
            self.printer = StdoutPrinter()
        else:
            self.printer = Printer()

    def add_non_solution(self, source_file: SourceFile):
        name = source_file.name
        log_prefix = "Compilation of non-solution {} ".format(name).ljust(50)
        self.non_solutions[name] = SourceFileCompilationResult(
            source_file.language.need_compilation)
        self.printer.text(log_prefix + "WAITING\n")
        if source_file.language.need_compilation:

            def notifyStartCompiltion():
                self.printer.text(log_prefix + "START\n")
                self.non_solutions[
                    name].status = SourceFileCompilationStatus.COMPILING
                self.running[log_prefix] = time.monotonic()

            def getResultCompilation(result: Result):
                del self.running[log_prefix]
                self.non_solutions[name].result = result
                cached = " [cached]" if result.was_cached else ""
                if result.status == ResultStatus.SUCCESS:
                    self.printer.green(log_prefix + "SUCCESS" + cached + "\n")
                    self.non_solutions[
                        name].status = SourceFileCompilationStatus.DONE
                else:
                    self.add_error("Failed to compile " + name)
                    self.printer.red(log_prefix + "FAIL: {} {}\n".format(
                        result.status, cached))
                    self.non_solutions[
                        name].status = SourceFileCompilationStatus.FAILURE

            def getStderr(stderr):
                if stderr:
                    self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")
                self.non_solutions[name].stderr = stderr

            source_file.compilation_stderr.getContentsAsString(getStderr)
            source_file.compilation.notifyStart(notifyStartCompiltion)
            source_file.compilation.getResult(getResultCompilation)
        else:
            self.printer.green(log_prefix + "SUCCESS\n")
            self.non_solutions[name].status = SourceFileCompilationStatus.DONE

    def add_solution(self, source_file: SourceFile):
        name = source_file.name
        log_prefix = "Compilation of solution {} ".format(name).ljust(50)
        self.solutions[name] = SourceFileCompilationResult(
            source_file.language.need_compilation)
        self.printer.text(log_prefix + "WAITING\n")

        if source_file.language.need_compilation:

            def notifyStartCompiltion():
                self.printer.text(log_prefix + "START\n")
                self.solutions[
                    name].status = SourceFileCompilationStatus.COMPILING
                self.running[log_prefix] = time.monotonic()

            def getResultCompilation(result: Result):
                del self.running[log_prefix]
                self.solutions[name].result = result
                cached = " [cached]" if result.was_cached else ""
                if result.status == ResultStatus.SUCCESS:
                    self.printer.green(log_prefix + "SUCCESS" + cached + "\n")
                    self.solutions[
                        name].status = SourceFileCompilationStatus.DONE
                else:
                    self.add_warning("Failed to compile: " + name)
                    self.printer.red(log_prefix + "FAIL: {} {}\n".format(
                        result.status, cached))
                    self.solutions[
                        name].status = SourceFileCompilationStatus.FAILURE

            def getStderr(stderr):
                if stderr:
                    self.printer.text(log_prefix + "STDERR\n" + stderr + "\n")
                self.solutions[name].stderr = stderr

            source_file.compilation_stderr.getContentsAsString(getStderr)
            source_file.compilation.notifyStart(notifyStartCompiltion)
            source_file.compilation.getResult(getResultCompilation)
        else:
            self.printer.green(log_prefix + "SUCCESS\n")
            self.solutions[name].status = SourceFileCompilationStatus.DONE

    def add_warning(self, message: str):
        self.warnings.append(message)

    def add_error(self, message: str):
        self.errors.append(message)


class FinishUI:
    LIMITS_MARGIN = 0.8

    def __init__(self, config: Config, interface: UIInterface):
        self.config = config
        self.interface = interface
        self.printer = StdoutPrinter()

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
                        result.result.status != ResultStatus.INVALID_REQUEST:
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
                elif result.result.status == ResultStatus.INVALID_REQUEST:
                    self.printer.text("  " + result.result.error)
                elif result.result.status == ResultStatus.SUCCESS:
                    pass
                else:
                    self.printer.text("  " + result.result.status)
        self.printer.text("\n")
        if result.stderr:
            self.printer.text(result.stderr)

    def _print_score(self, score: float, max_score: float,
                     individual: List[float]):
        if score == 0.0 and not all(individual):
            self.printer.red("{:.2f} / {:.2f}".format(score, max_score))
        elif score == max_score and all(individual):
            self.printer.green("{:.2f} / {:.2f}".format(score, max_score))
        else:
            self.printer.yellow("{:.2f} / {:.2f}".format(score, max_score))

    def _print_resources(self,
                         resources: Resources,
                         time_limit: float = 10**10,
                         memory_limt: float = 10**10,
                         name: str = ""):
        self._print_exec_stat(resources.cpu_time + resources.sys_time,
                              resources.memory / 1024, time_limit, memory_limt,
                              name)

    def _print_exec_stat(self, time, memory, time_limit, memory_limit, name):
        self.printer.text(" [")
        if name:
            self.printer.text(name + " ")
        if time >= FinishUI.LIMITS_MARGIN * time_limit:
            self.printer.yellow("{:.3f}s".format(time), bold=False)
        else:
            self.printer.text("{:.3f}s".format(time))
        self.printer.text(" |")
        if memory >= FinishUI.LIMITS_MARGIN * memory_limit / 1024:
            self.printer.yellow("{:5.1f}MiB".format(memory), bold=False)
        else:
            self.printer.text("{:5.1f}MiB".format(memory))
        self.printer.text("]")

    def _print_final_messages(self):
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


class CursesUI(ABC):
    FPS = 30

    def __init__(self):
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

            if time.monotonic() - last_draw < 1 / CursesUI.FPS:
                time.sleep(1 / CursesUI.FPS - (time.monotonic() - last_draw))

        curses.endwin()

    @abstractmethod
    def _loop(self, printer: CursesPrinter, loading: str):
        pass


def result_to_str(result: Result) -> str:
    status = result.status
    if status == ResultStatus.SUCCESS:
        return "Success"
    elif status == ResultStatus.SIGNAL:
        return "Killed with signal %d (%s)" % (
            result.signal, signal.Signals(result.signal).name)
    elif status == ResultStatus.RETURN_CODE:
        return "Exited with code %d" % result.return_code
    elif status == ResultStatus.TIME_LIMIT:
        return "Time limit exceeded"
    elif status == ResultStatus.WALL_LIMIT:
        return "Wall time limit exceeded"
    elif status == ResultStatus.MEMORY_LIMIT:
        return "Memory limit exceeded"
    elif status == ResultStatus.MISSING_FILES:
        return "Some files are missing"
    elif status == ResultStatus.INTERNAL_ERROR:
        return "Internal error: " + result.error
    else:
        raise ValueError(status)


def get_max_sol_len(interface: UIInterface):
    return max(
        map(
            len,
            list(interface.non_solutions.keys()) + list(
                interface.solutions.keys())))
