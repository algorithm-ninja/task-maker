#!/usr/bin/env python3

import os.path
import signal
from typing import Any, Union

from task_maker.args import get_parser, TaskFormat
from task_maker.config import Config
from task_maker.detect_format import find_task_dir
from task_maker.formats import ioi_format, tm_format, terry_format
from task_maker.help import check_help
from task_maker.languages import LanguageManager
from task_maker.manager import get_frontend, spawn_server, spawn_worker
from task_maker.uis.ioi import IOIUIInterface
from task_maker.uis.terry import TerryUIInterface


def get_task_format(fmt: TaskFormat):
    if fmt == TaskFormat.IOI:
        return ioi_format.IOIFormat
    elif fmt == TaskFormat.TM:
        return tm_format.TMFormat
    elif fmt == TaskFormat.TERRY:
        return terry_format.TerryFormat
    raise ValueError("Format %s not supported" % fmt)


def setup(config: Config):
    check_help(config)
    if config.run_server:
        return spawn_server(config)
    if config.run_worker:
        return spawn_worker(config)

    LanguageManager.load_languages()


def run(config: Config) -> Union[None, IOIUIInterface, TerryUIInterface]:
    task_dir, fmt = find_task_dir(config.task_dir, config.max_depth,
                                     config.format)
    if not fmt:
        raise ValueError(
            "Cannot detect format! It's probable that the task is ill-formed")
    task_format = get_task_format(fmt)

    os.chdir(task_dir)

    if config.clean:
        task_format.clean()
        return None

    frontend = get_frontend(config)

    def stop_server(signum: int, _: Any) -> None:
        frontend.stopEvaluation()

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)

    return task_format.evaluate_task(frontend, config)


def main():
    config = Config()
    args = get_parser().parse_args()
    config.apply_file()
    config.apply_args(args)
    setup(config)
    run(config)


if __name__ == '__main__':
    main()
