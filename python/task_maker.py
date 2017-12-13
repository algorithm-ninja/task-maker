#!/usr/bin/env python3

import glob
import os
import sys
from typing import List
from typing import Optional

from python.curses_ui import CursesUI
from python.dispatcher import Dispatcher
from python.evaluation import Evaluation
from python.generation import Generation
from python.task import Input
from python.task import ScoreMode
from python.task import Subtask
from python.task import Task
from python.task import Testcase
from python.ui import UI

EXTENSIONS = [".cpp", ".c", ".C", ".cc", ".py"]


def list_files(patterns: List[str],
               exclude: Optional[List[str]] = None) -> List[str]:
    if exclude is None:
        exclude = []
    files = [_file for pattern in patterns
             for _file in glob.glob(pattern)]  # type: List[str]
    return [
        res for res in files
        if res not in exclude and os.path.splitext(res)[1] in EXTENSIONS
    ]


def gen_testcases() -> List[Subtask]:
    generator = None  # type: Optional[str]
    generator_deps = []  # type: List[str]
    validator = None  # type: Optional[str]
    validator_deps = []  # type: List[str]
    subtasks = []  # type: List[Subtask]

    def create_subtask(testcases: List[Testcase], score: float) -> None:
        if testcases:
            subtasks.append(Subtask(score, ScoreMode.MIN, testcases))

    for _generator in list_files(["gen/generator.*", "gen/generatore.*"]):
        generator = _generator
    if not generator:
        raise RuntimeError("No generator found")
    generator_deps = list_files(["gen/varie.*", "gen/limiti.*", "gen/graph.*"])
    for _validator in list_files(["gen/validator.*", "gen/valida.*"]):
        validator = _validator
    if not validator:
        raise RuntimeError("No generator found")
    validator_deps = generator_deps

    current_testcases = []  # type: List[Testcase]
    current_score = 0.0
    for line in open("gen/GEN"):
        if line.startswith("#ST: "):
            create_subtask(current_testcases, current_score)
            current_testcases = []
            current_score = float(line.strip()[5:])
            continue
        elif line.startswith("#COPY: "):
            input_file = line[7:].strip()
            testcase_input = Input(path=input_file)
        else:
            line = line.split("#")[0].strip()
            if not line:
                continue
            testcase_input = Input(
                generator=generator,
                generator_deps=generator_deps,
                validator=validator,
                validator_deps=validator_deps,
                args=line.split())
        current_testcases.append(Testcase(testcase_input))

    create_subtask(current_testcases, current_score)
    # Hack for when subtasks are not specified.
    if len(subtasks) == 1 and subtasks[0].max_score == 0:
        subtasks[0].score_mode = ScoreMode.SUM
        subtasks[0].max_score = 100
    return subtasks


def parse_task_yaml(ui: UI) -> Task:
    # TODO(veluca): read data from task.yaml or ../task_name.yaml.
    time_limit = 1.0
    memory_limit = 256 * 1024
    input_file = None  # type: Optional[str]
    output_file = None  # type: Optional[str]
    task = Task(ui, time_limit, memory_limit)
    if input_file:
        task.set_input_file(input_file)
    if output_file:
        task.set_output_file(output_file)
    return task


def run_for_cwd() -> None:
    official_solution = None  # type: Optional[str]
    solutions = []  # type: List[str]
    graders = []  # type: List[str]
    checker = None  # type: Optional[str]
    subtasks = []  # type: List[Subtask]
    task_name = "test"

    ui = CursesUI(task_name)
    task = parse_task_yaml(ui)

    for solution in list_files(["sol/solution.*", "sol/soluzione.*"]):
        official_solution = solution
    if official_solution is None:
        raise RuntimeError("No official solution found")
    graders = list_files(["sol/grader.*"])
    solutions = list_files(["sol/*"], exclude=graders)

    subtasks = gen_testcases()
    task.add_solution(official_solution)

    if checker is not None:
        task.add_checker(checker)
    for grader in graders:
        task.add_grader(grader)
    for subtask in subtasks:
        task.add_subtask(subtask)
    dispatcher = Dispatcher(ui)
    Generation(dispatcher, ui, task)
    for solution in solutions:
        Evaluation(dispatcher, ui, task, solution)
    if not dispatcher.run():
        ui.fatal_error("Error running task")
    ui.print_final_status()


def main() -> None:
    if len(sys.argv) > 1:
        os.chdir(sys.argv[1])
    run_for_cwd()


if __name__ == '__main__':
    main()
