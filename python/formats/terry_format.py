#!/usr/bin/env python3
import glob
import os.path
import platform
import random
import traceback
from typing import Optional, List

from task_maker.args import Arch, CacheMode, UIS
from task_maker.config import Config
from task_maker.formats import get_options, TerryTask, list_files, \
    get_solutions, TaskFormat
from task_maker.formats.ioi_format import parse_task_yaml
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import Frontend
from task_maker.uis.terry import TerryUIInterface
from task_maker.uis.terry_curses_ui import TerryCursesUI
from task_maker.uis.terry_finish_ui import TerryFinishUI


def get_extension(target_arch: Arch):
    if target_arch == Arch.DEFAULT:
        return "." + platform.system().lower() + "." + platform.machine()
    elif target_arch == Arch.X86_64:
        return "." + platform.system().lower() + ".x86_64"
    elif target_arch == Arch.I686:
        return "." + platform.system().lower() + ".i686"
    else:
        raise ValueError("Unsupported architecture")


def create_task_from_yaml(data) -> TerryTask:
    name = get_options(data, ["name", "nome_breve"])
    title = get_options(data, ["description", "nome"])
    max_score = get_options(data, ["max_score"])
    if name is None:
        raise ValueError("The name is not set in the yaml")
    if title is None:
        raise ValueError("The title is not set in the yaml")

    return TerryTask(name, title, max_score)


def get_manager(manager: str, target_arch: Arch,
                optional: bool = False) -> Optional[SourceFile]:
    managers = list_files(
        ["managers/%s.*" % manager], exclude=["managers/%s.*.*" % manager])
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


def get_task(config: Config) -> TerryTask:
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
    solutions = get_solutions(config.solutions, "solutions/", [])
    sols = []  # type: List[SourceFile]
    for solution in solutions:
        path, ext = os.path.splitext(os.path.basename(solution))
        source = SourceFile.from_file(solution, task.name, config.copy_exe,
                                      "bin/" + path + "_" + ext[1:],
                                      Arch.DEFAULT, {})
        sols.append(source)

    return sols


def evaluate_task(frontend: Frontend, task: TerryTask,
                  solutions: List[SourceFile],
                  config: Config) -> TerryUIInterface:
    ui_interface = TerryUIInterface(task, config.ui == UIS.PRINT)
    if config.ui == UIS.CURSES:
        curses_ui = TerryCursesUI(ui_interface)
        curses_ui.start()

    try:
        task.generator.prepare(frontend, config)
        ui_interface.add_non_solution(task.generator)
        if task.validator:
            task.validator.prepare(frontend, config)
            ui_interface.add_non_solution(task.validator)
        if task.official_solution:
            task.official_solution.prepare(frontend, config)
            ui_interface.add_non_solution(task.official_solution)
        task.checker.prepare(frontend, config)
        ui_interface.add_non_solution(task.checker)

        for solution in solutions:
            solution.prepare(frontend, config)
            ui_interface.add_solution(solution)
            evaluate_solution(frontend, task, solution, config, ui_interface)

        frontend.evaluate()
    except:
        if config.ui == UIS.CURSES:
            curses_ui.stop()
        traceback.print_exc()
        return ui_interface

    if config.ui == UIS.CURSES:
        if curses_ui.errored:
            return ui_interface
        curses_ui.stop()
    if config.ui != UIS.SILENT:
        finish_ui = TerryFinishUI(config, task, ui_interface)
        finish_ui.print()
    return ui_interface


def evaluate_solution(frontend: Frontend, task: TerryTask,
                      solution: SourceFile, config: Config,
                      interface: TerryUIInterface):
    if config.seed:
        seed = config.seed
    else:
        seed = random.randint(0, 2**31 - 1)
    name = solution.name

    generation = task.generator.execute(
        frontend, "Generation of input for solution {} with seed {}".format(
            name, seed), [str(seed), "0"])
    if config.cache == CacheMode.NOTHING:
        generation.disableCache()
    input = generation.stdout(False)
    if task.official_solution:
        generation.addInput(task.official_solution.exe_name,
                            task.official_solution.executable)
    interface.add_generation(name, seed, generation)

    if task.validator:
        validation = task.validator.execute(
            frontend, "Validation of input for solution {}".format(name),
            ["0"])
        if config.cache == CacheMode.NOTHING:
            validation.disableCache()
        validation.setStdin(input)
        if task.official_solution:
            validation.addInput(task.official_solution.exe_name,
                                task.official_solution.executable)
        interface.add_validation(name, validation)

    solving = solution.execute(frontend, "Running solution {}".format(name),
                               [])
    if config.cache != CacheMode.ALL:
        solving.disableCache()
    solving.setStdin(input)
    if task.validator:
        solving.addInput("wait_for_validation", validation.stdout(False))
    output = solving.stdout(False)
    interface.add_solving(name, solving)

    checker = task.checker.execute(
        frontend, "Checking solution {}".format(name), ["input", "output"])
    if config.cache == CacheMode.NOTHING:
        checker.disableCache()
    checker.addInput("input", input)
    checker.addInput("output", output)
    if task.official_solution:
        checker.addInput(task.official_solution.exe_name,
                         task.official_solution.executable)
    interface.add_checking(name, checker)


class TerryFormat(TaskFormat):
    @staticmethod
    def clean():
        def remove_file(path: str) -> None:
            try:
                os.remove(path)
            except OSError:
                pass

        for manager in glob.glob("managers/*.*.*"):
            remove_file(manager)

    @staticmethod
    def evaluate_task(frontend: Frontend, config: Config):
        task = get_task(config)
        solutions = get_task_solutions(config, task)
        return evaluate_task(frontend, task, solutions, config)
