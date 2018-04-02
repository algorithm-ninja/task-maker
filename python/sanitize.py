#!/usr/bin/env python
import os.path
import string
from typing import List

from python.dependency_finder import Dependency


def sanitize_command(args):
    # type: (List[str]) -> List[Dependency]
    dependencies = []  # type: List[Dependency]
    for i, arg in enumerate(args):
        if os.path.exists(arg):
            name = sanitize_filename(arg)
            args[i] = name
            dependencies += [Dependency(name=name, path=arg)]
    return dependencies


def sanitize_filename(filename):
    # type: (str) -> str
    return "".join(
        filter(lambda x: x in string.ascii_letters + string.digits + "_-.",
               filename))
