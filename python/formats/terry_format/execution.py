#!/usr/bin/env python3
import random
from task_maker.args import CacheMode, UIS
from task_maker.config import Config
from task_maker.formats import TerryTask
from task_maker.remote import ExecutionPool, Execution
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import Frontend, Resources
from task_maker.uis.terry import TerryUIInterface
from task_maker.uis.terry_curses_ui import TerryCursesUI
from task_maker.uis.terry_finish_ui import TerryFinishUI
from task_maker.uis.terry_finish_ui_json import TerryFinishUIJSON
from typing import List


def evaluate_task(frontend: Frontend, task: TerryTask,
                  solutions: List[SourceFile],
                  config: Config) -> TerryUIInterface:
    """
    Build the computation DAG and run it in order to test all the solutions.
    """
    ui_interface = TerryUIInterface(
        task, config.ui == UIS.PRINT or config.ui == UIS.JSON,
              config.ui == UIS.JSON)
    pool = ExecutionPool(config, frontend, ui_interface.ui_printer)
    ui_interface.pool = pool
    curses_ui = None
    finish_ui = None
    if config.ui == UIS.CURSES:
        curses_ui = TerryCursesUI(config, ui_interface)
    if config.ui != UIS.SILENT and config.bulk_number is None:
        if config.ui == UIS.JSON:
            finish_ui = TerryFinishUIJSON(config, ui_interface)
        else:
            finish_ui = TerryFinishUI(config, ui_interface)

    with ui_interface.run_in_ui(curses_ui, finish_ui):
        task.generator.prepare(pool)
        ui_interface.add_non_solution(task.generator)
        if task.validator:
            task.validator.prepare(pool)
            ui_interface.add_non_solution(task.validator)
        if task.official_solution:
            task.official_solution.prepare(pool)
            ui_interface.add_non_solution(task.official_solution)
        task.checker.prepare(pool)
        ui_interface.add_non_solution(task.checker)

        for solution in solutions:
            solution.prepare(pool)
            ui_interface.add_solution(solution)
            evaluate_solution(pool, task, solution, ui_interface)

        pool.start()
    return ui_interface


def evaluate_solution(pool: ExecutionPool, task: TerryTask,
                      solution: SourceFile, interface: TerryUIInterface):
    """
    Build the part of the DAG relative of a single solution.
    """
    if pool.config.seed:
        seed = pool.config.seed
    else:
        seed = random.randint(0, 2 ** 31 - 1)
    name = solution.name

    inputs = dict()
    if task.official_solution:
        inputs[task.official_solution.
            exe_name] = task.official_solution.executable
    generation = Execution(
        "Generation of input for solution {} with seed {}".format(name, seed),
        pool,
        task.generator, [str(seed), "0"],
        "terry-generation", {
            "name": solution.name,
            "seed": seed
        },
        inputs=inputs,
        store_stderr=True)
    input = generation.stdout
    interface.add_generation(name, seed, generation)

    inputs = dict()
    if task.validator:
        val_inputs = dict()
        if task.official_solution:
            val_inputs[task.official_solution.
                exe_name] = task.official_solution.executable
        validation = Execution(
            "Validation of input for solution {}".format(name),
            pool,
            task.validator, ["0"],
            "terry-validation", {
                "name": solution.name,
                "seed": seed
            },
            stdin=input,
            inputs=val_inputs,
            store_stderr=True)
        inputs["wait_for_validation"] = validation.stdout
        interface.add_validation(name, validation)

    limits = Resources()
    limits.cpu_time = 20
    limits.wall_time = 30
    limits.memory = 1024*1024
    solving = Execution(
        "Running solution {}".format(name),
        pool,
        solution, [],
        "terry-evaluation", {
            "name": solution.name,
            "seed": seed
        },
        limits=limits,
        cache_on=[CacheMode.ALL],
        can_exclusive=True,
        stdin=input,
        store_stderr=True)
    output = solving.stdout
    interface.add_solving(name, solving)

    inputs = {"input": input, "output": output}
    if task.official_solution:
        inputs[task.official_solution.
            exe_name] = task.official_solution.executable
    checker = Execution(
        "Checking solution {}".format(name),
        pool,
        task.checker, ["input", "output"],
        "terry-checking", {
            "name": solution.name,
            "seed": seed
        },
        inputs=inputs,
        store_stderr=True,
        store_stdout=True)
    interface.add_checking(name, checker)
