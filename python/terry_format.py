#!/usr/bin/env python3
import argparse
import os.path
import platform

from proto.manager_pb2 import EvaluateTerryTaskRequest
from proto.task_pb2 import TerryTask

from python.absolutize import absolutize_source_file, absolutize_path
from python.ioi_format import parse_task_yaml, get_options, list_files
from python.source_file import from_file


def get_extension():
    return "." + platform.system().lower() + "." + platform.machine()


def create_task_from_yaml(data):
    name = get_options(data, ["name", "nome_breve"])
    title = get_options(data, ["description", "nome"])
    if name is None:
        raise ValueError("The name is not set in the yaml")
    if title is None:
        raise ValueError("The title is not set in the yaml")

    task = TerryTask()
    task.name = name
    task.title = title
    return task


def get_manager(manager, optional=False):
    managers = list_files(["managers/%s.*" % manager], exclude=[
        "managers/%s.*.*" % manager])
    if len(managers) == 0:
        if not optional:
            raise FileNotFoundError("Missing manager: %s" % manager)
        return None
    if len(managers) != 1:
        raise ValueError("Ambiguous manager: " + ", ".join(managers))
    return from_file(managers[0], "managers/%s%s" % (manager, get_extension()))


def get_request(args: argparse.Namespace):
    data = parse_task_yaml()
    if not data:
        raise RuntimeError("The task.yaml is not valid")

    task = create_task_from_yaml(data)
    task.generator.CopyFrom(get_manager("generator"))
    absolutize_source_file(task.generator)
    validator = get_manager("validator", optional=True)
    if validator:
        task.validator.CopyFrom(validator)
        absolutize_source_file(task.validator)
    task.checker.CopyFrom(get_manager("checker"))
    absolutize_source_file(task.checker)

    if args.solutions:
        solutions = [
            sol if sol.startswith("solutions/") else "solutions/" + sol
            for sol in args.solutions
        ]
    else:
        solutions = list_files(["solutions/*"])

    request = EvaluateTerryTaskRequest()
    request.task.CopyFrom(task)
    copy_compiled = args.copy_exe
    for solution in solutions:
        bin_file = copy_compiled and "bin/" + \
                   os.path.splitext(os.path.basename(solution))[0]
        source_file = from_file(solution, bin_file)
        absolutize_source_file(source_file)
        request.solutions.extend([source_file])
    request.store_dir = absolutize_path(args.store_dir)
    request.temp_dir = absolutize_path(args.temp_dir)
    request.cache_mode = args.cache
    if args.num_cores:
        request.num_cores = args.num_cores
    request.dry_run = args.dry_run
    if args.evaluate_on:
        request.evaluate_on = args.evaluate_on
    request.keep_sandbox = args.keep_sandbox
    return request
