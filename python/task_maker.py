#!/usr/bin/env python3

import argparse
import glob
import os
from typing import Dict, List, Any
from typing import Optional

from external.pyyaml.lib3 import yaml

from bindings import Execution
from python.curses_ui import CursesUI
from python.dispatcher import Dispatcher
from python.evaluation import Evaluation
from python.generation import Generation
from python.print_ui import PrintUI
from python.task import Input
from python.task import ScoreMode
from python.task import Subtask
from python.task import Task
from python.task import Testcase
from python.ui import UI

EXTENSIONS = [".cpp", ".c", ".C", ".cc", ".py", ".sh"]
UIS = {"print": PrintUI, "curses": CursesUI}
CACHES = {
    "all": (Execution.CachingMode.ALWAYS, Execution.CachingMode.SAME_EXECUTOR),
    "generation": (Execution.CachingMode.ALWAYS, Execution.CachingMode.NEVER),
    "nothing": (Execution.CachingMode.NEVER, Execution.CachingMode.NEVER)
}


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
    validator = None  # type: Optional[str]
    subtasks = []  # type: List[Subtask]

    def create_subtask(testcases: List[Testcase], score: float) -> None:
        if testcases:
            subtasks.append(Subtask(score, ScoreMode.MIN, testcases))

    for _generator in list_files(["gen/generator.*", "gen/generatore.*"]):
        generator = _generator
    if not generator:
        raise RuntimeError("No generator found")
    for _validator in list_files(["gen/validator.*", "gen/valida.*"]):
        validator = _validator
    if not validator:
        raise RuntimeError("No validator found")

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
                generator=generator, validator=validator, args=line.split())
        current_testcases.append(Testcase(testcase_input))

    create_subtask(current_testcases, current_score)
    # Hack for when subtasks are not specified.
    if len(subtasks) == 1 and subtasks[0].max_score == 0:
        subtasks[0].score_mode = ScoreMode.SUM
        subtasks[0].max_score = 100
    return subtasks


def detect_yaml() -> str:
    cwd = os.getcwd()
    task_name = os.path.basename(cwd)
    yaml_names = ["task", os.path.join("..", task_name)]
    yaml_ext = ["yaml", "yml"]
    for name in yaml_names:
        for ext in yaml_ext:
            path = os.path.join(cwd, name + "." + ext)
            if os.path.exists(path):
                return path
    raise FileNotFoundError("Cannot find the task yaml of %s" % cwd)


def parse_task_yaml() -> Dict[str, Any]:
    path = detect_yaml()
    with open(path) as yaml_file:
        return yaml.load(yaml_file)


def get_options(data: Dict[str, Any],
                names: List[str],
                default: Optional[Any] = None) -> Any:
    for name in names:
        if name in data:
            return data[name]
    return default


def create_task(ui: UI, data: Dict[str, Any]) -> Task:
    name = get_options(data, ["name", "nome_breve"])
    title = get_options(data, ["title", "nome"])
    if name is None:
        ui.fatal_error("The name is not set in the yaml")
    if title is None:
        ui.fatal_error("The title is not set in the yaml")
    ui.set_task_name("%s (%s)" % (title, name))

    time_limit = get_options(data, ["time_limit", "timeout"])
    memory_limit = get_options(data, ["memory_limit", "memlimit"]) * 1024
    input_file = get_options(data, ["infile"], "input.txt")
    output_file = get_options(data, ["outfile"], "output.txt")

    task = Task(ui, time_limit, memory_limit)
    if input_file:
        task.set_input_file(input_file)
    if output_file:
        task.set_output_file(output_file)
    return task


def run_for_cwd(args: argparse.Namespace) -> None:
    if args.clean:
        Task.do_clean(args.task_dir, args.temp_dir, args.store_dir)
        print("Task directory clean")
        return

    official_solution = None  # type: Optional[str]
    solutions = []  # type: List[str]
    graders = []  # type: List[str]
    checker = None  # type: Optional[str]
    subtasks = []  # type: List[Subtask]
    ui = UI()
    data = parse_task_yaml()

    if args.ui in UIS:
        ui = UIS[args.ui]()
    else:
        raise RuntimeError("Invalid UI %s" % args.ui)

    try:
        task = create_task(ui, data)

        for solution in list_files(["sol/solution.*", "sol/soluzione.*"]):
            official_solution = solution
        if official_solution is None:
            raise RuntimeError("No official solution found")
        graders = list_files(["sol/grader.*"])
        if args.solutions:
            solutions = [
                sol if sol.startswith("sol/") else "sol/" + sol
                for sol in args.solutions
            ]
        else:
            solutions = list_files(["sol/*"], exclude=graders)
        checkers = list_files(["cor/checker.*", "cor/correttore.cpp"])
        if checkers:
            checker = checkers[0]

        subtasks = gen_testcases()
        task.add_solution(official_solution)

        if checker is not None:
            task.add_checker(checker)
        for grader in graders:
            task.add_grader(grader)
        for subtask in subtasks:
            task.add_subtask(subtask)

        cache_mode, eval_cache_mode = CACHES[args.cache]
        eval_executor = args.evaluate_on

        dispatcher = Dispatcher(ui)
        if args.num_cores:
            dispatcher.core.set_num_cores(args.num_cores)
        if args.temp_dir:
            dispatcher.core.set_temp_directory(args.temp_dir)
        if args.store_dir:
            dispatcher.core.set_store_directory(args.store_dir)

        Generation(dispatcher, ui, task, cache_mode)
        for solution in solutions:
            Evaluation(dispatcher, ui, task, solution, args.exclusive,
                       eval_cache_mode, eval_executor)
        if not dispatcher.run():
            raise RuntimeError("Error running task")
        else:
            ui.print_final_status()
    except RuntimeError as exc:
        msg = str(exc)
        if msg.startswith("KeyboardInterrupt"):
            ui.fatal_error("Ctrl-C pressed")
        else:
            ui.fatal_error(str(exc))
            raise
    except Exception as exc:
        ui.fatal_error(str(exc))
        raise

    if args.dry_run:
        print("Dry run mode, the task directory has not been touched")
    else:
        task.store_results(os.getcwd())


def _validate_num_cores(num: str) -> int:
    error_message = "%s is not a positive number" % num
    try:
        if int(num) <= 0:
            raise argparse.ArgumentTypeError(error_message)
        return int(num)
    except ValueError:
        raise argparse.ArgumentTypeError(error_message)


def main() -> None:
    parser = argparse.ArgumentParser(description="The new cmsMake!")
    parser.add_argument(
        "solutions",
        help="Test only these solutions",
        nargs="*",
        default=[],
        metavar="solution")
    parser.add_argument(
        "--task-dir",
        help="Directory of the task to build",
        default=os.getcwd())
    parser.add_argument(
        "--ui",
        help="UI to use",
        action="store",
        choices=UIS.keys(),
        default="curses")
    parser.add_argument(
        "--exclusive",
        help="Evaluate the solutions using only one core at time",
        action="store_true",
        default=False)
    parser.add_argument(
        "--cache",
        help="Cache policy to use",
        action="store",
        choices=CACHES.keys(),
        default="all")
    parser.add_argument(
        "--evaluate-on",
        action="store",
        help="Where evaluations should be run",
        default=None)
    parser.add_argument(
        "--dry-run",
        help="Execute everything but do not touch the task directory",
        action="store_true",
        default=False)
    parser.add_argument(
        "--num-cores",
        help="Number of cores to use",
        action="store",
        type=_validate_num_cores,
        default=None)
    parser.add_argument(
        "--temp-dir",
        help="Where the sandboxes should be created",
        action="store",
        default="temp")
    parser.add_argument(
        "--store-dir",
        help="Where files should be stored",
        action="store",
        default="files")
    parser.add_argument(
        "--clean",
        help="Clear the task directory and exit",
        action="store_true",
        default=False)

    args = parser.parse_args()

    os.chdir(args.task_dir)
    run_for_cwd(args)


if __name__ == '__main__':
    main()
