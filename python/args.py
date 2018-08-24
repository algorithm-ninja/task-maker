#!/usr/bin/env python3

import argparse
import os.path
from enum import Enum

from task_maker.formats import Arch
from task_maker.version import TASK_MAKER_VERSION


class CacheMode(Enum):
    ALL = 0
    REEVALUATE = 1
    NOTHING = 2


class UIS(Enum):
    CURSES = 0
    PRINT = 1
    SILENT = 2


class TaskFormat(Enum):
    IOI = 0
    TERRY = 1
    TM = 2


for cls in [UIS, CacheMode, TaskFormat, Arch]:

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
        help="Format of the task",
        action="store",
        choices=list(TaskFormat),
        type=TaskFormat,
        default=None)


def add_remote_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Remote options")
    group.add_argument(
        "--server",
        action="store",
        help="address[:port] of the server to connect to",
        default="localhost:7071")
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
        "--copy-exe",
        help="Copy executable files in bin/ folder",
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
