#!/usr/bin/env python3
import os.path
import string
from task_maker.languages import Dependency
from typing import List


def sanitize_command(args: List[str]) -> List[Dependency]:
    """
    Look at the arguments list, the ones that matches an existing filename is
    considered a dependency and it will be copied inside the sandbox. The args
    parameter's content will be modified and the list of dependencies is
    returned.
    """
    dependencies = []  # type: List[Dependency]
    for i, arg in enumerate(args):
        if os.path.exists(arg):
            name = sanitize_filename(arg)
            args[i] = name
            dependencies += [Dependency(name=name, path=arg)]
    return dependencies


def sanitize_filename(filename: str) -> str:
    """
    Remove unsafe characters from a file name
    """
    allowed = string.ascii_letters + string.digits + "_-./"
    return "".join(filter(lambda x: x in allowed, filename))
