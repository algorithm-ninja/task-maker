#!/usr/bin/env python3

from task_maker.syspath_patch import patch_sys_path
patch_sys_path()

import os.path
import shutil
import sys
from typing import List

import pytest

from task_maker.args import UIS
from task_maker.uis.silent_ui import SilentUI
from task_maker.task_maker import main


class TestingUI(SilentUI):
    inst = None

    def __init__(self, solutions: List[str], format: str) -> None:
        super().__init__(solutions, format)
        TestingUI.inst = self
        self.fatal_errors = []  # type: List[str]

    def fatal_error(self, msg: str) -> None:
        self.fatal_errors.append(msg)
        print("FATAL ERROR", msg, file=sys.stderr)


# inject the testing UI to the valid UIs
UIS["testing"] = TestingUI


def run_tests(task_name, file):
    file = os.path.abspath(file)
    task_dir = "task_" + task_name
    orig_task_dir = os.path.join(os.path.dirname(__file__), task_dir)
    task_path = os.path.join(os.getenv("TEST_TMPDIR", "/tmp"), task_dir)
    if os.path.exists(task_path):
        shutil.rmtree(task_path)
    shutil.copytree(orig_task_dir, task_path)

    os.chdir(task_path)

    sys.argv = [
        sys.argv[0], "--ui=testing", "--cache=nothing",
        "--task-dir=" + task_path, "--dry-run"
    ]

    main()
    raise SystemExit(
        pytest.main([
            os.path.join(os.path.dirname(__file__), "utils.py"), file,
            "--override-ini=python_classes=XXXX", "--verbose", "--color=yes"
        ]))
