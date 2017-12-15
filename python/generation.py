#!/usr/bin/env python3

from typing import Dict  # pylint: disable=unused-import
from typing import List  # pylint: disable=unused-import
from typing import Optional
from bindings import Execution  # pylint: disable=unused-import
from bindings import FileID  # pylint: disable=unused-import
from python.dispatcher import Dispatcher
from python.dispatcher import Event
from python.dispatcher import EventStatus
from python.source_file import SourceFile
from python.task import Task
from python.task import Testcase
from python.ui import GenerationStatus
from python.ui import UI


class SingleGenerationState:
    def __init__(self) -> None:
        self.input_gen = None  # type: Optional[Event]
        self.validation = None  # type: Optional[Execution]
        self.output_gen = None  # type: Optional[Event]


class Generation:
    def _callback(self, testcase_num: int, event: Event,
                  status: EventStatus) -> bool:
        def is_event(event1: Event, event2: Optional[Event]) -> bool:
            if event2 is None:
                return False
            return event1.id() == event2.id()

        if status == EventStatus.FAILURE:
            assert isinstance(event, Execution)
            message = event.stderr().contents(1024 * 1024)
            self._ui.set_generation_status(testcase_num,
                                           GenerationStatus.FAILURE, message)
            return False

        generation_state = self._generations[testcase_num]
        if is_event(event, generation_state.input_gen):
            if status == EventStatus.START:
                self._ui.set_generation_status(testcase_num,
                                               GenerationStatus.GENERATING)
            else:
                self._ui.set_generation_status(testcase_num,
                                               GenerationStatus.GENERATED)
        if is_event(event, generation_state.validation):
            if status == EventStatus.START:
                self._ui.set_generation_status(testcase_num,
                                               GenerationStatus.VALIDATING)
            else:
                self._ui.set_generation_status(testcase_num,
                                               GenerationStatus.VALIDATED)
        if is_event(event, generation_state.output_gen):
            if status == EventStatus.START:
                self._ui.set_generation_status(testcase_num,
                                               GenerationStatus.SOLVING)
            else:
                self._ui.set_generation_status(testcase_num,
                                               GenerationStatus.SUCCESS)
        return True

    def _generate_testcase(self, num: int, testcase: Testcase,
                           cache_mode: Execution.CachingMode) -> None:
        def callback(event: Event, status: EventStatus) -> bool:
            return self._callback(num, event, status)

        if testcase.subtask is None or testcase.subtask.task is None:
            raise ValueError("Invalid testcase configuration")
        task = testcase.subtask.task

        # Input
        generation_state = SingleGenerationState()
        if testcase.input.path is not None:
            input_gen = self._dispatcher.load_file(
                "input %d" % num, testcase.input.path, callback)
            testcase.input_id = input_gen
            generation_state.input_gen = input_gen
        else:
            if testcase.input.generator is None:
                raise ValueError("Invalid testcase configuration")
            if testcase.input.args is None:
                raise ValueError("Invalid testcase configuration")
            generation_state.input_gen = self._generator_cache[
                testcase.input.generator].execute(
                    "Generation of input %d" % num, testcase.input.args,
                    callback, exclusive=False, cache_mode=cache_mode)
            testcase.input_id = generation_state.input_gen.stdout()

        # We make the output generation depend on the validator stdout
        # so that we can ensure that the validation is executed before.
        validator_output = None  # type: Optional[FileID]
        if testcase.input.validator is not None:
            generation_state.validation = self._generator_cache[
                testcase.input.validator].execute(
                    "Validation of input %d" % num,
                    ["input", str(testcase.subtask.num + 1)], callback,
                    exclusive=False, cache_mode=cache_mode)
            assert testcase.input_id is not None  # Help mypy
            generation_state.validation.input("input", testcase.input_id)
            validator_output = generation_state.validation.stdout()

        # Output
        if testcase.output is not None:
            output_gen = self._dispatcher.load_file("output %d" % num,
                                                    testcase.output, callback)
            testcase.output_id = output_gen
            generation_state.output_gen = output_gen
        else:
            if task.solution is None:
                raise ValueError("Invalid task configuration")
            # TODO(edomora97): raise up the timelimit for the solution when generating the
            # official outputs?
            generation_state.output_gen = task.solution.execute(
                "Generation of output %d" % num, [], callback,
                exclusive=False, cache_mode=cache_mode)
            if validator_output is not None:
                generation_state.output_gen.input("dummy_foobar_deadbaba",
                                                  validator_output)
            assert testcase.input_id is not None  # Help mypy
            testcase.output_id = task.setup_io(generation_state.output_gen,
                                               testcase.input_id)
        self._generations.append(generation_state)
        self._ui.set_generation_status(num, GenerationStatus.WAITING)

    def __init__(self, dispatcher: Dispatcher, ui: UI, task: Task,
                 cache_mode: Execution.CachingMode) -> None:
        self._dispatcher = dispatcher
        self._ui = ui
        self._task = task
        self._generator_cache = dict()  # type: Dict[str, SourceFile]
        self._generations = []  # type: List[SingleGenerationState]

        # Compilations needed: solution, checker, generator(s) and validator(s)
        if task.solution_src is not None:
            task.solution = SourceFile(dispatcher, ui, task.solution_src, is_solution=False)
            task.solution.compile(task.graders(task.solution.get_language()), cache_mode=cache_mode)
        if task.checker_src is not None:
            task.checker = SourceFile(dispatcher, ui, task.checker_src, is_solution=False)
            task.checker.compile([], cache_mode=cache_mode)
        for testcase in task.testcases:
            generator_info = (testcase.input.generator,
                              testcase.input.generator_deps)
            validator_info = (testcase.input.validator,
                              testcase.input.validator_deps)
            for binary, deps in [generator_info, validator_info]:
                if binary is None:
                    continue
                if binary in self._generator_cache:
                    continue
                source_file = SourceFile(dispatcher, ui, binary, is_solution=False)
                source_file.compile(deps, cache_mode)
                self._generator_cache[binary] = source_file

        for num, testcase in enumerate(task.testcases):
            self._generate_testcase(num, testcase, cache_mode)
        task.generated = True
