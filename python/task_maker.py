#!/usr/bin/env python3

import sys
from collections import namedtuple

import os.path
from task_maker.args import get_parser, TaskFormat
from task_maker.config import Config
from task_maker.detect_format import find_task_dir
from task_maker.formats import ioi_format, tm_format, terry_format
from task_maker.help import check_help
from task_maker.languages import LanguageManager
from task_maker.manager import get_frontend, spawn_server, spawn_worker, stop

MainRet = namedtuple("MainRet", ["exitcode", "interface", "stopped"])


def get_task_format(fmt: TaskFormat):
    """
    Get the format class based on the format of the task.
    """
    if fmt == TaskFormat.IOI:
        return ioi_format.IOIFormat
    elif fmt == TaskFormat.TM:
        return tm_format.TMFormat
    elif fmt == TaskFormat.TERRY:
        return terry_format.TerryFormat
    raise ValueError("Format %s not supported" % fmt)


def setup(config: Config):
    """
    This function has to be called as soon as possible and exactly once to setup
    the system.
    """
    check_help(config)
    if config.run_server:
        return spawn_server(config)
    if config.run_worker:
        return spawn_worker(config)

    LanguageManager.load_languages()


def run(config: Config) -> MainRet:
    """
    Execute task-maker on the given configuration.
    """
    if config.stop:
        stop()
        return MainRet(exitcode=0, interface=None, stopped=True)
    task_dir, fmt = find_task_dir(config.task_dir, config.max_depth,
                                  config.format)
    config.task_dir = task_dir
    if not fmt:
        raise ValueError(
            "Cannot detect format! It's probable that the task is ill-formed")
    task_format = get_task_format(fmt)

    os.chdir(task_dir)

    if config.clean:
        task_format.clean()
        return MainRet(exitcode=0, interface=None, stopped=False)
    if config.task_info:
        task_format.task_info(config)
        return MainRet(exitcode=0, interface=None, stopped=False)
    if config.fuzz_checker:
        ret = task_format.fuzz_checker(config)
        return MainRet(exitcode=ret, interface=None, stopped=True)

    frontend = get_frontend(config)

    interface = task_format.evaluate_task(frontend, config)
    return MainRet(
        exitcode=len(interface.errors),
        interface=interface,
        stopped=interface.pool.stopped)


def main():
    config = Config()
    args = get_parser(False).parse_args()
    config.apply_file()
    config.apply_args(args)
    setup(config)
    sys.exit(run(config).exitcode)


if __name__ == '__main__':
    main()
