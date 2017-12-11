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
        self._ui_thread = threading.Thread(
            target=curses.wrapper, args=(self._ui, ))
        self._ui_thread.start()

    def _ui(self, stdscr: 'curses._CursesWindow') -> None:
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, curses.COLORS):
            curses.init_pair(i, i, -1)
        curses.halfdelay(1)
        loading_chars = "-\\|/"
        cur_loading_char = 0

        loading_attr = curses.A_BOLD
        if curses.COLORS >= 256:
            # Extended color support
            success_attr = curses.A_BOLD | curses.color_pair(82)
        else:
            success_attr = curses.color_pair(curses.COLOR_GREEN)
        failure_attr = curses.A_BOLD | curses.color_pair(curses.COLOR_RED)

        def print_compilation_status(status: CompilationStatus) -> None:
            if status == CompilationStatus.WAITING:
                stdscr.addstr("...\n")
            elif status == CompilationStatus.RUNNING:
                stdscr.addstr(loading_chars[cur_loading_char], loading_attr)
                stdscr.addstr("\n")
            elif status == CompilationStatus.SUCCESS:
                stdscr.addstr("OK", success_attr)
                stdscr.addstr("\n")
            elif status == CompilationStatus.FAILURE:
                stdscr.addstr("FAILURE", failure_attr)
                stdscr.addstr("\n")

        def subtask_scores(status: SolutionStatus) -> str:
            loading = loading_chars[cur_loading_char]
            res = ""
            if not status.subtask_scores:
                res += "% 4s" % "..."
            elif status.score is not None:
                res += "% 4.f" % status.score
            else:
                res += "% 4s" % loading

            for subtask in self._subtask_max_scores:
                testcases = self._subtask_testcases[subtask]
                if all(tc not in status.testcase_status or
                       status.testcase_status[tc] == EvaluationStatus.WAITING
                       for tc in testcases):
                    res += " % 6s" % "..."
                elif subtask in status.subtask_scores:
                    res += " % 6.f" % status.subtask_scores[subtask]
                else:
                    res += " % 6s" % loading

            return res

        while True:
            cur_loading_char = (cur_loading_char + 1) % len(loading_chars)
            stdscr.clear()

            if self._done:
                stdscr.addstr("Done\n", success_attr)
            elif self._failure:
                stdscr.addstr("Failure\n", failure_attr)
            else:
                stdscr.addstr("Running...\n", loading_attr)

            stdscr.addstr("Time limit: %.2f\n" % self._time_limit)
            stdscr.addstr("Memory limit: %.2f\n" % (self._memory_limit / 1024))
            for comp in self._other_compilations:
                stdscr.addstr("%30s: " % comp)
                print_compilation_status(self._compilation_status[comp])

            stdscr.addstr("\n")
            for comp in sorted(self._solutions):
                stdscr.addstr("%30s: " % comp)
                print_compilation_status(self._compilation_status[comp])
            stdscr.addstr("\n")

            stdscr.addstr(
                "Generation status: % 2d/%d\n" % (len(
                    list(
                        filter(lambda x: x == GenerationStatus.SUCCESS,
                               self._generation_status.values()))),
                                                  self._num_testcases))
            stdscr.addstr("\n")

            stdscr.addstr("%s score" % (" " * 39))
            for max_score in self._subtask_max_scores.values():
                stdscr.addstr("% 6.f " % max_score)
            stdscr.addstr("\n")

            for sol in sorted(self._solutions):
                stdscr.addstr("%30s: % 3d/%d  %s\n" %
                              (sol,
                               len(self._solution_status[sol].testcase_result),
                               self._num_testcases,
                               subtask_scores(self._solution_status[sol])))
            stdscr.refresh()
            try:
                pressed_key = stdscr.getkey()
                if self._done and pressed_key == 'q':
                    break
            except curses.error:
                pass

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
            if file_name not in self._solution_status:
                self._solution_status[file_name] = SolutionStatus()
        else:
            if file_name not in self._other_compilations:
                self._other_compilations.append(file_name)
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

    def fatal_error(self, msg: str) -> None:
        self._failure = msg
