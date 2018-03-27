#!/usr/bin/env python3

import argparse
import os.path

from proto.manager_pb2 import ALL, GENERATION, NOTHING
from proto.task_pb2 import DEFAULT, X86_64, I686

from python.uis.curses_ui import CursesUI
from python.uis.print_ui import PrintUI
from python.uis.silent_ui import SilentUI

UIS = {"curses": CursesUI, "print": PrintUI, "silent": SilentUI}

CACHES = {"all": ALL, "generation": GENERATION, "nothing": NOTHING}

ARCHS = {"default": DEFAULT, "x86-64": X86_64, "i686": I686}


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


def _validate_arch(arch: str) -> int:
    try:
        return ARCHS[arch]
    except ValueError:
        raise argparse.ArgumentTypeError("Not valid target architecture %s" %
                                         arch)


def get_parser() -> argparse.ArgumentParser:
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
        help="UI to use (%s)" % ("|".join(UIS.keys())),
        choices=UIS.keys(),
        action="store",
        default="curses")
    parser.add_argument(
        "--cache",
        help="Cache policy to use (%s)" % ("|".join(CACHES.keys())),
        action="store",
        type=_validate_cache_mode,
        default="all")
    parser.add_argument(
        "--evaluate-on",
        action="store",
        help="Where evaluations should be run",
        default=None)
    parser.add_argument(
        "--manager-port",
        action="store",
        help="port of the manager",
        default=7071,
        type=int)
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
        "--copy-exe",
        help="Copy executable files in bin/ folder",
        action="store_true",
        default=False)
    parser.add_argument(
        "--keep-sandbox",
        help="Do not drop the sandbox folder",
        action="store_true",
        default=False)
    parser.add_argument(
        "--arch",
        help="Architecture to target the managers in Terry format (%s)"
             % "|".join(ARCHS.keys()),
        action="store",
        type=_validate_arch,
        default="default")
    parser.add_argument(
        "--clean",
        help="Clear the task directory and exit",
        action="store_true",
        default=False)
    parser.add_argument(
        "--format",
        help="Format of the task (ioi|terry)",
        choices=["ioi", "terry"],
        action="store",
        default=None)

    return parser
