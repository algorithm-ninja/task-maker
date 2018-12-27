#!/usr/bin/env python3

import time

import curses
import signal
import threading
import traceback
from abc import ABC, abstractmethod
from contextlib import contextmanager
from enum import Enum
from task_maker.config import Config
from task_maker.formats import Task
from task_maker.printer import StdoutPrinter, Printer, CursesPrinter
from task_maker.remote import Execution, ExecutionPool
from task_maker.source_file import SourceFile
from task_maker.statements import Statement, StatementCompilationStatus, \
    StatementDepInfo, StatementDepCompilationStatus
from task_maker.task_maker_frontend import Result, ResultStatus, Resources
from task_maker.uis.ui_printer import UIPrinter
from typing import Dict, List, Optional


class SourceFileCompilationStatus(Enum):
    """
    Status of the compilation of a source file
    - WAITING: the compilation has not started yet
    - COMPILING: the compilation has started
    - DONE: the compilation has successfully completed
    - FAILURE: the compilation failed
    """
    WAITING = 0
    COMPILING = 1
    DONE = 2
    FAILURE = 3


class SourceFileCompilationResult:
    """
    Result information about a compilation of a source file
    """

    def __init__(self, need_compilation):
        self.need_compilation = need_compilation
        self.status = SourceFileCompilationStatus.WAITING
        self.execution = None  # type: Execution
        # TODO remove those vvv
        self.stderr = ""
        self.result = None  # type: Result


class UIInterface:
    """
    This class is the binding between the frontend and the task format and the
    UIs. The format will register the solutions, the frontend will call its
    callbacks and the state is stored in this class (and in it's subclasses).
    The UI will use the data inside this.
    """

    def __init__(self, task: Task, do_print: bool, json: bool):
        """
        :param task: The task this UIInterface is bound to
        :param do_print: Whether the logs should be printed to stdout (print
        interface)
        """
        self.task = task
        self.non_solutions = dict(
        )  # type: Dict[str, SourceFileCompilationResult]
        self.solutions = dict()  # type: Dict[str, SourceFileCompilationResult]
        self.statements = dict()  # type: Dict[str, Statement]
        self.warnings = list()  # type: List[str]
        self.errors = list()  # type: List[str]
        self.pool = None  # type: ExecutionPool

        if do_print:
            self.printer = StdoutPrinter()
        else:
            self.printer = Printer()
        self.ui_printer = UIPrinter(self.printer, json)

    def add_non_solution(self, source_file: SourceFile):
        """
        Add a non-solution file to the ui (ie a generator/checker/...)
        """
        name = source_file.name
        self.non_solutions[name] = SourceFileCompilationResult(
            source_file.language.need_compilation)

        if source_file.language.need_compilation:
            self.non_solutions[name].execution = source_file.compilation

            def on_start():
                self.non_solutions[
                    name].status = SourceFileCompilationStatus.COMPILING

            def on_done(result: Result):
                self.non_solutions[name].result = result
                self.non_solutions[
                    name].stderr = source_file.compilation.stderr_content
                if result.status == ResultStatus.SUCCESS:
                    self.non_solutions[
                        name].status = SourceFileCompilationStatus.DONE
                else:
                    self.add_error("Failed to compile " + name)
                    self.non_solutions[
                        name].status = SourceFileCompilationStatus.FAILURE

            source_file.compilation.bind(on_done, on_start)
        else:
            self.non_solutions[name].status = SourceFileCompilationStatus.DONE

    def add_solution(self, source_file: SourceFile):
        """
        Add a solution to the UI
        """
        name = source_file.name
        self.solutions[name] = SourceFileCompilationResult(
            source_file.language.need_compilation)

        if source_file.language.need_compilation:
            self.solutions[name].execution = source_file.compilation

            def on_start():
                self.solutions[
                    name].status = SourceFileCompilationStatus.COMPILING

            def on_done(result: Result):
                self.solutions[name].result = result
                self.solutions[
                    name].stderr = source_file.compilation.stderr_content
                if result.status == ResultStatus.SUCCESS:
                    self.solutions[
                        name].status = SourceFileCompilationStatus.DONE
                else:
                    self.add_warning("Failed to compile: " + name)
                    self.solutions[
                        name].status = SourceFileCompilationStatus.FAILURE

            source_file.compilation.bind(on_done, on_start)
        else:
            self.solutions[name].status = SourceFileCompilationStatus.DONE

    def add_statement(self, statement: Statement):
        """
        Add a statement to the UI
        """
        self.statements[statement.name] = statement

        def on_start():
            statement.compilation_status = StatementCompilationStatus.COMPILING

        def on_done(result: Result):
            statement.compilation_result = result
            if result.status in [
                ResultStatus.SUCCESS, ResultStatus.RETURN_CODE
            ]:
                statement.compilation_status = StatementCompilationStatus.DONE
            else:
                statement.compilation_status = StatementCompilationStatus.FAILED
                self.add_warning(
                    "Failed to compile statement %s" % statement.name)

        statement.compilation.bind(on_done, on_start)

        deps_done = 0  # how many dependencies have been completed

        for info in statement.other_executions:

            def register_execution(info: StatementDepInfo):
                def dep_on_start():
                    statement.compilation_status = \
                        StatementCompilationStatus.COMPILING_DEPS
                    info.status = StatementDepCompilationStatus.RUNNING

                def dep_on_done(result: Result):
                    nonlocal deps_done
                    info.result = result
                    deps_done += 1
                    if result.status == ResultStatus.SUCCESS:
                        info.status = StatementDepCompilationStatus.DONE
                        if statement.compilation_status != \
                                StatementCompilationStatus.FAILED:
                            if deps_done == len(statement.other_executions):
                                statement.compilation_status = \
                                    StatementCompilationStatus.COMPILED_DEPS
                    else:
                        info.status = StatementDepCompilationStatus.FAILED
                        statement.compilation_status = \
                            StatementCompilationStatus.FAILED
                        self.add_warning(
                            "Failed to compile statement dependency: %s" %
                            info.name)

                info.execution.bind(dep_on_done, dep_on_start)

            register_execution(info)

    def add_warning(self, message: str):
        """
        Add a warning message to the list of warnings
        """
        self.warnings.append(message)
        self.ui_printer.warning(message.strip())

    def add_error(self, message: str):
        """
        Add an error message to the list of errors, this wont stop anything
        """
        self.errors.append(message)
        self.ui_printer.error(message.strip())

    @contextmanager
    def run_in_ui(self, curses_ui: Optional["CursesUI"],
                  finish_ui: Optional["FinishUI"]):
        """
        Wrap a block in the UI's setup/teardown. A curses UI should be stopped
        before the program exists otherwise the terminal is messed up. This
        wrapper will start the UIs, yield and stop them after. At the end it
        will print with the finish ui
        """
        if curses_ui:
            curses_ui.start()
        try:
            yield
        except:
            if curses_ui:
                curses_ui.stop()
            traceback.print_exc()
            return
        else:
            if curses_ui:
                curses_ui.stop()
        if finish_ui:
            finish_ui.print()


class FinishUI(ABC):
    """
    UI used to print the summary of the execution
    """
    # if the time / memory usage is greater of the limit * LIMITS_MARGIN that
    # time/memory is highlighted
    LIMITS_MARGIN = 0.8

    def __init__(self, config: Config, interface: Optional[UIInterface]):
        self.config = config
        self.interface = interface
        self.printer = StdoutPrinter()

    @abstractmethod
    def print(self):
        """
        Print the entire result summary
        """
        pass

    @abstractmethod
    def print_summary(self):
        """
        Print only the summary grid with the overview of the results
        """
        pass

    def print_final_messages(self):
        """
        Print the warning and error messages
        """
        if not self.interface:
            return
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

    def _print_statement(self, name: str, statement: Statement,
                         max_sol_len: int):
        if statement.compilation_status == StatementCompilationStatus.DONE:
            self.printer.green(
                "{:<{len}}    OK\n".format(name, len=max_sol_len), bold=True)
        else:
            self.printer.red(
                "{:<{len}}    FAIL\n".format(name, len=max_sol_len), bold=True)
        for dep in statement.other_executions:
            self.printer.text("{:<{len}}    ".format(
                dep.name, len=max_sol_len))
            if dep.status == StatementDepCompilationStatus.DONE:
                self.printer.green("OK\n")
            else:
                self.printer.red("FAIL\n")

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


class CursesUI(ABC):
    """
    Running interface using the curses library to look nice in the terminal
    """
    # limit the frame rate
    FPS = 30

    def __init__(self, config: Config, interface: UIInterface):
        self.config = config
        self.interface = interface
        # the ui runs in a different thread
        self.thread = threading.Thread(
            target=curses.wrapper, args=(self._wrapper, ))
        self.stopped = False
        self.errored = False

    def start(self):
        """
        Start the UI starting the thread and messing up the terminal
        """
        self.stopped = False
        self.thread.start()

    def stop(self):
        """
        Stops the thread and wait for it's termination. This will fix the
        terminal closing curses
        """
        self.stopped = True
        self.thread.join()

    def _wrapper(self, stdscr):
        try:
            curses.start_color()
            curses.use_default_colors()
            if hasattr(curses, "COLORS"):
                for i in range(1, curses.COLORS):
                    curses.init_pair(i, i, -1)
            curses.halfdelay(1)
            pad = curses.newpad(10000, 1000)
            printer = CursesPrinter(pad)
            loading_chars = r"◐◓◑◒"
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
                    time.sleep(1 / CursesUI.FPS -
                               (time.monotonic() - last_draw))
        except:
            curses.endwin()
            traceback.print_exc()
            self.errored = True
        finally:
            curses.endwin()

    @abstractmethod
    def _loop(self, printer: CursesPrinter, loading: str):
        """
        The UI should inherit from this class and implement this method to print
        to the screen
        """
        pass

    def _print_running_tasks(self, printer: CursesPrinter):
        printer.blue("Running tasks:\n", bold=True)
        running = sorted(
            (t, n) for n, t in self.interface.pool.running.copy().items())
        now = time.monotonic()
        for start, task in running:
            duration = now - start
            printer.text(" - {0: <50} {1: .1f}s\n".format(task.name, duration))


def result_to_str(result: Result) -> str:
    """
    String representation of the result
    """
    status = result.status
    if status == ResultStatus.SUCCESS:
        return "Success"
    elif status == ResultStatus.SIGNAL:
        return "Killed with signal %d (%s)" % (
            result.signal, signal.Signals(result.signal).name)
    elif status == ResultStatus.RETURN_CODE:
        return "Exited with code %d" % result.return_code
    elif status == ResultStatus.TIME_LIMIT:
        if result.was_killed:
            return "Time limit exceeded (killed)"
        else:
            return "Time limit exceeded"
    elif status == ResultStatus.WALL_LIMIT:
        if result.was_killed:
            return "Wall time limit exceeded (killed)"
        else:
            return "Wall time limit exceeded"
    elif status == ResultStatus.MEMORY_LIMIT:
        if result.was_killed:
            return "Memory limit exceeded (killed)"
        else:
            return "Memory limit exceeded"
    elif status == ResultStatus.MISSING_FILES:
        return "Some files are missing"
    elif status == ResultStatus.INTERNAL_ERROR:
        return "Internal error: " + result.error
    else:
        raise ValueError(status)


def get_max_sol_len(interface: UIInterface):
    """
    Compute the maximum length of the source files in the interface
    """
    lens = []
    lens += list(map(len, list(interface.solutions.keys())))
    lens += list(map(len, list(interface.non_solutions.keys())))
    lens += list(map(len, list(interface.statements.keys())))
    for statement in interface.statements.values():
        lens += [len(oth.name) for oth in statement.other_executions]
    return max(lens, default=0)
