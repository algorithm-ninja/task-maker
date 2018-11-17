#!/usr/bin/env python3

import os.path
import pytest
import shutil
import sys
from typing import Union

from task_maker.args import UIS, CacheMode
from task_maker.config import Config
from task_maker.uis.ioi import IOIUIInterface
from task_maker.task_maker import run, setup

interface = None  # type: Union[IOIUIInterface]


def run_tests(task_name, file):
    file = os.path.abspath(file)
    task_dir = "task_" + task_name
    orig_task_dir = os.path.join(os.path.dirname(__file__), task_dir)
    temp_dir = os.getenv("TEST_TMPDIR", "/tmp/task-maker")
    task_path = os.path.join(temp_dir, task_dir)
    if os.path.exists(task_path):
        shutil.rmtree(task_path)
    os.makedirs(temp_dir, exist_ok=True)
    shutil.copytree(orig_task_dir, task_path)

    os.chdir(task_path)

    config = Config()
    config.ui = UIS.SILENT
    config.cache = CacheMode.NOTHING
    config.task_dir = task_path
    config.dry_run = True
    config.server_args = \
        "--store-dir='{}/files' " \
        "--temp-dir='{}/temp' " \
        "--pidfile='{}/server.pid' " \
        "--port=7070".format(temp_dir, temp_dir, temp_dir)
    config.worker_args = \
        "--store-dir='{}/files' " \
        "--temp-dir='{}/temp' " \
        "--pidfile='{}/worker.pid' " \
        "--name=local " \
        "--server=127.0.0.1:7070".format(temp_dir, temp_dir, temp_dir)
    global interface
    setup(config)
    interface = run(config)
    exitcode = pytest.main([
        os.path.join(os.path.dirname(__file__), "utils.py"), file,
        "--override-ini=python_classes=XXXX", "--verbose", "--color=yes"
    ])

    try:
        with open(temp_dir + "/server.pid") as f:
            pid = int(f.read())
            os.kill(pid, 9)
    except:
        print("Failed to kill the server", file=sys.stderr)
    try:
        with open(temp_dir + "/worker.pid") as f:
            pid = int(f.read())
            os.kill(pid, 9)
    except:
        print("Failed to kill the worker", file=sys.stderr)

    if os.path.exists(task_path):
        shutil.rmtree(task_path)

    raise SystemExit(exitcode)
