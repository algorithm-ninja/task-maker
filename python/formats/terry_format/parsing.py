#!/usr/bin/env python3
import os.path
import platform
from task_maker.args import Arch
from task_maker.config import Config
from task_maker.formats import get_options, TerryTask, list_files, \
    get_solutions
from task_maker.formats.ioi_format.parsing import parse_task_yaml
from task_maker.source_file import SourceFile
from typing import Optional, List


def get_extension(target_arch: Arch):
    """
    In terry format the managers should have an extension dependent on the
    platform and the architecture. This function returns the extension (starting
    with a dot).
    """
    if target_arch == Arch.DEFAULT:
        return "." + platform.system().lower() + "." + platform.machine()
    elif target_arch == Arch.X86_64:
        return "." + platform.system().lower() + ".x86_64"
    elif target_arch == Arch.I686:
        return "." + platform.system().lower() + ".i686"
    else:
        raise ValueError("Unsupported architecture")


def get_manager(manager: str, target_arch: Arch,
                optional: bool = False) -> Optional[SourceFile]:
    """
    Search for a manager and create the relative SourceFile. `manager` is the
    base name without the extension (eg. "checker"). If `optional` is set to
    true and no managers are found, None is returned, otherwise an exception is
    raised.
    """
    managers = list_files(["managers/%s.*" % manager],
                          exclude=["managers/%s.*.*" % manager])
    if len(managers) == 0:
        if not optional:
            raise FileNotFoundError("Missing manager: %s" % manager)
        return None
    if len(managers) != 1:
        raise ValueError("Ambiguous manager: " + ", ".join(managers))
    return SourceFile.from_file(
        managers[0], manager, True,
        "managers/%s%s" % (manager, get_extension(target_arch)), target_arch,
        {})


def create_task_from_yaml(data) -> TerryTask:
    """
    Extract the base information about a task.
    """
    name = get_options(data, ["name", "nome_breve"])
    title = get_options(data, ["description", "nome"])
    max_score = get_options(data, ["max_score"])
    if name is None:
        raise ValueError("The name is not set in the yaml")
    if title is None:
        raise ValueError("The title is not set in the yaml")

    return TerryTask(name, title, max_score)


def get_task(config: Config) -> TerryTask:
    """
    Extract all the information of a task.
    """
    data = parse_task_yaml()
    if not data:
        raise RuntimeError("The task.yaml is not valid")

    task = create_task_from_yaml(data)

    task.generator = get_manager("generator", config.arch)
    task.validator = get_manager("validator", config.arch, optional=True)
    task.official_solution = get_manager(
        "solution", config.arch, optional=True)
    task.checker = get_manager("checker", config.arch)
    return task


def get_task_solutions(config: Config, task: TerryTask) -> List[SourceFile]:
    """
    Search in the solutions/ folder and using the provided filters, get a list
    of all the solutions.
    """
    solutions = get_solutions(config.solutions, "solutions/", [])
    sols = []  # type: List[SourceFile]
    for solution in solutions:
        path, ext = os.path.splitext(os.path.basename(solution))
        source = SourceFile.from_file(solution, task.name, config.copy_exe,
                                      "bin/" + path + "_" + ext[1:],
                                      Arch.DEFAULT, {})
        sols.append(source)

    return sols
