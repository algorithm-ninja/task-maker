#!/usr/bin/env python3
import argparse
import glob
import os.path
import platform
import random

from manager_pb2 import EvaluateTerryTaskRequest, TerrySolution
from task_pb2 import TerryTask, DEFAULT, X86_64, I686

from task_maker.absolutize import absolutize_source_file, absolutize_path
from task_maker.ioi_format import parse_task_yaml, get_options, list_files
from task_maker.source_file import from_file


def get_extension(target_arch=DEFAULT):
    if target_arch == DEFAULT:
        return "." + platform.system().lower() + "." + platform.machine()
    elif target_arch == X86_64:
        return "." + platform.system().lower() + ".x86_64"
    elif target_arch == I686:
        return "." + platform.system().lower() + ".i686"
    else:
        raise ValueError("Unsupported architecture")


def create_task_from_yaml(data):
    name = get_options(data, ["name", "nome_breve"])
    title = get_options(data, ["description", "nome"])
    max_score = get_options(data, ["max_score"])
    if name is None:
        raise ValueError("The name is not set in the yaml")
    if title is None:
        raise ValueError("The title is not set in the yaml")

    task = TerryTask()
    task.name = name
    task.title = title
    task.max_score = max_score
    return task


def get_manager(manager, target_arch, optional=False):
    managers = list_files(
        ["managers/%s.*" % manager], exclude=["managers/%s.*.*" % manager])
    if len(managers) == 0:
        if not optional:
            raise FileNotFoundError("Missing manager: %s" % manager)
        return None
    if len(managers) != 1:
        raise ValueError("Ambiguous manager: " + ", ".join(managers))
    return from_file(managers[0], "managers/%s%s" %
                     (manager, get_extension(target_arch)), target_arch)


def get_request(args: argparse.Namespace):
    data = parse_task_yaml()
    if not data:
        raise RuntimeError("The task.yaml is not valid")

    task = create_task_from_yaml(data)

    task.generator.CopyFrom(get_manager("generator", args.arch))
    absolutize_source_file(task.generator)

    validator = get_manager("validator", args.arch, optional=True)
    if validator:
        task.validator.CopyFrom(validator)
        absolutize_source_file(task.validator)

    task.checker.CopyFrom(get_manager("checker", args.arch))
    absolutize_source_file(task.checker)

    solution = get_manager("solution", args.arch, optional=True)
    if solution:
        task.solution.CopyFrom(solution)
        absolutize_source_file(task.solution)

    if args.solutions:
        solutions = [
            sol if sol.startswith("solutions/") else "solutions/" + sol
            for sol in args.solutions
        ]
    else:
        solutions = list_files(
            ["solutions/*"], exclude=["solutions/__init__.py"])

    request = EvaluateTerryTaskRequest()
    request.task.CopyFrom(task)
    copy_compiled = args.copy_exe
    for solution in solutions:
        path, ext = os.path.splitext(os.path.basename(solution))
        bin_file = copy_compiled and "bin/" + path + "_" + ext[1:]
        source_file = from_file(solution, bin_file)
        absolutize_source_file(source_file)
        terry_solution = TerrySolution()
        terry_solution.solution.CopyFrom(source_file)
        if args.seed:
            terry_solution.seed = args.seed
        else:
            terry_solution.seed = random.randint(0, 2**32 - 1)
        request.solutions.extend([terry_solution])
    request.store_dir = absolutize_path(args.store_dir)
    request.temp_dir = absolutize_path(args.temp_dir)
    request.cache_mode = args.cache
    if args.num_cores:
        request.num_cores = args.num_cores
    request.dry_run = args.dry_run
    if args.evaluate_on:
        request.evaluate_on = args.evaluate_on
    request.keep_sandbox = args.keep_sandbox
    request.exclusive = args.exclusive
    return request


def clean():
    def remove_file(path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass

    for manager in glob.glob("managers/*.linux.*"):
        remove_file(manager)
