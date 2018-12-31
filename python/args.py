#!/usr/bin/env python3

import argparse
from enum import Enum

try:
    # this files comes from the build system
    from task_maker.version import TASK_MAKER_VERSION
except ImportError:
    TASK_MAKER_VERSION = "unknown"


class CacheMode(Enum):
    """
    The mode on how the cache should be used
    """
    ALL = 0  # cache everything
    REEVALUATE = 1  # do not cache the evaluations
    NOTHING = 2  # do not cache anything


class UIS(Enum):
    """
    Kind of UI to use
    """
    CURSES = 0  # animated terminal curses interface
    PRINT = 1  # print to stdout the information as soon as they arrive
    JSON = 2  # print json information instead of plain text
    SILENT = 3  # do not print


class TaskFormat(Enum):
    """
    Format of the task
    """
    IOI = 0  # IOI-like task
    TERRY = 1  # Terry-like task
    TM = 2  # Task-maker format


class Arch(Enum):
    """
    Architecture to target the executables
    """
    DEFAULT = 0  # use the default one
    X86_64 = 1  # force x86-64 64-bit executables
    I686 = 2  # force i686 32-bit executables


# patch the classes for argparse
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


def add_generic_group(parser: argparse.ArgumentParser, bulk: bool):
    group = parser.add_argument_group("Generic options")
    if not bulk:
        group.add_argument("--task-dir", help="Directory of the task to build")
        group.add_argument(
            "--max-depth",
            help="Look at most for this number of parents to search the task",
            type=int)
    group.add_argument(
        "--ui", help="UI to use", choices=list(UIS), type=UIS, action="store")
    group.add_argument(
        "--cache",
        help="Cache policy to use",
        action="store",
        choices=list(CacheMode),
        type=CacheMode)
    group.add_argument(
        "--dry-run",
        help="Execute everything but do not touch the task directory",
        action="store_true")
    group.add_argument(
        "--clean",
        help="Clear the task directory and exit",
        action="store_true")
    group.add_argument(
        "--task-info",
        help="Show the task information and exit",
        action="store_true")
    group.add_argument(
        "--format",
        help="Format of the task",
        action="store",
        choices=list(TaskFormat),
        type=TaskFormat)
    group.add_argument(
        "--fuzz-checker",
        action="store",
        nargs=2,
        metavar=("INPUT_FILE", "OUTPUT_FILE"),
        help="Fuzz the checker mutating the output file with radamsa")


def add_remote_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Remote options")
    group.add_argument(
        "--server",
        action="store",
        help="address[:port] of the server to connect to")
    group.add_argument(
        "--no-spawn",
        action="store_true",
        help="Never spawn the server and worker, will fail if cannot connect")
    group.add_argument(
        "--run-server",
        action="store_true",
        help="Run the server in foreground instead of running a task")
    group.add_argument(
        "--run-worker",
        action="store_true",
        help="Run a worker in foreground instead of running a task")
    group.add_argument(
        "--stop",
        action="store_true",
        help="Stop all the running task-maker processes")
    group.add_argument(
        "--storedir",
        action="store",
        help="Path where the files should be stored")
    group.add_argument(
        "--tempdir",
        action="store",
        help="Path where the sandboxes should be stored")
    group.add_argument(
        "--cache-size",
        action="store",
        type=int,
        help="Maximum size of the cache, in megabytes. 0 means unlimited")


def add_server_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Server options")
    group.add_argument(
        "--server-logfile",
        action="store",
        help="Path where the log file of the server should be stored")
    group.add_argument(
        "--server-pidfile",
        action="store",
        help="Path where the pidfile of the server should be stored")
    group.add_argument(
        "--server-address", action="store", help="Address to listen on")
    group.add_argument(
        "--server-port", action="store", type=int, help="Port to listen on")
    group.add_argument(
        "--server-verbose",
        action="store_true",
        help="Verbose logging for the server")


def add_worker_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Worker group")
    group.add_argument(
        "--worker-logfile",
        action="store",
        help="Path where the log file of the worker should be stored")
    group.add_argument(
        "--worker-pidfile",
        action="store",
        help="Path where the pidfile of the worker should be stored")
    group.add_argument(
        "--worker-keep-sandboxes",
        action="store_true",
        help="Keep the sandboxes after evaluation")
    group.add_argument(
        "--worker-name", action="store", help="Name of this worker")
    group.add_argument(
        "--worker-num-cores",
        action="store",
        type=int,
        help="Number of cores to use")
    group.add_argument(
        "--worker-port", action="store", type=int, help="Port to connect to")
    group.add_argument(
        "--worker-address", action="store", help="Address to connect to")
    group.add_argument(
        "--worker-pending-requests",
        action="store",
        type=int,
        help="Maximum number of pending requests")
    group.add_argument(
        "--worker-verbose",
        action="store_true",
        help="Verbose logging for the worker")


def add_execution_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Execution options")
    group.add_argument(
        "--exclusive",
        help="Evaluate the solutions one test at the time",
        action="store_true")
    group.add_argument(
        "--extra-time",
        help="Add some time to the evaluation of the solutions",
        action="store",
        type=float)
    group.add_argument(
        "--copy-exe",
        help="Copy executable files in bin/ folder",
        action="store_true")


def add_ioi_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("IOI options")
    group.add_argument(
        "--detailed-checker",
        help="Show the execution information also for the checker",
        action="store_true")


def add_terry_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Terry options")
    group.add_argument(
        "--arch",
        help="Architecture to target the managers in Terry format",
        action="store",
        choices=list(Arch),
        type=Arch)

    group.add_argument(
        "--seed",
        help="Seed for the terry generator",
        type=int,
        action="store")


def add_statement_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Statement options")
    group.add_argument(
        "--no-statement",
        help="Do not compile the statements",
        action="store_true")
    group.add_argument(
        "--set",
        help="Set a template variable for the statements",
        action="append")


def add_help_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Help options")
    group.add_argument(
        "--help-colors",
        help="Display some help about the used colors in the UI",
        action="store_true")


def add_bulk_group(parser: argparse.ArgumentParser):
    group = parser.add_argument_group("Bulk options")
    group.add_argument(
        "--contest-dir", help="Directory with all the tasks to build")
    group.add_argument(
        "--contest-yaml",
        help="Path to the contest.yaml to get the tasks from")
    group.add_argument(
        "--make-booklet",
        help="Build the booklet with the statements of all the tasks",
        action="store_true")


def get_parser(bulk: bool) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="The new cmsMake!")
    parser.add_argument(
        "--version", action="version", version=TASK_MAKER_VERSION)
    add_generic_group(parser, bulk)
    add_remote_group(parser)
    add_server_group(parser)
    add_worker_group(parser)
    add_execution_group(parser)
    add_ioi_group(parser)
    add_terry_group(parser)
    add_statement_group(parser)
    add_help_group(parser)
    if bulk:
        add_bulk_group(parser)

    parser.add_argument(
        "solutions",
        help="Test only these solutions",
        nargs="*",
        metavar="solution")

    return parser
