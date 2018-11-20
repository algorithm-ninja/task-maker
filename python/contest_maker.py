#!/usr/bin/env python3

import ruamel.yaml
from typing import List
import os
import sys

from task_maker.uis.bulk_finish_ui import BulkFinishUI
from task_maker.args import get_parser, UIS
from task_maker.config import Config
from task_maker.task_maker import setup, run


def get_task_paths(config: Config) -> List[str]:
    if config.contest_yaml:
        yaml_dir = os.path.dirname(config.contest_yaml)
        with open(config.contest_yaml) as f:
            yaml = ruamel.yaml.safe_load(f)
        return [os.path.join(yaml_dir, d) for d in yaml.get("tasks", [])]
    return [d.path for d in os.scandir(config.contest_dir) if d.is_dir()]


def bulk_run(config: Config) -> int:
    tasks = get_task_paths(config)
    if not tasks:
        raise ValueError("No tasks found")
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
