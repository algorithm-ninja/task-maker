#!/usr/bin/env python3

import argparse
import os

from proto.manager_pb2 import ALL, GENERATION, NOTHING  # CacheMode

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
    print(request)


if __name__ == '__main__':
    main()
