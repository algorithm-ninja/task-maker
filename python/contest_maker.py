#!/usr/bin/env python3

import sys

import os
import ruamel.yaml
from task_maker.args import get_parser, UIS
from task_maker.config import Config
from task_maker.detect_format import find_task_dir
from task_maker.formats import Task
from task_maker.manager import get_frontend
from task_maker.task_maker import setup, run, get_task_format
from task_maker.uis.bulk_finish_ui import BulkFinishUI
from typing import List, Tuple


def get_task_paths(config: Config) -> List[str]:
    """
    Get the paths of the tasks that have to be executed
    """
    if config.contest_yaml:
        yaml_dir = os.path.dirname(config.contest_yaml)
        with open(config.contest_yaml) as f:
            yaml = ruamel.yaml.safe_load(f)
        return [os.path.join(yaml_dir, d) for d in yaml.get("tasks", [])]
    return [d.path for d in os.scandir(config.contest_dir) if d.is_dir()]


def make_booklet(config: Config, tasks: List[str]) -> int:
    res = []  # type: List[Tuple[str, Task]]
    task_format = None
    for path in tasks:
        task_dir, fmt = find_task_dir(path, config.max_depth, config.format)
        if not fmt:
            continue
        task_format = get_task_format(fmt)
        config.task_dir = path
        os.chdir(path)
        res.append((path, task_format.get_task(config)))
    if not task_format:
        raise RuntimeError("No valid task found")
    frontend = get_frontend(config)
    return task_format.make_booklet(frontend, config, res)


def bulk_run(config: Config) -> int:
    """
    Run all the tasks using task-maker, will return the exit code to use
    """
    tasks = get_task_paths(config)
    if not tasks:
        raise ValueError("No tasks found")
    if config.make_booklet:
        return make_booklet(config, tasks)
    config.bulk_total = len(tasks)
    finish_ui = BulkFinishUI(config)
    exitcode = 0
    for index, task in enumerate(tasks):
        config.task_dir = task
        config.bulk_number = index
        try:
            if config.ui != UIS.SILENT:
                print("Running task %s [%d / %d]" %
                      (task, config.bulk_number + 1, config.bulk_total))
            ret = run(config)
            if ret.interface:
                finish_ui.add_interface(ret.interface)
            exitcode += ret.exitcode
            if ret.stopped:
                break
        except:
            finish_ui.add_error("Failed to build " + task)
            exitcode += 1

    if config.ui != UIS.SILENT:
        finish_ui.print()
    return exitcode


def main():
    config = Config()
    args = get_parser(True).parse_args()
    config.apply_file()
    config.apply_args(args)
    setup(config)
    sys.exit(bulk_run(config))


if __name__ == '__main__':
    main()
