#!/usr/bin/env python3

import argparse
import os

from proto.manager_pb2 import ALL, GENERATION, NOTHING  # CacheMode
from proto.manager_pb2 import EvaluateTaskRequest
from proto.task_pb2 import Task, Subtask, TestCase, SourceFile, GraderInfo

from python.curses_ui import CursesUI
from python.italian_format import get_request
from python.print_ui import PrintUI
from python.silent_ui import SilentUI

UIS = {
    "curses": CursesUI,
    "print": PrintUI,
    "silent": SilentUI
}

CACHES = {
    "all": ALL,
    "generation": GENERATION,
    "nothing": NOTHING
}


def absolutize_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(os.getcwd(), path)


def absolutize_source_file(source_file: SourceFile) -> None:
    source_file.path = absolutize_path(source_file.path)
    for dependency in source_file.deps:
        dependency.path = absolutize_path(dependency.path)


def absolutize_testcase(testcase: TestCase) -> None:
    if testcase.HasField("generator"):
        absolutize_source_file(testcase.generator)
    if testcase.HasField("validator"):
        absolutize_source_file(testcase.validator)
    if testcase.input_file:
        testcase.input_file = absolutize_path(testcase.input_file)
    if testcase.output_file:
        testcase.output_file = absolutize_path(testcase.output_file)


def absolutize_subtask(subtask: Subtask) -> None:
    for testcase in subtask.testcases:
        absolutize_testcase(testcase)


def absolutize_grader_info(info: GraderInfo) -> None:
    for dependency in info.files:
        dependency.path = absolutize_path(dependency.path)


def absolutize_task(task: Task) -> None:
    for subtask in task.subtasks:
        absolutize_subtask(subtask)
    if task.HasField("official_solution"):
        absolutize_source_file(task.official_solution)
    for info in task.grader_info:
        absolutize_grader_info(info)
    if task.HasField("checker"):
        absolutize_source_file(task.checker)


def absolutize_request(request: EvaluateTaskRequest) -> None:
    absolutize_task(request.task)
    for solution in request.solutions:
        absolutize_source_file(solution)
    request.store_dir = absolutize_path(request.store_dir)
    request.temp_dir = absolutize_path(request.temp_dir)
    for testcase in request.write_inputs_to:
        request.write_inputs_to[testcase] =\
            absolutize_path(request.write_inputs_to[testcase])
    for testcase in request.write_outputs_to:
        request.write_outputs_to[testcase] =\
            absolutize_path(request.write_outputs_to[testcase])
    if request.write_checker_to:
        request.write_checker_to = absolutize_path(request.write_checker_to)


def _validate_num_cores(num: str) -> int:
    error_message = "%s is not a positive number" % num
    try:
        if int(num) <= 0:
            raise argparse.ArgumentTypeError(error_message)
        return int(num)
    except ValueError:
        raise argparse.ArgumentTypeError(error_message)


def _validate_cache_mode(mode: str) -> int:
    try:
        return CACHES[mode]
    except ValueError:
        raise argparse.ArgumentTypeError("Not valid cache mode %s" % mode)


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
        "--cache",
        help="Cache policy to use",
        action="store",
        choices=CACHES.keys(),
        type=_validate_cache_mode,
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

    if args.clean:
        # TODO: implement the clean process on the manager
        return

    request = get_request(args)
    absolutize_request(request)
    print(request)


if __name__ == '__main__':
    main()
