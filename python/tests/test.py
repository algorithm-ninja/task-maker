#!/usr/bin/env python3
from task_maker.syspath_patch import patch_sys_path

patch_sys_path()

import os.path
import pytest
import shutil
from typing import Union

from task_maker.args import UIS, CacheMode, get_parser
from task_maker.config import Config
from task_maker.uis.ioi import IOIUIInterface
from task_maker.task_maker import run

interface = None  # type: Union[IOIUIInterface]


def run_tests(task_name, file):
    file = os.path.abspath(file)
    task_dir = "task_" + task_name
    orig_task_dir = os.path.join(os.path.dirname(__file__), task_dir)
    task_path = os.path.join(os.getenv("TEST_TMPDIR", "/tmp"), task_dir)
    if os.path.exists(task_path):
        shutil.rmtree(task_path)
    shutil.copytree(orig_task_dir, task_path)

    os.chdir(task_path)

    parser = get_parser()
    config = Config(parser.parse_args([]))
    config.ui = UIS.SILENT
    config.cache = CacheMode.NOTHING
    config.task_dir = task_path
    config.dry_run = True

    global interface
    interface = run(config)
    raise SystemExit(
        pytest.main([
            os.path.join(os.path.dirname(__file__), "utils.py"), file,
            "--override-ini=python_classes=XXXX", "--verbose", "--color=yes"
        ]))
