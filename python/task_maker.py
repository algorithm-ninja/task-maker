#!/usr/bin/env python3

# enable discovery of capnp folder and installed venv
from task_maker.syspath_patch import patch_sys_path
from task_maker.uis.ioi import IOIUIInterface

patch_sys_path()  # noqa

import os.path
import signal
from typing import Any, Union

from task_maker.args import get_parser, TaskFormat
from task_maker.config import Config
from task_maker.detect_format import find_task_dir
from task_maker.formats import ioi_format, tm_format, terry_format
from task_maker.languages import LanguageManager
from task_maker.manager import get_frontend, spawn_server, spawn_worker


def run(config: Config) -> Union[None, IOIUIInterface]:
    if config.run_server:
        return spawn_server(config)
    if config.run_worker:
        return spawn_worker(config)

    LanguageManager.load_languages()
    task_dir, format = find_task_dir(config.task_dir, config.max_depth,
                                     config.format)
    if not format:
        raise ValueError(
            "Cannot detect format! It's probable that the task is ill-formed")

    os.chdir(task_dir)

    if config.clean:
        if format == TaskFormat.IOI:
            ioi_format.clean()
        elif format == TaskFormat.TM:
            tm_format.clean()
        elif format == "terry":
            terry_format.clean()
        else:
            raise ValueError("Format %s not supported" % format)
        return None

    frontend = get_frontend(config)

    def stop_server(signum: int, _: Any) -> None:
        frontend.stopEvaluation()

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)

    if format == TaskFormat.IOI:
        task, solutions = ioi_format.get_request(config)
        return ioi_format.evaluate_task(frontend, task, solutions, config)
    elif format == TaskFormat.TM:
        task, solutions = tm_format.get_request(config)
        return ioi_format.evaluate_task(frontend, task, solutions, config)
    elif format == TaskFormat.TERRY:
        task, solutions = terry_format.get_request(config)
        return terry_format.evaluate_task(frontend, task, solutions, config)
    else:
        raise ValueError("Format %s not supported" % format)


def main():
    config = Config(get_parser().parse_args())
    run(config)


if __name__ == '__main__':
    main()
