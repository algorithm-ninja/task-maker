#!/usr/bin/env python3

import argparse
import os.path
from enum import Enum

# from task_maker.uis.curses_ui import CursesUI
# from task_maker.uis.print_ui import PrintUI
# from task_maker.uis.silent_ui import SilentUI
from task_maker.formats import Arch
from task_maker.version import TASK_MAKER_VERSION
from task_maker import CacheMode

# TODO restore the UIs classes
# class UIS(Enum):
#     curses = CursesUI
#     print = PrintUI
#     silent = SilentUI


class UIS(Enum):
    CURSES = 0
    PRINT = 1
    SILENT = 2


for cls in [UIS, CacheMode, Arch]:

    def from_string(cls, name: str):
        try:
            return cls[name.upper()]
        except:
            raise ValueError()

    cls.__new__ = from_string
    cls.__str__ = lambda self: self.name.lower()


def _validate_num_cores(num: str) -> int:
    error_message = "%s is not a positive number" % num
    try:
        if int(num) <= 0:
            raise argparse.ArgumentTypeError(error_message)
        return int(num)
    except ValueError:
        raise argparse.ArgumentTypeError(error_message)


def add_generic_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Generic options")
    group.add_argument(
        "--task-dir",
        help="Directory of the task to build",
        default=os.getcwd())
    group.add_argument(
        "--max-depth",
        help="Look at most for this number of parents to search the task",
        type=int,
        default=2)
    group.add_argument(
        "--ui",
        help="UI to use",
        choices=list(UIS),
        type=UIS,
        action="store",
        default="curses")
    group.add_argument(
        "--cache",
        help="Cache policy to use",
        action="store",
        choices=list(CacheMode),
        type=CacheMode,
        default="all")
    group.add_argument(
        "--dry-run",
        help="Execute everything but do not touch the task directory",
        action="store_true",
        default=False)
    group.add_argument(
        "--clean",
        help="Clear the task directory and exit",
        action="store_true",
        default=False)
    group.add_argument(
        "--format",
        help="Format of the task (ioi|terry)",
        choices=["ioi", "terry"],
        action="store",
        default=None)


def add_remote_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Remote options")
    group.add_argument(
        "--evaluate-on",
        action="store",
        help="Where evaluations should be run",
        default=None)
    group.add_argument(
        "--manager-port",
        action="store",
        help="Port of the manager",
        default=7071,
        type=int)
    group.add_argument(
        "--run-manager",
        action="store",
        nargs=argparse.REMAINDER,
        help="Run the manager in foreground instead of running a task",
        default=None)
    group.add_argument(
        "--run-server",
        action="store",
        nargs=argparse.REMAINDER,
        help="Run the server in foreground instead of running a task",
        default=None)
    group.add_argument(
        "--run-worker",
        action="store",
        nargs=argparse.REMAINDER,
        help="Run a worker in foreground instead of running a task",
        default=None)


def add_execution_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Execution options")
    group.add_argument(
        "--num-cores",
        help="Number of cores to use",
        action="store",
        type=_validate_num_cores,
        default=None)
    group.add_argument(
        "--exclusive",
        help="Evaluate the solutions one test at the time",
        action="store_true",
        default=False)
    group.add_argument(
        "--extra-time",
        help="Add some time to the evaluation of the solutions",
        action="store",
        type=float,
        default=0)
    group.add_argument(
        "--temp-dir",
        help="Where the sandboxes should be created",
        action="store",
        default="temp")
    group.add_argument(
        "--store-dir",
        help="Where files should be stored",
        action="store",
        default="files")
    group.add_argument(
        "--copy-exe",
        help="Copy executable files in bin/ folder",
        action="store_true",
        default=False)
    group.add_argument(
        "--keep-sandbox",
        help="Do not drop the sandbox folder",
        action="store_true",
        default=False)
    group.add_argument(
        "--quit-manager",
        help="Tell the manager to quit after processing the last request",
        action="store_true",
        default=False)
    group.add_argument(
        "--kill-manager",
        help="Tell the manager to quit ASAP",
        action="store_true",
        default=False)


def add_terry_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Terry options")
    group.add_argument(
        "--arch",
        help="Architecture to target the managers in Terry format",
        action="store",
        choices=list(Arch),
        type=Arch,
        default="default")

    group.add_argument(
        "--seed",
        help="Seed for the terry generator",
        type=int,
        action="store",
        default=None)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="The new cmsMake!")
    parser.add_argument(
        "--version", action="version", version=TASK_MAKER_VERSION)
    add_generic_group(parser)
    add_remote_group(parser)
    add_execution_group(parser)
    add_terry_group(parser)

    parser.add_argument(
        "solutions",
        help="Test only these solutions",
        nargs="*",
        default=[],
        metavar="solution")

    return parser
