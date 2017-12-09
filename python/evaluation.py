#!/usr/bin/env python3

import shutil
from typing import cast
from typing import List
from typing import Optional  # pylint: disable=unused-import
from bindings import Execution
from python.dispatcher import Dispatcher
from python.dispatcher import Event
from python.dispatcher import EventStatus
from python.source_file import SourceFile
from python.task import Subtask
from python.task import Task
from python.task import Testcase
from python.ui import EvaluationResult
from python.ui import EvaluationStatus
from python.ui import UI


class SingleEvaluationState:
    def __init__(self, execution: Execution, check: Execution,
                 subtask_num: int, testcase_offset: int,
                 has_checker: bool) -> None:
        self.execution = execution
        self.check = check
        self.subtask_num = subtask_num
        self.testcase_offset = testcase_offset
        self.has_checker = has_checker


class SubtaskScoreInfo:
    def __init__(self, evaluation: 'Evaluation', subtask: Subtask,
                 ui: UI) -> None:
        self._subtask = subtask
        self._testcase_scores = \
            [None for _ in subtask.testcases]  # type: List[Optional[float]]
        self._evaluation = evaluation
        self._ui = ui

    def update_score(self, testcase_offset: int, score: float) -> None:
        self._testcase_scores[testcase_offset] = score
        if all(score is not None for score in self._testcase_scores):
            testcase_scores = cast(List[float], self._testcase_scores)
            score = self._subtask.compute_score(testcase_scores)
            self._ui.set_subtask_score(self._subtask.num,
                                       self._evaluation.solution_src, score)
            self._evaluation.update_score(self._subtask.num, score)


class Evaluation:
    def _callback(self, testcase_num: int, event: Event,
                  status: EventStatus) -> bool:
        evaluation_state = self._evaluations[testcase_num]
        execution = evaluation_state.execution

        def evaluation_result(score: float, msg: str) -> EvaluationResult:
            return EvaluationResult(score, msg,
                                    execution.cpu_time(),
                                    execution.wall_time(), execution.memory())

        if status == EventStatus.START:
            if execution.id() == event.id():
                self._ui.set_evaluation_status(testcase_num, self.solution_src,
                                               EvaluationStatus.EXECUTING)
            else:
                self._ui.set_evaluation_status(testcase_num, self.solution_src,
                                               EvaluationStatus.CHECKING)
            return True
        if status == EventStatus.SUCCESS and event.id() == execution.id():
            self._ui.set_evaluation_status(testcase_num, self.solution_src,
                                           EvaluationStatus.EXECUTED)
            return True
        if status == EventStatus.FAILURE and evaluation_state.has_checker \
                and event.id() == evaluation_state.check:
            display_msg = evaluation_state.check.stderr().contents(1024 * 1024)
            self._ui.set_evaluation_status(testcase_num, self.solution_src,
                                           EvaluationStatus.FAILURE,
                                           evaluation_result(0.0, display_msg))
            return False
        if status == EventStatus.FAILURE and event.id() == execution.id():
            if execution.signal() != 0:
                display_msg = "Signal " + str(execution.signal())
            elif execution.status_code() != 0:
                display_msg = "Return code " + str(execution.status_code())
            else:
                display_msg = "Missing output files"
            score = 0.0
        if not evaluation_state.has_checker:
            if status == EventStatus.FAILURE:
                display_msg = "Output not correct"
                score = 0.0
            else:
                display_msg = "Output is correct"
                score = 1.0
        else:
            display_msg = evaluation_state.check.stderr().contents(1024 * 1024)
            try:
                score = float(
                    evaluation_state.check.stdout().contents(1024 * 1024))
            except ValueError:
                self._ui.set_evaluation_status(
                    testcase_num, self.solution_src, EvaluationStatus.FAILURE,
                    evaluation_result(0.0, display_msg),
                    "Invalid score returned by checker")
        self._ui.set_evaluation_status(testcase_num, self.solution_src,
                                       EvaluationStatus.SUCCESS,
                                       evaluation_result(score, display_msg))
        self._subtask_score_info[evaluation_state.subtask_num].update_score(
            evaluation_state.testcase_offset, score)
        return True

    def _evaluate_testcase(self, num: int, testcase: Testcase) -> None:
        def callback(event: Event, status: EventStatus) -> bool:
            return self._callback(num, event, status)

        if testcase.input_id is None or testcase.output_id is None \
                or testcase.subtask is None:
            raise ValueError("Invalid testcase state")

        execution = self._solution.execute(
            "Evaluation of solution %s on testcase %d" % (self.solution_src,
                                                          num), [], callback)
        execution.cpu_limit(self._task.time_limit)
        execution.wall_limit(self._task.time_limit + 0.2)
        execution.memory_limit(self._task.memory_limit)
        contestant_output = self._task.setup_io(execution, testcase.input_id)
        check_description = "Checking result of solution %s on testcase %d" % (
            self.solution_src, num)
        if self._task.checker is None:
            has_checker = False
            # TODO(veluca): replace this with our own utility?
            check = self._dispatcher.add_execution(
                check_description,
                cast(str, self._diff_path),
                ["-w", "output", "contestant_output"], callback)
        else:
            has_checker = True
            check = self._task.checker.execute(
                check_description, ["input", "output",
                                    "contestant_output"], callback)
            check.input("input", testcase.input_id)
        check.input("output", testcase.output_id)
        check.input("contestant_output", contestant_output)
        check.cpu_limit(10 * self._task.time_limit)
        check.memory_limit(10 * self._task.memory_limit)
        testcase_offset = testcase.num - testcase.subtask.testcases[0].num
        self._evaluations.append(
            SingleEvaluationState(execution, check, testcase.subtask.num,
                                  testcase_offset, has_checker))
        self._ui.set_evaluation_status(num, self.solution_src,
                                       EvaluationStatus.WAITING)

    def __init__(self, dispatcher: Dispatcher, ui: UI, task: Task,
                 solution: str) -> None:
        if not task.generated:
            raise ValueError("You must first generate the task")
        self._diff_path = shutil.which("diff")
        if task.checker is None and self._diff_path is None:
            raise RuntimeError(
                "Could not find diff utility and no checker present")
        self.solution_src = solution
        self.subtask_scores = \
            [None for _ in task.subtasks]  # type: List[Optional[float]]
        self.score = None  # type: Optional[float]
        self._dispatcher = dispatcher
        self._solution = SourceFile(dispatcher, ui, solution, True)
        self._solution.compile(task.graders(self._solution.get_language()))
        self._task = task
        self._ui = ui
        self._evaluations = []  # type: List[SingleEvaluationState]
        self._subtask_score_info = \
            [SubtaskScoreInfo(self, subtask, ui) for subtask in task.subtasks]
        for num, testcase in enumerate(task.testcases):
            self._evaluate_testcase(num, testcase)

    def update_score(self, subtask_num: int, score: float) -> None:
        self.subtask_scores[subtask_num] = score
        if all(score is not None for score in self.subtask_scores):
            self.score = sum(self.subtask_scores)
            self._ui.set_task_score(self.solution_src, cast(float, self.score))
