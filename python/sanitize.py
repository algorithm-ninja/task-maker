#!/usr/bin/env python3
import os.path
import string
from typing import List

from task_maker.dependency_finder import Dependency

# TODO the new sandbox supports subfolders, so it's not needed to flatten the
# tree


def sanitize_command(args: List[str]) -> List[Dependency]:
    dependencies = []  # type: List[Dependency]
    for i, arg in enumerate(args):
        if os.path.exists(arg):
            name = sanitize_filename(arg)
            args[i] = name
            dependencies += [Dependency(name=name, path=arg)]
    return dependencies


def sanitize_filename(filename: str) -> str:
    return "".join(
        filter(lambda x: x in string.ascii_letters + string.digits + "_-.",
               filename))
